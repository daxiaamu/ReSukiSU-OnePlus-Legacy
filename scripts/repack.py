"""Replace only the kernel in an explicitly identified stock boot image."""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from check_module_abi import compare
from check_stock_modules import verify as verify_stock_modules
from prepare_protocol import protocol_directory
import tempfile
import urllib.request
import zipfile
from project import ROOT, PATCHES, device, run, save, sha256

def boot_header(path):
    with path.open("rb") as stream:
        data = stream.read(44)
    if len(data) != 44 or data[:8] != b"ANDROID!":
        raise ValueError("Not a supported Android boot image")
    return int.from_bytes(data[40:44], "little")

def repack(args):
    data = device(args.device)
    known = data["firmware"][args.os]["layout"]
    if known != "unverified" and args.layout != known:
        raise ValueError("Partition layout conflicts with the device profile")
    if not re.fullmatch(r"[A-Za-z0-9._()-]+", args.firmware):
        raise ValueError("Firmware ID may only contain letters, digits, dot, dash, underscore and parentheses")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.stock_sha256):
        raise ValueError("A full stock boot SHA-256 is required")
    stock = args.stock.resolve()
    if sha256(stock) != args.stock_sha256.lower():
        raise ValueError("Stock boot checksum mismatch")
    original_version = boot_header(stock)
    registered = data["firmware"][args.os]
    if args.firmware != registered["build_id"] or args.stock_sha256.lower() != registered["stock_boot_sha256"]:
        raise ValueError("Stock firmware is not the registered image for this model and OS")
    built = ROOT / "out" / args.device / args.os
    manifest = json.loads((built / "build.json").read_text(encoding="utf-8"))
    if manifest["device"] != args.device or manifest["os"] != args.os or not manifest["compile_verified"]:
        raise ValueError("No matching successful build")
    if any(manifest.get(key) != data[key] for key in ("kernel", "resukisu", "vendor")):
        raise ValueError("Stale build: source profile changed")
    vendor_name = {"oneplus-8-pro": "oneplus-8", "oneplus-9-pro": "oneplus-9"}.get(args.device, args.device)
    expected_patches = {
        "patch_sha256": ROOT / "patches" / (PATCHES[args.device] + ".patch"),
        "vendor_patch_sha256": ROOT / "patches" / ("vendor-" + vendor_name + ".patch"),
        "compat_patch_sha256": ROOT / "patches" / ("compat-" + data["platform"] + ".patch"),
    }
    for key, patch in expected_patches.items():
        expected = sha256(patch) if patch.exists() else None
        if manifest.get(key) != expected:
            raise ValueError("Stale build: patch changed: " + key)
    if manifest["firmware"] != args.firmware:
        raise ValueError("Build targets another firmware")
    if sha256(built / "Image") != manifest["image_sha256"]:
        raise ValueError("Compiled kernel checksum mismatch")
    if manifest["kernel_release"] != registered["kernel_release"]:
        raise ValueError("Kernel release differs from stock; module compatibility requires review")
    if sha256(built / "kernel.config") != manifest["config_sha256"]:
        raise ValueError("Compiled config checksum mismatch")
    protocol = manifest.get("stock_protocol") or {}
    directory = protocol_directory(data)
    for key, filename in (("schema_sha256", "netlink_msg.proto"),
                          ("reflection_sha256", "protocol-reflection.json")):
        if protocol.get(key) != sha256(directory / filename):
            raise ValueError("Stale build: stock protocol changed")
    if data["platform"] == "sm8350":
        if protocol.get("cfi_safe_initializers") is not True:
            raise ValueError("Build lacks CFI-safe protobuf initializer callbacks")
        final_config = (built / "kernel.config").read_text().splitlines()
        for required in ("CONFIG_OPLUS_FINGERPRINT_COMMON=y", "CONFIG_CFI_CLANG=y"):
            if required not in final_config:
                raise ValueError("Required stock interface/config missing: " + required)
    tools = json.loads((ROOT / "tools.lock.json").read_text())["magiskboot"]
    dest = ROOT / "out" / args.device / (args.os + "-" + args.firmware)
    if dest.exists():
        raise ValueError("Refusing to overwrite an existing firmware artifact directory")
    with tempfile.TemporaryDirectory() as temp:
        work = pathlib.Path(temp)
        apk = work / "magisk.apk"
        cached = ROOT / ".work/tools/Magisk-v30.7.apk"
        if cached.is_file() and sha256(cached) == tools["sha256"]:
            shutil.copyfile(cached, apk)
        else:
            urllib.request.urlretrieve(tools["url"], apk)
        if sha256(apk) != tools["sha256"]:
            raise ValueError("Magisk tool checksum mismatch")
        with zipfile.ZipFile(apk) as archive:
            binary = work / "magiskboot"
            binary.write_bytes(archive.read(tools["member"]))
        binary.chmod(0o755)
        original, verify = work / "original", work / "verify"
        original.mkdir()
        verify.mkdir()
        run(binary, "unpack", "-h", stock, cwd=original)
        abi_path = built / "abi-report.json"
        if not abi_path.is_file():
            stock_map = work / "stock.map"
            with stock_map.open("wb") as stream:
                subprocess.run([sys.executable, str(ROOT / "scripts/recover_symbols.py"),
                                str(original / "kernel")], stdout=stream, check=True)
            compare(original / "kernel", stock_map, built, abi_path)
        abi = json.loads(abi_path.read_text())
        if abi.get("image_sha256") != manifest["image_sha256"]:
            raise ValueError("Export CRC check failed or belongs to another kernel")
        if abi.get("system_map_sha256") != sha256(built / "System.map"):
            raise ValueError("ABI report symbol map changed")
        if abi.get("stock_kernel_sha256") != sha256(original / "kernel"):
            raise ValueError("ABI report targets a different stock kernel")
        module_check = None
        if not abi.get("passed"):
            # These two callbacks use a private, internally compiled touchpanel_data.
            # Accept a changed private type only after verifying the actual ROM modules.
            private_callbacks = {"preconfig_power_control", "reconfig_power_control"}
            differences = set(abi.get("mismatch", {}))
            if data["platform"] != "sm8250" or abi.get("missing") or not differences or not differences <= private_callbacks:
                raise ValueError("Unresolved stock export ABI differences")
            inventory = stock.parent / "module-inventory.json"
            module_check = verify_stock_modules(inventory, built, original / "kernel",
                                                stock.parent / "stock.map", stock)
            if not module_check["passed"] or differences & set(module_check["required_kernel_symbols"]):
                raise ValueError("Original ROM modules require the changed interfaces")
            module_check["unused_private_export_differences"] = sorted(differences)
        preserved = {p.name: sha256(p) for p in original.iterdir()
                     if p.is_file() and p.name not in ("kernel", "header")}
        if "ramdisk.cpio" not in preserved:
            raise ValueError("Stock boot has no ramdisk; this recipe requires review")
        shutil.copyfile(built / "Image", original / "kernel")
        candidate = work / "boot.img"
        run(binary, "repack", stock, candidate, cwd=original)
        if boot_header(candidate) != original_version:
            raise ValueError("Boot header version changed")
        if candidate.stat().st_size > stock.stat().st_size:
            raise ValueError("New image exceeds stock image size; partition size must be reviewed")
        run(binary, "unpack", "-h", candidate, cwd=verify)
        actual = {p.name: sha256(p) for p in verify.iterdir()
                  if p.is_file() and p.name not in ("kernel", "header")}
        if (original / "header").read_bytes() != (verify / "header").read_bytes():
            raise ValueError("Boot command line or OS header fields changed")
        if actual != preserved:
            raise ValueError("Repack changed ramdisk, DTB or another non-kernel component")
        if sha256(verify / "kernel") != manifest["image_sha256"]:
            raise ValueError("Repacked kernel does not match the compiled image")
        dest.mkdir(parents=True)
        shutil.copyfile(candidate, dest / "boot.img")
    manifest.update({"os": args.os, "firmware": args.firmware, "partition_layout": args.layout,
        "stock_boot_sha256": args.stock_sha256.lower(), "boot_sha256": sha256(dest / "boot.img"),
        "boot_header_version": original_version, "magiskboot": tools, "export_crc_check": abi, "module_crc_check": module_check, "abi_compatible": True, "device_verified": False})
    save(dest / "build.json", manifest)
    (dest / "SHA256SUMS").write_text(manifest["boot_sha256"] + "  boot.img\n", encoding="utf-8")
    print("Created experimental boot.img:", dest)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True, choices=list(PATCHES))
    parser.add_argument("--os", required=True, choices=("coloros", "oxygenos"))
    parser.add_argument("--layout", required=True, choices=("a-only", "a/b"))
    parser.add_argument("--firmware", required=True)
    parser.add_argument("--stock", required=True, type=pathlib.Path)
    parser.add_argument("--stock-sha256", required=True)
    repack(parser.parse_args())

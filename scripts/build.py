"""Experimental Linux compile; a successful compile is not device validation."""
import argparse
import datetime
import os
import pathlib
import re
import shutil
import subprocess
from toolchain import configure
from prepare_protocol import prepare
from project import ROOT, PATCHES, device, run, save, sha256

def checkout(repo, commit, dest, shallow=True):
    run("git", "init", "--quiet", dest)
    run("git", "remote", "add", "origin", "https://github.com/" + repo + ".git", cwd=dest)
    command = ["git", "fetch", "--no-tags"]
    if shallow:
        command += ["--depth=1"]
    run(*command, "origin", commit, cwd=dest)
    run("git", "checkout", "--detach", "FETCH_HEAD", cwd=dest)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
    if actual != commit:
        raise ValueError("Source commit mismatch")

def build(name, config=None, rom='coloros'):
    if os.name != "posix":
        raise RuntimeError("Build on Linux (GitHub Actions or WSL)")
    data = device(name)
    firmware = data["firmware"][rom]
    compiler_lock = configure(data["platform"])
    stock_config = config is None
    if config is None:
        if not firmware.get("config"):
            raise RuntimeError("No verified stock config for " + name + "/" + rom)
        config = ROOT / firmware["config"]
        if sha256(config) != firmware["config_sha256"]:
            raise ValueError("Registered stock config checksum mismatch")
    for program in ("git", "make", "clang", "ld.lld", "aarch64-linux-gnu-gcc", "arm-linux-gnueabi-gcc"):
        if not shutil.which(program):
            raise RuntimeError("Missing build dependency: " + program)
    work = ROOT / ".work" / (name + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    work.mkdir(parents=True, exist_ok=False)
    source, output = work / "kernel" / ("msm-" + ".".join(data["kernel"]["version"].split(".")[:2])), work / "obj"
    checkout(data["kernel"]["repository"], data["kernel"]["commit"], source)
    modules = work / "modules"
    checkout(data["vendor"]["repository"], data["vendor"]["commit"], modules)
    vendor_patch = ROOT / "patches" / ("vendor-" + {"oneplus-8-pro": "oneplus-8", "oneplus-9-pro": "oneplus-9"}.get(name, name) + ".patch")
    if vendor_patch.exists():
        run("git", "apply", "--check", vendor_patch, cwd=modules)
        run("git", "apply", vendor_patch, cwd=modules)
    protocol = prepare(modules) if data["platform"] == "sm8350" else None
    (work / "vendor").symlink_to(modules / "vendor", target_is_directory=True)
    overlay = modules / "kernel" / source.name
    for item in overlay.rglob("*"):
        if item.is_dir() and not item.is_symlink():
            continue
        target = source / item.relative_to(overlay)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if item.is_symlink() and target.is_symlink() and os.readlink(item) == os.readlink(target):
                continue
            if not item.is_symlink() and not target.is_symlink() and sha256(item) == sha256(target):
                continue
            raise RuntimeError("Vendor overlay conflicts with kernel source: " + str(target))
        if item.is_symlink():
            target.symlink_to(os.readlink(item))
        else:
            shutil.copyfile(item, target)
    patch = ROOT / "patches" / (PATCHES[name] + ".patch")
    run("git", "apply", "--check", patch, cwd=source)
    run("git", "apply", patch, cwd=source)
    compat_patch = ROOT / "patches" / ("compat-" + data["platform"] + ".patch")
    if compat_patch.exists():
        run("git", "apply", "--check", compat_patch, cwd=source)
        run("git", "apply", compat_patch, cwd=source)
    checkout(data["resukisu"]["repository"], data["resukisu"]["commit"], source / "KernelSU", False)
    (source / "drivers/kernelsu").symlink_to("../KernelSU/kernel", target_is_directory=True)
    for path, addition in (
        ("drivers/Makefile", "\nobj-$(CONFIG_KSU) += kernelsu/\n"),
        ("drivers/Kconfig", '\nsource "drivers/kernelsu/Kconfig"\n'),
    ):
        with (source / path).open("a", encoding="utf-8") as stream:
            stream.write(addition)
    output.mkdir()
    env = dict(os.environ, ARCH="arm64", SUBARCH="arm64")
    native_features = {}
    if data["platform"] == "sm8250":
        # Android normally exports these variables to every recursive make.
        # Reading the include in the top-level make alone does not export them.
        feature_file = source / "oplus_native_features.mk"
        for line in feature_file.read_text().splitlines():
            match = re.fullmatch(r"([A-Z][A-Z0-9_]*)=(.*)", line.strip())
            if match:
                native_features[match[1]] = match[2]
        if not native_features:
            raise ValueError("Official native feature assignments are missing")
        env.update(native_features)
    linker = "aarch64-linux-gnu-ld" if data["platform"] == "sm8250" else "ld.lld"
    # Preserve module release string; provenance records the real source commits.
    release = firmware.get("kernel_release")
    if release:
        if not release.startswith(data["kernel"]["version"]):
            raise RuntimeError("Stock kernel version differs from source baseline")
        (source / ".scmversion").write_text("", encoding="utf-8")

    options = ["make", "-C", str(source), "O=" + str(output), "ARCH=arm64",
               "CC=clang", "LD=" + linker, "AR=llvm-ar", "NM=llvm-nm",
               "OBJCOPY=" + ("aarch64-linux-gnu-objcopy" if data["platform"] == "sm8250" else "llvm-objcopy"), "OBJDUMP=llvm-objdump", "STRIP=llvm-strip",
               "CLANG_TRIPLE=aarch64-linux-gnu-", "CROSS_COMPILE=aarch64-linux-gnu-",
               "CROSS_COMPILE_ARM32=arm-linux-gnueabi-"]
    options += ["OPLUS_FEATURE_SECURE_GUARD=" + ("yes" if data["platform"] == "sm8250" else "no"), "OPLUS_FEATURE_SECURE_ROOTGUARD=no",
                "OPLUS_FEATURE_SECURE_MOUNTGUARD=no", "OPLUS_FEATURE_SECURE_EXECGUARD=no",
                "OPLUS_FEATURE_SECURE_KEYINTERFACESGUARD=no"]
    if data["platform"] == "sm8250":
        options += ["KCFLAGS=-gdwarf-4"]
    if config:
        shutil.copyfile(config, output / ".config")
    else:
        target = data["kernel"]["defconfig"]
        if data["platform"] == "sm8350":
            target = "vendor/lahaina-qgki_defconfig"
            run("bash", "scripts/gki/generate_defconfig.sh", target, cwd=source, env=env)
        run(*options, target, env=env)
    translations = {}
    if data["platform"] == "sm8350":
        stock_lines = (output / ".config").read_text().splitlines()
        for line in stock_lines:
            if line.startswith("CONFIG_OPPO_FINGERPRINT") and "=" in line:
                key, value = line.split("=", 1)
                translations[key] = key.replace("CONFIG_OPPO_", "CONFIG_OPLUS_", 1)
                with (output / ".config").open("a") as stream:
                    stream.write(translations[key] + "=" + value + "\n")
    fragment = (ROOT / "configs/resukisu.config").read_text(encoding="utf-8")
    with (output / ".config").open("a", encoding="utf-8") as stream:
        stream.write("\n" + fragment)
        if release:
            stream.write('CONFIG_LOCALVERSION="' + release[len(data["kernel"]["version"]):] + '"\n')
            stream.write("# CONFIG_LOCALVERSION_AUTO is not set\n")

    run(*options, "olddefconfig", env=env)
    final_config = (output / ".config").read_text()
    for required in ("CONFIG_KSU=y", "CONFIG_KSU_MANUAL_HOOK=y", "CONFIG_KALLSYMS_ALL=y"):
        if required not in final_config.splitlines():
            raise RuntimeError("Kconfig dropped required option: " + required)
    run(*options, "-j" + str(os.cpu_count() or 2), "Image", env=env)
    image = output / "arch/arm64/boot/Image"
    if not image.is_file() or image.stat().st_size < 1024:
        raise RuntimeError("Kernel image missing")
    dest = ROOT / "out" / name / rom
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, dest / "Image")
    shutil.copyfile(output / ".config", dest / "kernel.config")
    for diagnostic in ("Module.symvers", "System.map"):
        if (output / diagnostic).is_file():
            shutil.copyfile(output / diagnostic, dest / diagnostic)
    compiler = subprocess.check_output(["clang", "--version"], text=True)
    save(dest / "build.json", {"device": name, "os": rom, "firmware": firmware["build_id"], "kernel_release": (output / "include/config/kernel.release").read_text().strip(), "kernel": data["kernel"], "resukisu": data["resukisu"],
        "compat_patch_sha256": sha256(compat_patch) if compat_patch.exists() else None, "vendor_patch_sha256": sha256(vendor_patch) if vendor_patch.exists() else None, "vendor": data["vendor"], "patch_sha256": sha256(patch), "image_sha256": sha256(image), "compiler": compiler, "compiler_lock": compiler_lock, "stock_protocol": protocol, "linker": subprocess.check_output([linker, "--version"], text=True).splitlines()[0], "native_features": native_features,
        "config_sha256": sha256(output / ".config"), "stock_config_supplied": stock_config, "config_translations": translations,
        "compile_verified": True, "device_verified": False})
    print("Compile complete; boot packaging and on-device checks remain.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True, choices=list(PATCHES))
    parser.add_argument("--os", choices=("coloros", "oxygenos"), default="coloros")
    parser.add_argument("--config", type=pathlib.Path, help="Uncompressed config from the matching stock kernel")
    args = parser.parse_args()
    build(args.device, args.config, args.os)

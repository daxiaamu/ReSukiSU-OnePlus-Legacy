"""Preserve stock module signing trust without disabling signature enforcement."""
import base64
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import tempfile
from project import ROOT, sha256

MARKER = b"~Module signature appended~\n"

def certificates(image, symbol_map):
    symbols = {}
    for line in symbol_map.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            symbols[fields[2]] = int(fields[0], 16)
    raw = image.read_bytes()
    base = symbols["_text"]
    offset = symbols["system_certificate_list"] - base
    size_offset = symbols["system_certificate_list_size"] - base
    if not (0 <= offset < len(raw) and 0 <= size_offset <= len(raw) - 8):
        raise ValueError("Invalid certificate symbol bounds")
    size = struct.unpack_from("<Q", raw, size_offset)[0]
    if not 0 < size <= min(1048576, len(raw) - offset):
        raise ValueError("Invalid certificate list size")
    data = raw[offset:offset + size]
    result = []
    while data:
        if data[0] != 0x30 or len(data) < 2:
            raise ValueError("Invalid DER certificate")
        count = data[1] & 0x7f
        if data[1] & 0x80:
            if count == 0 or count > 4 or len(data) < count + 2:
                raise ValueError("Invalid DER length")
            length = 2 + count + int.from_bytes(data[2:2 + count], "big")
        else:
            length = 2 + count
        if length > len(data):
            raise ValueError("Truncated certificate")
        result.append(data[:length])
        data = data[length:]
    return result

def pem(certificates):
    return b"".join(b"-----BEGIN CERTIFICATE-----\n" + base64.encodebytes(cert)
                    + b"-----END CERTIFICATE-----\n" for cert in certificates)

def configured(firmware):
    entries = firmware.get("trusted_module_certificates", [])
    for entry in entries:
        path = ROOT / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise ValueError("Stock module certificate changed: " + str(path))
    return entries

def install(firmware, source):
    entries = configured(firmware)
    if not entries:
        return None
    target = source / "certs/stock-trusted.pem"
    target.write_bytes(b"".join((ROOT / item["path"]).read_bytes() for item in entries))
    return {"certificates": entries, "enforcement": True,
            "source_boot_sha256": firmware["stock_boot_sha256"]}

def verify_embedded(firmware, built):
    config = (built / "kernel.config").read_text().splitlines()
    stock_config = (ROOT / firmware["config"]).read_text().splitlines()
    expected_force = "CONFIG_MODULE_SIG_FORCE=y" in stock_config
    actual_force = "CONFIG_MODULE_SIG_FORCE=y" in config
    if expected_force != actual_force:
        raise ValueError("Module signature enforcement differs from original firmware")
    if not expected_force:
        return {"enforcement": False, "passed": True, "reason": "original firmware does not force module signatures"}
    entries = configured(firmware)
    if not entries:
        raise ValueError("Forced module signatures require registered stock trust anchors")
    actual = {hashlib.sha256(cert).hexdigest()
              for cert in certificates(built / "Image", built / "System.map")}
    expected = {item["der_sha256"] for item in entries}
    if not expected <= actual:
        raise ValueError("Compiled kernel does not trust original module signing certificates")
    return {"passed": True, "enforcement": True,
            "trusted_certificate_sha256": sorted(expected)}

def verify_modules(firmware, built, inventory_path):
    result = verify_embedded(firmware, built)
    if not result["passed"]:
        raise ValueError("Module signature enforcement was disabled")
    # Module inventory layout is intentionally not assumed; the verified module
    # directory is adjacent to the inventory and hashes are checked by the ABI audit.
    modules = sorted((inventory_path.parent / "module-set").rglob("*.ko"))
    if not modules:
        raise ValueError("No original modules available for signature verification")
    if not shutil.which("openssl"):
        raise RuntimeError("openssl is required to verify original module signatures")
    with tempfile.TemporaryDirectory() as temp:
        work = pathlib.Path(temp)
        trust = work / "stock.pem"
        trust.write_bytes(b"".join((ROOT / item["path"]).read_bytes()
                                  for item in configured(firmware)))
        checked = []
        for module in modules:
            raw = module.read_bytes()
            if not raw.endswith(MARKER) or len(raw) < len(MARKER) + 12:
                raise ValueError("Unsigned original module: " + str(module))
            end = len(raw) - len(MARKER) - 12
            info = raw[end:end + 12]
            length = int.from_bytes(info[8:12], "big")
            if info[2] != 2 or info[3] or info[4] or not 0 < length <= end:
                raise ValueError("Unsupported module signature: " + str(module))
            signature, content = work / "signature.der", work / "content.bin"
            signature.write_bytes(raw[end - length:end])
            content.write_bytes(raw[:end - length])
            # -nointern forces the signer to come from the pinned stock certificate.
            # -noverify skips CA/time policy, as Linux module trust does; the detached
            # content signature is still cryptographically verified.
            p = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER",
                                "-in", str(signature), "-content", str(content),
                                "-certfile", str(trust), "-nointern", "-noverify",
                                "-out", str(work / "verified.bin")],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode:
                raise ValueError("Original module signature rejected: " + str(module)
                                 + ": " + p.stderr.decode(errors="replace"))
            checked.append({"path": module.relative_to(inventory_path.parent).as_posix(),
                            "sha256": sha256(module)})
    result["modules"] = checked
    result["module_count"] = len(checked)
    return result

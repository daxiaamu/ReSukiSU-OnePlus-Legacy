"""Reuse a compile only when both OS profiles have identical verified inputs."""
import argparse
import json
import shutil
from project import ROOT, PATCHES, device, sha256, save

def reuse(name, source_os, target_os):
    if source_os == target_os:
        raise ValueError("Source and target OS must differ")
    profile = device(name)
    source, target = profile["firmware"][source_os], profile["firmware"][target_os]
    for firmware in (source, target):
        if not firmware.get("verified_from_stock_image") or not firmware.get("config"):
            raise ValueError("Both OS profiles require verified stock images and configs")
        if sha256(ROOT / firmware["config"]) != firmware["config_sha256"]:
            raise ValueError("Stock config checksum mismatch")
    if source["config_sha256"] != target["config_sha256"] or source["kernel_release"] != target["kernel_release"]:
        raise ValueError("Stock build inputs differ; a separate compile is required")
    built = ROOT / "out" / name / source_os
    manifest = json.loads((built / "build.json").read_text())
    if not manifest["compile_verified"] or not manifest.get("stock_config_supplied"):
        raise ValueError("Reuse requires a successful build using the registered stock config")
    if manifest["device"] != name or manifest["os"] != source_os or manifest["firmware"] != source["build_id"]:
        raise ValueError("Source build identity differs")
    if any(manifest.get(key) != profile[key] for key in ("kernel", "vendor", "resukisu")):
        raise ValueError("Source pins changed")
    if sha256(built / "Image") != manifest["image_sha256"] or sha256(built / "kernel.config") != manifest["config_sha256"]:
        raise ValueError("Compiled artifacts changed")
    if manifest["kernel_release"] != target["kernel_release"]:
        raise ValueError("Compiled release differs from stock")
    destination = ROOT / "out" / name / target_os
    destination.mkdir(parents=True, exist_ok=False)
    for filename in ("Image", "kernel.config", "Module.symvers", "System.map"):
        if (built / filename).exists():
            shutil.copyfile(built / filename, destination / filename)
    manifest.update({"os": target_os, "firmware": target["build_id"],
        "reuse_from": {"os": source_os, "firmware": source["build_id"],
                      "reason": "identical verified stock config and kernel release"},
        "device_verified": False})
    save(destination / "build.json", manifest)
    print(destination)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True, choices=list(PATCHES))
    parser.add_argument("--from-os", required=True, choices=("coloros", "oxygenos"))
    parser.add_argument("--to-os", required=True, choices=("coloros", "oxygenos"))
    args = parser.parse_args()
    reuse(args.device, args.from_os, args.to_os)

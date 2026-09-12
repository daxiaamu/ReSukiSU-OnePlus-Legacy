"""Read a local/UNC official ROM without modifying it; write boot into .work."""
import argparse
import pathlib
import shutil
import tempfile
import zipfile
from project import ROOT, PATCHES, device, run, sha256

def extract(name, rom, source, dumper=None):
    profile = device(name)["firmware"][rom]
    expected = profile.get("stock_boot_sha256")
    if not expected:
        raise ValueError("No verified stock boot registered for this model and OS")
    source = source.resolve(strict=True)
    destination = ROOT / ".work" / "stock" / name / rom
    destination.mkdir(parents=True, exist_ok=True)
    result = destination / "boot.img"
    if result.exists():
        if sha256(result) != expected:
            raise ValueError("Existing boot differs from registered firmware; refusing overwrite")
        return result
    # Temporary output is local even when the source is on a read-only NAS.
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        work = pathlib.Path(temporary)
        candidate = work / "boot.img"
        with zipfile.ZipFile(source, "r") as archive:
            boot = [entry for entry in archive.infolist()
                    if pathlib.PurePosixPath(entry.filename).name == "boot.img"]
            payload = [entry for entry in archive.infolist()
                       if pathlib.PurePosixPath(entry.filename).name == "payload.bin"]
            if len(boot) == 1:
                # Do not use extractall: write the one known partition to a fixed path.
                with archive.open(boot[0], "r") as src, candidate.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
            elif len(boot) > 1:
                raise ValueError("Ambiguous ROM: more than one boot.img")
            elif len(payload) != 1:
                raise ValueError("ROM contains neither one boot.img nor one payload.bin")
        if not candidate.exists():
            if dumper is None:
                raise ValueError("A payload ROM requires --dumper pointing to Payload_Dumper_C executable")
            run(dumper.resolve(strict=True), "-p", "boot", "-o", work, source)
        if sha256(candidate) != expected:
            raise ValueError("Extracted boot is not the registered final firmware image")
        with candidate.open("rb") as src, result.open("xb") as dst:
            shutil.copyfileobj(src, dst)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True, choices=list(PATCHES))
    parser.add_argument("--os", required=True, choices=("coloros", "oxygenos"))
    parser.add_argument("--rom", required=True, type=pathlib.Path)
    parser.add_argument("--dumper", type=pathlib.Path)
    args = parser.parse_args()
    print(extract(args.device, args.os, args.rom, args.dumper))

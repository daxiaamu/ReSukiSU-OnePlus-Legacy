"""Verify every pinned source and patch without claiming a kernel build."""
import argparse
import concurrent.futures
import pathlib
import tempfile
import urllib.request
from make_patches import FILES, transform
from project import ROOT, PATCHES, device, run

def audit(name):
    data = device(name)
    with tempfile.TemporaryDirectory() as temp:
        directory = pathlib.Path(temp)
        patch = ROOT / "patches" / (PATCHES[name] + ".patch")
        paths = [line[6:] for line in patch.read_text().splitlines() if line.startswith("+++ b/")]
        for path in dict.fromkeys(paths):
            url = "https://raw.githubusercontent.com/{}/{}/{}".format(
                data["kernel"]["repository"], data["kernel"]["commit"], path)
            target = directory / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                target.write_bytes(response.read())
        run("git", "init", "--quiet", directory)
        patch = ROOT / "patches" / (PATCHES[name] + ".patch")
        run("git", "apply", "--check", patch, cwd=directory)
        expected = {p: transform(p, (directory / p).read_text(encoding="utf-8")) for p in FILES}
        run("git", "apply", patch, cwd=directory)
        for path in FILES:
            if (directory / path).read_text(encoding="utf-8") != expected[path]:
                raise ValueError("Patch differs from reviewed hooks: " + path)
    vendor_patch = ROOT / "patches" / ("vendor-" + {"oneplus-8-pro": "oneplus-8", "oneplus-9-pro": "oneplus-9"}.get(name, name) + ".patch")
    additional = [(vendor_patch, data["vendor"]), (ROOT / "patches" / ("compat-" + data["platform"] + ".patch"), data["kernel"])]
    for extra_patch, origin in additional:
        if not extra_patch.exists():
            continue
        with tempfile.TemporaryDirectory() as temp:
            directory = pathlib.Path(temp)
            paths = [line[6:] for line in extra_patch.read_text().splitlines() if line.startswith("+++ b/")]
            for path in paths:
                url = "https://raw.githubusercontent.com/{}/{}/{}".format(
                    origin["repository"], origin["commit"], path)
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(url, timeout=60) as response:
                    target.write_bytes(response.read())
            run("git", "init", "--quiet", directory)
            run("git", "apply", "--check", extra_patch, cwd=directory)
    print(name + ": pinned source and patches verified", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=list(PATCHES))
    args = parser.parse_args()
    names = [args.device] if args.device else list(PATCHES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(audit, names))

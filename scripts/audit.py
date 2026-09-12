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
        for path in FILES:
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
    print(name + ": pinned source and patch verified", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=list(PATCHES))
    args = parser.parse_args()
    names = [args.device] if args.device else list(PATCHES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(audit, names))

"""Fetch the AOSP compiler used by the stock CFI-enabled SM8350 kernel."""
import json
import os
import subprocess
from project import ROOT, run

def configure(platform):
    if platform != "sm8350":
        return None
    lock = json.loads((ROOT / "tools.lock.json").read_text())["android_clang"]
    destination = ROOT / ".work" / "toolchains" / lock["commit"]
    binary = destination / lock["directory"] / "bin"
    if not (binary / "clang").exists():
        destination.mkdir(parents=True, exist_ok=True)
        run("git", "init", "--quiet", destination)
        run("git", "remote", "add", "origin", lock["repository"], cwd=destination)
        run("git", "config", "remote.origin.promisor", "true", cwd=destination)
        run("git", "config", "remote.origin.partialclonefilter", "blob:none", cwd=destination)
        run("git", "sparse-checkout", "set", lock["directory"], cwd=destination)
        run("git", "fetch", "--filter=blob:none", "--depth=1", "origin", lock["commit"], cwd=destination)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=destination)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()
    if commit != lock["commit"]:
        raise ValueError("AOSP compiler source commit mismatch")
    os.environ["PATH"] = str(binary) + os.pathsep + os.environ["PATH"]
    version = subprocess.check_output(["clang", "--version"], text=True)
    if lock["version_string"] not in version:
        raise ValueError("AOSP compiler version mismatch: " + version)
    return lock

"""Shared manifest loading and checked subprocess helpers."""
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCHES = {"oneplus-8": "op8", "oneplus-8-pro": "op8", "oneplus-8t": "op8t",
           "oneplus-9r": "op9r", "oneplus-9": "op9", "oneplus-9-pro": "op9"}


def device(name):
    if name not in PATCHES:
        raise ValueError("Unsupported device: " + name)
    data = json.loads((ROOT / "devices" / (name + ".json")).read_text(encoding="utf-8"))
    assert data["id"] == name and data["branch"] == name
    for source in ("kernel", "resukisu", "vendor"):
        assert re.fullmatch(r"[0-9a-f]{40}", data[source]["commit"])
    return data


def run(*args, cwd=None, env=None):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

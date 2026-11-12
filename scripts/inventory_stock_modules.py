"""Read-only inventory of stock EXT4 or EROFS vendor/odm modules."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from project import device


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def filesystem(image):
    with image.open("rb") as stream:
        stream.seek(1024)
        header = stream.read(58)
    if header[:4] == bytes.fromhex("e2e1f5e0"):
        return "erofs"
    if header[56:58] == bytes.fromhex("53ef"):
        return "ext4"
    raise ValueError("Unsupported stock filesystem: " + str(image))


def debugfs_read(debugfs, image, operation, path):
    if any(char in path for char in "\n\r\0"):
        raise ValueError("Invalid filesystem path")
    quoted = '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'
    result = subprocess.run([str(debugfs), "-R", operation + " " + quoted, str(image)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if b"Filesystem not open" in result.stderr:
        raise ValueError(result.stderr.decode(errors="replace"))
    return result.stdout


def entries(image, path, kind, dump, debugfs):
    if kind == "ext4":
        text = debugfs_read(debugfs, image, "ls -p", path).decode()
        parsed = []
        for line in text.splitlines():
            if not line.startswith("/"):
                continue
            inode, mode, uid, gid, name, size = line.split("/")[1:7]
            if int(inode):
                file_type = int(mode, 8) & 0o170000
                parsed.append((name, file_type == 0o040000, file_type == 0o100000, inode))
        if not parsed:
            raise ValueError("Failed to list EXT4 directory: " + path)
        return parsed
    text = subprocess.check_output([str(dump), "--ls", "--path=" + path, str(image)], text=True)
    parsed = []
    for line in text.splitlines():
        match = re.fullmatch(r"\s*(\d+)\s+(\d+)\s+(.+)", line)
        if match:
            inode, file_type, name = match.groups()
            parsed.append((name, file_type == "2", file_type == "1", inode))
    if not parsed:
        raise ValueError("Failed to list EROFS directory: " + path)
    return parsed


def scan(directory, dump="dump.erofs", debugfs="debugfs", output=None):
    name, rom = directory.parent.name, directory.name
    expected = device(name)["firmware"][rom]["stock_boot_sha256"]
    if sha(directory / "boot.img") != expected:
        raise ValueError("Stock boot does not match the registered firmware")
    result = {"device": name, "os": rom, "stock_boot_sha256": expected,
              "partitions": {}, "modules": []}
    for part in ("vendor", "odm"):
        image = directory / "partitions" / (part + ".img")
        kind = filesystem(image)
        pending, seen = ["/"], set()
        files = 0
        while pending:
            path = pending.pop()
            if path in seen:
                raise ValueError("Repeated filesystem directory: " + path)
            seen.add(path)
            for base, is_dir, regular, inode in entries(image, path, kind, dump, debugfs):
                if base in (".", ".."):
                    continue
                if not base or "/" in base or any(c in base for c in "\n\r\0"):
                    raise ValueError("Invalid filesystem entry")
                target = path.rstrip("/") + "/" + base
                if is_dir:
                    pending.append(target)
                    continue
                files += 1
                if not re.search(r"\.ko(?:\.(?:gz|xz|zst))?$", base):
                    continue
                if not regular or not base.endswith(".ko"):
                    raise ValueError("Unsupported non-regular or compressed module: " + target)
                if kind == "ext4":
                    content = debugfs_read(debugfs, image, "cat", target)
                else:
                    content = subprocess.check_output([str(dump), "--cat", "--nid=" + inode, str(image)])
                if content[:4] != b"\x7fELF":
                    raise ValueError("Invalid extracted ELF module: " + target)
                destination = directory / "module-set" / part / target.lstrip("/")
                destination.resolve().relative_to((directory / "module-set").resolve())
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    if destination.read_bytes() != content:
                        raise ValueError("Existing module differs from the original image: " + str(destination))
                else:
                    destination.write_bytes(content)
                result["modules"].append({"partition": part, "path": target,
                                          "sha256": hashlib.sha256(content).hexdigest()})
        result["partitions"][part] = {"sha256": sha(image), "size": image.stat().st_size,
                                      "directories_scanned": len(seen), "files_scanned": files}
    if not result["modules"]:
        raise ValueError("No original modules found")
    expected_paths = {directory / "module-set" / m["partition"] / m["path"].lstrip("/")
                      for m in result["modules"]}
    if set((directory / "module-set").rglob("*.ko")) != expected_paths:
        raise ValueError("Stale modules exist outside the new inventory")
    output = output or directory / "module-inventory.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(name, rom, len(result["modules"]), "modules", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-dir", required=True, type=pathlib.Path)
    parser.add_argument("--dump-erofs", default="dump.erofs", help="EROFS dump tool with --ls/--cat support")
    parser.add_argument("--debugfs", default="debugfs", help="Read-only EXT4 debugfs executable")
    parser.add_argument("--output", type=pathlib.Path, help="Optional separate inventory report")
    args = parser.parse_args()
    scan(args.stock_dir.resolve(), args.dump_erofs, args.debugfs, args.output)

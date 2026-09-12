"""Verify the actual unchanged vendor/odm module dependency graph."""
import argparse
import json
import pathlib
import struct
from check_module_abi import exports
from project import device, save, sha256

def module_symbols(path):
    raw = path.read_bytes()
    if raw[:6] != b"\x7fELF\x02\x01":
        raise ValueError("Expected a little-endian ELF64 module: " + str(path))
    offset = struct.unpack_from("<Q", raw, 40)[0]
    stride, count, string_index = struct.unpack_from("<HHH", raw, 58)
    if stride != 64 or not count or string_index >= count:
        raise ValueError("Unsupported ELF section table")
    sections = [struct.unpack_from("<IIQQQQIIQQ", raw, offset + stride * i) for i in range(count)]
    def section_data(s):
        if s[4] + s[5] > len(raw):
            raise ValueError("ELF section extends beyond module")
        return raw[s[4]:s[4] + s[5]]
    strings = section_data(sections[string_index])
    named = {}
    for s in sections:
        name = strings[s[0]:strings.index(b"\0", s[0])].decode()
        named[name] = s
    versions = section_data(named["__versions"])
    if not versions or len(versions) % 64:
        raise ValueError("Invalid module version table")
    imports = {}
    for i in range(0, len(versions), 64):
        crc = struct.unpack_from("<Q", versions, i)[0]
        name = versions[i + 8:i + 64].split(b"\0")[0].decode()
        if not name or crc > 0xffffffff:
            raise ValueError("Invalid module import")
        imports[name] = crc
    info = section_data(named[".modinfo"]).split(b"\0")
    vermagic = [x[9:].decode() for x in info if x.startswith(b"vermagic=")]
    if len(vermagic) != 1:
        raise ValueError("Missing or ambiguous vermagic")
    symtab = named[".symtab"]
    if symtab[9] != 24:
        raise ValueError("Unexpected ELF symbol size")
    names = section_data(sections[symtab[6]])
    symbols = {}
    data = section_data(symtab)
    for i in range(0, len(data), 24):
        name_offset, info, other, index, value, size = struct.unpack_from("<IBBHQQ", data, i)
        name = names[name_offset:names.index(b"\0", name_offset)].decode()
        symbols[name] = (index, value)
    provided = {}
    for name in symbols:
        if not name.startswith("__ksymtab_"):
            continue
        export = name[len("__ksymtab_"):]
        key = "__crc_" + export
        if key not in symbols:
            raise ValueError("Export without module CRC: " + export)
        index, value = symbols[key]
        if index == 0xfff1:
            crc = value & 0xffffffff
        elif 0 < index < len(sections):
            crc = struct.unpack_from("<I", section_data(sections[index]), value)[0]
        else:
            raise ValueError("Unresolved module export CRC: " + export)
        provided[export] = crc
    return imports, provided, vermagic[0]

def verify(inventory_path, built, stock_kernel, stock_map, stock_boot):
    inventory = json.loads(inventory_path.read_text())
    profile = device(inventory["device"])["firmware"][inventory["os"]]
    boot_hash = sha256(stock_boot)
    if boot_hash != inventory["stock_boot_sha256"] or boot_hash != profile["stock_boot_sha256"]:
        raise ValueError("Module inventory belongs to another stock firmware")
    if set(inventory["partitions"]) != {"vendor", "odm"} or not inventory["modules"]:
        raise ValueError("Both vendor and odm must be inventoried")
    for name, metadata in inventory["partitions"].items():
        image = inventory_path.parent / "partitions" / (name + ".img")
        if image.stat().st_size != metadata["size"] or sha256(image) != metadata["sha256"]:
            raise ValueError("Inventoried original partition changed: " + name)
        if metadata["directories_scanned"] < 1 or metadata["files_scanned"] < 1:
            raise ValueError("Incomplete partition inventory")
    stock = exports(stock_kernel, stock_map)
    compiled = exports(built / "Image", built / "System.map")
    required, provided = {}, {}
    for entry in inventory["modules"]:
        relative = pathlib.PurePosixPath(entry["path"])
        if ".." in relative.parts or entry["partition"] not in inventory["partitions"]:
            raise ValueError("Invalid module path")
        path = inventory_path.parent / "module-set" / entry["partition"] / entry["path"].lstrip("/")
        if sha256(path) != entry["sha256"]:
            raise ValueError("Original module changed: " + entry["path"])
        imports, exported, vermagic = module_symbols(path)
        if not vermagic.startswith(profile["kernel_release"] + " "):
            raise ValueError("Module kernel release differs")
        for table, incoming in ((required, imports), (provided, exported)):
            for name, crc in incoming.items():
                if name in table and table[name] != crc:
                    raise ValueError("Original modules disagree on CRC: " + name)
                table[name] = crc
    failures = {}
    for name, crc in required.items():
        if name in stock:
            if stock[name] != crc or compiled.get(name) != crc:
                failures[name] = {"module": hex(crc), "stock": hex(stock[name]),
                                  "built": hex(compiled[name]) if name in compiled else None}
        elif provided.get(name) != crc:
            failures[name] = {"module": hex(crc), "module_provider": provided.get(name)}
    result = {"passed": not failures, "device": inventory["device"], "os": inventory["os"],
              "stock_boot_sha256": boot_hash, "stock_kernel_sha256": sha256(stock_kernel),
              "image_sha256": sha256(built / "Image"), "system_map_sha256": sha256(built / "System.map"),
              "inventory_sha256": sha256(inventory_path), "partitions": inventory["partitions"],
              "modules": inventory["modules"], "module_count": len(inventory["modules"]),
              "kernel_import_count": sum(n in stock for n in required),
              "module_import_count": sum(n not in stock for n in required),
              "required_kernel_symbols": sorted(n for n in required if n in stock), "failures": failures,
              "scope": "All .ko files inventoried in original vendor and odm; checks CRCs and release, not runtime behavior."}
    save(built / "module-abi-report.json", result)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-dir", required=True, type=pathlib.Path)
    parser.add_argument("--built-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    d = args.stock_dir
    result = verify(d / "module-inventory.json", args.built_dir, d / "unpacked/kernel", d / "stock.map", d / "boot.img")
    print(json.dumps({key: result[key] for key in ("passed", "module_count", "kernel_import_count", "failures")}))
    raise SystemExit(0 if result["passed"] else 1)

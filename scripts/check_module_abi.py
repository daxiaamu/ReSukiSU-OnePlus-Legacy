"""Compare exported-symbol CRC tables in the actual stock and compiled Images."""
import argparse
import json
import pathlib
import struct
from project import sha256, save

def exports(kernel, symbol_map):
    raw = kernel.read_bytes()
    symbols = {}
    for line in symbol_map.read_text().splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    base = symbols["_text"]
    result = {}
    for suffix in ("", "_gpl", "_gpl_future", "_unused", "_unused_gpl"):
        start, stop = "__start___ksymtab" + suffix, "__stop___ksymtab" + suffix
        if start not in symbols or symbols[start] == symbols[stop]:
            continue
        entries = sorted((address, name[len("__ksymtab_"):])
                         for name, address in symbols.items()
                         if name.startswith("__ksymtab_") and symbols[start] <= address < symbols[stop])
        if len(entries) < 2:
            raise ValueError("Cannot establish symbol table stride: " + suffix)
        stride = entries[1][0] - entries[0][0]
        if stride not in (8, 12, 24) or len(entries) * stride != symbols[stop] - symbols[start]:
            raise ValueError("Unexpected symbol table layout: " + suffix)
        crcs = symbols["__start___kcrctab" + suffix] - base
        for index, (address, name) in enumerate(entries):
            offset = address - base
            nameoffset = (symbols["__kstrtab_" + name] - base if stride == 24 else
                          offset + 4 + struct.unpack_from("<i", raw, offset + 4)[0])
            if nameoffset < 0 or nameoffset >= len(raw):
                raise ValueError("Symbol name outside Image: " + name)
            actual = raw[nameoffset:raw.index(b"\0", nameoffset)].decode()
            if actual != name:
                raise ValueError("Symbol name mismatch: " + name)
            result[name] = struct.unpack_from("<I", raw, crcs + 4 * index)[0]
    if not result:
        raise ValueError("No export CRCs recovered")
    return result

def compare(stock_kernel, stock_map, built, report):
    stock = exports(stock_kernel, stock_map)
    compiled = exports(built / "Image", built / "System.map")
    missing = sorted(set(stock) - set(compiled))
    mismatch = {name: {"stock": hex(value), "built": hex(compiled[name])}
                for name, value in stock.items() if name in compiled and value != compiled[name]}
    result = {"stock_kernel_sha256": sha256(stock_kernel), "stock_map_sha256": sha256(stock_map),
              "image_sha256": sha256(built / "Image"), "system_map_sha256": sha256(built / "System.map"),
              "stock_exports": len(stock), "built_exports": len(compiled),
              "matching": sum(compiled.get(name) == value for name, value in stock.items()),
              "missing": missing, "mismatch": mismatch, "passed": not missing and not mismatch,
              "scope": "Export names and CRCs only; does not establish runtime or CFI compatibility."}
    save(report, result)
    print(json.dumps({key: result[key] for key in ("stock_exports", "built_exports", "matching", "passed")}))
    return result["passed"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-kernel", required=True, type=pathlib.Path)
    parser.add_argument("--stock-map", required=True, type=pathlib.Path)
    parser.add_argument("--built-dir", required=True, type=pathlib.Path)
    parser.add_argument("--report", required=True, type=pathlib.Path)
    args = parser.parse_args()
    raise SystemExit(0 if compare(args.stock_kernel, args.stock_map, args.built_dir, args.report) else 1)

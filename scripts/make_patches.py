"""Generate exact manual-hook patches for the reviewed OnePlus snapshots."""
import difflib
import pathlib
import re

FILES = ("fs/exec.c", "fs/open.c", "fs/stat.c", "kernel/reboot.c")


def guard(lines):
    return "#ifdef CONFIG_KSU_MANUAL_HOOK\n" + lines + "\n#endif\n"


def hook(text, signature, declaration, anchor, call):
    match = re.search(signature + r"[^{]*\{\n", text, flags=re.M)
    if not match:
        raise ValueError("Function not found: " + signature)
    start = match.end()
    end = text.index("\n}", start)
    body = text[start:end]
    if body.count(anchor) != 1:
        raise ValueError("Ambiguous anchor: " + anchor)
    body = guard(declaration) + body.replace(anchor, guard("\t" + call) + anchor, 1)
    return text[:start] + body + text[end:]


def transform(path, text):
    if "ksu_handle_" in text:
        raise ValueError("Source already hooked")
    if path == "fs/exec.c":
        return hook(text, r"^static int do_execveat_common\(",
                    "extern int ksu_handle_execveat(int *, struct filename **, void *, void *, int *);",
                    "\treturn __do_execve_file(",
                    "ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);")
    if path == "fs/open.c":
        return hook(text, r"^SYSCALL_DEFINE3\(faccessat,",
                    "extern int ksu_handle_faccessat(int *, const char __user **, int *, int *);",
                    "\treturn do_faccessat(",
                    "ksu_handle_faccessat(&dfd, &filename, &mode, NULL);")
    if path == "kernel/reboot.c":
        return hook(text, r"^SYSCALL_DEFINE4\(reboot,",
                    "extern int ksu_handle_sys_reboot(int, int, unsigned int, void __user **);",
                    "\t/* We only trust the superuser",
                    "ksu_handle_sys_reboot(magic1, magic2, cmd, &arg);")
    for name in ("newfstatat", "fstatat64"):
        text = hook(text, r"^SYSCALL_DEFINE4\(" + name + ",",
                    "extern int ksu_handle_stat(int *, const char __user **, int *);",
                    "\terror = vfs_fstatat(",
                    "ksu_handle_stat(&dfd, &filename, &flag);")
    for name, fdtype, stattype, handler in (
        ("newfstat", "unsigned int", "stat", "ksu_handle_newfstat_ret"),
        ("fstat64", "unsigned long", "stat64", "ksu_handle_fstat64_ret"),
    ):
        text = hook(text, r"^SYSCALL_DEFINE2\(" + name + ",",
                    "extern void %s(%s *, struct %s __user **);" % (handler, fdtype, stattype),
                    "\treturn error;", handler + "(&fd, &statbuf);")
    return text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    patch = ""
    for path in FILES:
        original = (args.source / path).read_text(encoding="utf-8")
        patch += "".join(difflib.unified_diff(
            original.splitlines(True), transform(path, original).splitlines(True),
            fromfile="a/" + path, tofile="b/" + path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patch.encode("utf-8"))

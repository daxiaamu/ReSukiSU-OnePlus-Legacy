"""Project release branding without relaxing module ABI or signature checks."""
import re

SUFFIX = "-daxiaamu"


def branded_release(stock):
    if not isinstance(stock, str) or not re.fullmatch(r"[A-Za-z0-9._+-]+", stock):
        raise ValueError("Invalid stock kernel release")
    release = stock + SUFFIX
    if len(release.encode()) > 64:
        raise ValueError("Branded kernel release exceeds the UTS limit")
    return release


def validate_release(manifest, stock, config):
    actual = manifest.get("kernel_release")
    if actual == stock and not manifest.get("kernel_release_suffix"):
        return  # Existing release artifacts retain their original version.
    if (actual != branded_release(stock)
            or manifest.get("stock_kernel_release") != stock
            or manifest.get("kernel_release_suffix") != SUFFIX):
        raise ValueError("Kernel release differs from the registered stock release and project suffix")
    if "CONFIG_MODVERSIONS=y" not in config.read_text().splitlines():
        raise ValueError("Branded kernel requires CONFIG_MODVERSIONS for stock modules")

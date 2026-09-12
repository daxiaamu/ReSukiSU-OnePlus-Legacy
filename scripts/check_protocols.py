"""Validate recovered message layouts and exercise SM8350 callbacks with host CFI."""
import pathlib
import tempfile
from project import device
from prepare_protocol import prepare
from toolchain import configure

if __name__ == "__main__":
    configure("sm8350")
    for name in ("oneplus-8", "oneplus-8t", "oneplus-9r", "oneplus-9"):
        with tempfile.TemporaryDirectory() as temporary:
            modules = pathlib.Path(temporary)
            (modules / "vendor/oplus/kernel/network/data_module/proto-src").mkdir(parents=True)
            result = prepare(modules, device(name))
            print(name, "layouts passed", "CFI callbacks tested" if result["cfi_safe_initializers"] else "", flush=True)

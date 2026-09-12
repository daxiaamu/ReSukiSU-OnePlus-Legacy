import pathlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from project import PATCHES, device
from repack import repack, boot_header
from make_patches import transform


class ProfileTests(unittest.TestCase):
    def test_all_devices_pin_sources(self):
        for name in PATCHES:
            data = device(name)
            self.assertEqual(data["resukisu"]["hook"], "manual")
            self.assertFalse(data["status"]["device_verified"])

    def test_9r_layout_mismatch_rejected_before_download(self):
        for os_name, bad_layout in (("coloros", "a/b"), ("oxygenos", "a-only")):
            args = types.SimpleNamespace(device="oneplus-9r", os=os_name, layout=bad_layout)
            with self.assertRaisesRegex(ValueError, "layout"):
                repack(args)

    def test_invalid_boot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "boot.img"
            path.write_bytes(b"ANDROID!")
            with self.assertRaises(ValueError):
                boot_header(path)
            path.write_bytes(b"\x00" * 100)
            with self.assertRaises(ValueError):
                boot_header(path)

    def test_duplicate_hooks_rejected(self):
        with self.assertRaisesRegex(ValueError, "already hooked"):
            transform("fs/exec.c", "ksu_handle_execveat()")

    def test_source_drift_is_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            transform("fs/exec.c", "int different_function(void) {}\n")


if __name__ == "__main__":
    unittest.main()

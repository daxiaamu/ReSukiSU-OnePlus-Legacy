import json
import pathlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from project import ROOT, PATCHES, device
from repack import repack, boot_header
from make_patches import transform


class ProfileTests(unittest.TestCase):
    def test_all_devices_pin_sources(self):
        for name in PATCHES:
            data = device(name)
            self.assertEqual(data["resukisu"]["hook"], "manual")

    def test_verified_devices_have_matching_boot_receipts(self):
        for name in PATCHES:
            data = device(name)
            status = data["status"]
            if not status["device_verified"]:
                continue
            self.assertTrue(status.get("validation_records"))
            confirmed = set()
            for path in status["validation_records"]:
                record = json.loads((ROOT / path).read_text())
                self.assertTrue(record["boot_completed"])
                firmware = next(f for f in data["firmware"].values()
                                if f["build_id"] == record["firmware"])
                self.assertEqual(record["boot_sha256"], firmware["output_boot_sha256"])
                confirmed.add(record["firmware"])
            self.assertEqual(confirmed, set(status["verified_firmware"]))

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

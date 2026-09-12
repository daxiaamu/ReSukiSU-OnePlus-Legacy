import hashlib
import pathlib
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import extract_stock

class ExtractTests(unittest.TestCase):
    def check_image(self, expected):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        rom = root / "rom.zip"
        with zipfile.ZipFile(rom, "w") as archive:
            archive.writestr("boot.img", b"stock boot")
            archive.writestr("../../escape", b"must not extract")
        before = rom.read_bytes()
        profile = {"firmware": {"coloros": {"stock_boot_sha256": expected}}}
        with patch.object(extract_stock, "ROOT", root), patch.object(extract_stock, "device", return_value=profile):
            if expected == hashlib.sha256(b"stock boot").hexdigest():
                result = extract_stock.extract("oneplus-9r", "coloros", rom)
                self.assertEqual(result.read_bytes(), b"stock boot")
            else:
                with self.assertRaisesRegex(ValueError, "registered"):
                    extract_stock.extract("oneplus-9r", "coloros", rom)
                self.assertFalse((root / ".work/stock/oneplus-9r/coloros/boot.img").exists())
        self.assertEqual(rom.read_bytes(), before)
        self.assertFalse((root / ".work/stock/escape").exists())

    def test_direct_boot_extraction_leaves_rom_unchanged(self):
        self.check_image(hashlib.sha256(b"stock boot").hexdigest())

    def test_wrong_firmware_is_not_published(self):
        self.check_image("0" * 64)

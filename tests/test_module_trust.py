"""Exercise signature rejection with real detached signatures and small fixtures."""
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from module_trust import verify_embedded, verify_modules, MARKER

@unittest.skipUnless(shutil.which("openssl"), "openssl is required")
class ModuleTrustTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        for name in ("stock", "other"):
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048",
                            "-keyout", str(cls.root / (name + ".key")),
                            "-out", str(cls.root / (name + ".pem")), "-nodes",
                            "-subj", "/CN=" + name, "-days", "1"],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["openssl", "x509", "-in", str(cls.root / (name + ".pem")),
                            "-outform", "DER", "-out", str(cls.root / (name + ".der"))],
                           check=True)
        content = cls.root / "content"
        content.write_bytes(b"ELF fixture: kernel ABI is tested separately.\n")
        signature = cls.root / "signature"
        subprocess.run(["openssl", "cms", "-sign", "-binary", "-noattr", "-nocerts",
                        "-in", str(content), "-signer", str(cls.root / "stock.pem"),
                        "-inkey", str(cls.root / "stock.key"), "-outform", "DER",
                        "-out", str(signature)], check=True)
        sig = signature.read_bytes()
        cls.signed = content.read_bytes() + sig + bytes([0, 0, 2, 0, 0, 0, 0, 0]) + len(sig).to_bytes(4, "big") + MARKER

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.built = pathlib.Path(self.work.name)
        cert = self.root / "stock.pem"
        self.firmware = {"config": str(self.built / "original.config"),
                         "trusted_module_certificates": [{
                             "path": str(cert),
                             "sha256": hashlib.sha256(cert.read_bytes()).hexdigest(),
                             "der_sha256": hashlib.sha256((self.root / "stock.der").read_bytes()).hexdigest()}]}
        for filename in ("original.config", "kernel.config"):
            (self.built / filename).write_text("CONFIG_MODULE_SIG_FORCE=y\n")
        (self.built / "System.map").write_text(
            "00001000 T _text\n00001010 D system_certificate_list_size\n00001040 D system_certificate_list\n")
        self.set_image((self.root / "stock.der").read_bytes())
        self.stock = self.built / "rom"
        (self.stock / "module-set").mkdir(parents=True)
        self.module = self.stock / "module-set/test.ko"
        self.module.write_bytes(self.signed)
        self.inventory = self.stock / "module-inventory.json"
        self.inventory.write_text("{}")

    def set_image(self, der):
        raw = bytearray(64) + der
        struct.pack_into("<Q", raw, 16, len(der))
        (self.built / "Image").write_bytes(raw)

    def test_correct_signature(self):
        result = verify_modules(self.firmware, self.built, self.inventory)
        self.assertTrue(result["passed"])
        self.assertEqual(result["module_count"], 1)

    def test_modified_module_rejected(self):
        raw = bytearray(self.signed)
        raw[8] ^= 1
        self.module.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "signature rejected"):
            verify_modules(self.firmware, self.built, self.inventory)

    def test_new_build_key_does_not_replace_stock_trust(self):
        self.set_image((self.root / "other.der").read_bytes())
        with self.assertRaisesRegex(ValueError, "does not trust"):
            verify_embedded(self.firmware, self.built)

    def test_signature_enforcement_cannot_be_disabled(self):
        (self.built / "kernel.config").write_text("# CONFIG_MODULE_SIG_FORCE is not set\n")
        with self.assertRaisesRegex(ValueError, "enforcement differs"):
            verify_embedded(self.firmware, self.built)

    def test_pinned_certificate_cannot_be_changed(self):
        self.firmware["trusted_module_certificates"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "certificate changed"):
            verify_embedded(self.firmware, self.built)

    def test_unsigned_module_rejected(self):
        self.module.write_bytes(b"unsigned")
        with self.assertRaisesRegex(ValueError, "Unsigned"):
            verify_modules(self.firmware, self.built, self.inventory)

if __name__ == "__main__":
    unittest.main()

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from kernel_release import SUFFIX, branded_release, validate_release
from project import PATCHES, device


class KernelReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = pathlib.Path(self.temp.name) / "kernel.config"
        self.config.write_text("CONFIG_MODVERSIONS=y\n")
        self.stock = "4.19.157-perf+"
        self.manifest = {"kernel_release": branded_release(self.stock),
                         "stock_kernel_release": self.stock,
                         "kernel_release_suffix": SUFFIX}

    def test_every_firmware_can_append_brand_within_uts_limit(self):
        for name in PATCHES:
            for firmware in device(name)["firmware"].values():
                stock = firmware["kernel_release"]
                self.assertEqual(branded_release(stock), stock + "-daxiaamu")
                self.assertLessEqual(len(branded_release(stock)), 64)

    def test_accepts_branded_and_existing_release(self):
        validate_release(self.manifest, self.stock, self.config)
        validate_release({"kernel_release": self.stock}, self.stock, self.config)

    def test_rejects_unrelated_release_changes_or_missing_provenance(self):
        for key, value in (("kernel_release", "4.19.999-daxiaamu"),
                           ("stock_kernel_release", "4.19.999"),
                           ("kernel_release_suffix", "-other")):
            with self.subTest(key=key):
                bad = dict(self.manifest, **{key: value})
                with self.assertRaises(ValueError):
                    validate_release(bad, self.stock, self.config)
        with self.assertRaises(ValueError):
            validate_release({"kernel_release": branded_release(self.stock)}, self.stock, self.config)

    def test_branded_release_requires_module_versions(self):
        self.config.write_text("# CONFIG_MODVERSIONS is not set\n")
        with self.assertRaisesRegex(ValueError, "CONFIG_MODVERSIONS"):
            validate_release(self.manifest, self.stock, self.config)

    def test_rejects_oversized_or_invalid_release(self):
        for stock in ("x" * 64, "4.19.157 invalid", ""):
            with self.subTest(stock=stock):
                with self.assertRaises(ValueError):
                    branded_release(stock)


if __name__ == "__main__":
    unittest.main()

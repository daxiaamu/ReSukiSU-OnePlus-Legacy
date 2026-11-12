import io
import pathlib
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from toolchain import download_legacy_linker


class LegacyLinkerDownloadTests(unittest.TestCase):
    url = "https://example.invalid/linker"

    def error(self, code):
        return HTTPError(self.url, code, "test response", {}, None)

    def test_recovers_from_observed_503(self):
        with patch("toolchain.urllib.request.urlopen", side_effect=[self.error(503), io.BytesIO(b"payload")]) as fetch, \
                patch("toolchain.time.sleep") as sleep:
            self.assertEqual(download_legacy_linker(self.url), b"payload")
            self.assertEqual(fetch.call_count, 2)
            sleep.assert_called_once_with(2)

    def test_does_not_retry_missing_source(self):
        with patch("toolchain.urllib.request.urlopen", side_effect=self.error(404)) as fetch, \
                patch("toolchain.time.sleep") as sleep:
            with self.assertRaises(HTTPError):
                download_legacy_linker(self.url)
            self.assertEqual(fetch.call_count, 1)
            sleep.assert_not_called()

    def test_transient_failures_are_bounded(self):
        with patch("toolchain.urllib.request.urlopen", side_effect=self.error(503)) as fetch, \
                patch("toolchain.time.sleep") as sleep:
            with self.assertRaises(HTTPError):
                download_legacy_linker(self.url)
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

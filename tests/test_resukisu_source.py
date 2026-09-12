import copy
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from resukisu_source import resolve, validate_manifest


class ReSukiSUSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = {"repository": "ReSukiSU/ReSukiSU",
                       "commit": "1" * 40, "hook": "manual"}

    def latest(self):
        output = "ref: refs/heads/main\tHEAD\n" + "2" * 40 + "\tHEAD\n"
        with patch("resukisu_source.subprocess.check_output", return_value=output):
            source, selection = resolve(self.source)
        return {"resukisu": source, "resukisu_selection": selection}

    def test_resolves_default_branch_and_preserves_baseline(self):
        manifest = self.latest()
        self.assertEqual(manifest["resukisu"]["commit"], "2" * 40)
        self.assertEqual(self.source["commit"], "1" * 40)
        self.assertEqual(manifest["resukisu_selection"]["resolved_ref"], "refs/heads/main")
        validate_manifest(manifest, self.source)

    def test_tracks_a_renamed_default_branch(self):
        output = "ref: refs/heads/development\tHEAD\n" + "3" * 40 + "\tHEAD\n"
        with patch("resukisu_source.subprocess.check_output", return_value=output):
            source, selection = resolve(self.source)
        self.assertEqual(source["commit"], "3" * 40)
        self.assertEqual(selection["resolved_ref"], "refs/heads/development")

    def test_resolution_failure_does_not_fall_back(self):
        for output in ("", "abcdef\tHEAD\n", "2" * 40 + "\tHEAD\n",
                       "ref: refs/tags/v1\tHEAD\n" + "2" * 40 + "\tHEAD\n"):
            with self.subTest(output=output):
                with patch("resukisu_source.subprocess.check_output", return_value=output):
                    with self.assertRaises(ValueError):
                        resolve(self.source)
        with patch("resukisu_source.subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(128, "git")):
            with self.assertRaises(subprocess.CalledProcessError):
                resolve(self.source)

    def test_existing_release_manifest_remains_valid(self):
        validate_manifest({"resukisu": self.source}, self.source)

    def test_changed_commit_requires_latest_provenance(self):
        manifest = self.latest()
        del manifest["resukisu_selection"]
        with self.assertRaises(ValueError):
            validate_manifest(manifest, self.source)

    def test_rejects_changed_repository_hook_or_baseline(self):
        original = self.latest()
        for section, key, value in (
            ("resukisu", "repository", "other/repository"),
            ("resukisu", "hook", "different"),
            ("resukisu", "commit", "main"),
            ("resukisu_selection", "baseline_commit", "3" * 40),
            ("resukisu_selection", "mode", "pinned"),
            ("resukisu_selection", "resolved_ref", "refs/tags/v1"),
            ("resukisu_selection", "requested_ref", "arbitrary"),
        ):
            with self.subTest(key=key):
                manifest = copy.deepcopy(original)
                manifest[section][key] = value
                with self.assertRaises(ValueError):
                    validate_manifest(manifest, self.source)


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the Data-only source validation path."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import validate_source
import validate_published_manifest


ROOT = Path(__file__).resolve().parents[1]


class SourceValidationTests(unittest.TestCase):
    def copy_fixture(self, target: Path) -> Path:
        for name in ("items", "recipes", "dist"):
            shutil.copytree(ROOT / name, target / name)
        shutil.copy2(ROOT / "id-redirects.json", target / "id-redirects.json")
        shutil.copy2(ROOT / ".data-version", target / ".data-version")
        return target

    def test_current_source_data_passes(self) -> None:
        validate_source.validate(ROOT)

    def test_crystallization_f8_recipe_and_custom_identity_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            path = root / "recipes/hoplite.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            recipe = next(r for r in document["recipes"] if r["id"] == "hoplite:crystallization_shard")
            recipe["key"]["C"] = {"item": "minecraft:potion"}
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(validate_source.ValidationError, "current F8 observation"):
                validate_source.validate(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            path = root / "items/hoplite.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            item = next(i for i in document["items"] if i["id"] == "hoplite:crystallization_shard")
            item["matcher"] = {"item": "minecraft:amethyst_shard"}
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(validate_source.ValidationError, "distinct from a vanilla Amethyst Shard"):
                validate_source.validate(root)

    def test_duplicate_recipe_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            path = root / "recipes/hoplite.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["recipes"][1]["id"] = document["recipes"][0]["id"]
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(validate_source.ValidationError, "duplicate recipe IDs"):
                validate_source.validate(root)

    def test_dangling_redirect_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            path = root / "id-redirects.json"
            redirects = json.loads(path.read_text(encoding="utf-8"))
            redirects[next(iter(redirects))] = "hoplite:missing_target"
            path.write_text(json.dumps(redirects), encoding="utf-8")
            with self.assertRaisesRegex(validate_source.ValidationError, "invalid redirect"):
                validate_source.validate(root)

    def test_stale_source_manifest_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_fixture(Path(temporary))
            path = root / "dist/manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["files"][0]["sha256"] = "0" * 64
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(validate_source.ValidationError, "size/hash mismatch"):
                validate_source.validate(root)

    def test_published_validation_rejects_placeholders_before_network(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholder URL or commit"):
            validate_published_manifest.validate(ROOT, "tanzana7/just-enough-hoplite-data")


if __name__ == "__main__":
    unittest.main()

"""Validate Data repository Draft 2020-12 schemas and source files offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
from referencing import Registry
from referencing.exceptions import NoSuchResource


def deny_remote(uri: str) -> None:
    raise NoSuchResource(ref=uri)


def validate(root: Path) -> None:
    validators = {}
    for kind in ("items", "recipes", "manifest", "overrides"):
        schema = json.loads((root / "schema" / f"{kind}.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validators[kind] = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
            registry=Registry(retrieve=deny_remote),
        )

    count = 0
    for kind in ("items", "recipes"):
        for path in sorted((root / kind).glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            validators[kind].validate(document)
            count += 1
    manifest = root / "dist/manifest.json"
    if manifest.exists():
        validators["manifest"].validate(json.loads(manifest.read_text(encoding="utf-8")))
        count += 1
    validators["overrides"].validate({"schema_version": 2, "deletes": {"items": [], "recipes": []}})
    print(f"PASS: four Draft 2020-12 schemas, {count} data/manifest files, default overrides; remote refs disabled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    validate(parser.parse_args().data)

"""Fail-closed public artifact check for a release or an explicit manual run."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import jsonschema
from referencing import Registry
from referencing.exceptions import NoSuchResource


def validate(root: Path, expected_repository: str | None = None) -> None:
    schemas = {}
    for kind in ("items", "recipes", "manifest"):
        schema = json.loads((root / "schema" / f"{kind}.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        schemas[kind] = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
            registry=Registry(retrieve=lambda uri: (_ for _ in ()).throw(NoSuchResource(ref=uri))),
        )
    manifest_path = root / "dist/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schemas["manifest"].validate(manifest)
    try:
        source_version = int((root / ".data-version").read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise ValueError(".data-version must contain an integer") from exc
    if manifest.get("data_version") != source_version:
        raise ValueError("published manifest data_version differs from .data-version")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("published manifest has no files")
    expected_repo = expected_repository or "tanzana7/just-enough-hoplite-data"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", expected_repo):
        raise ValueError("expected repository must be owner/name")
    seen: set[str] = set()
    commit_refs: set[str] = set()
    for entry in entries:
        url = entry.get("url", "")
        if any(token in unquote(url).lower() for token in ("<owner>", "<repo>", "0000000000000000000000000000000000000000")):
            raise ValueError("published manifest contains a placeholder URL or commit")
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if (
            parsed.scheme != "https"
            or parsed.netloc != "raw.githubusercontent.com"
            or len(parts) < 4
            or "/".join(parts[:2]).casefold() != expected_repo.casefold()
            or not re.fullmatch(r"[0-9a-f]{40}", parts[2])
            or parts[3] not in {"items", "recipes"}
            or ".." in parts
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("published URL must be an immutable raw.githubusercontent.com URL for the configured repository")
        relative = "/".join(parts[3:])
        if relative not in {"items/hoplite.json", "recipes/hoplite.json"} or relative in seen:
            raise ValueError(f"unexpected or duplicate published file path: {relative}")
        seen.add(relative)
        commit_refs.add(parts[2])
        request = Request(url, headers={"User-Agent": "JEH-published-manifest-validator/1"})
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read()
                if response.status != 200:
                    raise ValueError(f"public artifact returned HTTP {response.status}: {relative}")
        except (HTTPError, URLError, TimeoutError) as exc:
            status = getattr(exc, "code", None)
            detail = f"HTTP {status}" if status is not None else type(exc).__name__
            raise ValueError(f"public artifact is not anonymously retrievable ({detail}): {relative}") from exc
        if len(content) != entry.get("size"):
            raise ValueError(f"published artifact size mismatch: {relative}")
        if hashlib.sha256(content).hexdigest() != entry.get("sha256"):
            raise ValueError(f"published artifact SHA-256 mismatch: {relative}")
        document = json.loads(content)
        schemas[parts[3]].validate(document)
    if seen != {"items/hoplite.json", "recipes/hoplite.json"}:
        raise ValueError("published manifest must contain the items and recipes artifacts")
    if len(commit_refs) != 1:
        raise ValueError("published files must share one immutable commit reference")
    print("PASS: public URLs, anonymous retrieval, JSON, sizes and SHA-256 values")


if __name__ == "__main__":
    try:
        if len(sys.argv) not in {2, 3}:
            raise ValueError("usage: validate_published_manifest.py DATA_ROOT [owner/repository]")
        validate(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) == 3 else None)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

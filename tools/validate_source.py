"""Validate editable JEH data without relying on a private Mod checkout."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED = {"items": 86, "recipes": 74, "redirects": 3, "key_ingredients": 8}


class ValidationError(Exception):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read valid JSON: {path}") from exc


def identity(value: dict[str, Any]) -> tuple[str, str]:
    for field in ("item", "tag", "hoplite"):
        if field in value:
            return field, value[field]
    if "any_of" in value:
        return "any_of", json.dumps(value["any_of"], sort_keys=True, separators=(",", ":"))
    raise ValidationError("ingredient has no supported identity")


def ingredient_counts(recipe: dict[str, Any]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()

    def add(ingredient: dict[str, Any], multiplier: int = 1) -> None:
        counts[identity(ingredient)] += ingredient.get("count", 1) * multiplier

    if recipe["type"] == "crafting_shaped":
        occurrences = Counter(char for row in recipe["pattern"] for char in row if char != " ")
        for symbol, amount in occurrences.items():
            add(recipe["key"][symbol], amount)
    elif recipe["type"] == "crafting_shapeless":
        for ingredient in recipe["ingredients"]:
            add(ingredient)
    else:
        for ingredient in recipe.get("inputs", {}).values():
            add(ingredient)
    return counts


def validate(root: Path) -> None:
    items_doc = read_json(root / "items/hoplite.json")
    recipes_doc = read_json(root / "recipes/hoplite.json")
    redirects = read_json(root / "id-redirects.json")
    items = items_doc.get("items", [])
    recipes = recipes_doc.get("recipes", [])
    item_ids = [item["id"] for item in items]
    recipe_ids = [recipe["id"] for recipe in recipes]
    if len(item_ids) != len(set(item_ids)):
        raise ValidationError("duplicate item IDs")
    if len(recipe_ids) != len(set(recipe_ids)):
        raise ValidationError("duplicate recipe IDs")
    item_by_id = {item["id"]: item for item in items}
    recipe_by_id = {recipe["id"]: recipe for recipe in recipes}
    if len(items) != EXPECTED["items"] or len(recipes) != EXPECTED["recipes"]:
        raise ValidationError(f"unexpected dataset size: items={len(items)} recipes={len(recipes)}")
    if len(redirects) != EXPECTED["redirects"]:
        raise ValidationError(f"unexpected redirect count: {len(redirects)}")

    def check_ingredient(ingredient: dict[str, Any], where: str) -> None:
        if "hoplite" in ingredient and ingredient["hoplite"] not in item_by_id:
            raise ValidationError(f"unknown Hoplite item reference at {where}: {ingredient['hoplite']}")
        for choice in ingredient.get("any_of", []):
            check_ingredient(choice, where)

    key_count = 0
    for recipe in recipes:
        for ingredient in ingredient_counts(recipe):
            kind, target = ingredient
            if kind == "hoplite" and target not in item_by_id:
                raise ValidationError(f"unknown recipe ingredient in {recipe['id']}: {target}")
        for symbol, ingredient in recipe.get("key", {}).items():
            check_ingredient(ingredient, f"{recipe['id']}.key.{symbol}")
        for ingredient in recipe.get("ingredients", []):
            check_ingredient(ingredient, recipe["id"])
        for field in ("inputs", "catalysts"):
            for ingredient in recipe.get(field, {}).values():
                check_ingredient(ingredient, f"{recipe['id']}.{field}")
        result = recipe["result"]
        if "hoplite" in result and result["hoplite"] not in item_by_id:
            raise ValidationError(f"unknown recipe result in {recipe['id']}: {result['hoplite']}")
        available = ingredient_counts(recipe)
        for key in recipe.get("keyIngredients", []):
            key_count += 1
            normalized = {"item": key} if isinstance(key, str) else key
            if isinstance(key, str) and key.startswith("hoplite:") and key not in item_by_id:
                raise ValidationError(f"unknown key ingredient item in {recipe['id']}: {key}")
            check_ingredient(normalized, f"{recipe['id']}.keyIngredients")
            required = normalized.get("count", 1)
            if available[identity(normalized)] < required:
                raise ValidationError(f"key ingredient quantity is not present in {recipe['id']}")
        note = recipe.get("availability_note")
        if note is not None:
            if not isinstance(note.get("en_us"), str) or not note["en_us"].strip():
                raise ValidationError(f"availability_note requires en_us: {recipe['id']}")
            for locale, text in note.items():
                if not isinstance(text, str) or not text.strip():
                    raise ValidationError(f"availability_note has empty {locale}: {recipe['id']}")
    if key_count != EXPECTED["key_ingredients"]:
        raise ValidationError(f"unexpected keyIngredients count: {key_count}")

    for source, target in redirects.items():
        if source in item_by_id or target not in item_by_id or source == target:
            raise ValidationError(f"invalid redirect: {source} -> {target}")
        seen = {source}
        cursor = target
        while cursor in redirects:
            if cursor in seen:
                raise ValidationError(f"redirect cycle contains {cursor}")
            seen.add(cursor)
            cursor = redirects[cursor]
        if cursor not in item_by_id:
            raise ValidationError(f"redirect target does not resolve to an item: {source}")

    for item in items:
        for acquisition in item.get("acquisition", []):
            for recipe_id in acquisition.get("recipe_ids", []):
                if recipe_id not in recipe_by_id:
                    raise ValidationError(f"unknown acquisition recipe on {item['id']}: {recipe_id}")

    for item_id, display_name in (
        ("hoplite:portable_villager", "Portable Villager"),
        ("hoplite:ender_pack", "Ender Pack"),
    ):
        recipe = recipe_by_id.get(item_id)
        item = item_by_id.get(item_id)
        if (
            not item
            or item.get("name", {}).get("en_us") != display_name
            or not recipe
            or recipe.get("category") != "utility"
            or recipe["result"].get("hoplite") != item_id
        ):
            raise ValidationError(f"Portable Villager / Ender Pack linkage invalid: {item_id}")

    revival = recipe_by_id.get("hoplite:revival_item")
    if not revival or revival["result"].get("hoplite") != "hoplite:revival_item":
        raise ValidationError("Revival Star canonical identity or recipe result is missing")
    revival_ingredients = ingredient_counts(revival)
    required_revival = {
        ("item", "minecraft:golden_apple"): 1,
        ("item", "minecraft:diamond"): 2,
        ("item", "minecraft:player_head"): 1,
        ("item", "minecraft:clock"): 1,
    }
    if revival_ingredients != Counter(required_revival):
        raise ValidationError("Revival Star ingredient identities or quantities differ from the current F8 recipe")
    if revival.get("pattern") != [" A ", "BCB", " D "]:
        raise ValidationError("Revival Star grid differs from the current F8 recipe")
    if revival["result"].get("count") != 1:
        raise ValidationError("Revival Star result count differs from the current F8 recipe")
    if revival.get("availability_note") != {"en_us": "Team modes only", "ja_jp": "チーム戦のみ"}:
        raise ValidationError("Revival Star availability note differs from its independent item-lore evidence")

    crystal = recipe_by_id.get("hoplite:crystallization_shard")
    if (
        not crystal
        or crystal.get("pattern") != [" A ", "BCB", " B "]
        or crystal.get("key") != {
            "A": {"item": "minecraft:player_head"},
            "B": {"item": "minecraft:amethyst_shard"},
            "C": {"item": "minecraft:honey_bottle"},
        }
        or crystal.get("result") != {"count": 1, "hoplite": "hoplite:crystallization_shard"}
        or crystal.get("evidence", {}).get("status") != "verified"
    ):
        raise ValidationError("Crystallization Shard recipe or evidence status differs from the current F8 observation")
    crystal_item = item_by_id.get("hoplite:crystallization_shard", {})
    crystal_matcher = crystal_item.get("matcher", {})
    if (
        crystal_matcher.get("item") != "minecraft:amethyst_shard"
        or crystal_matcher.get("custom_model_data", {}).get("floats") != [1.0]
        or crystal_matcher.get("custom_data") != {
            "equals": "crystallization_shard",
            "path": 'PublicBukkitValues."hoplite:civid"',
        }
    ):
        raise ValidationError("Crystallization Shard matcher must remain distinct from a vanilla Amethyst Shard")

    manifest_path = root / "dist/manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        try:
            source_version = int((root / ".data-version").read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as exc:
            raise ValidationError(".data-version must contain an integer") from exc
        if manifest.get("data_version") != source_version:
            raise ValidationError("source manifest data_version differs from .data-version")
        if manifest.get("id_redirects") != redirects:
            raise ValidationError("source manifest redirects differ from id-redirects.json")
        expected_paths = {"items/hoplite.json", "recipes/hoplite.json"}
        actual_paths: set[str] = set()
        for entry in manifest.get("files", []):
            match = re.search(r"/(items|recipes)/([^/?#]+)$", entry.get("url", ""))
            if not match:
                raise ValidationError("source manifest entry does not map to an editable data file")
            rel = f"{match.group(1)}/{match.group(2)}"
            if rel in actual_paths:
                raise ValidationError(f"duplicate source manifest entry: {rel}")
            actual_paths.add(rel)
            content = (root / rel).read_bytes()
            if entry.get("size") != len(content) or entry.get("sha256") != hashlib.sha256(content).hexdigest():
                raise ValidationError(f"source manifest size/hash mismatch: {rel}")
        if actual_paths != expected_paths:
            raise ValidationError("source manifest must cover the items and recipes source files")

    print(
        "PASS: source references, unique IDs, redirects, keyIngredients, localized notes, "
        f"source manifest and approved records ({len(items)} items / {len(recipes)} recipes / {len(redirects)} redirects / {key_count} keyIngredients)"
    )


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValidationError("usage: validate_source.py DATA_ROOT")
        validate(Path(sys.argv[1]))
    except (ValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

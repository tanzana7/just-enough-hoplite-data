# JEH data repository

This repository holds the independently versioned JSON dataset for Just Enough Hoplite. `schema/` contains the four Draft 2020-12 schemas; `items/` and `recipes/` contain curated records; `dist/manifest.json` describes content-addressed files; `reports/` retains importer provenance, live identity fixtures and unresolved evidence.

Validate from the JEH mod checkout with:

```sh
./gradlew -p ../just-enough-hoplite :core:runValidator -PjehDataRoot=.
python ../just-enough-hoplite/tools/validate_schema.py --data .
```

Regenerate the imported records from the copied evidence with:

```sh
python ../just-enough-hoplite/tools/import_seed_data.py \
  --seed ../evidence/jeh_hoplite_recipe_dataset_v8.json \
  --live ../evidence/jeh_hoplite_live_item_identity_2026-10-19.json \
  --render-candidates ../evidence/jeh_resource_pack_render_candidates_2026-10-20.json \
  --current-recipe-dumps ../evidence/jeh_hoplite_current_rotation_2026-10-21.json \
  --official-regular-recipes ../evidence/jeh_hoplite_official_regular_recipe_evidence_2026-10-21.json \
  --normalized-recipe-evidence reports/revival-star-recipe-evidence-2026-10-24.json \
  --output . \
  --bundled ../just-enough-hoplite/src/main/resources/jeh/bundled
python ../just-enough-hoplite/tools/prepare_bundled.py \
  --data . --bundled ../just-enough-hoplite/src/main/resources/jeh/bundled
```

`publishManifest` validates and changes only `.data-version` and `dist/manifest.json`. Configure `JEH_DATA_REPOSITORY`, then run it with a real 40-character commit and publication timestamp. The checked-in offline manifest uses a placeholder repository and cannot be fetched. GitHub publishing requires repository variables that pin the mod checkout and validator ref; those account settings and the public repository do not exist in this local implementation.

`runValidator` defaults to editable source validation: data PRs do not need to regenerate the manifest. Add `-PjehValidationMode=validate-published` to verify a published fixture, including hashes, sizes and publication URLs. The checked-in offline placeholder intentionally fails that URL policy. `publishManifest` runs both validations around generation. `id-redirects.json` is the editable redirect map and is copied into manifest `id_redirects`.

The current dataset has 86 items / 74 recipes / 51 legendary items / 40 legendary recipe records / 53 live-civid identities / 55 total matchers. Portable Villager and Ender Pack recipes are recorded from user-provided in-game screenshots; `keyIngredients` annotates eight recipes and remains optional for existing records. Official Shortbow and Bundled Arrows layouts are imported from a separate current-source evidence file; Revival Star uses a normalized in-game Recipe Book record; its canonical output and Nether Reactor Core ingredient are cross-checked against live item identities, and its localized Team modes only note comes from the captured item lore. The resource-pack render audit supplies base-item + CustomModelData stacks for 19 high-confidence display mappings, leaving 12 actual fallback icons; those mappings are render-only and do not alter matcher or evidence fields. The 10 ambiguous mappings and 2 unmapped items remain fallbacks. The 34 unresolved report entries are excluded recipe candidates. Emerald Blade resolves to the live `hoplite:emerald_sword` ID; the former `hoplite:emerald_blade` ID redirects to it. Its carrot and golden-carrot candidates remain disputed. Panacea and Crystallization Shard also remain disputed, with source alternatives preserved in runtime evidence and the report.

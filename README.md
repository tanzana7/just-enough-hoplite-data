# JEH data repository

This repository holds the independently versioned JSON dataset for Just Enough Hoplite. `schema/` contains the four Draft 2020-12 schemas; `items/` and `recipes/` contain curated records; `dist/manifest.json` describes content-addressed files; `reports/` retains importer provenance, live identity fixtures and unresolved evidence.

Validate the editable Data source locally with:

```sh
python -m pip install jsonschema==4.25.1
python tools/validate_schema.py --data .
python tools/validate_source.py .
```

GitHub Actions runs these source-only checks without checking out the private Mod repository. A separate Mod compatibility job checks out `JEH_MOD_REPOSITORY` at the immutable `JEH_VALIDATOR_REF` using `JEH_MOD_READ_TOKEN`, then runs the Java validator and compares the item and recipe files with the pinned Mod bundle. The token is used only to read the Mod repository. The preflight reports sanitized HTTP status guidance and never prints its response body or credential. Fine-grained token access should be limited to this Mod repository with Contents: read-only.

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

The checked-in `dist/manifest.json` is an offline source fixture. It contains placeholder repository/commit values and is not a release artifact. Do not replace those values until files exist at their final immutable URLs. On release, or on an explicit `workflow_dispatch` with `validate_published` enabled, the published-artifact job requires anonymous HTTP retrieval, the expected repository, valid schemas, exact file sizes and SHA-256 values, and no placeholders. It is intentionally fail-closed while the Data repository is private or the URLs are not publicly readable.

Manifest generation in CI is deterministic-tested only in temporary directories. Automatic main-branch manifest publishing is disabled unless `JEH_ENABLE_DATA_PUBLISH=true`; even then it refuses to run while the Data repository is private, and the public artifact validation runs before generated files are committed. `id-redirects.json` is the editable redirect map and is copied into the generated manifest. No release or public artifact has been created by this change.

The current dataset has 86 items / 74 recipes / 51 legendary items / 40 legendary recipe records / 53 live-civid identities / 55 total matchers. Portable Villager and Ender Pack recipes are recorded from user-provided in-game screenshots; `keyIngredients` annotates eight recipes and remains optional for existing records. Official Shortbow and Bundled Arrows layouts are imported from a separate current-source evidence file; Revival Star uses a normalized in-game Recipe Book record; its canonical output and Nether Reactor Core ingredient are cross-checked against live item identities, and its localized Team modes only note comes from the captured item lore. The resource-pack render audit supplies base-item + CustomModelData stacks for 19 high-confidence display mappings, leaving 12 actual fallback icons; those mappings are render-only and do not alter matcher or evidence fields. The 10 ambiguous mappings and 2 unmapped items remain fallbacks. The 34 unresolved report entries are excluded recipe candidates. Emerald Blade resolves to the live `hoplite:emerald_sword` ID; the former `hoplite:emerald_blade` ID redirects to it. Its carrot and golden-carrot candidates remain disputed. Panacea and Crystallization Shard also remain disputed, with source alternatives preserved in runtime evidence and the report.

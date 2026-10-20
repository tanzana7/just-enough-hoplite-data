# JEH data repository

This repository holds the independently versioned JSON dataset for Just Enough Hoplite. `schema/` contains the four Draft 2020-12 schemas; `items/` and `recipes/` contain curated records; `dist/manifest.json` describes content-addressed files; `reports/import-report.json` retains summarized importer provenance and unresolved evidence. Raw source captures and live identity fixtures are excluded.

Validate from the JEH mod checkout with:

```sh
./gradlew -p ../just-enough-hoplite :core:runValidator -PjehDataRoot=.
python ../just-enough-hoplite/tools/validate_schema.py --data .
```

To regenerate records locally, provide paths to source captures that you already hold. Raw captures are not stored in this repository. Run from the Mod repository root:

```sh
python tools/import_seed_data.py \
  --seed <local-seed-json> \
  --live <local-live-identity-json> \
  --render-candidates <local-render-candidates-json> \
  --output ../just-enough-hoplite-data \
  --bundled src/main/resources/jeh/bundled
python tools/prepare_bundled.py --data ../just-enough-hoplite-data --bundled src/main/resources/jeh/bundled
```

The importer writes curated records and a summarized provenance report; it does not copy the raw live capture fixture.
`publishManifest` validates and changes only `.data-version` and `dist/manifest.json`. Configure `JEH_DATA_REPOSITORY`, then run it with a real 40-character commit and publication timestamp. The checked-in offline manifest uses a placeholder repository and cannot be fetched. GitHub publishing requires repository variables that pin the mod checkout and validator ref; those account settings and the cross-repository variables still need owner configuration.

`runValidator` defaults to editable source validation: data PRs do not need to regenerate the manifest. Add `-PjehValidationMode=validate-published` to verify a published fixture, including hashes, sizes and publication URLs. The checked-in offline placeholder intentionally fails that URL policy. `publishManifest` runs both validations around generation. `id-redirects.json` is the editable redirect map and is copied into manifest `id_redirects`.

The current import has 84 items / 61 recipes / 51 legendary items / 32 legendary recipes / 53 civid matchers / 31 items without matchers. Nineteen high-confidence render mappings provide display-only base-item and CustomModelData stacks, leaving 12 fallback icons. Ambiguous and unmapped candidates remain fallbacks. Emerald Blade resolves to `hoplite:emerald_sword`; `hoplite:emerald_blade` redirects to it, and the competing carrot recipes remain disputed. The 34 unresolved report entries are excluded recipe candidates. Panacea and Crystallization Shard also remain disputed.

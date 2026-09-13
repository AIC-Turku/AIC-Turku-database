# Vocabulary final adversarial audit — 2026-09-13

## Scope

This pass audited current `main` after PR #435 merged. The audit re-ran the failure modes from the two prior vocabulary audits and inspected the actual post-merge repository rather than relying on PR descriptions.

## Critical post-merge finding

PR #435 merged its temporary transformation scripts and one-shot workflows instead of the verified transformed tree. The intended fixes therefore remained dormant on `main`. This PR applies those transformations, incorporates the import-cycle correction discovered during the earlier verification run, and removes all transfer/patch machinery before the result is committed.

## Additional residual findings corrected

- Historical QC charts previously grouped values solely by `metric_id`; the same metric recorded in different units could therefore create a false numerical discontinuity. Histories now split by authored unit when a metric has multiple units. No conversion is inferred.
- `x-cite`, `diode`, `tunable laser`, `fs laser`, and `ti:sapphire` were too ambiguous to be rewrite-safe aliases for a single light-source kind. They are no longer auto-canonicalized. Exact model/technology evidence remains in source records.
- Objective source descriptions now distinguish cover-glass specification, correction-collar hardware, and multi-immersion capability instead of conflating them.
- The central repository vocabulary builder now includes every authored vocabulary file before merging policy aliases/settings, so unbound vocabularies do not disappear from shared consumers.
- Dashboard vocabulary labels now use the central diagnostic resolver rather than silently exposing unknown raw IDs.
- The scheduled autofix workflow now invokes the package module correctly and validates proposed changes before opening its PR.

## Verification contract

The preparation workflow must remove itself and all historical transfer machinery, then pass compilation, generated-template freshness, repository validation, the full pytest suite, JavaScript syntax checks, strict dashboard generation, strict MkDocs generation, conservative autofix check, and `git diff --check` before committing the clean tree.

No PR is merged automatically.

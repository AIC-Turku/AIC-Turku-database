# Objectives catalogue: design and maintenance

## Unified catalogue (PR #432 extension)

**Objectives** is now one discovery page for microscope records and the spare pool.
The existing `objective_pool/` URL and `pool-*` anchors remain valid. There is no
second manually maintained copy of microscope objective specifications.

The main views are **All objectives**, **On microscopes** and **Spare pool**.
Filter further by microscope, installation state, manufacturer, immersion, condition
and item type. Current records are shown by default; a separate checkbox includes
clearly labelled retired-instrument records. A microscope-specific link enables the
historical view when necessary. The instrument page and catalogue link in both
directions, to its Objectives section and to a prefiltered catalogue respectively.

Installation is a three-state fact taken only from canonical `is_installed`:

| Source flag | Catalogue label | What it does not establish |
|---|---|---|
| `true` | Installed - as recorded | Serviceability, availability for borrowing, or a fresh physical check |
| `false` | Associated - not installed | Membership of the shared spare pool |
| missing/null | Installation unconfirmed | Either installed or spare |

Optional-objective notes remain visible without inferring optional status from every
false flag. Historical flags retain their original meaning within a historical record;
retired objectives are not automatically spare. Pool entries remain **Spare-pool
listings** with their original condition and availability, not confirmed live stock.

`inventory/objective_pool.yaml` remains authoritative for pool records only.
`scripts/dashboard/objective_catalogue.py` projects those validated pool views and
canonical instrument DTOs into the shared page and `assets/objectives.json`.
`assets/objective_pool.json` remains the original pool-only export. Catalogue filters
are display metadata, never new capabilities. The Air/dry filter groups the pool's
Dry descriptor with canonical Air; source values and per-item labels are preserved.
Working distances on microscopes retain their recorded units; pool units remain
unconfirmed where the source does not specify them.

As of this source snapshot the page has **135 current records**: 100 on active
microscopes (90 explicitly installed and 10 explicitly not installed), plus 35 pool
records including one calibration item. Two retired-SP5 objective records are
available in the historical view. Counts refer to source records, not physical assets.
`facility.non_public_instrument_ids` explicitly excludes the existing synthetic
`scope-testx1` fixture. The catalogue honours that site-wide list, so a record
withheld from the public site cannot reappear here through a second list drifting out
of sync; `facility.objective_catalogue.exclude_instrument_ids` remains available for
catalogue-only exclusions. Exclusions from either list must be known, unique IDs. No
name-based synthetic detection or browser-side hardware inference is used.

### Adversarial boundaries

- Product codes identify models, not physical copies. No installed/pool records or
  equal models across microscopes are merged. Stable instrument keys combine the
  instrument ID and objective ID; missing/duplicate source IDs fail rather than
  causing a silent merge or a position-dependent link.
- Instrument entries offer **View microscope**, not a borrowing request. Catalogue
  associations are not portable compatibility approvals. Pool enquiries retain their
  original fault warnings; faults on one source record are not copied to equal models.
- No source YAML objective, installed-instrument export, methods-generator input,
  LLM instrument inventory or simulator configuration is expanded by this feature.
  Joining these records for discovery is not installing an objective.
- The complete server-rendered catalogue is readable without JavaScript, including
  labelled historical entries. JavaScript applies the current-only default and filters.
  Shared item links reveal their target despite conflicting filters; unknown microscope
  links produce a notice, not a misleading empty catalogue.
- Unknown quantities, whereabouts, compatibility, condition and inspection dates
  remain unknown. Verified physical IDs, loans and movement history require subsequent
  evidence-backed work, not automatic reconciliation by this catalogue.

### Validation

Unit tests cover all three installation states, duplicate/missing IDs, nonmutation,
source coverage, optional notes, units and exclusion validation. Chromium interaction
tests cover filters, history, unknown state, old anchors and query input (only the
query-string boundary is stubbed for offline execution). A separate generated-MkDocs
acceptance test exercises real navigation, assets, instrument links, historical queries,
mobile overflow and browser errors on a local HTTP server. That test explicitly skips
only when MkDocs is absent; CI installs the build dependencies and runs it.

## Original spare-pool design review


| Option | Benefit | Objection | Decision |
|---|---|---|---|
| Word document or static table | Small change, preserves list | Limited filtering; damaged optics and missing data easy to overlook | Preserve source text within item details, not as the main interface |
| Add spares to individual microscopes | Convenient discovery | No verified compatibility or current installation evidence; duplicates stock and risks false methods claims | Reject until combinations and installations are documented |
| Separate searchable catalogue | Fits the existing YAML/MkDocs architecture | Could still look like live stock or compatibility approval | Selected with explicit condition, availability and staff-check boundaries |
| Full booking/loan application | Tracks movements | No physical IDs, stock counts, storage locations or lending process supplied; static site has no transaction backend | Defer; do not fake bookings with browser storage |

The original spare-pool page, now included in the unified **Objectives** catalogue, uses a server-rendered catalogue with search, filters, sorting, stable record links, original source details and copyable enquiries. The unified discovery view never adds pool records to installed instrument hardware, the methods generator or the simulator. No message or booking is sent.

## Source and boundaries

The supplied `ZEISSThread M27.docx` was read and both pages visually inspected. `docs/sources/objective_pool_020426.txt` preserves the text (trailing whitespace trimmed); the original file SHA-256 is in `inventory/objective_pool.yaml`. The binary document is not committed. The literal date `020426` is not interpreted as an ISO date without confirmation.

There are **35 source records: 34 objectives and one ZEISS APO Calibration LSM item**. Source groups contain ZEISS 18, Leica 11, Olympus 3, IncuCyte 2 and Nikon 1 records. These are not verified physical-stock counts. All quantities, storage locations, current availability and inspection dates are unknown.

Eight records carry problem notes: one ZEISS internal-droplet warning; two Leica stuck irises and one Leica UV-transmission issue; two Olympus stuck correction collars; and two damaged IncuCyte objectives. IncuCyte 4628 is recorded as unusable and not offered for imaging. Absence of a problem note means **Not assessed**, not working or available.

Preserved rather than silently corrected:

- Original codes, including spaces, en dashes and parenthesised alternatives. A row with two codes is not expanded into two physical objectives.
- Leica NA ranges 1.00-0.50, 1.40-0.60 and 1.40-0.70.
- Missing WD for Leica 506170 and the Olympus/IncuCyte lenses; missing Olympus product codes; missing Nikon mounting information.
- The ZEISS 441351-9970 qualifier `2,9 at cover glass 0,75`. WD units are not stated explicitly in the source. Values remain source text until units are confirmed.
- Mount headings ZEISS `M27/0.75`, Leica `M25`, Olympus `thread 20` / `tubus length 160`, and IncuCyte `thread -23`. No pitch, adapter, RMS or individual objective compatibility is inferred.
- Unspecified immersion for Olympus, IncuCyte and Nikon. Universal immersion does not establish an approved list of liquids. No magnification, NA or immersion is invented for the calibration item.

## Challenges to the chosen design

**Could a matching thread imply compatibility?** The page offers no compatibility filter, microscope recommendation or automatic installation. A brand/thread is a source descriptor. Optical correction, tube systems and parfocal length also matter. This is a general design boundary supported by Nikon's primary explanation, not evidence about these specific lenses:
https://www.microscopyu.com/microscopy-basics/working-distance-and-parfocal-length

**Could damaged optics look like normal stock?** All records and warnings are visible by default. The unusable item's enquiry asks about its status, not availability for imaging. Copy text includes condition and availability.

**Could an unflagged row look inspected?** It is marked Not assessed. Available stock requires a serviceability check with an inspection date and person; source compilation dates do not count as inspections.

**Could spares contaminate publication methods?** The dedicated JSON declares `inventory_kind: objective_pool`, `installed_hardware: false` and `compatibility_status: not_verified`. No pool records are passed to existing instrument exports. Installation requires a separate instrument-ledger update supported by evidence.

**Does the catalogue fail without JavaScript, network or clipboard access?** All records, warnings and enquiry text are present in the generated HTML. JavaScript only filters, sorts and copies; it needs no data fetch or new CDN. Without it, users can use browser Find and copy text manually. Clipboard failures select the enquiry and explain manual copying.

**What about stale filters and shared links?** A stable item anchor reveals its target and clears conflicting filters. Generated catalogue IDs are not described as physical asset tags or serial numbers.

## Implementation and maintenance

`inventory/objective_pool.yaml` -> `schema/objective_pool.schema.json` plus semantic checks -> canonical pool -> explicit display view -> page and `assets/objective_pool.json`.

`python -m scripts.validate` checks the pool along with existing ledgers when its schema or inventory is present, and requires both. Minimal instrument-only fixtures without either remain supported. The builder preflights the pool before replacing generated pages and fails on malformed/missing data even in non-strict mode. An explicitly empty `items: []` is supported. Duplicate YAML keys/IDs, invalid references/numbers and inconsistent availability/condition are rejected.

The schema owns filter labels. The browser never infers missing hardware. Update source YAML, not generated `dashboard_docs`. PR validation and deployment watch `inventory/**`; pool-schema changes trigger deployment too. The normal dependency sets include the JSON Schema validator. Facility contact and enquiry name come from `facility.yaml`.

Keep catalogue IDs stable. Split physical records only when multiple distinguishable copies are confirmed. `quantity: null` means unknown, not one. A serviceability check can be recorded as `condition: verified_serviceable`, `inspection: {date: 'YYYY-MM-DD', by: 'Reviewer'}` and appropriate notes. Only then can `availability: available` be used. Update availability promptly: this remains a staff-maintained snapshot, not a booking system. Microscope compatibility remains unverified in this first version, even for serviceable items.

Do not erase problem history without documenting reassessment. Use actual inspection dates, not commit dates. Confirm installations and their effective dates in microscope ledgers; do not let catalogue status alter them implicitly. Future compatibility records need configuration-specific evidence, separately from stock and condition.

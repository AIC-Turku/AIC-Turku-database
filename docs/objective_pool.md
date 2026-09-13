# Spare objectives: design and maintenance

## Options and adversarial review

| Option | Benefit | Objection | Decision |
|---|---|---|---|
| Word document or static table | Small change, preserves list | Limited filtering; damaged optics and missing data easy to overlook | Preserve source text within item details, not as the main interface |
| Add spares to individual microscopes | Convenient discovery | No verified compatibility or current installation evidence; duplicates stock and risks false methods claims | Reject until combinations and installations are documented |
| Separate searchable catalogue | Fits the existing YAML/MkDocs architecture | Could still look like live stock or compatibility approval | Selected with explicit condition, availability and staff-check boundaries |
| Full booking/loan application | Tracks movements | No physical IDs, stock counts, storage locations or lending process supplied; static site has no transaction backend | Defer; do not fake bookings with browser storage |

The new **Spare objectives** navigation category and homepage link lead to a server-rendered catalogue with search, filters, sorting, stable record links, original source details and copyable enquiries. It never adds pool records to installed instrument hardware, the methods generator or the simulator. No message or booking is sent.

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

## Copy-ready Slack draft (not sent)

Hi everyone, please help us complete the new spare-objective section of the AIC website. We have entered Jari's list and kept the reported problems visible. Could you help with these remaining details?

1. Does "020426" mean 2 April 2026? Are all working-distance values in the list in millimetres?
2. Where is the pool stored, who should users contact, and are these lenses still in the pool? Please flag anything installed, on loan or no longer held. Are any entries multiple physical copies?
3. Have these problems been repaired or reassessed: ZEISS 1022-818 (internal droplets); Leica 506007/506316 (stuck iris) and 506082 (UV transmission); Olympus 20x/40x CDPlan (stuck collars); IncuCyte 4628/4629 (damaged lenses)? Please give the check date and who checked them.
4. What is the working distance of Leica 506170? Do we have working distances and immersion details for the Olympus/IncuCyte lenses, and immersion/mounting details for Nikon MRH 00041?
5. What do "thread 20" and "thread -23" mean, and what is the Leica M25 pitch? Are the group-level thread labels correct for every objective in each group?
6. Which objective/microscope combinations have actually been checked, and do any need adapters or particular settings? Please distinguish optical suitability from simply being able to screw a lens in.
7. Is ZEISS APO Calibration LSM 420639-9000-700 (SN 53811) calibration-only, and who should authorise its use?

Photos of accessible labels, a storage list or partial answers are welcome. Please do not install or remove objectives just to answer these questions. Thanks!

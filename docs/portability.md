# Reusing this project at another imaging facility

This project is built so a second facility can publish its own dashboard by
editing configuration and YAML records, not Python or JavaScript. This page
records what that actually requires, what is reused unchanged, and which
AIC-specific assumptions remain on purpose.

The claim is exercised by `tests/test_facility_portability.py`, which builds a
complete site for a synthetic facility (`tests/fixtures/example_facility/`)
using only the documented build command and then asserts that no generated page
names AIC.

## Minimum files another facility edits

| File | Why it must change |
| --- | --- |
| `facility.yaml` | Facility identity, public URLs, acknowledgements, branding, and withheld records. Everything the generated site says *about the facility* comes from here. |
| `instruments/*.yaml` | The local microscope inventory. Instrument IDs here are the IDs every other layer refers to. |
| `inventory/objective_pool.yaml` | **Required.** The build fails before writing any page if this file is missing or invalid. A facility with no spare pool still needs a valid file with an empty `items` list. |

Edited only when the local situation differs:

| File | When |
| --- | --- |
| `vocab/*.yaml` | Local hardware needs controlled terms the shipped vocabularies do not cover. Validation rejects unknown terms rather than passing them through, so this is where new terms belong. |
| `schema/instrument_policy.yaml`, `schema/QC_policy.yaml`, `schema/maintenance_policy.yaml` | The local completeness or event policy differs. |
| `assets/images/logo.svg`, `assets/images/favicon.svg` | Facility branding. The shipped files are a generic microscope glyph, not AIC branding, so they can also be left as they are. `branding.logo` / `branding.favicon` in `facility.yaml` can point elsewhere instead. |
| `assets/images/<instrument_id>.jpg` | Optional local instrument photos, resolved by instrument ID. Missing photos fall back to `assets/images/placeholder.svg`. Remove production AIC instrument photos when creating a reusable fork so an identical instrument ID cannot accidentally select an AIC photo. |
| `qc/sessions/**`, `maintenance/events/**` | Local QC and maintenance history. Both are optional; instruments with no events render an explicit "no events recorded" note rather than an empty page. |

Nothing else has to be touched to get a working, correctly branded site.

## What is reused unchanged

- **All of `scripts/`.** Validation, canonical DTOs, light-path parsing, the
  dashboard/LLM/methods/VM exports, and page rendering contain no facility
  identity.
- **All of `assets/javascripts/`.** The Virtual Microscope, Methods generator,
  objective catalogue and chart runtimes read their facility-specific values
  from the JSON config block each generated page embeds.
- **`mkdocs.yml`.** It is *generated* by the dashboard build from
  `facility.yaml` plus the instrument ledger — site name, site URL, logo,
  favicon, and the full navigation including every instrument page. Editing it
  by hand is reverted by the next build.
- **`.github/workflows/`.** The deploy workflow leaves the authored site URL to
  `facility.public_site_url`, so a fork can use its normal GitHub Pages URL, a
  Pages custom domain, or another canonical public URL without changing Python
  or JavaScript. The GitHub environment link is reported from the Pages deploy
  action itself rather than being hard-coded from the repository owner/name.
- **`vocab/`, `schema/`, `assets/data/spectra/`** as shipped, unless the local
  inventory needs more terms or stricter policy.

## Facility-specific behaviour in `facility.yaml`

```yaml
facility:
  short_name: "Example Imaging"          # used wherever a page addresses visitors
  full_name: "Example Imaging Facility at Example University"
  site_name: "Example Imaging Microscopy Dashboard"   # browser/site title
  public_site_url: "https://example.org/dashboard/"
  contact_url: "https://example.org/imaging/contact/" # "Contact ... staff" links
  organization_url: "https://example.org/imaging/"
  non_public_instrument_ids: []          # ledger records withheld from the public site
  acknowledgements:
    standard: "Imaging was performed at ..."
    # Added to a methods draft only when one of the listed instruments was used.
    additional:
      - text: "The confocal was funded by the Example Instrument Donation Fund."
        instrument_ids: [scope-example-confocal]
  methods_generator:
    output_title: "Light Microscopy Methods"
  plan_experiments:
    contact_button_label: "Contact Example Imaging Staff"
branding:
  logo: "assets/images/logo.svg"
  favicon: "assets/images/favicon.svg"
```

`short_name` (falling back to `full_name`) is the name every generated page uses
when it tells a reader who to ask about access, training, or missing metadata.
With neither set, pages read "Core Imaging Facility" rather than naming any real
facility. The fallback is applied after loading `facility.yaml`, so a deployment
that authors only `full_name` does not inherit the neutral default short name.

`acknowledgements.additional[]` binds a conditional credit to **recorded
instrument IDs**. An unknown ID fails the build instead of silently detaching
the credit, the same rule `non_public_instrument_ids` follows. The older
`acknowledgements.xcelligence_addition` key — which made the frontend recognise
one AIC instrument by name — is rejected with a message pointing here, so a fork
that copied it is told rather than quietly losing the text.

## Build and verify

```bash
pip install -r requirements-docs.txt
PYTHONPATH=. python scripts/dashboard_builder.py --strict   # writes dashboard_docs/ and mkdocs.yml
mkdocs build --strict
```

The strict build reports missing or inconsistent metadata as diagnostics. It
does not invent values, so a new facility's first build is expected to list gaps
in its own records.

## Remaining AIC-specific assumptions (intentional)

These are deliberate and do not block reuse:

1. **`aic-*` identifier namespaces.** CSS class names (`aic-card`,
   `aic-timeline-*`), custom properties (`--aic-status-color`), `data-aic-*`
   attributes, DOM element IDs (`aicSearch`), the shared browser storage key
   `aic.virtualMicroscope.selectedConfiguration`, and the `[AIC]` console
   prefix. These are private identifiers, not text a visitor reads. Renaming
   them would invalidate users' stored Virtual Microscope configurations and
   restyle every page for no portability gain.
2. **The production data itself.** `instruments/`, `qc/`, `maintenance/`,
   `inventory/objective_pool.yaml` and the instrument photos in
   `assets/images/` are AIC records. A fork replaces them. The portability test
   intentionally reuses only generic runtime assets and generic glyphs, not AIC
   instrument photos.
3. **Inventory-specific tests.** Several suites assert against AIC's own records
   — objective counts, specific instrument IDs, QC metric histories. A fork that
   replaces the inventory must update or drop these. The portability boundaries
   themselves are covered separately by `tests/test_facility_portability.py`,
   which is inventory-independent.
4. **`docs/light_path_model.md`.** The current light-path authoring contract. A
   fork needs it to author `hardware.sources`, `optical_path_elements` and
   `light_paths` correctly.
5. **`scripts/import_spectrascope.py`** defaults its `--source` to a
   `SpectraScope-master` directory beside the repository. It is an optional
   import utility with an explicit flag, not part of the production build path.

## Boundary being defended

Configuration covers **facility identity and facility-specific behaviour**:
names, URLs, branding, acknowledgements, which records are public, and which
instruments a conditional credit belongs to.

It deliberately does **not** cover generic UI terminology. Page headings such as
"Fleet overview", "Objectives" or "Methods generator", and phrasing such as
"staff can help with access and training", are the application's own language.
Turning every string into configuration would make deployments harder to
maintain without making any of them more portable.

# Methods Generator black-box functional and scientific prose audit

> Archived verbatim for traceability: independent external (ChatGPT) black-box audit of the Methods generator, consolidated with the in-repo audit in [`methods_generator_consolidated_findings.md`](methods_generator_consolidated_findings.md). Not edited.

**Repository:** `AIC-Turku/AIC-Turku-database`  
**Audited commit:** `2988377cfafe3ac8b5db0d459f0e4d372e7c1ce3` (current `main` deployment artifact at audit time)  
**Audit approach:** rendered deployed UI, browser-driven selections and Add-acquisition interactions first; implementation inspected only after user-visible failures were reproduced. No code was changed and nothing was merged.

## A. Executive assessment

### Overall readiness
The current Methods Generator is **not yet ready to be presented as reliably publication-ready for unsupervised real users**. It is already useful as a structured first-draft generator, and many clean single-acquisition cases produce scientifically sensible prose. However, four reproducible High-severity failure classes mean a user can still obtain text that incorrectly states hardware was used, omits the actual imaging method, publishes unresolved hardware placeholders, or accepts a severely incomplete specialist acquisition without a direct warning.

I found **no Critical defects** under the requested severity definition. I identified **4 High**, **5 Medium**, and **1 Low** systemic defect classes. Across the captured runs, the scenario-level assessments were: **PASS: 20**, **MINOR ISSUE: 67**, **MAJOR ISSUE: 25**.

### Scientific reliability
- **Strong:** method identity is generally kept separate from physical path. STED stays STED even though it uses the point-scanning path; Airyscan is reported as ISM/Airyscan; FLIM/FRET/FCS/Spectral are additive readouts rather than route names. Route-specific sources, filters and detectors clear correctly when the method changes.
- **Blocking weakness:** method-independent UI state is not actually method-independent. Specialist modules remain checked across method changes and are then stated as used in the next acquisition. Placeholder detector identities can also be emitted as facts.
- **Fail-safe weakness:** Add acquisition validates method/path in the method-first workflow, but it does not validate technique-essential hardware. A STED draft can be generated with no excitation source, no depletion source and no detector.

### Generated prose
- Clean configurations often produce a usable two-paragraph structure: method + instrument/objective/software, then illumination/optics/detection.
- Prose degrades when metadata are incomplete: "Unknown Camera", bare manufacturer names, "other microscope", and "route" language leak into publication-facing text or its review block.
- Review prompts are often scientifically useful for STED, TIRF, SIM, SMLM, Airyscan, FLIM/FRET/FCS and light-sheet. The main systemic problem is that global database blockers are mixed into experiment-specific review prompts, creating irrelevant and duplicate warnings.

### Selection workflow
- The method → compatible physical path workflow is substantially improved. Incompatible routes are hidden/disabled, and a sole compatible path is automatically selected.
- The largest state bug is outside route-specific controls: `module` checkboxes are global and survive a method change even when the module is incompatible with the new method.
- The retired SP5 multiphoton record bypasses the method-first workflow entirely; it can add an acquisition with no path selected, and even after selecting the Multiphoton path the finished text never explicitly says multiphoton/two-photon imaging.

### Incomplete metadata
- The generator is conservative in some places: it asks users to verify unresolved optics and technique-specific settings rather than inventing values.
- It is not conservative enough in others: an unresolved camera can become `Unknown Camera`, while broad instrument-level blockers such as `Software version is not recorded` are appended even when the user did not select acquisition software.

### Multi-acquisition sections
- Multiple acquisitions are accumulated correctly at a basic level, but the output reads as concatenated form entries. The same instrument, objective, software, specimen prompt and generic reporting advice are repeated.
- More importantly, the stale-module defect crosses acquisition boundaries: STED→confocal, SIM→widefield and Airyscan→conventional confocal can make the second entry scientifically wrong.

## Audit coverage

- **72** distinct baseline method/instrument configurations captured through the UI.
- **17** additional targeted specialist configurations captured successfully (STED, RESOLFT, SIM, SMLM, TIRF, spectral, FLIM, FRET, FCS, light-sheet, reflected light).
- **13** adversarial checkbox/state-change runs.
- **10** two-acquisition Methods sections.
- **112 total successfully captured UI runs** represented in the attached machine-readable bundle. Three exploratory specialist attempts failed only because the audit harness requested an imprecise label; they were excluded and not counted as application failures.

Coverage includes widefield fluorescence, transmitted brightfield, phase contrast, DIC, darkfield, point-scanning confocal, spinning-disk confocal, TIRF, STED, RESOLFT, SIM, SMLM, ISM/Airyscan, multiphoton, light-sheet, spectral readout, FLIM, FRET, FCS, optical sectioning and reflected-light imaging where exposed by the catalogue.

## C. Prioritised defect list

### D1. Specialist modules survive method changes and are reported as used — HIGH

**Affected:** Abberior STED/RESOLFT, DeltaVision OMX SIM/TIRF, Zeiss LSM 880 Airyscan, Leica STELLARIS FLIM; also multi-acquisition sections using those transitions.

**Reproduction:**
Example: select Abberior → STED → point-scanning path → Easy3D STED module → objective + excitation/depletion + detector; then change the method to Confocal point scanning and add the acquisition. Equivalent failures reproduce for SIM→widefield, TIRF→widefield, Airyscan→transmitted brightfield and FLIM→widefield.

**Actual generated text:**
```text
Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
```

**Expected behavior:** Changing method/path must clear any specialist module that is no longer compatible. A confocal-reference acquisition must not claim the Easy3D STED module unless the user deliberately selects it for that acquisition and the UI marks it compatible.

**Likely root cause:** `assets/javascripts/methods_generator_app.js` binds `dto.modules` globally. The method-change handler explicitly clears route/readout/light/detector/filter/splitter state, but `module` is absent from that clear/filter list. The prose builder later treats every checked module as actually used.

**Suggested fix:** Attach method/path compatibility metadata to modules and re-render/filter them exactly like route-specific hardware. On method/path change, clear checked modules that are not explicitly compatible. At minimum, clear `module`, `optical-modulator` and `illumination-logic` on a method change unless a component is explicitly marked compatible with both old and new configurations.

**Browser regression:** Use real records and exact clicks: (1) Abberior STED→Confocal; (2) DeltaVision SIM→Widefield; (3) LSM880 ISM/Airyscan→Transmitted; (4) STELLARIS Confocal+FLIM→Widefield. Assert the previous module becomes unchecked/hidden and its name is absent from generated text.

### D2. Legacy multiphoton workflow can add a route-less acquisition and never states the method — HIGH

**Affected:** Retired Leica TCS SP5 Multiphoton (and any future route-only/legacy record without method-first identity).

**Reproduction:**
Open Leica TCS SP5 Multiphoton and click Add acquisition before selecting the Multiphoton path. Then select the sole Multiphoton path, software, objective, laser and NDD PMT and add again.

**Actual generated text:**
```text
Light Microscopy Methods:

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope.

Review before publication:
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope, with the Multiphoton route. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). Instrument control and image acquisition were performed using Leica LAS AF.

Excitation was provided by pulsed near-ir laser (Coherent Chameleon Vision II). Images were recorded using NDD PMT.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting excitation wavelength, mean power at the sample, and pulse width. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Leica LAS AF]
```

**Expected behavior:** If a physical path exists, Add must require it even when no method picker was built. For this record the method should be recoverable as Multiphoton imaging (or two-photon fluorescence microscopy), the sole path should auto-select, and finished prose should never fall back to “with the Multiphoton route”.

**Likely root cause:** The source YAML records `modalities: [confocal_point, multiphoton]` and a Multiphoton light path, but the deployed route identity exposes no method option. Add validation is gated by `methodFirst`, so route-only instruments bypass the route check. The prose fallback uses route labels when no method exists.

**Suggested fix:** Migrate/derive the route identity from the recorded multiphoton modality and give it a publication phrase. Independently require a selected physical path whenever a route section exists; auto-select a sole route. Remove the route-clause fallback from finished prose and keep topology/schema diagnostics outside publication text.

**Browser regression:** Real SP5 browser test: immediately clicking Add must not append an acquisition; selecting the instrument should expose/derive Multiphoton imaging and auto-select the only compatible path; a completed acquisition must contain “multiphoton” or “two-photon” as the method and must not contain “route”, “Capability axes”, “Optical path element ID/type” or “Light path route type”.

### D3. Placeholder/unresolved hardware identities leak into finished prose — HIGH

**Affected:** Leica DM IRBE, DM RB and DM RE camera-port records; Zeiss LSM 510 JPK AFM placeholder objective/detector data.

**Reproduction:**
On a Leica DM IRBE/RB/RE choose a normal imaging method and select the UI camera option labelled `Unknown Camera — Unknown`; generate. On LSM510 choose confocal and the available endpoint/objective.

**Actual generated text:**
```text
Widefield fluorescence imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Illumination was provided by arc lamp (Leica 50W HBO short arc bulb). The light path included Filter Cube EGFP in the Fluorescence Turret. Images were recorded using Unknown Camera.

Review before publication:


Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The microscope used a galvanometric scanner.

Illumination was provided by 488 nm laser. Images were recorded using Zeiss.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
```

**Expected behavior:** Unresolved identities must never be presented as publication facts. Omit the unresolved component from finished prose and add a direct review prompt such as `[PLEASE SPECIFY: detector manufacturer and model]`. A bare manufacturer such as “Zeiss” is not a sufficient detector identity. Placeholder should not appear in user-facing publication/review wording.

**Likely root cause:** The source records contain placeholder identities (`manufacturer: Unknown`, `model: Unknown Camera`). Placeholder sanitization exists in parts of `instrument_view.py`, but the optical-path publication projection still constructs publication labels/method sentences from fallback/display identity, and can accept a manufacturer alone as sufficient endpoint identity.

**Suggested fix:** Centralize a publication-identity validator for objectives/sources/endpoints/modules. Treat Unknown/Placeholder and single-field non-identifying fallbacks as unresolved. UI can display an unresolved option, but Methods prose must omit it and generate a specific identity prompt.

**Browser regression:** Run real DM IRBE widefield + camera and LSM510 confocal. Assert generated publication prose contains none of `Unknown`, `Placeholder`, or `Images were recorded using Zeiss.` and instead has the specific missing detector/objective identity prompts.

### D4. Severely incomplete specialist acquisitions are accepted without essential-hardware warnings — HIGH

**Affected:** Specialist techniques where essential hardware can be selected but is omitted; reproduced on Abberior STED.

**Reproduction:**
Select Abberior → STED → 100× objective. Deliberately select no excitation source, no depletion source, no detector, no acquisition software and click Add acquisition.

**Actual generated text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:
```

**Expected behavior:** The generator should either block Add with actionable missing essentials or emit explicit warnings that no excitation source, STED depletion source and detector were selected. A generic “report depletion wavelength/power” recommendation is not equivalent to noticing the absence of the depletion beam itself.

**Likely root cause:** The Add handler enforces method and path presence but has no technique-aware minimum-selection validation. Technique prompts report settings that should be documented, not whether the essential component category was selected at all.

**Suggested fix:** Add method-specific essential-category contracts (for example STED: excitation + depletion + detector; fluorescence imaging: excitation + detector; SMLM: excitation/detection with activation optional/conditional). Prefer an explicit incomplete-acquisition status over inventing defaults.

**Browser regression:** Abberior STED + objective only: Add must be blocked or output must contain explicit missing source/depletion/detector warnings. Repeat for SIM and SMLM with their essential categories.

### D5. Instrument-global metadata blockers are mixed into acquisition-specific review prompts — MEDIUM
The review block appends all `methods_generation.blockers` for the instrument, regardless of what the user selected. This produces 33/72 baseline outputs with a generic `Software version is not recorded` warning. In ONI SMLM it appears even when acquisition software is unchecked; when NimOS is checked, the generator emits both a specific version prompt and the generic software warning. Similar global module-model warnings can appear when no module was selected.

**Fix:** keep facility data-quality blockers in a separate UI diagnostic. Promote only blockers tied to selected components/actions into `Review before publication`. Dedupe a specific acquisition-software-version prompt against any generic software blocker.

**Regression:** generate ONI SMLM once with NimOS unchecked and once checked. The first must not mention acquisition-software version; the second must contain one specific NimOS version prompt, not two.

### D6. Implementation vocabulary leaks into publication/review text — MEDIUM
Examples include `Point-scanning confocal route`, `Spinning-disk confocal route`, `selected route`, the SP5 phrase `with the Multiphoton route`, and schema terms such as `Capability axes`, `Optical path element ID`, `Optical path element type`, and `Light path route type`. These are meaningful internally but do not belong in a microscopy Methods section or a user-facing manuscript checklist.

**Fix:** author user-facing hardware labels independently of route/schema labels. Phrase unresolved selectors as “which emission filter was used for this point-scanning acquisition?” rather than exposing the route abstraction. Move schema completeness diagnostics outside Methods output.

### D7. Raw light-source count is used as a proxy for channel count — MEDIUM
STED with one excitation laser + one depletion laser, RESOLFT switching illumination, and SMLM activation + excitation can trigger `[PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously…]`. These selected lights are not necessarily separate imaging channels.

**Root cause:** the prose builder counts checked `light` controls and fires the channel-order prompt when the count is >1. **Fix:** infer channel multiplicity from detection/channel structure and source roles; exclude depletion/activation/switching beams. Keep dedicated STED/SMLM sequencing prompts where appropriate.

### D8. Partially incomplete topology is not diagnosed granularly — MEDIUM
For 3i CSU-W1, 3i Marianas Med C and Leica Thunder transmitted-light modes, the UI can expose a detector but no illumination source, and the output does not directly say that illumination is unrecorded. By contrast, a fully empty LSM510 transmitted route gets a generic topology-incomplete warning. This all-or-nothing behavior can leave one missing side of a route silent.

**Fix:** track illumination and detection completeness independently per selected physical path. If a technique requires illumination and no source is recorded/selectable, prompt specifically for it; do the same independently for detection.

### D10. Multi-acquisition output is structurally repetitive — MEDIUM
The same microscope identity, objective, software sentence, specimen-preparation prompt and generic reporting recommendation are repeated for each acquisition. Even scientifically correct sections read like concatenated forms. Stale module state makes some combinations worse by turning repetition into incorrect science.

**Fix:** build a section-level renderer. Hoist invariant instrument/software/objective facts when identical, then describe the differences per acquisition. Aggregate and dedupe review prompts at the end of the Methods section while retaining acquisition-specific prompts where needed.

### D9. `other microscope` appears as an instrument description — LOW
ONI Nanoimager and M Squared Aurora output phrases such as `the ONI Nanoimager other microscope`. The stand-orientation enum value `other` is being rendered literally.

**Fix:** suppress `other`/unknown stand qualifiers in publication prose; use `the ONI Nanoimager` or `the M Squared Aurora Airy Beam microscope`.

## D. Prose-quality review

### What is working
- Method publication phrases are generally strong: `Stimulated emission depletion (STED) imaging`, `Structured illumination microscopy (SIM)`, `Single-molecule localization microscopy (SMLM)`, `Image scanning microscopy (ISM; Airyscan)`, and `Light-sheet imaging` are preferable to route-derived labels.
- Readouts are generally correctly additive: `FLIM data were acquired`, `FRET data were acquired`, `FCS data were acquired`, and spectral readout wording do not replace the underlying imaging method.
- Role-aware illumination sentences can be excellent when metadata are complete: STED output distinguishes excitation from stimulated-emission depletion instead of flattening both to lasers.
- Technique-specific reporting prompts are mostly scientifically sensible. The STED/TIRF/SIM/SMLM/Airyscan/FLIM/FRET/FCS/light-sheet prompts are materially better than one generic checklist.

### Systemic writing problems
1. **Form-like sentence cadence.** Many entries use `X imaging was performed… Imaging was performed with… The microscope used… Instrument control…`, which exposes the field-by-field assembly. Combining objective + scanner + acquisition software into one or two natural sentences would improve manuscript readability.
2. **Component-by-component reporting can become robotic.** The light-path paragraph is often one sentence per checkbox. Compatible source/filter/detector facts should be combined where doing so remains readable.
3. **Database vocabulary leaks.** `route`, schema blocker names, `Placeholder`, `Unknown`, and `other microscope` are the clearest examples.
4. **Review prompts are too globally repetitive.** The generic specimen-preparation and catch-all acquisition-settings prompts recur for every acquisition and dominate multi-acquisition sections.
5. **Source-role questions are sometimes implausibly broad.** Asking whether a 488-nm laser in a TIRF or light-sheet acquisition was “excitation, transmitted illumination, or depletion” is technically cautious but not useful to a microscopist. The current method/path should constrain the alternatives.
6. **Instrument naming can be verbose.** Names such as `3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope` are accurate but heavy when repeated across acquisitions. Section-level deduplication would solve most of this.

## E. Regression recommendations

### Required browser regressions for every High-severity defect
1. **Stale specialist modules:** real-instrument click sequences for Abberior STED→confocal, DeltaVision SIM→widefield, LSM880 Airyscan→transmitted, STELLARIS FLIM→widefield. Assert stale modules are unchecked and absent from output.
2. **Legacy route-only safeguard:** SP5 immediate Add must be rejected; sole path should auto-select or be required; completed output must explicitly state multiphoton imaging and contain no `route`/schema vocabulary.
3. **Placeholder publication invariant:** DM IRBE widefield + camera and LSM510 confocal must never emit `Unknown`, `Placeholder`, or a bare-manufacturer endpoint sentence; unresolved identities must become targeted review prompts.
4. **Incomplete specialist acquisition:** STED + objective only must be blocked or explicitly warn that excitation, depletion and detector selections are missing. Repeat the same design for SIM/SMLM essentials.

### Useful Medium-severity regressions
- ONI software unchecked/checked pair: assert selection semantics and one relevant version prompt only.
- STED 640+775 and SMLM 405+640: assert no generic “channels sequentially/simultaneously” prompt merely because two lights were checked.
- 3i transmitted route: assert a missing-illumination warning when detection is recorded but illumination is not.
- Multi-acquisition smoke test: repeated invariant facts/prompts should be deduplicated at section level.
- Lexical publication guard: in finished Methods prose reject `DTO`, `runtime`, `selected execution`, `inventory`, raw internal IDs, `Unknown`, `Placeholder`, and literal `other microscope`. Treat `route` as a UI/internal term, not a publication sentence term.

## B. Scenario results

### Baseline configuration matrix (72 distinct configurations)

| # | Instrument | Imaging method | Physical path | Assessment | Main finding |
|---:|---|---|---|---|---|
| 1 | 3i CSU-W1 Spinning Disk | Confocal spinning disk | Spinning-disk confocal | **MINOR ISSUE** | D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 2 | 3i CSU-W1 Spinning Disk | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 3 | 3i CSU-W1 Spinning Disk | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 4 | 3i CSU-W1 Spinning Disk | Phase contrast | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 5 | 3i CSU-W1 Spinning Disk | DIC | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 6 | 3i Marianas CSU-W1 Spinning Disk Med C | Confocal spinning disk | Spinning-disk confocal | **MINOR ISSUE** | D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 7 | 3i Marianas CSU-W1 Spinning Disk Med C | Widefield fluorescence | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 8 | 3i Marianas CSU-W1 Spinning Disk Med C | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 9 | 3i Marianas CSU-W1 Spinning Disk Med C | Phase contrast | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 10 | 3i Marianas CSU-W1 Spinning Disk Med C | DIC | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning. |
| 11 | Andor BC43 Benchtop Confocal | Confocal spinning disk | Spinning-disk confocal | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 12 | Andor BC43 Benchtop Confocal | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 13 | Andor BC43 Benchtop Confocal | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 14 | Andor BC43 Benchtop Confocal | Phase contrast | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 15 | EVOS fl | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 16 | EVOS fl | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 17 | EVOS fl | Phase contrast | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 18 | Leica DM IRBE | Widefield fluorescence | Widefield fluorescence | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 19 | Leica DM IRBE | Transmitted brightfield | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 20 | Leica DM IRBE | Phase contrast | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 21 | Leica DM IRBE | Darkfield | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 22 | Leica DM RB | Widefield fluorescence | Widefield fluorescence | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 23 | Leica DM RB | Transmitted brightfield | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 24 | Leica DM RB | Darkfield | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 25 | Leica DM RE | Transmitted brightfield | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 26 | Leica DM RE | DIC | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 27 | Leica DM RE | Phase contrast | Transmitted light | **MAJOR ISSUE** | D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera"). |
| 28 | Leica Thunder | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 29 | Leica Thunder | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 30 | Leica Thunder | Phase contrast | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 31 | Leica Thunder | DIC | Transmitted light | **MINOR ISSUE** | D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 32 | Nikon Ti2-E Crest V3 | Confocal spinning disk | Spinning-disk confocal | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 33 | Nikon Ti2-E Crest V3 | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 34 | Nikon Ti2-E Crest V3 | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 35 | Nikon Ti2-E Crest V3 | DIC | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 36 | Nikon Eclipse Ti2-E | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 37 | Nikon Eclipse Ti2-E | Transmitted brightfield | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 38 | Nikon Eclipse Ti2-E | DIC | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 39 | Nikon Eclipse Ti2-E | Phase contrast | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 40 | Olympus BX60 | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 41 | Olympus BX60 | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 42 | Olympus BX60 | Phase contrast | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 43 | Agilent xCELLigence RTCA eSight | Widefield fluorescence | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 44 | Agilent xCELLigence RTCA eSight | Transmitted brightfield | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 45 | Zeiss AxioZoom.V16 | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 46 | Zeiss AxioZoom.V16 | Optical sectioning | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 47 | Zeiss AxioZoom.V16 | Reflected brightfield | Reflected light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 48 | Zeiss AxioZoom.V16 | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 49 | Zeiss LSM 510 JPK AFM | Confocal point scanning | Point-scanning confocal | **MAJOR ISSUE** | D3: placeholder/incomplete hardware identity leaks into publication-facing output.; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 50 | Zeiss LSM 510 JPK AFM | Transmitted brightfield | Transmitted light | **MAJOR ISSUE** | D3: placeholder/incomplete hardware identity leaks into publication-facing output.; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 51 | Zeiss LSM 880 with AiryScan | Confocal point scanning | Point-scanning confocal | **MINOR ISSUE** | Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role. |
| 52 | Zeiss LSM 880 with AiryScan | ISM (AiryScan) | Point-scanning confocal | **PASS** | No reproduced user-facing defect in this configuration. |
| 53 | Zeiss LSM 880 with AiryScan | Transmitted brightfield | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 54 | Zeiss LSM 880 with AiryScan | DIC | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 55 | Zeiss TIRF | Widefield fluorescence | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 56 | Zeiss TIRF | TIRF | Widefield fluorescence | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role. |
| 57 | Zeiss TIRF | Transmitted brightfield | Transmitted light | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 58 | Abberior STED | Confocal point scanning | Point-scanning confocal | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 59 | Abberior STED | STED | Point-scanning confocal | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D7: raw light-source count is treated as channel count, producing an inappropriate sequencing prompt for specialist beams. |
| 60 | Abberior STED | RESOLFT | Point-scanning confocal | **MINOR ISSUE** | D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 61 | Deltavision OMX | Widefield fluorescence | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 62 | Deltavision OMX | TIRF | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 63 | Deltavision OMX | SIM | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 64 | Deltavision OMX | SMLM | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 65 | Lambert FLIM | Widefield fluorescence | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 66 | Leica STELLARIS 8 FALCON FLIM | Confocal point scanning | Point-scanning confocal | **MINOR ISSUE** | Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role. |
| 67 | Leica STELLARIS 8 FALCON FLIM | Widefield fluorescence | Widefield fluorescence | **PASS** | No reproduced user-facing defect in this configuration. |
| 68 | Leica STELLARIS 8 FALCON FLIM | Transmitted brightfield | Transmitted light | **PASS** | No reproduced user-facing defect in this configuration. |
| 69 | Leica TCS SP5 Multiphoton | Multiphoton | Multiphoton | **MAJOR ISSUE** | D2: legacy multiphoton record has no method-first selection; output falls back to "Multiphoton route" and schema-facing review language.; D6: implementation-oriented "route" terminology leaks into publication/review text. |
| 70 | MSquared Aurora Airy Beam | Light sheet | Light sheet | **MINOR ISSUE** | D9: stand-orientation vocabulary leaks as the phrase "other microscope".; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 71 | ONI Nanoimager | TIRF | Widefield fluorescence | **MINOR ISSUE** | D9: stand-orientation vocabulary leaks as the phrase "other microscope".; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |
| 72 | ONI Nanoimager | SMLM | Widefield fluorescence | **MINOR ISSUE** | D9: stand-orientation vocabulary leaks as the phrase "other microscope".; D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software. |

### Targeted specialist configurations

| Scenario | Configuration | Method | Path | Assessment |
|---|---|---|---|---|
| A01 | Abberior confocal GFP | Confocal point scanning | Point-scanning confocal | **MINOR ISSUE** |
| A02 | Abberior STED far-red | STED | Point-scanning confocal | **MINOR ISSUE** |
| A03 | Abberior STED 561 | STED | Point-scanning confocal | **MINOR ISSUE** |
| A04 | Abberior RESOLFT | RESOLFT | Point-scanning confocal | **MINOR ISSUE** |
| D01 | DeltaVision SIM | SIM | Widefield fluorescence | **PASS** |
| D02 | DeltaVision SMLM | SMLM | Widefield fluorescence | **MINOR ISSUE** |
| D03 | DeltaVision TIRF | TIRF | Widefield fluorescence | **PASS** |
| O01 | ONI SMLM | SMLM | Widefield fluorescence | **MINOR ISSUE** |
| O02 | ONI TIRF FRET | TIRF | Widefield fluorescence, FRET | **MINOR ISSUE** |
| S01 | Stellaris confocal | Confocal point scanning | Point-scanning confocal | **MINOR ISSUE** |
| S02 | Stellaris spectral | Confocal point scanning | Point-scanning confocal, Spectral Imaging | **MINOR ISSUE** |
| S03 | Stellaris FLIM | Confocal point scanning | Point-scanning confocal, FLIM | **MINOR ISSUE** |
| S04 | Stellaris FCS | Confocal point scanning | Point-scanning confocal, FCS | **MINOR ISSUE** |
| S05 | Stellaris FRET | Confocal point scanning | Point-scanning confocal, FRET | **MINOR ISSUE** |
| Z02 | Zeiss TIRF | TIRF | Widefield fluorescence | **MINOR ISSUE** |
| L01 | Aurora light sheet | Light sheet | Light sheet | **MINOR ISSUE** |
| R01 | AxioZoom reflected | Reflected brightfield | Reflected light | **MINOR ISSUE** |

### Adversarial state/checkbox scenarios

| Scenario | Instrument | Test | Assessment |
|---|---|---|---|
| T01 | Abberior STED | STED selections then switch to confocal | **MAJOR ISSUE** |
| T02 | Deltavision OMX | SIM module/hardware then switch to widefield | **MAJOR ISSUE** |
| T03 | Deltavision OMX | TIRF module/objective then switch to widefield | **MAJOR ISSUE** |
| T04 | Zeiss LSM 880 with AiryScan | Airyscan module/laser then switch to transmitted brightfield | **MAJOR ISSUE** |
| T05 | Leica STELLARIS 8 FALCON FLIM | Confocal+FLIM readout/module then switch to widefield | **MAJOR ISSUE** |
| T06 | 3i CSU-W1 Spinning Disk | Spinning-disk fluorescence hardware then switch to transmitted brightfield | **PASS** |
| T07 | 3i CSU-W1 Spinning Disk | Transmitted hardware then switch to spinning-disk confocal | **PASS** |
| T08 | ONI Nanoimager | SMLM generated with acquisition software intentionally unchecked | **MINOR ISSUE** |
| T09 | ONI Nanoimager | Same SMLM configuration with acquisition software checked | **MINOR ISSUE** |
| T10 | Abberior STED | Optional STED module selected then deselected before generation | **MINOR ISSUE** |
| T11 | Abberior STED | Generate STED before choosing illumination/detector/software | **MAJOR ISSUE** |
| T12a | Leica TCS SP5 Multiphoton | Attempt generation before choosing the only Multiphoton physical path | **MAJOR ISSUE** |
| T12b | Leica TCS SP5 Multiphoton | Choose only Multiphoton physical path and generate | **MAJOR ISSUE** |

### Multi-acquisition sections

| Scenario | Instrument | Acquisitions | Assessment |
|---|---|---|---|
| M01 | 3i CSU-W1 Spinning Disk | Widefield followed by spinning-disk confocal | **MINOR ISSUE** |
| M02 | 3i CSU-W1 Spinning Disk | Transmitted brightfield followed by fluorescence | **MINOR ISSUE** |
| M03 | Abberior STED | STED followed by confocal reference imaging | **MAJOR ISSUE** |
| M04 | Deltavision OMX | SIM followed by conventional widefield | **MAJOR ISSUE** |
| M05 | ONI Nanoimager | SMLM followed by TIRF | **MINOR ISSUE** |
| M06 | Zeiss LSM 880 with AiryScan | Airyscan followed by conventional confocal | **MAJOR ISSUE** |
| M07 | Leica STELLARIS 8 FALCON FLIM | FLIM acquisition followed by FRET acquisition | **MINOR ISSUE** |
| M08 | Leica Thunder | Phase contrast followed by fluorescence | **MINOR ISSUE** |
| M09 | Zeiss TIRF | Conventional fluorescence followed by TIRF | **MINOR ISSUE** |
| M10 | Leica DM IRBE | Darkfield followed by widefield fluorescence | **MAJOR ISSUE** |

## Full scenario record

Every successfully captured UI run is reproduced below with the selected controls and exact generator output. The exact text is intentionally preserved verbatim, including acknowledgements and awkward wording.

<details><summary><strong>1. scope-3i-csu-w1-spinning-disk:Confocal spinning disk — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Confocal spinning disk</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path:** Spinning-disk confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
- **method:** Confocal spinning disk
- **route:** Spinning-disk confocal
- **scanner:** Spinning Disk Scanner
- **objective:** Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
- **light:** 488 nm laser (3i LaserStack v4) — 3i
- **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). The microscope used a spinning disk scanner (pinhole 50 µm). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Spinning Disk Scanner]
- [PLEASE SPECIFY: which position of CSU-W1 Dichroic Slider (Spinning-disk confocal route) and CSU-W1 Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>2. scope-3i-csu-w1-spinning-disk:Widefield fluorescence — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Widefield fluorescence</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
- **light:** LED (Excelitas X-Cite XLED1) — Excelitas
- **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by LED (Excelitas X-Cite XLED1). Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of XLED Excitation Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>3. scope-3i-csu-w1-spinning-disk:Transmitted brightfield — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Transmitted brightfield</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
- **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>4. scope-3i-csu-w1-spinning-disk:Phase contrast — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Phase contrast</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
- **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>5. scope-3i-csu-w1-spinning-disk:DIC — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / DIC</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
- **method:** DIC
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
- **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>6. scope-3i-csu-w1-spinning-disk-med-c:Confocal spinning disk — MINOR ISSUE</strong> — 3i Marianas CSU-W1 Spinning Disk Med C / Confocal spinning disk</summary>

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Confocal spinning disk  
**Physical path:** Spinning-disk confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using SlideBook (v6).
- **method:** Confocal spinning disk
- **route:** Spinning-disk confocal
- **scanner:** Spinning Disk Scanner
- **objective:** Plan-Apochromat 63x/1.4 NA Oil OIL — Zeiss
- **light:** 488 nm laser (3i LaserStack v4) — 3i
- **detector:** Photometrics Prime BSI — Photometrics

**Problems found:**
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). The microscope used a spinning disk scanner (pinhole 50 µm). Instrument control and image acquisition were performed using SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). Images were recorded using Photometrics Prime BSI.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Spinning Disk Scanner]
- [PLEASE SPECIFY: which position of CSU-W1 Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>7. scope-3i-csu-w1-spinning-disk-med-c:Widefield fluorescence — PASS</strong> — 3i Marianas CSU-W1 Spinning Disk Med C / Widefield fluorescence</summary>

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using SlideBook (v6).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** Plan-Apochromat 20x/0.8 NA AIR — Zeiss
- **light:** LED (CoolLED pE-300) — CoolLED
- **filter:** Zeiss Widefield Fluorescence Positions, LED-FITC-A-ZHE-Zero (catalogue no. LED-FITC-A-ZHE-Zero)
- **detector:** Photometrics Prime BSI — Photometrics

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8 NA, 420650-9902-000). Instrument control and image acquisition were performed using SlideBook (v6).

Illumination was provided by LED (CoolLED pE-300). The light path included LED-FITC-A-ZHE-Zero (catalogue no. LED-FITC-A-ZHE-Zero) in the Zeiss Widefield Fluorescence Positions. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE SPECIFY: the role of LED (CoolLED pE-300) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for LED-FITC-A-ZHE-Zero are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>8. scope-3i-csu-w1-spinning-disk-med-c:Transmitted brightfield — MINOR ISSUE</strong> — 3i Marianas CSU-W1 Spinning Disk Med C / Transmitted brightfield</summary>

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using SlideBook (v6).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 NA AIR — Zeiss
- **detector:** Photometrics Prime BSI — Photometrics

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8 NA, 420650-9902-000). Instrument control and image acquisition were performed using SlideBook (v6).

Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>9. scope-3i-csu-w1-spinning-disk-med-c:Phase contrast — MINOR ISSUE</strong> — 3i Marianas CSU-W1 Spinning Disk Med C / Phase contrast</summary>

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using SlideBook (v6).
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 NA AIR — Zeiss
- **detector:** Photometrics Prime BSI — Photometrics

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8 NA, 420650-9902-000). Instrument control and image acquisition were performed using SlideBook (v6).

Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>10. scope-3i-csu-w1-spinning-disk-med-c:DIC — MINOR ISSUE</strong> — 3i Marianas CSU-W1 Spinning Disk Med C / DIC</summary>

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using SlideBook (v6).
- **method:** DIC
- **route:** Transmitted light
- **objective:** Plan-Apochromat 20x/0.8 NA AIR — Zeiss
- **detector:** Photometrics Prime BSI — Photometrics

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.

**Suggested improvement:** See prioritized defects D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8 NA, 420650-9902-000). Instrument control and image acquisition were performed using SlideBook (v6).

Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>11. scope-andor-bc43:Confocal spinning disk — MINOR ISSUE</strong> — Andor BC43 Benchtop Confocal / Confocal spinning disk</summary>

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Confocal spinning disk  
**Physical path:** Spinning-disk confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
- **method:** Confocal spinning disk
- **route:** Spinning-disk confocal
- **scanner:** Spinning Disk Scanner
- **objective:** 60X Plan Apo LD Oil 60x/1.42 OIL — Nikon
- **light:** 488 nm laser (Andor Borealis Illumination) — Andor
- **detector:** Andor 4.1 MP sCMOS — Andor

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 60x/1.42 Oil objective (Nikon 60X Plan Apo LD Oil, INS-OBJ-60D-142-0). The microscope used a spinning disk scanner (pinhole 50 µm). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by 488 nm laser (Andor Borealis Illumination). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Spinning Disk Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>12. scope-andor-bc43:Widefield fluorescence — MINOR ISSUE</strong> — Andor BC43 Benchtop Confocal / Widefield fluorescence</summary>

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
- **light:** 488 nm laser (Andor Borealis Illumination) — Andor
- **detector:** Andor 4.1 MP sCMOS — Andor

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by 488 nm laser (Andor Borealis Illumination). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>13. scope-andor-bc43:Transmitted brightfield — MINOR ISSUE</strong> — Andor BC43 Benchtop Confocal / Transmitted brightfield</summary>

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
- **light:** LED (Andor Transmitted Light Illuminator) — Andor
- **detector:** Andor 4.1 MP sCMOS — Andor

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Transmitted-light illumination was provided by LED (Andor Transmitted Light Illuminator). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Transmitted light route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>14. scope-andor-bc43:Phase contrast — MINOR ISSUE</strong> — Andor BC43 Benchtop Confocal / Phase contrast</summary>

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
- **light:** LED (Andor Transmitted Light Illuminator) — Andor
- **detector:** Andor 4.1 MP sCMOS — Andor

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Transmitted-light illumination was provided by LED (Andor Transmitted Light Illuminator). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Transmitted light route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>15. scope-evos-fl:Widefield fluorescence — MINOR ISSUE</strong> — EVOS fl / Widefield fluorescence</summary>

**Instrument:** EVOS fl  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using On-board EVOS interface.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
- **light:** 357 nm LED (Thermo Fisher / AMG EVOS DAPI Light Cube LED) — Thermo Fisher / AMG
- **filter:** Light Cube Turret, GFP/Alexa 488 (catalogue no. ZP-EPI-9002)
- **detector:** AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD) — AMG (Thermo Fisher)

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by 357 nm LED (Thermo Fisher / AMG EVOS DAPI Light Cube LED). The light path included GFP/Alexa 488 (catalogue no. ZP-EPI-9002) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of 357 nm LED (Thermo Fisher / AMG EVOS DAPI Light Cube LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>16. scope-evos-fl:Transmitted brightfield — MINOR ISSUE</strong> — EVOS fl / Transmitted brightfield</summary>

**Instrument:** EVOS fl  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using On-board EVOS interface.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
- **light:** LED (Thermo Fisher / AMG Transmitted Light LED) — Thermo Fisher / AMG
- **detector:** AMG (Thermo Fisher) Sony ICX285AQ Color CCD — AMG (Thermo Fisher)

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by LED (Thermo Fisher / AMG Transmitted Light LED). Images were recorded using AMG (Thermo Fisher) Sony ICX285AQ Color CCD.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of LED (Thermo Fisher / AMG Transmitted Light LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>17. scope-evos-fl:Phase contrast — MINOR ISSUE</strong> — EVOS fl / Phase contrast</summary>

**Instrument:** EVOS fl  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using On-board EVOS interface.
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
- **light:** LED (Thermo Fisher / AMG Transmitted Light LED) — Thermo Fisher / AMG
- **detector:** AMG (Thermo Fisher) Sony ICX285AQ Color CCD — AMG (Thermo Fisher)

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by LED (Thermo Fisher / AMG Transmitted Light LED). Images were recorded using AMG (Thermo Fisher) Sony ICX285AQ Color CCD.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of LED (Thermo Fisher / AMG Transmitted Light LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>18. scope-leica-dm-irbe:Widefield fluorescence — MAJOR ISSUE</strong> — Leica DM IRBE / Widefield fluorescence</summary>

**Instrument:** Leica DM IRBE  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** arc lamp (Leica 50W HBO short arc bulb) — Leica
- **filter:** Fluorescence Turret, Filter Cube EGFP
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Illumination was provided by arc lamp (Leica 50W HBO short arc bulb). The light path included Filter Cube EGFP in the Fluorescence Turret. Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Leica 50W HBO short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>19. scope-leica-dm-irbe:Transmitted brightfield — MAJOR ISSUE</strong> — Leica DM IRBE / Transmitted brightfield</summary>

**Instrument:** Leica DM IRBE  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>20. scope-leica-dm-irbe:Phase contrast — MAJOR ISSUE</strong> — Leica DM IRBE / Phase contrast</summary>

**Instrument:** Leica DM IRBE  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>21. scope-leica-dm-irbe:Darkfield — MAJOR ISSUE</strong> — Leica DM IRBE / Darkfield</summary>

**Instrument:** Leica DM IRBE  
**Imaging method:** Darkfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Darkfield
- **route:** Transmitted light
- **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>22. scope-leica-dm-rb:Widefield fluorescence — MAJOR ISSUE</strong> — Leica DM RB / Widefield fluorescence</summary>

**Instrument:** Leica DM RB  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** HC PL APO 20x/0.70 CS AIR — Leica
- **light:** arc lamp (Osram 50W HBO short arc bulb) — Osram
- **filter:** Fluorescence Turret, Filter Cube EGFP
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica DM RB upright microscope. Imaging was performed with a 20x/0.7 Air objective (Leica HC PL APO 20x/0.70 CS, 506513).

Illumination was provided by arc lamp (Osram 50W HBO short arc bulb). The light path included Filter Cube EGFP in the Fluorescence Turret. Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Osram 50W HBO short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>23. scope-leica-dm-rb:Transmitted brightfield — MAJOR ISSUE</strong> — Leica DM RB / Transmitted brightfield</summary>

**Instrument:** Leica DM RB  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** HC PL APO 20x/0.70 CS AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems Leica DM RB upright microscope. Imaging was performed with a 20x/0.7 Air objective (Leica HC PL APO 20x/0.70 CS, 506513).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>24. scope-leica-dm-rb:Darkfield — MAJOR ISSUE</strong> — Leica DM RB / Darkfield</summary>

**Instrument:** Leica DM RB  
**Imaging method:** Darkfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Darkfield
- **route:** Transmitted light
- **objective:** HC PL APO 20x/0.70 CS AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica Microsystems Leica DM RB upright microscope. Imaging was performed with a 20x/0.7 Air objective (Leica HC PL APO 20x/0.70 CS, 506513).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>25. scope-leica-dmre:Transmitted brightfield — MAJOR ISSUE</strong> — Leica DM RE / Transmitted brightfield</summary>

**Instrument:** Leica DM RE  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems Leica DM RE upright microscope. Imaging was performed with a 20x/0.5 Air objective (Leica HC PL FLUOTAR 20x/0.50 PH2, 506506).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>26. scope-leica-dmre:DIC — MAJOR ISSUE</strong> — Leica DM RE / DIC</summary>

**Instrument:** Leica DM RE  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** DIC
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Leica Microsystems Leica DM RE upright microscope. Imaging was performed with a 20x/0.5 Air objective (Leica HC PL FLUOTAR 20x/0.50 PH2, 506506).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>27. scope-leica-dmre:Phase contrast — MAJOR ISSUE</strong> — Leica DM RE / Phase contrast</summary>

**Instrument:** Leica DM RE  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR 20x/0.50 PH2 AIR — Leica
- **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
- **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: unresolved detector identity is emitted as finished Methods prose ("Unknown Camera").

**Suggested improvement:** See prioritized defects D3.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Leica Microsystems Leica DM RE upright microscope. Imaging was performed with a 20x/0.5 Air objective (Leica HC PL FLUOTAR 20x/0.50 PH2, 506506).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>28. scope-leica-thunder:Widefield fluorescence — MINOR ISSUE</strong> — Leica Thunder / Widefield fluorescence</summary>

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
- **light:** 395 nm LED (Leica LED 8) — Leica
- **detector:** Leica K8 — Leica

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 395 nm LED (Leica LED 8). Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 395 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) and Standalone Emission Wheel (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>29. scope-leica-thunder:Transmitted brightfield — MINOR ISSUE</strong> — Leica Thunder / Transmitted brightfield</summary>

**Instrument:** Leica Thunder  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
- **detector:** Leica K3C — Leica

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5, D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>30. scope-leica-thunder:Phase contrast — MINOR ISSUE</strong> — Leica Thunder / Phase contrast</summary>

**Instrument:** Leica Thunder  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
- **detector:** Leica K3C — Leica

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5, D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>31. scope-leica-thunder:DIC — MINOR ISSUE</strong> — Leica Thunder / DIC</summary>

**Instrument:** Leica Thunder  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
- **method:** DIC
- **route:** Transmitted light
- **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
- **detector:** Leica K3C — Leica

**Problems found:**
- D8: transmitted-light path exposes detection but no selectable/recorded illumination and gives no targeted illumination warning.
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5, D8.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>32. scope-nikon-crest-v3:Confocal spinning disk — MINOR ISSUE</strong> — Nikon Ti2-E Crest V3 / Confocal spinning disk</summary>

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Confocal spinning disk  
**Physical path:** Spinning-disk confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NIS-Elements AR.
- **method:** Confocal spinning disk
- **route:** Spinning-disk confocal
- **scanner:** Spinning Disk Scanner
- **objective:** CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE — Nikon
- **light:** 406 nm laser (Lumencor Celesta 7ch with Despeckler) — Lumencor
- **detector:** Photometrics Kinetix — Photometrics

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D5, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). The microscope used a spinning disk scanner (pinhole 50 µm). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 406 nm laser (Lumencor Celesta 7ch with Despeckler). Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Spinning Disk Scanner]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 406 nm laser (Lumencor Celesta 7ch with Despeckler) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Crest Excitation Wheel (Spinning-disk confocal route), Crest Dichroic Wheel (Spinning-disk confocal route), and Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>33. scope-nikon-crest-v3:Widefield fluorescence — MINOR ISSUE</strong> — Nikon Ti2-E Crest V3 / Widefield fluorescence</summary>

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NIS-Elements AR.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon
- **light:** LED (Nikon D-LEDI Fluorescence LED Illumination System) — Nikon
- **filter:** Epi Turret, FITC Ti2 32mm Cube SB LFOV (catalogue no. MXR00716)
- **detector:** Photometrics Kinetix — Photometrics

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon CFI Plan Apochromat Lambda D 20X DIC N2, MRD70270). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by LED (Nikon D-LEDI Fluorescence LED Illumination System). The light path included FITC Ti2 32mm Cube SB LFOV (catalogue no. MXR00716) in the Epi Turret. Images were recorded using Photometrics Kinetix.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of LED (Nikon D-LEDI Fluorescence LED Illumination System) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>34. scope-nikon-crest-v3:Transmitted brightfield — MINOR ISSUE</strong> — Nikon Ti2-E Crest V3 / Transmitted brightfield</summary>

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NIS-Elements AR.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon
- **light:** LED (Nikon T12-D-LHLED LED Lamp House) — Nikon
- **detector:** Photometrics Kinetix — Photometrics

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon CFI Plan Apochromat Lambda D 20X DIC N2, MRD70270). Instrument control and image acquisition were performed using NIS-Elements AR.

Transmitted-light illumination was provided by LED (Nikon T12-D-LHLED LED Lamp House). Images were recorded using Photometrics Kinetix.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>35. scope-nikon-crest-v3:DIC — MINOR ISSUE</strong> — Nikon Ti2-E Crest V3 / DIC</summary>

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NIS-Elements AR.
- **method:** DIC
- **route:** Transmitted light
- **objective:** CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon
- **light:** LED (Nikon T12-D-LHLED LED Lamp House) — Nikon
- **detector:** Photometrics Kinetix — Photometrics

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon CFI Plan Apochromat Lambda D 20X DIC N2, MRD70270). Instrument control and image acquisition were performed using NIS-Elements AR.

Transmitted-light illumination was provided by LED (Nikon T12-D-LHLED LED Lamp House). Images were recorded using Photometrics Kinetix.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>36. scope-nikon-eclipse-ti2-e:Widefield fluorescence — MINOR ISSUE</strong> — Nikon Eclipse Ti2-E / Widefield fluorescence</summary>

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** S Plan Fluor ELWD ADM 20x/0.45 DIC N1 AIR — Nikon
- **light:** 395 nm LED (Lumencor Spectra X LED system) — Lumencor
- **detector:** Hamamatsu Orca Flash4.0 V3 — Hamamatsu

**Problems found:**
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Nikon S Plan Fluor ELWD ADM 20x/0.45 DIC N1, MRH08230). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by 395 nm LED (Lumencor Spectra X LED system). Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the role of 395 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) and Emission Wheel (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>37. scope-nikon-eclipse-ti2-e:Transmitted brightfield — PASS</strong> — Nikon Eclipse Ti2-E / Transmitted brightfield</summary>

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** S Plan Fluor ELWD ADM 20x/0.45 DIC N1 AIR — Nikon
- **light:** LED (Nikon Ti2 Transmitted Illuminator) — Nikon
- **detector:** Hamamatsu Orca Flash4.0 V3 — Hamamatsu

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Nikon S Plan Fluor ELWD ADM 20x/0.45 DIC N1, MRH08230). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>38. scope-nikon-eclipse-ti2-e:DIC — PASS</strong> — Nikon Eclipse Ti2-E / DIC</summary>

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).
- **method:** DIC
- **route:** Transmitted light
- **objective:** S Plan Fluor ELWD ADM 20x/0.45 DIC N1 AIR — Nikon
- **light:** LED (Nikon Ti2 Transmitted Illuminator) — Nikon
- **detector:** Hamamatsu Orca Flash4.0 V3 — Hamamatsu

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Nikon S Plan Fluor ELWD ADM 20x/0.45 DIC N1, MRH08230). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>39. scope-nikon-eclipse-ti2-e:Phase contrast — PASS</strong> — Nikon Eclipse Ti2-E / Phase contrast</summary>

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** S Plan Fluor ELWD ADM 20x/0.45 DIC N1 AIR — Nikon
- **light:** LED (Nikon Ti2 Transmitted Illuminator) — Nikon
- **detector:** Hamamatsu Orca Flash4.0 V3 — Hamamatsu

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Nikon S Plan Fluor ELWD ADM 20x/0.45 DIC N1, MRH08230). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>40. scope-olympus-bx60:Widefield fluorescence — MINOR ISSUE</strong> — Olympus BX60 / Widefield fluorescence</summary>

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Olympus Cell^D.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** UPlanFl 20x/0.50 Ph1 AIR — Olympus
- **light:** arc lamp (Osram HBO 103W short arc bulb) — Osram
- **filter:** Fluorescence Turret, U-MWIB (GFP wide) (catalogue no. U-MWIB)
- **detector:** Olympus DP71 — Olympus

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 20x/0.5 Air objective (Olympus UPlanFl 20x/0.50 Ph1). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by arc lamp (Osram HBO 103W short arc bulb). The light path included U-MWIB (GFP wide) (catalogue no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>41. scope-olympus-bx60:Transmitted brightfield — MINOR ISSUE</strong> — Olympus BX60 / Transmitted brightfield</summary>

**Instrument:** Olympus BX60  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Olympus Cell^D.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** UPlanFl 20x/0.50 Ph1 AIR — Olympus
- **light:** halogen lamp (Olympus 12V 100W halogen bulb) — Olympus
- **detector:** Olympus DP71 — Olympus

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 20x/0.5 Air objective (Olympus UPlanFl 20x/0.50 Ph1). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>42. scope-olympus-bx60:Phase contrast — MINOR ISSUE</strong> — Olympus BX60 / Phase contrast</summary>

**Instrument:** Olympus BX60  
**Imaging method:** Phase contrast  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Olympus Cell^D.
- **method:** Phase contrast
- **route:** Transmitted light
- **objective:** UPlanFl 20x/0.50 Ph1 AIR — Olympus
- **light:** halogen lamp (Olympus 12V 100W halogen bulb) — Olympus
- **detector:** Olympus DP71 — Olympus

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 20x/0.5 Air objective (Olympus UPlanFl 20x/0.50 Ph1). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>43. scope-agilent-rtca-esight:Widefield fluorescence — PASS</strong> — Agilent xCELLigence RTCA eSight / Widefield fluorescence</summary>

**Instrument:** Agilent xCELLigence RTCA eSight  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** 10x Objective 10x/0.3 AIR — Agilent
- **light:** 393 nm LED (Agilent High-power LED (Blue)) — Agilent
- **filter:** Internal Filter Turret, Blue Channel
- **detector:** Sony 5.0 MP Monochromatic CMOS — Sony

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Agilent xCELLigence RTCA eSight benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).

Illumination was provided by 393 nm LED (Agilent High-power LED (Blue)). The light path included Blue Channel in the Internal Filter Turret. Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 393 nm LED (Agilent High-power LED (Blue)) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for Blue Channel are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

</details>

<details><summary><strong>44. scope-agilent-rtca-esight:Transmitted brightfield — PASS</strong> — Agilent xCELLigence RTCA eSight / Transmitted brightfield</summary>

**Instrument:** Agilent xCELLigence RTCA eSight  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** 10x Objective 10x/0.3 AIR — Agilent
- **light:** LED (Agilent Transmitted LED) — Agilent
- **detector:** Sony 5.0 MP Monochromatic CMOS — Sony

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Agilent xCELLigence RTCA eSight benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).

Transmitted-light illumination was provided by LED (Agilent Transmitted LED). Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

</details>

<details><summary><strong>45. scope-zeiss-axiozoom-v16:Widefield fluorescence — MINOR ISSUE</strong> — Zeiss AxioZoom.V16 / Widefield fluorescence</summary>

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN Pro.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** PlanApo Z 0.5x/0.125 AIR — Zeiss
- **light:** arc lamp (Zeiss HXP 200C) — Zeiss
- **filter:** Fluorescence Turret, Alexa 488 (Filter set 38 HE) (catalogue no. 38 HE)
- **detector:** Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Illumination was provided by arc lamp (Zeiss HXP 200C). The light path included Alexa 488 (Filter set 38 HE) (catalogue no. 38 HE) in the Fluorescence Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: the role of arc lamp (Zeiss HXP 200C) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>46. scope-zeiss-axiozoom-v16:Optical sectioning — MINOR ISSUE</strong> — Zeiss AxioZoom.V16 / Optical sectioning</summary>

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Optical sectioning  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN Pro.
- **method:** Optical sectioning
- **route:** Widefield fluorescence
- **module:** SIM Module — Zeiss
- **objective:** PlanApo Z 0.5x/0.125 AIR — Zeiss
- **light:** arc lamp (Zeiss HXP 200C) — Zeiss
- **filter:** Fluorescence Turret, Alexa 488 (Filter set 38 HE) (catalogue no. 38 HE)
- **detector:** Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Optical sectioning was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). The SIM Module was used (Zeiss ApoTome.2). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Illumination was provided by arc lamp (Zeiss HXP 200C). The light path included Alexa 488 (Filter set 38 HE) (catalogue no. 38 HE) in the Fluorescence Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: the role of arc lamp (Zeiss HXP 200C) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>47. scope-zeiss-axiozoom-v16:Reflected brightfield — MINOR ISSUE</strong> — Zeiss AxioZoom.V16 / Reflected brightfield</summary>

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Reflected brightfield  
**Physical path:** Reflected light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN Pro.
- **method:** Reflected brightfield
- **route:** Reflected light
- **objective:** PlanApo Z 0.5x/0.125 AIR — Zeiss
- **light:** LED (Zeiss CL 9000 LED CAN ring light) — Zeiss
- **detector:** Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>48. scope-zeiss-axiozoom-v16:Transmitted brightfield — MINOR ISSUE</strong> — Zeiss AxioZoom.V16 / Transmitted brightfield</summary>

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN Pro.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** PlanApo Z 0.5x/0.125 AIR — Zeiss
- **light:** LED (VisiLED MC1000 LED base light) — VisiLED
- **detector:** Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Transmitted-light illumination was provided by LED (VisiLED MC1000 LED base light). Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>49. scope-zeiss-lsm-510-jpk-afm:Confocal point scanning — MAJOR ISSUE</strong> — Zeiss LSM 510 JPK AFM / Confocal point scanning</summary>

**Instrument:** Zeiss LSM 510 JPK AFM  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Galvanometric Scanner
- **objective:** Placeholder 10x/0.3 AIR — Unknown
- **light:** 488 nm laser — Unknown
- **detector:** Zeiss — Zeiss

**Problems found:**
- D3: placeholder/incomplete hardware identity leaks into publication-facing output.
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects D3, D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The microscope used a galvanometric scanner.

Illumination was provided by 488 nm laser. Images were recorded using Zeiss.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>50. scope-zeiss-lsm-510-jpk-afm:Transmitted brightfield — MAJOR ISSUE</strong> — Zeiss LSM 510 JPK AFM / Transmitted brightfield</summary>

**Instrument:** Zeiss LSM 510 JPK AFM  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Placeholder 10x/0.3 AIR — Unknown

**Problems found:**
- D3: placeholder/incomplete hardware identity leaks into publication-facing output.
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D3, D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss LSM 510 JPK AFM inverted microscope. Imaging was performed with a 10x/0.3 Air objective.

Review before publication:
- [PLEASE VERIFY: the recorded hardware topology for the Transmitted light light path is incomplete; confirm the illumination and detection components used]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>51. scope-zeiss-lsm-880-with-airyscan:Confocal point scanning — MINOR ISSUE</strong> — Zeiss LSM 880 with AiryScan / Confocal point scanning</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Resonant Scanner
- **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
- **light:** 488 nm laser (Argon) — Unknown
- **detector:** PMT (Ch1) — Unknown

**Problems found:**
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The microscope used a resonant scanner (line rate 8000 Hz). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon). Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>52. scope-zeiss-lsm-880-with-airyscan:ISM (AiryScan) — PASS</strong> — Zeiss LSM 880 with AiryScan / ISM (AiryScan)</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan)  
**Physical path:** Point-scanning confocal  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
- **method:** ISM (AiryScan)
- **route:** Point-scanning confocal
- **module:** AiryScan Detector/Module — Zeiss
- **scanner:** Resonant Scanner
- **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
- **light:** 488 nm laser (Argon) — Unknown

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Image scanning microscopy (ISM; Airyscan) was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). The microscope used a resonant scanner (line rate 8000 Hz). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting detector/reconstruction mode and the reconstruction software/version and settings used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>53. scope-zeiss-lsm-880-with-airyscan:Transmitted brightfield — PASS</strong> — Zeiss LSM 880 with AiryScan / Transmitted brightfield</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Plan-APOCHROMAT 20x/0.8 AIR — Zeiss
- **light:** halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)) — Zeiss
- **detector:** Transmitted light PMT — Unknown

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-APOCHROMAT 20x/0.8, 420650-9901). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)). Images were recorded using Transmitted light PMT.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>54. scope-zeiss-lsm-880-with-airyscan:DIC — PASS</strong> — Zeiss LSM 880 with AiryScan / DIC</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** DIC  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
- **method:** DIC
- **route:** Transmitted light
- **objective:** Plan-APOCHROMAT 20x/0.8 AIR — Zeiss
- **light:** halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)) — Zeiss
- **detector:** Transmitted light PMT — Unknown

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-APOCHROMAT 20x/0.8, 420650-9901). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)). Images were recorded using Transmitted light PMT.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>55. scope-zeiss-tirf:Widefield fluorescence — MINOR ISSUE</strong> — Zeiss TIRF / Widefield fluorescence</summary>

**Instrument:** Zeiss TIRF  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** Plan Apochromat 20x/0.45 AIR — Zeiss
- **light:** 488 nm laser — Unknown
- **filter:** Filter Turret, Filter set 38 HE (GFP) (catalogue no. 38 HE)
- **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Zeiss Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>56. scope-zeiss-tirf:TIRF — MINOR ISSUE</strong> — Zeiss TIRF / TIRF</summary>

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **method:** TIRF
- **route:** Widefield fluorescence
- **objective:** Alpha Plan Apochromat 63x/1.46 OIL — Zeiss
- **light:** 488 nm laser — Unknown
- **filter:** Filter Turret, Filter set 38 HE (GFP) (catalogue no. 38 HE)
- **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>57. scope-zeiss-tirf:Transmitted brightfield — MINOR ISSUE</strong> — Zeiss TIRF / Transmitted brightfield</summary>

**Instrument:** Zeiss TIRF  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** Plan Apochromat 20x/0.45 AIR — Zeiss
- **light:** halogen lamp (Zeiss Transmitted Halogen Lamp) — Zeiss
- **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Zeiss Plan Apochromat).

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted Halogen Lamp). Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>58. scope-1e33f909:Confocal point scanning — MINOR ISSUE</strong> — Abberior STED / Confocal point scanning</summary>

**Instrument:** Abberior STED  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Galvanometric Scanner
- **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
- **light:** 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
- **filter:** Emission Filter Wheel, 525/25 (catalogue no. FF01-525/25)
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>59. scope-1e33f909:STED — MINOR ISSUE</strong> — Abberior STED / STED</summary>

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** STED
- **route:** Point-scanning confocal
- **module:** Easy3D STED — Abberior
- **scanner:** Galvanometric Scanner
- **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
- **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
- **filter:** Emission Filter Wheel, 525/25 (catalogue no. FF01-525/25)
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D7: raw light-source count is treated as channel count, producing an inappropriate sequencing prompt for specialist beams.

**Suggested improvement:** See prioritized defects D5, D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The Easy3D STED module was used (Abberior easy3D STED). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>60. scope-1e33f909:RESOLFT — MINOR ISSUE</strong> — Abberior STED / RESOLFT</summary>

**Instrument:** Abberior STED  
**Imaging method:** RESOLFT  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** RESOLFT
- **route:** Point-scanning confocal
- **scanner:** Galvanometric Scanner
- **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
- **light:** 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant, 561 nm laser (PicoQuant PDL-T 561) — PicoQuant
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D6: implementation-oriented "route" terminology leaks into publication/review text.
- D7: raw light-source count is treated as channel count, producing an inappropriate sequencing prompt for specialist beams.

**Suggested improvement:** See prioritized defects D5, D6, D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485) and 561 nm laser (PicoQuant PDL-T 561). Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>61. scope-deltavision-omx:Widefield fluorescence — PASS</strong> — Deltavision OMX / Widefield fluorescence</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **light:** 488 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>62. scope-deltavision-omx:TIRF — PASS</strong> — Deltavision OMX / TIRF</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** TIRF
- **route:** Widefield fluorescence
- **module:** TIRF Module — GE Healthcare
- **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **light:** 488 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The TIRF Module was used (GE Healthcare Ring TIRF with PhotoKinetic Optics). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>63. scope-deltavision-omx:SIM — PASS</strong> — Deltavision OMX / SIM</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** SIM  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** SIM
- **route:** Widefield fluorescence
- **module:** 3D-SIM Module — GE Healthcare
- **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **light:** 488 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>64. scope-deltavision-omx:SMLM — PASS</strong> — Deltavision OMX / SMLM</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** SMLM
- **route:** Widefield fluorescence
- **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **light:** 405 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 405 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>65. scope-lambert-flim-frequency-domain:Widefield fluorescence — PASS</strong> — Lambert FLIM / Widefield fluorescence</summary>

**Instrument:** Lambert FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** LD-Plan NEOFLUAR 20x/0.4 Ph2 Korr AIR — Zeiss
- **light:** 406 nm LED (Multi-LED excitation) — Unknown
- **detector:** Lambert Instruments LIFA Camera — Lambert Instruments

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert Instruments LIFA (frequency domain FLIM) inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Zeiss LD-Plan NEOFLUAR 20x/0.4 Ph2 Korr, 421351-9970).

Illumination was provided by 406 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: the role of 406 nm LED (Multi-LED excitation) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version and Detector pixel pitch (um) are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>66. scope-leica-stellaris-8-falcon-flim-resonant:Confocal point scanning — MINOR ISSUE</strong> — Leica STELLARIS 8 FALCON FLIM / Confocal point scanning</summary>

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Tandem Scanner (Galvo/Resonant)
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **detector:** Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems

**Problems found:**
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>67. scope-leica-stellaris-8-falcon-flim-resonant:Widefield fluorescence — PASS</strong> — Leica STELLARIS 8 FALCON FLIM / Widefield fluorescence</summary>

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Widefield fluorescence
- **route:** Widefield fluorescence
- **objective:** HC PL APO 20x/0.75 CS2 AIR — Leica Microsystems
- **light:** LED (Leica Microsystems Leica LED 3) — Leica Microsystems
- **filter:** LED/filter-cube observation path, Filter Cube GFP (catalogue no. 15525314)
- **detector:** Leica Microsystems K5 Microscope Camera — Leica Microsystems

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 20x/0.75 Air objective (Leica Microsystems HC PL APO 20x/0.75 CS2, 15506517). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by LED (Leica Microsystems Leica LED 3). The light path included Filter Cube GFP (catalogue no. 15525314) in the LED/filter-cube observation path. Images were recorded using Leica Microsystems K5 Microscope Camera.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of LED (Leica Microsystems Leica LED 3) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>68. scope-leica-stellaris-8-falcon-flim-resonant:Transmitted brightfield — PASS</strong> — Leica STELLARIS 8 FALCON FLIM / Transmitted brightfield</summary>

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Transmitted brightfield
- **route:** Transmitted light
- **objective:** HC PL APO 20x/0.75 CS2 AIR — Leica Microsystems
- **light:** LED (Leica Microsystems Leica LED 3) — Leica Microsystems
- **detector:** Leica Microsystems K5 Microscope Camera — Leica Microsystems

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 20x/0.75 Air objective (Leica Microsystems HC PL APO 20x/0.75 CS2, 15506517). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by LED (Leica Microsystems Leica LED 3). Images were recorded using Leica Microsystems K5 Microscope Camera.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of LED (Leica Microsystems Leica LED 3) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>69. scope-leica-tcs-sp5-multiphoton:route — MAJOR ISSUE</strong> — Leica TCS SP5 Multiphoton / Multiphoton</summary>

**Instrument:** Leica TCS SP5 Multiphoton  
**Imaging method:** Multiphoton  
**Physical path:** Multiphoton  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Leica LAS AF.
- **route:** Multiphoton
- **scanner:** Resonant Scanner
- **objective:** HCX IR APO L 25x/0.95 WATER — Leica
- **light:** pulsed near-ir laser (Coherent Chameleon Vision II) — Coherent
- **detector:** NDD PMT

**Problems found:**
- D2: legacy multiphoton record has no method-first selection; output falls back to "Multiphoton route" and schema-facing review language.
- D6: implementation-oriented "route" terminology leaks into publication/review text.

**Suggested improvement:** See prioritized defects D2, D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope, with the Multiphoton route. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). The microscope used a resonant scanner. Instrument control and image acquisition were performed using Leica LAS AF.

Excitation was provided by pulsed near-ir laser (Coherent Chameleon Vision II). Images were recorded using NDD PMT.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting excitation wavelength, mean power at the sample, and pulse width. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: acquisition software version for Leica LAS AF]
- [PLEASE SPECIFY: wavelength used from the recorded 690-1040 nm tunable range of pulsed near-ir laser (Coherent Chameleon Vision II)]
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>70. scope-msquared-aurora-airy-beam:Light sheet — MINOR ISSUE</strong> — MSquared Aurora Airy Beam / Light sheet</summary>

**Instrument:** MSquared Aurora Airy Beam  
**Imaging method:** Light sheet  
**Physical path:** Light sheet  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using M Squared Cubes Acquisition.
- **method:** Light sheet
- **route:** Light sheet
- **scanner:** Tandem Scanner (Galvo/Resonant)
- **objective:** 54-10-12 Airy beam dipping objective 17x/0.4 MULTI-IMMERSION — Special Optics
- **light:** 488 nm laser (Coherent OBIS laser) — Coherent OBIS
- **filter:** Emission Wheel, GFP filter
- **detector:** Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU) — Hamamatsu

**Problems found:**
- D9: stand-orientation vocabulary leaks as the phrase "other microscope".
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects D5, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Light-sheet imaging was performed using the M Squared Aurora Airy Beam other microscope. Imaging was performed with a 17x/0.4 Multi-Immersion objective (Special Optics 54-10-12 Airy beam dipping objective, 54-10-12). The microscope used a tandem scanner (galvo/resonant, light-sheet type airy beam, line rate 8000 Hz). Instrument control and image acquisition were performed using M Squared Cubes Acquisition.

Illumination was provided by 488 nm laser (Coherent OBIS laser). The light path included GFP filter in the Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for M Squared Cubes Acquisition]
- [PLEASE SPECIFY: the role of 488 nm laser (Coherent OBIS laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>71. scope-oni-nanoimager:TIRF — MINOR ISSUE</strong> — ONI Nanoimager / TIRF</summary>

**Instrument:** ONI Nanoimager  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
- **method:** TIRF
- **route:** Widefield fluorescence
- **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
- **light:** 488 nm laser (ONI blue) — ONI
- **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D9: stand-orientation vocabulary leaks as the phrase "other microscope".
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects D5, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 488 nm laser (ONI blue). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 488 nm laser (ONI blue) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>72. scope-oni-nanoimager:SMLM — MINOR ISSUE</strong> — ONI Nanoimager / SMLM</summary>

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
- **method:** SMLM
- **route:** Widefield fluorescence
- **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
- **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
- **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D9: stand-orientation vocabulary leaks as the phrase "other microscope".
- D5: instrument-global software blocker is appended even when it is not tied to the selected acquisition software.
- D7: raw light-source count is treated as channel count, producing an inappropriate sequencing prompt for specialist beams.
- Prompt quality: source role is unresolved using overly broad alternatives despite the selected technique/path constraining the plausible role.

**Suggested improvement:** See prioritized defects D5, D7, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 405 nm laser (ONI violet) and 640 nm laser (ONI red). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 405 nm laser (ONI violet) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>73. A01 — MINOR ISSUE</strong> — Abberior confocal GFP / Confocal point scanning</summary>

**Instrument:** Abberior confocal GFP  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Galvanometric Scanner
- **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
- **light:** 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
- **filter:** Emission Filter Wheel, 525/25 (catalogue no. FF01-525/25)
- **detector:** Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>74. A02 — MINOR ISSUE</strong> — Abberior STED far-red / STED</summary>

**Instrument:** Abberior STED far-red  
**Imaging method:** STED  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** STED
- **route:** Point-scanning confocal
- **module:** Easy3D STED — Abberior
- **scanner:** Galvanometric Scanner
- **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
- **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
- **filter:** Emission Filter Wheel, 685/35 (catalogue no. ET685/35)
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
- **modulator:** Spatial Light Modulator — Abberior

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- D7: multiple specialist illumination beams are treated as acquisition channels.

**Suggested improvement:** See prioritized defects D5, D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 685/35 (catalogue no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR. STED beam shaping used Abberior easy3D SLM.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: which phase mask profile was applied (Vortex, Bottle, and 3D-STED are recorded for this modulator)]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>75. A03 — MINOR ISSUE</strong> — Abberior STED 561 / STED</summary>

**Instrument:** Abberior STED 561  
**Imaging method:** STED  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **method:** STED
- **route:** Point-scanning confocal
- **module:** Adaptive Optics — Abberior
- **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
- **light:** 561 nm laser (PicoQuant PDL-T 561) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
- **filter:** Emission Filter Wheel, BrightLine 615/10
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- D7: multiple specialist illumination beams are treated as acquisition channels.

**Suggested improvement:** See prioritized defects D5, D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Adaptive Optics module was used (Abberior).

Excitation was provided by 561 nm laser (PicoQuant PDL-T 561). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included BrightLine 615/10 in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>76. A04 — MINOR ISSUE</strong> — Abberior RESOLFT / RESOLFT</summary>

**Instrument:** Abberior RESOLFT  
**Imaging method:** RESOLFT  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
- **method:** RESOLFT
- **route:** Point-scanning confocal
- **module:** RESCue STED — Abberior
- **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
- **light:** 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant, 561 nm laser (PicoQuant PDL-T 561) — PicoQuant
- **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
- **modulator:** Spatial Light Modulator — Abberior
- **illum:** RESCue STED

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- D6: "route" terminology appears in review text.
- D7: multiple specialist illumination beams are treated as acquisition channels.

**Suggested improvement:** See prioritized defects D5, D6, D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The RESCue STED module was used (Abberior). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485) and 561 nm laser (PicoQuant PDL-T 561). Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR. STED beam shaping used Abberior easy3D SLM. Adaptive illumination used RESCue STED.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: which phase mask profile was applied (Vortex, Bottle, and 3D-STED are recorded for this modulator)]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>77. D01 — PASS</strong> — DeltaVision SIM / SIM</summary>

**Instrument:** DeltaVision SIM  
**Imaging method:** SIM  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** SIM
- **route:** Widefield fluorescence
- **module:** 3D-SIM Module — GE Healthcare
- **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **light:** 488 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>78. D02 — MINOR ISSUE</strong> — DeltaVision SMLM / SMLM</summary>

**Instrument:** DeltaVision SMLM  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** SMLM
- **route:** Widefield fluorescence
- **objective:** APO N TIRF 60x/1.49 OIL — Olympus
- **light:** 405 nm laser (GE Healthcare) — GE Healthcare, 642 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Cy5
- **detector:** PCO Edge — PCO

**Problems found:**
- D7: multiple specialist illumination beams are treated as acquisition channels.

**Suggested improvement:** See prioritized defects D7.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 405 nm laser (GE Healthcare) and 642 nm laser (GE Healthcare). The light path included Cy5 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>79. D03 — PASS</strong> — DeltaVision TIRF / TIRF</summary>

**Instrument:** DeltaVision TIRF  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence  
**Assessment:** **PASS**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
- **method:** TIRF
- **route:** Widefield fluorescence
- **module:** TIRF Module — GE Healthcare
- **objective:** APO N TIRF 60x/1.49 OIL — Olympus
- **light:** 488 nm laser (GE Healthcare) — GE Healthcare
- **filter:** OMX Emission Filters, Alexa 488
- **detector:** PCO Edge — PCO

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** No change required from this scenario.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). The TIRF Module was used (GE Healthcare Ring TIRF with PhotoKinetic Optics). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>80. O01 — MINOR ISSUE</strong> — ONI SMLM / SMLM</summary>

**Instrument:** ONI SMLM  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
- **method:** SMLM
- **route:** Widefield fluorescence
- **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
- **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
- **splitter:** Internal Emission Splitter
- **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D9: "other microscope" appears in finished prose.
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- D7: multiple specialist illumination beams are treated as acquisition channels.
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects D5, D7, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 405 nm laser (ONI violet) and 640 nm laser (ONI red). Light was directed through Internal Emission Splitter. Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 405 nm laser (ONI violet) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>81. O02 — MINOR ISSUE</strong> — ONI TIRF FRET / TIRF</summary>

**Instrument:** ONI TIRF FRET  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence, FRET  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
- **method:** TIRF
- **route:** Widefield fluorescence, FRET
- **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
- **light:** 488 nm laser (ONI blue) — ONI, 561 nm laser (ONI green) — ONI
- **splitter:** Internal Emission Splitter
- **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D9: "other microscope" appears in finished prose.
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- D7: multiple specialist illumination beams are treated as acquisition channels.
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects D5, D7, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. FRET data were acquired. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 488 nm laser (ONI blue) and 561 nm laser (ONI green). Light was directed through Internal Emission Splitter. Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 488 nm laser (ONI blue) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 561 nm laser (ONI green) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>82. S01 — MINOR ISSUE</strong> — Stellaris confocal / Confocal point scanning</summary>

**Instrument:** Stellaris confocal  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal
- **scanner:** Tandem Scanner (Galvo/Resonant)
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **filter:** AOBS, Spectral detection / SP module
- **detector:** Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems

**Problems found:**
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). The light path included AOBS and Spectral detection / SP module. Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>83. S02 — MINOR ISSUE</strong> — Stellaris spectral / Confocal point scanning</summary>

**Instrument:** Stellaris spectral  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal, Spectral Imaging  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal, Spectral Imaging
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **detector:** Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems

**Problems found:**
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Spectral Imaging data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>84. S03 — MINOR ISSUE</strong> — Stellaris FLIM / Confocal point scanning</summary>

**Instrument:** Stellaris FLIM  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal, FLIM  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal, FLIM
- **module:** FLIM Module — Leica Microsystems
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **detector:** Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems

**Problems found:**
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FLIM data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>85. S04 — MINOR ISSUE</strong> — Stellaris FCS / Confocal point scanning</summary>

**Instrument:** Stellaris FCS  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal, FCS  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal, FCS
- **module:** FCS Module — Leica Microsystems
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **detector:** Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems

**Problems found:**
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FCS data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FCS Module was used (Leica Microsystems STELLARIS 8 FCS). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: FCS measurement duration, number of repeats, how the confocal volume was calibrated, and the fitting model]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>86. S05 — MINOR ISSUE</strong> — Stellaris FRET / Confocal point scanning</summary>

**Instrument:** Stellaris FRET  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal, FRET  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
- **method:** Confocal point scanning
- **route:** Point-scanning confocal, FRET
- **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
- **detector:** Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems

**Problems found:**
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects .

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FRET data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>87. Z02 — MINOR ISSUE</strong> — Zeiss TIRF / TIRF</summary>

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **method:** TIRF
- **route:** Widefield fluorescence
- **objective:** Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
- **light:** 488 nm laser — Unknown
- **filter:** Filter Turret, Filter set 38 HE (GFP) (catalogue no. 38 HE)
- **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>88. L01 — MINOR ISSUE</strong> — Aurora light sheet / Light sheet</summary>

**Instrument:** Aurora light sheet  
**Imaging method:** Light sheet  
**Physical path:** Light sheet  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using M Squared Cubes Acquisition.
- **method:** Light sheet
- **route:** Light sheet
- **scanner:** Tandem Scanner (Galvo/Resonant)
- **objective:** 54-10-12 Airy beam dipping objective 17x/0.4 MULTI-IMMERSION — Special Optics
- **light:** 488 nm laser (Coherent OBIS laser) — Coherent OBIS
- **filter:** Emission Wheel, GFP filter
- **detector:** Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU) — Hamamatsu

**Problems found:**
- D9: "other microscope" appears in finished prose.
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.
- Prompt quality: source-role prompt offers overly broad alternatives for a technique-constrained source.

**Suggested improvement:** See prioritized defects D5, D9.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Light-sheet imaging was performed using the M Squared Aurora Airy Beam other microscope. Imaging was performed with a 17x/0.4 Multi-Immersion objective (Special Optics 54-10-12 Airy beam dipping objective, 54-10-12). The microscope used a tandem scanner (galvo/resonant, light-sheet type airy beam, line rate 8000 Hz). Instrument control and image acquisition were performed using M Squared Cubes Acquisition.

Illumination was provided by 488 nm laser (Coherent OBIS laser). The light path included GFP filter in the Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for M Squared Cubes Acquisition]
- [PLEASE SPECIFY: the role of 488 nm laser (Coherent OBIS laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>89. R01 — MINOR ISSUE</strong> — AxioZoom reflected / Reflected brightfield</summary>

**Instrument:** AxioZoom reflected  
**Imaging method:** Reflected brightfield  
**Physical path:** Reflected light  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN Pro.
- **method:** Reflected brightfield
- **route:** Reflected light
- **objective:** PlanApo Z 1x/0.125 AIR — Zeiss
- **light:** LED (Zeiss CL 9000 LED CAN ring light) — Zeiss
- **detector:** Zeiss AxioCam 105 Color — Zeiss

**Problems found:**
- D5: generic instrument-global software-version blocker is duplicated or unrelated to the selected software action.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 1x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Zeiss AxioCam 105 Color.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>90. T01 — MAJOR ISSUE</strong> — Abberior STED / Confocal point scanning</summary>

**Instrument:** Abberior STED  
**Imaging method:** Confocal point scanning  
**Physical path:** Point-scanning confocal  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
  - **method:** STED
  - **route:** Point-scanning confocal
  - **module:** Easy3D STED — Abberior
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
  - **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  - **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
- **after:**
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal
  - **module:** Easy3D STED — Abberior
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
- **final_or_current:**
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal
  - **module:** Easy3D STED — Abberior
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus

**Problems found:**
- D1: Easy3D STED module survives STED → confocal and is asserted as used.

**Suggested improvement:** See prioritized defects D1.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>91. T02 — MAJOR ISSUE</strong> — Deltavision OMX / Widefield fluorescence</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
  - **method:** SIM
  - **route:** Widefield fluorescence
  - **module:** 3D-SIM Module — GE Healthcare
  - **objective:** Plan Apo N 60x/1.42 OIL — Olympus
  - **light:** 488 nm laser (GE Healthcare) — GE Healthcare
  - **detector:** PCO Edge — PCO
- **after:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** 3D-SIM Module — GE Healthcare
  - **objective:** Plan Apo N 60x/1.42 OIL — Olympus
- **final_or_current:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** 3D-SIM Module — GE Healthcare
  - **objective:** Plan Apo N 60x/1.42 OIL — Olympus

**Problems found:**
- D1: 3D-SIM module survives SIM → widefield and is asserted as used.

**Suggested improvement:** See prioritized defects D1.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine).

Review before publication:
- [PLEASE SPECIFY: which position of OMX Emission Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>92. T03 — MAJOR ISSUE</strong> — Deltavision OMX / Widefield fluorescence</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
  - **method:** TIRF
  - **route:** Widefield fluorescence
  - **module:** TIRF Module — GE Healthcare
  - **objective:** APO N TIRF 60x/1.49 OIL — Olympus
  - **light:** 488 nm laser (GE Healthcare) — GE Healthcare
  - **detector:** PCO Edge — PCO
- **after:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** TIRF Module — GE Healthcare
  - **objective:** APO N TIRF 60x/1.49 OIL — Olympus
- **final_or_current:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** TIRF Module — GE Healthcare
  - **objective:** APO N TIRF 60x/1.49 OIL — Olympus

**Problems found:**
- D1: TIRF module survives TIRF → widefield and is asserted as used.

**Suggested improvement:** See prioritized defects D1.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). The TIRF Module was used (GE Healthcare Ring TIRF with PhotoKinetic Optics).

Review before publication:
- [PLEASE SPECIFY: which position of OMX Emission Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>93. T04 — MAJOR ISSUE</strong> — Zeiss LSM 880 with AiryScan / Transmitted brightfield</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
  - **method:** ISM (AiryScan)
  - **route:** Point-scanning confocal
  - **module:** AiryScan Detector/Module — Zeiss
  - **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  - **light:** 488 nm laser (Argon) — Unknown
- **after:**
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **module:** AiryScan Detector/Module — Zeiss
  - **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
- **final_or_current:**
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **module:** AiryScan Detector/Module — Zeiss
  - **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss

**Problems found:**
- D1: Airyscan module survives ISM/Airyscan → transmitted brightfield and is asserted as used.

**Suggested improvement:** See prioritized defects D1.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan).

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>94. T05 — MAJOR ISSUE</strong> — Leica STELLARIS 8 FALCON FLIM / Widefield fluorescence</summary>

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path:** Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal, FLIM
  - **module:** FLIM Module — Leica Microsystems
  - **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  - **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  - **detector:** Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
- **after:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** FLIM Module — Leica Microsystems
  - **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
- **final_or_current:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** FLIM Module — Leica Microsystems
  - **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems

**Problems found:**
- D1: FLIM module survives confocal+FLIM → widefield and is asserted as used.

**Suggested improvement:** See prioritized defects D1.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON).

Review before publication:
- [PLEASE SPECIFY: which position of LED/filter-cube observation path (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>95. T06 — PASS</strong> — 3i CSU-W1 Spinning Disk / Transmitted brightfield</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Transmitted brightfield  
**Physical path:** Transmitted light  
**Assessment:** **PASS**

**Selections made in the UI:**
- **before:**
  - **method:** Confocal spinning disk
  - **route:** Spinning-disk confocal
  - **objective:** Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  - **light:** 488 nm laser (3i LaserStack v4) — 3i
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu
- **after:**
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **objective:** Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
- **final_or_current:**
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **objective:** Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** The tested state transition behaved correctly.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900).

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>96. T07 — PASS</strong> — 3i CSU-W1 Spinning Disk / Confocal spinning disk</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path:** Spinning-disk confocal  
**Assessment:** **PASS**

**Selections made in the UI:**
- **before:**
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu
- **after:**
  - **method:** Confocal spinning disk
  - **route:** Spinning-disk confocal
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
- **final_or_current:**
  - **method:** Confocal spinning disk
  - **route:** Spinning-disk confocal
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss

**Problems found:**
- None reproduced in this scenario.

**Suggested improvement:** The tested state transition behaved correctly.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of CSU-W1 Dichroic Slider (Spinning-disk confocal route) and CSU-W1 Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>97. T08 — MINOR ISSUE</strong> — ONI Nanoimager / SMLM</summary>

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **after:**
  - **method:** SMLM
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
- **final_or_current:**
  - **method:** SMLM
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D5: software selection itself is respected, but a generic software-version blocker remains; when software is checked it duplicates the specific version prompt.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO).

Illumination was provided by 405 nm laser (ONI violet) and 640 nm laser (ONI red). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 405 nm laser (ONI violet) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>98. T09 — MINOR ISSUE</strong> — ONI Nanoimager / SMLM</summary>

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM  
**Physical path:** Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **after:**
  - **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
  - **method:** SMLM
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
- **final_or_current:**
  - **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
  - **method:** SMLM
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D5: software selection itself is respected, but a generic software-version blocker remains; when software is checked it duplicates the specific version prompt.

**Suggested improvement:** See prioritized defects D5.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 405 nm laser (ONI violet) and 640 nm laser (ONI red). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 405 nm laser (ONI violet) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>99. T10 — MINOR ISSUE</strong> — Abberior STED / STED</summary>

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path:** Point-scanning confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **after:**
  - **method:** STED
  - **route:** Point-scanning confocal
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
  - **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  - **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
- **final_or_current:**
  - **method:** STED
  - **route:** Point-scanning confocal
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
  - **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  - **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D7/D6: optional module deselection works, but the STED output still carries the raw light-count channel prompt and route terminology in review text.

**Suggested improvement:** See prioritized defects D7/D6.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836).

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>100. T11 — MAJOR ISSUE</strong> — Abberior STED / STED</summary>

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path:** Point-scanning confocal  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **after:**
  - **method:** STED
  - **route:** Point-scanning confocal
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus
- **final_or_current:**
  - **method:** STED
  - **route:** Point-scanning confocal
  - **objective:** UPlanSApo 100x/1.40 Oil OIL — Olympus

**Problems found:**
- D4: an STED acquisition with no excitation/depletion source or detector is accepted without explicit essential-hardware omission warnings.

**Suggested improvement:** See prioritized defects D4.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>101. T12a — MAJOR ISSUE</strong> — Leica TCS SP5 Multiphoton / legacy/no method picker</summary>

**Instrument:** Leica TCS SP5 Multiphoton  
**Imaging method:** legacy/no method picker  
**Physical path:** None selected  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **before:**
- **after:**
- **final_or_current:**

**Problems found:**
- D2: Add succeeds before the only physical path is selected on the legacy multiphoton instrument.

**Suggested improvement:** See prioritized defects D2.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope.

Review before publication:
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>102. T12b — MAJOR ISSUE</strong> — Leica TCS SP5 Multiphoton / legacy/no method picker</summary>

**Instrument:** Leica TCS SP5 Multiphoton  
**Imaging method:** legacy/no method picker  
**Physical path:** Multiphoton  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **after:**
  - **confirmed:** Instrument control and image acquisition were performed using Leica LAS AF.
  - **route:** Multiphoton
  - **objective:** HCX IR APO L 25x/0.95 WATER — Leica
  - **light:** pulsed near-ir laser (Coherent Chameleon Vision II) — Coherent
  - **detector:** NDD PMT
- **final_or_current:**
  - **confirmed:** Instrument control and image acquisition were performed using Leica LAS AF.
  - **route:** Multiphoton
  - **objective:** HCX IR APO L 25x/0.95 WATER — Leica
  - **light:** pulsed near-ir laser (Coherent Chameleon Vision II) — Coherent
  - **detector:** NDD PMT

**Problems found:**
- D2: after selecting Multiphoton path the output still lacks an explicit multiphoton imaging method and contains "route"/schema language; the invalid first acquisition remains in the section.

**Suggested improvement:** See prioritized defects D2.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope.

Review before publication:
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope, with the Multiphoton route. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). Instrument control and image acquisition were performed using Leica LAS AF.

Excitation was provided by pulsed near-ir laser (Coherent Chameleon Vision II). Images were recorded using NDD PMT.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting excitation wavelength, mean power at the sample, and pulse width. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Leica LAS AF]
- [PLEASE SPECIFY: wavelength used from the recorded 690-1040 nm tunable range of pulsed near-ir laser (Coherent Chameleon Vision II)]
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>103. M01 — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Widefield fluorescence → Confocal spinning disk</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Widefield fluorescence → Confocal spinning disk  
**Physical path:** Widefield fluorescence → Spinning-disk confocal  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
  - **light:** LED (Excelitas X-Cite XLED1) — Excelitas
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
  - **method:** Confocal spinning disk
  - **route:** Spinning-disk confocal
  - **scanner:** Spinning Disk Scanner
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
  - **light:** 488 nm laser (3i LaserStack v4) — 3i
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by LED (Excelitas X-Cite XLED1). Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of XLED Excitation Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). The microscope used a spinning disk scanner (pinhole 50 µm). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Spinning Disk Scanner]
- [PLEASE SPECIFY: which position of CSU-W1 Dichroic Slider (Spinning-disk confocal route) and CSU-W1 Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>104. M02 — MINOR ISSUE</strong> — 3i CSU-W1 Spinning Disk / Transmitted brightfield → Widefield fluorescence</summary>

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Transmitted brightfield → Widefield fluorescence  
**Physical path:** Transmitted light → Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
  - **method:** Transmitted brightfield
  - **route:** Transmitted light
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using 3i SlideBook (v6).
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **objective:** Plan-Apochromat 20x/0.8 AIR — Zeiss
  - **light:** LED (Excelitas X-Cite XLED1) — Excelitas
  - **detector:** Hamamatsu ORCA-Flash4.0 — Hamamatsu

**Problems found:**
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by LED (Excelitas X-Cite XLED1). Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of XLED Excitation Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>105. M03 — MAJOR ISSUE</strong> — Abberior STED / STED → Confocal point scanning</summary>

**Instrument:** Abberior STED  
**Imaging method:** STED → Confocal point scanning  
**Physical path:** Point-scanning confocal → Point-scanning confocal  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
  - **method:** STED
  - **route:** Point-scanning confocal
  - **module:** Easy3D STED — Abberior
  - **scanner:** Galvanometric Scanner
  - **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
  - **light:** 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant, 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  - **filter:** Emission Filter Wheel, 525/25 (catalogue no. FF01-525/25)
  - **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using Abberior Imspector.
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal
  - **module:** Easy3D STED — Abberior
  - **scanner:** Galvanometric Scanner
  - **objective:** UPlanSApo 60x/1.2 W WATER — Olympus
  - **light:** 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  - **filter:** Emission Filter Wheel, 525/25 (catalogue no. FF01-525/25)
  - **detector:** Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies

**Problems found:**
- D1: second (confocal) acquisition inherits and reports the STED module.
- D10: repeated microscope/objective/software/review blocks also reduce multi-acquisition readability.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The Easy3D STED module was used (Abberior easy3D STED). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). The Easy3D STED module was used (Abberior easy3D STED). The microscope used a galvanometric scanner. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Galvanometric Scanner]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>106. M04 — MAJOR ISSUE</strong> — Deltavision OMX / SIM → Widefield fluorescence</summary>

**Instrument:** Deltavision OMX  
**Imaging method:** SIM → Widefield fluorescence  
**Physical path:** Widefield fluorescence → Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  - **method:** SIM
  - **route:** Widefield fluorescence
  - **module:** 3D-SIM Module — GE Healthcare
  - **objective:** Plan Apo N 60x/1.42 OIL — Olympus
  - **light:** 488 nm laser (GE Healthcare) — GE Healthcare
  - **filter:** OMX Emission Filters, Alexa 488
  - **detector:** PCO Edge — PCO
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **module:** 3D-SIM Module — GE Healthcare
  - **objective:** Plan Apo N 60x/1.42 OIL — Olympus
  - **light:** 488 nm laser (GE Healthcare) — GE Healthcare
  - **filter:** OMX Emission Filters, Alexa 488
  - **detector:** PCO Edge — PCO

**Problems found:**
- D1: second (widefield) acquisition inherits and reports the 3D-SIM module.
- D10: repeated microscope/objective/software/review blocks also reduce multi-acquisition readability.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>107. M05 — MINOR ISSUE</strong> — ONI Nanoimager / SMLM → TIRF</summary>

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM → TIRF  
**Physical path:** Widefield fluorescence → Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
  - **method:** SMLM
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 405 nm laser (ONI violet) — ONI, 640 nm laser (ONI red) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using NimOS microscope control software.
  - **method:** TIRF
  - **route:** Widefield fluorescence
  - **objective:** UPLXAPO100XO 100x/1.45 OIL — Olympus
  - **light:** 488 nm laser (ONI blue) — ONI
  - **detector:** Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu

**Problems found:**
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 405 nm laser (ONI violet) and 640 nm laser (ONI red). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 405 nm laser (ONI violet) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 488 nm laser (ONI blue). Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 488 nm laser (ONI blue) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>108. M06 — MAJOR ISSUE</strong> — Zeiss LSM 880 with AiryScan / ISM (AiryScan) → Confocal point scanning</summary>

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan) → Confocal point scanning  
**Physical path:** Point-scanning confocal → Point-scanning confocal  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
  - **method:** ISM (AiryScan)
  - **route:** Point-scanning confocal
  - **module:** AiryScan Detector/Module — Zeiss
  - **scanner:** Resonant Scanner
  - **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  - **light:** 488 nm laser (Argon) — Unknown
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal
  - **module:** AiryScan Detector/Module — Zeiss
  - **scanner:** Resonant Scanner
  - **objective:** C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  - **light:** 488 nm laser (Argon) — Unknown
  - **detector:** PMT (Ch1) — Unknown

**Problems found:**
- D1: second conventional confocal acquisition inherits and reports the Airyscan module.
- D10: repeated microscope/objective/software/review blocks also reduce multi-acquisition readability.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Image scanning microscopy (ISM; Airyscan) was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). The microscope used a resonant scanner (line rate 8000 Hz). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting detector/reconstruction mode and the reconstruction software/version and settings used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). The microscope used a resonant scanner (line rate 8000 Hz). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon). Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>109. M07 — MINOR ISSUE</strong> — Leica STELLARIS 8 FALCON FLIM / Confocal point scanning → Confocal point scanning</summary>

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning → Confocal point scanning  
**Physical path:** Point-scanning confocal, FLIM → Point-scanning confocal, FRET  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal, FLIM
  - **module:** FLIM Module — Leica Microsystems
  - **scanner:** Tandem Scanner (Galvo/Resonant)
  - **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  - **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  - **detector:** Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.
  - **method:** Confocal point scanning
  - **route:** Point-scanning confocal, FRET
  - **module:** FLIM Module — Leica Microsystems
  - **scanner:** Tandem Scanner (Galvo/Resonant)
  - **objective:** HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  - **light:** white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  - **detector:** Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems

**Problems found:**
- D1/D10: FLIM module state persists into the second FRET entry, creating ambiguity about whether it was deliberately reused; the section is also highly repetitive.
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FLIM data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FRET data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>110. M08 — MINOR ISSUE</strong> — Leica Thunder / Phase contrast → Widefield fluorescence</summary>

**Instrument:** Leica Thunder  
**Imaging method:** Phase contrast → Widefield fluorescence  
**Physical path:** Transmitted light → Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
  - **method:** Phase contrast
  - **route:** Transmitted light
  - **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
  - **detector:** Leica K3C — Leica
- **second_acquisition:**
  - **confirmed:** Instrument control and image acquisition were performed using LAS X with Navigator.
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **objective:** HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
  - **light:** 395 nm LED (Leica LED 8) — Leica
  - **detector:** Leica K8 — Leica

**Problems found:**
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 395 nm LED (Leica LED 8). Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 395 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) and Standalone Emission Wheel (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>111. M09 — MINOR ISSUE</strong> — Zeiss TIRF / Widefield fluorescence → TIRF</summary>

**Instrument:** Zeiss TIRF  
**Imaging method:** Widefield fluorescence → TIRF  
**Physical path:** Widefield fluorescence → Widefield fluorescence  
**Assessment:** **MINOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **objective:** Plan Apochromat 20x/0.45 AIR — Zeiss
  - **light:** 488 nm laser — Unknown
  - **filter:** Filter Turret, Filter set 38 HE (GFP) (catalogue no. 38 HE)
  - **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu
- **second_acquisition:**
  - **method:** TIRF
  - **route:** Widefield fluorescence
  - **objective:** Plan Apochromat 20x/0.45 AIR — Zeiss
  - **light:** 488 nm laser — Unknown
  - **filter:** Filter Turret, Filter set 38 HE (GFP) (catalogue no. 38 HE)
  - **detector:** Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu

**Problems found:**
- D10: repeated microscope/objective/software/review blocks make the combined section read as concatenated form output rather than one Methods section.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Zeiss Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 20x/0.45 Air objective (Zeiss Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

<details><summary><strong>112. M10 — MAJOR ISSUE</strong> — Leica DM IRBE / Darkfield → Widefield fluorescence</summary>

**Instrument:** Leica DM IRBE  
**Imaging method:** Darkfield → Widefield fluorescence  
**Physical path:** Transmitted light → Widefield fluorescence  
**Assessment:** **MAJOR ISSUE**

**Selections made in the UI:**
- **first_acquisition:**
  - **method:** Darkfield
  - **route:** Transmitted light
  - **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
  - **light:** halogen lamp (Leica 12V 100W halogen bulb) — Leica
  - **detector:** Unknown Camera — Unknown
- **second_acquisition:**
  - **method:** Widefield fluorescence
  - **route:** Widefield fluorescence
  - **objective:** PL FLUOTAR 20x/0.50 PH2 AIR — Leica
  - **light:** arc lamp (Leica 50W HBO short arc bulb) — Leica
  - **filter:** Fluorescence Turret, Filter Cube EGFP
  - **detector:** Unknown Camera — Unknown

**Problems found:**
- D3: both acquisitions report unresolved "Unknown Camera" detector identity.
- D10: repeated microscope/objective/software/review blocks also reduce multi-acquisition readability.

**Suggested improvement:** See prioritized defects D1/D3 where applicable and D10 for section-level deduplication.

**Exact generated Methods text:**
```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Widefield fluorescence imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013).

Illumination was provided by arc lamp (Leica 50W HBO short arc bulb). The light path included Filter Cube EGFP in the Fluorescence Turret. Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Leica 50W HBO short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

</details>

## Code-level diagnosis references

All paths below refer to commit `2988377cfafe3ac8b5db0d459f0e4d372e7c1ce3` and were inspected only after the corresponding UI failure had been reproduced:

- `assets/javascripts/methods_generator_app.js`: method-change handler clears route/readout/light/detector/filter/filter-position/splitter state but not modules; same file globally binds `dto.modules`.
- `assets/javascripts/methods_generator_app.js`: Add-acquisition validation requires method/path only inside the method-first branch; prose fallback can append `with the <route> route`; instrument-wide metadata blockers are appended to every acquisition.
- `instruments/retired/Leica TCS SP5 Multiphoton.yaml`: source record explicitly contains `multiphoton` capability/path information, despite the deployed generator exposing no method picker for the record.
- `instruments/Leica DM IRBE.yaml`, `Leica DM RB.yaml`, `Leica DMRE.yaml`: camera endpoint identity is recorded as `Unknown` / `Unknown Camera`.
- `scripts/dashboard/instrument_view.py`: placeholder-identity sanitization exists for some publication references, confirming the desired policy, but it is not consistently applied to the optical-path publication projection; instrument-reference construction also appends the stand-orientation label literally.

## Bottom line

The method-first redesign is directionally correct and already prevents many route/hardware mistakes. The next release should focus less on adding more prose rules and more on **state ownership and publication-safety invariants**: every selected fact must be compatible with the current method/path; every emitted hardware identity must be genuinely known; incomplete specialist acquisitions must be explicit; and database diagnostics must stay outside manuscript prose. Fixing D1–D4 first would materially change the trustworthiness of the generator.
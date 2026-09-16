# Methods generator — consolidated findings, ledger questions and planned UX changes

Consolidates two independent black-box audits of the rendered Methods generator:

* **Audit A** (this repository): 116 Playwright-driven sessions, all 22 active
  records plus the retired SP5 — [`methods_generator_ui_audit.md`](methods_generator_ui_audit.md),
  transcripts in [`methods_generator_ui_audit_transcripts.md`](methods_generator_ui_audit_transcripts.md).
* **Audit B** (external, ChatGPT): 112 captured UI runs on the deployed site at
  commit `2988377`, defect classes D1–D10.

Both audits were black-box first and inspected the implementation only after
reproducing a user-visible failure. Neither changed any code.

## How the two audits line up

They agree on the shape of the product: technique-first prose is good, review
prompts are mostly technique-appropriate, and the method → path → hardware
workflow is sound in its basic form. They agree on eight defects (§1.1, 1.4,
1.6, 1.7, 1.8, 2.1, 2.2, 2.5, 3.1 below), which is strong evidence those are
real and not artefacts of either harness.

Each found things the other did not, because they probed different things:

| Found only by Audit A | Why B missed it |
|---|---|
| Objectives persist across acquisitions (§1.2) | B tested module persistence but not objective persistence |
| Two instruments render under one name (§1.3) | B never put both 3i systems in one section |
| Re-generating after a correction duplicates the entry (§1.9) | B did not test the correct-and-regenerate loop |
| **Clear all** leaves every checkbox ticked (§1.10) | not tested |
| Multi-camera acquisitions collapse to one camera (§1.11) | B did not tick two cameras |
| Route hardware is wiped on a *same-path* method change (§1.5) | B read this as correct behaviour (see below) |

| Found only by Audit B | Why A missed it |
|---|---|
| SP5: **Add** with nothing selected emits a full acquisition (§1.6b) | A always let the route auto-select |
| SP5 prose contains "with the Multiphoton route" (§2.1) | same |

**One genuine disagreement.** Audit B lists "route-specific sources, filters and
detectors clear correctly when the method changes" as a strength. Audit A
reproduces the same behaviour but classifies it as a defect, because the handler
clears unconditionally — including when the new method uses the *same* recorded
path (Zeiss TIRF widefield → TIRF, OMX SMLM → SIM, brightfield → phase contrast
everywhere). Both readings are consistent with the code; the disagreement is
about whether wiping still-valid selections without telling the user is
acceptable. Audit A's reproductions (B09, B10, B11, C10, C13, D08) show it
produces TIRF and SIM paragraphs with no excitation source and no camera, so it
is treated as a defect here. **The planned move to multi-select imaging methods
(§4.3) dissolves this disagreement**: clearing then becomes "drop what is no
longer available under any selected method", which is correct in both readings.

**Severity reconciliation.** Audit B reports no Critical defects; Audit A reports
four. The gap is mostly scope, not judgement: B's own rubric defines Critical as
"generated text contains a scientifically false statement or attributes
hardware/method/software to the experiment that the user did not select", and
B's own D1 (stale modules) does exactly that. This document uses Audit A's
severities and marks B's classification where it differs.

---

# Part 1 — Consolidated bug list

Numbered fresh. `A:` and `B:` give the originating audit's identifier.

## Critical — text asserts something the user did not select, or is factually wrong

### 1.1 Modules, scanners, modulators and illumination logic survive a method change and are then reported as used
`A: D-01` · `B: D1` · **both audits**

**Affects:** Abberior STED/RESOLFT, Zeiss LSM 880, Deltavision OMX, STELLARIS,
Nikon Crest V3 — any record with modules.

**Repro:** LSM 880 → *ISM (AiryScan)* → tick the AiryScan module → Add. Change
the method to *DIC*, tick the halogen lamp and transmitted PMT → Add.

**Actual:**
> Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. … **The AiryScan Detector/Module was used (Zeiss Airyscan).** Transmitted-light illumination was provided by halogen lamp…

Also reproduced as: Easy3D STED in a confocal-reference paragraph; 3D-SIM module
in a widefield-reference paragraph; Easy3D STED in a RESOLFT paragraph;
STED module after switching to widefield on the STELLARIS.

**Root cause:** `assets/javascripts/methods_generator_app.js:1436-1439` — the
method-change handler clears exactly
`["route","readout","light","det","filter","filterposition","splitter"]`.
`module`, `scanner`, `magnification-changer`, `optical-modulator`,
`illumination-logic` and `obj` are not in the list.

**Fix:** give modules and specialist hardware method/path compatibility metadata
and re-render them like route-scoped hardware. Under the planned multi-select
methods (§4.3) the rule becomes: *a selection survives only while it is still
offered by at least one selected method.*

### 1.2 Objectives persist across acquisitions and are attributed to every later entry
`A: D-01 (objective variant)` · Audit A only

**Repro:** 3i CSU-W1 → widefield with the 20×/0.8 → Add. Switch to *Confocal
spinning disk*, tick the 63×/1.4 → Add.

**Actual (second entry):**
> Imaging was performed with a **20x/0.8 Air objective** (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000) **and a 63x/1.4 Oil objective** (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900).

Also C02 (Zeiss TIRF), C06 (Ti2-E), C10 (EVOS, three entries compounding),
D08 (OMX SIM entry keeps the SMLM TIRF objective).

**Fix:** as 1.1. Objectives are legitimately multi-select *within* one
acquisition (some experiments do use two), so the fix is per-entry scoping, not
making the control exclusive.

### 1.3 Two different instruments are given the same name in prose
`A: D-02` · Audit A only

`3i CSU-W1 Spinning Disk` and `3i Marianas CSU-W1 Spinning Disk Med C` share
`manufacturer: 3i / Zeiss` and `model: Marianas CSU-W1 Spinning Disk Confocal`
but have distinct `display_name`s. Both render as *"the 3i / Zeiss Marianas
CSU-W1 Spinning Disk Confocal inverted microscope"*, so a section using both is
unreadable and the second system is described under the other's name.

**Root cause:** `scripts/dashboard/instrument_view.py:944-955` builds
`instrument_reference` from manufacturer + model and only falls back to
`display_name` when both are absent. The correct implementation already exists —
`_microscope_sentence()` in `scripts/dashboard/methods_export.py:270-306` prefers
`display_name`, adds manufacturer/model parenthetically and suppresses
placeholder stand values — but it is only reachable through the `base_sentence`
fallback, which is why the SP5 renders correctly and nothing else does.

**Fix:** one identity builder. Expected output:
*"…using the 3i Marianas CSU-W1 Spinning Disk Med C (3i / Zeiss Marianas CSU-W1
Spinning Disk Confocal), an inverted microscope."*

### 1.4 Placeholder hardware identities are published as prose
`A: D-09` · `B: D3` · **both audits**

**Affects:** Leica DM IRBE / DM RB / DM RE (`Images were recorded using Unknown
Camera.`), Zeiss LSM 510 JPK AFM (`Images were recorded using Zeiss.` — the
manufacturer alone standing in for the detector). Neither emits a review prompt,
although the same record's placeholder *objective* does get one.

**Root cause:** `scripts/dashboard/optical_path_view.py:304-330`. Its docstring
states publication prose "never carries an internal id or the word 'Unknown'",
and `_identity_value()` does strip placeholder manufacturer/model — but the last
line is `return identity or authored or clean_text(item.get("id"))` and
`authored` is the raw `display_label`, which is literally `Unknown Camera`. For
the LSM 510 the model is stripped and the bare manufacturer survives.

**Fix:** when `_identity_value()` strips an identity, return an empty label and
let the caller emit `[PLEASE SPECIFY: the camera used for this acquisition
(manufacturer and model); the facility record does not identify it]` instead of
a sentence. Treat manufacturer-without-model as unresolved for endpoints.

## High — misleading or materially incomplete output, or lost user state

### 1.5 Route-scoped selections are wiped when the method changes even though the path does not
`A: D-03` · Audit A only (see disagreement above)

**Repro:** Zeiss TIRF → *Widefield fluorescence* → 63×/1.46, 561 nm laser,
Filter set 43 HE, ORCA-Flash4.0. Realise it was TIRF → switch the method to
*TIRF* (the recorded path is "Widefield fluorescence" both times). Add.

**Actual:** *"Total internal reflection fluorescence (TIRF) imaging was performed
using the Zeiss TIRF inverted microscope. Imaging was performed with a 63x/1.46
Oil objective (Zeiss Alpha Plan Apochromat)."* — laser, filter and camera gone
from the prose **and** from the checkboxes, silently, with nothing in the review
block.

**Fix:** compare the new method's `routeIds` with the checked route; retain when
it is still allowed (`updateHardwareVisibility(dto, /*preserveHardware*/ true)`
already exists). Announce any clearing in the status line. §4.3 supersedes this.

### 1.6 No completeness check on the entry: missing detector, illumination or objective is neither reported nor requested
`A: D-04` · `B: D4, D8` · **both audits**

`buildAcquisitionEntry()` validates route-level topology
(`item.topologyIncomplete`) but never checks whether the finished entry actually
contains an illumination, detection or objective statement.

* **Detector:** LSM 880 ISM (A53) emits an entry with no detection sentence at
  all. Also B03, B23, C03, C05, C13, D06, D08, D15.
* **Illumination:** transmitted-light methods on 3i CSU-W1, 3i Med C and Leica
  Thunder produce no illumination sentence because no lamp is recorded on that
  route — and say nothing about it (`B: D8`).
* **Objective:** untick it and there is no objective in the prose and no request
  (B25, D03).
* **Technique essentials:** Abberior STED with only an objective produces a
  complete-looking STED paragraph with no excitation source, no depletion source
  and no detector (`B: D4`, A: B12).

All are QUAREP-LiMi minimum-reporting items, so their absence is precisely what
the review block exists for.

**Fix:** after assembling the paragraphs, check the three universal categories
and push the corresponding `[PLEASE SPECIFY]`. Add method-specific essential
contracts on top (STED: excitation + depletion + detector; SMLM: excitation +
detector; SIM: excitation + detector + reconstruction).

### 1.6b Route-only records bypass the Add validation entirely
`B: D2` · reproduced and confirmed in this repo

Selecting *Leica TCS SP5 Multiphoton (Retired)* and pressing **Add to methods**
with nothing selected appends a complete acquisition:

```text
Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope.

Review before publication:
- [PLEASE VERIFY: this instrument is recorded as retired; …]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; …]
```

— including a prompt about "the selected route" when no route is selected. The
guard in the Add handler is gated on `methodFirst`, which is false for records
with no method section.

**Fix:** require a selected path whenever a route section exists, and auto-select
a sole path at load (not only on method change).

### 1.7 The multiphoton entry never states the method, and falls back to route vocabulary
`A: D-08` · `B: D2` · **both audits**

With the path explicitly selected the SP5 produces:

> Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope, **with the Multiphoton route**. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). … Excitation was provided by pulsed near-ir laser (Coherent Chameleon Ultra II). Images were recorded using NDD PMT.

Nothing says multiphoton, two-photon excitation or non-descanned detection, and
"route" appears in finished prose.

**Root cause:** the technique-first opening sentence is only used when a `method`
radio is checked (`methods_generator_app.js:1647-1650`); with no method list the
code falls back to `methods.base_sentence` plus a route clause.

**Fix:** derive the opening from the selected route's publication phrase when no
method control exists; delete the route clause from publication prose; add
multiphoton to the technique-specific reporting map.

### 1.8 Instrument-global metadata blockers are injected into acquisition-specific review prompts
`A: D-10` · `B: D5` · **both audits** (B: 33 of 72 baseline outputs affected)

`methods_generator_app.js:1753-1760` pushes every
`getMethodsMetadataStatus(dto)` blocker into every entry regardless of what the
user selected. Consequences:

* `[PLEASE VERIFY: Software version is not recorded for this instrument]` appears
  when no software was confirmed (A15) — and on the Zeiss TIRF, which offers no
  acquisition-software control at all (A56).
* `[PLEASE VERIFY: Module model is not recorded…]` appears when no module was
  selected (A12).
* When software *is* confirmed, the user gets both a specific version prompt and
  the generic blocker (`B: D5`, ONI).

**Fix:** scope blockers to the component categories the entry reports; keep the
rest in the on-page "Details to confirm" banner, which already shows them.

### 1.9 Correcting a selection after generating adds a duplicate acquisition
`A: D-05` · Audit A only

Generate a widefield entry, notice the acquisition software was not ticked, tick
it, press **Add to methods** again → two complete near-identical paragraphs with
two identical review blocks, and no way to remove the first except **Clear all**
(which does not reset the form — 1.10).

**Root cause:** `methods_generator_app.js:1818-1823` keys entries on
`JSON.stringify([id, sessionLabel, allCheckedIds, runtimeConfirm, text])`, so any
checkbox change is a new key. The behaviour is documented on the page, but it
makes the most natural correction workflow produce wrong output.

**Fix:** key on `(instrumentId, sessionLabel)` and replace on re-add, with a
visible "Replaced the previous entry for *Figure 2*" status message.

### 1.10 "Clear all" clears the draft but leaves every checkbox ticked
`A: D-06` · Audit A only

`methods_generator_app.js:1829-1833` resets `accumulatedEntries` and
`usedInstruments` only. The page text says "Use **Clear all** to start again";
combined with 1.1/1.2 this is how stale hardware reaches users who believe they
reset.

**Fix:** also uncheck everything under `#hardware-options`, clear the acquisition
reference, and re-run `updateHardwareVisibility`. If retaining the configuration
is deliberate, split into "Clear draft" and "Reset selections".

### 1.11 Multi-camera acquisitions cannot be reported
`A: D-07` · Audit A only

Nikon Crest V3 with the DualCam splitter and **both** `Photometrics Kinetix`
cameras ticked yields *"Light was directed through MXR00547 V3
DualCam-GFP/mCherry 2 Bands Celesta Set. **Images were recorded using
Photometrics Kinetix.**"* — a simultaneous two-camera acquisition described as
single-camera, with a prompt asking the user to pick *one*. On the Deltavision
OMX the three `PCO Edge` cameras are exclusive radios, so the configuration
cannot be expressed at all and no prompt is emitted.

**Root cause:** the publication label is `manufacturer + model`
(`optical_path_view.py:328-329`), identical for both cameras, so
`mergeByPublicationTemplate` collapses them into one sentence subject.

**Fix:** disambiguate identically-named endpoints by their recorded branch/port
label and count them in the sentence. Needs the ledger change in §3.3.

## Medium

| # | Defect | Source | Note |
|---|---|---|---|
| 1.12 | Source-role `[PLEASE SPECIFY: … excitation, transmitted illumination, or depletion]` fires purely on missing `role` metadata, once per source (up to four copies in one block), and flips the verb between "Excitation was provided by" and "Illumination was provided by" for identical physics on different instruments | A: D-13 · B: prompt quality | 65 sources across 19 records lack `role` (§3.1). The selected method and path already constrain the answer |
| 1.13 | Implementation vocabulary in user-facing text: `(Widefield fluorescence route)` in prompts, `with the Multiphoton route` in prose, `position EMP_BF`, `Power HyD S SP pos 1…pos 5`, schema blocker names (`Capability axes`, `Optical path element ID/type`, `Light path route type`) | A: D-18/D-19 · B: D6 | Both audits flag this; B's lexical guard test is the right regression |
| 1.14 | Light-source count used as channel count, so STED (excitation + depletion), SMLM (activation + excitation) and RESOLFT trigger `[PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously]` | A: A01/A03 · B: D7 | Exclude depletion/activation/switching roles from the count |
| 1.15 | Method/hardware contradictions unflagged: confocal + depletion laser; STED without depletion; Airyscan + descanned Ch1 PMT; two-camera splitter with one camera; EVOS GFP LED cube paired with the Cy5 cube (physically one integrated unit) | A: D-11 | Emit `[PLEASE VERIFY]`, do not block |
| 1.16 | Transmitted-light methods never report the contrast optics — no condenser annulus for phase contrast, no Wollaston prisms/analyser for DIC — and nothing asks for them | A: D-14 · B: D8 | Only 5 of 22 records mention any contrast optic (§3.6) |
| 1.17 | Readouts appended as one-clause stubs: `Spectral Imaging data were acquired. FLIM data were acquired. FCS data were acquired. FRET data were acquired.` | A: D-15 · B: prose §2 | UI title case travels into prose |
| 1.18 | Over-ticking collapses into one sentence per checkbox; on the STELLARIS five LAS X workflow modules are each described as having "performed instrument control and image acquisition", and five separate version numbers are requested | A: D-12 · B: prose §1/§2 | Needs the ledger change in §3.4 |
| 1.19 | Multi-acquisition sections repeat microscope identity, objective, software and the generic prompts verbatim per entry | A: D-25 · B: D10 | **Being addressed by §4.1** |
| 1.20 | FLIM prompt asks time- vs frequency-domain even when the record settles it (Lambert LIFA is named "frequency domain FLIM"; STELLARIS FALCON is TCSPC) | A: D-16 | |
| 1.21 | A filter holder ticked without a position is described as an optical element: `The light path included Emission Filter Wheel.` | A: D-17 | **Interacts with §4.2** |
| 1.22 | Andor BC43: the fluorescence emission wheel is recorded on the transmitted-light route, so a brightfield draft is asked which emission filter was used — and ticking a nonsense one both writes it into brightfield prose and silences the prompt | A: D-20 | Ledger question §3.5 |
| 1.23 | The Zeiss ApoTome.2 is presented as "The SIM Module was used", inviting a super-resolution SIM reading; no sectioning parameters requested | A: D-21 | `type: sim_module` in the record |
| 1.24 | RESOLFT gets no technique-specific reporting recommendation | A: D-22 | |
| 1.25 | **Add to methods** with an instrument but no method silently does nothing | A: D-23 | |
| 1.26 | The same fact stated twice when a component appears in two categories: `The RESCue STED module was used (Abberior).` … `Adaptive illumination used RESCue STED.` | A: D-24 | |

## Low

| # | Defect | Source |
|---|---|---|
| 1.27 | Missing articles before generated labels: "Excitation was provided by 640 nm laser" → "by a 640 nm laser" | A: D-26 |
| 1.28 | `the Transmitted light light path` — duplicated word | A: D-27 |
| 1.29 | `the ONI Nanoimager other microscope` — the `other` stand enum rendered literally (ONI, MSquared) | A: D-03 note · B: D9 |
| 1.30 | Catalogue codes as sentence subjects: `Light was directed through MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set.` | A: D-28 |
| 1.31 | `The light path included NIR dichroic position in the CSU-W1 Dichroic Slider` — "position" is inventory wording | A: D-29 |
| 1.32 | FCS entry says "Images were recorded using …" — FCS records photon traces, not images | A: D-31 |

---

# Part 2 — Suggested fix order

1. **Scoping** (1.1, 1.2, 1.5, 1.10) — one change to what "this acquisition"
   means fixes four defects and is a prerequisite for §4.3.
2. **Publication-identity validator** (1.3, 1.4, 1.13, 1.29) — one function
   deciding what may appear as a name in prose.
3. **Entry completeness contract** (1.6, 1.6b, 1.7, 1.15, 1.25).
4. **Review-block scoping** (1.8, 1.12, 1.14, 1.19 + §4.1).
5. **Sentence assembly** (1.11, 1.17, 1.18, 1.21, 1.26, and §4.2).

---

# Part 3 — Questions for the YAML ledger

These are the data gaps the generator could not work around. Each is phrased as
a question to put to facility staff, with the exact records affected. None
should be filled by assumption; where a value is genuinely not applicable, that
should be recorded explicitly rather than left blank.

## 3.1 Light-source role — **highest impact**

`hardware.sources[].role` is unset for **65 sources across 19 instruments**.
This produces the single noisiest review prompt (1.12) and makes the illumination
verb inconsistent between instruments.

> For each recorded light source, what is its role on the light path:
> excitation, transmitted illumination, reflected illumination, depletion,
> activation, or alignment?

Records to complete (all sources unless noted):

| Instrument | Sources missing `role` |
|---|---|
| Andor BC43 Benchtop Confocal | 405, 488, 561, 638 nm Borealis lasers |
| EVOS fl | transmitted LED + all five Light Cube LEDs |
| Lambert FLIM | 406, 469, 533 nm multi-LED |
| Leica STELLARIS 8 FALCON FLIM | white light laser, 405 nm DMOD, Leica LED 3 |
| Leica Thunder | all eight LED 8 lines |
| MSquared Aurora Airy Beam | 488, 561, 640 nm OBIS |
| Nikon Eclipse Ti2-E | all seven Spectra X lines |
| Nikon Ti2-E Crest V3 | all eight Celesta lines |
| ONI Nanoimager | 405, 488, 561, 640 nm |
| Zeiss LSM 880 with AiryScan | 405, 458, 488, 514, 543, 633 nm |
| Zeiss TIRF | 488, 561, 639 nm |
| Agilent xCELLigence RTCA eSight | 393, 482, 595 nm LEDs |
| Zeiss AxioZoom.V16 | HXP 200C arc lamp |
| Olympus BX60 | HBO 103W arc lamp |
| Leica DM IRBE / Leica DM RB | HBO arc lamps |
| 3i CSU-W1 / 3i Med C | the widefield LED only (lasers already carry roles) |
| Zeiss LSM 510 JPK AFM | 488 nm placeholder laser |

Worth confirming separately: should the Abberior **775 nm Katana HP** stay
`depletion` and the ONI/OMX **405 nm** be `activation` rather than `excitation`?
That distinction is what stops the channel-count prompt firing wrongly (1.14).

## 3.2 Detector identity

Six records carry placeholder detector identities that currently reach prose
(1.4):

| Instrument | Recorded as | Question |
|---|---|---|
| Leica DM IRBE | `Unknown / Unknown Camera` | Which camera is on the port? Is there one at all, or is this stand visual-only plus an ad-hoc camera? |
| Leica DM RB | `Unknown / Unknown Camera` | as above |
| Leica DM RE | `Unknown / Unknown Camera` | as above |
| Zeiss LSM 510 JPK AFM | `Zeiss / Unknown PMT` | Which PMT model? If the record is a placeholder pending decommissioning, should it be marked as such? |
| Zeiss LSM 880 with AiryScan | `Unknown` manufacturer on all five detectors | These are Zeiss/Hamamatsu parts — can the manufacturer be filled in? |
| Leica TCS SP5 (retired) | empty manufacturer on the non-descanned PMTs | Can the retired record be completed from the last service report, or should it be marked historically unresolvable? |

## 3.3 Detectors that are indistinguishable, and detectors that are unreachable

**Duplicate labels** (1.11). Two records have detectors whose
`manufacturer + model` are identical, so neither the UI nor the prose can tell
them apart:

* **Deltavision OMX** — three × `PCO Edge`
* **Nikon Ti2-E Crest V3** — two × `Photometrics Kinetix`

> Do these cameras have port or channel names (camera 1/2/3, "green camera" /
> "red camera", a physical port label)? Can each be given a distinguishing
> `model` suffix or a port label that is safe to print in a Methods section?

**Unreachable detectors — Zeiss LSM 880.** The record lists five detectors, but
only three are referenced by any light path:

| Detector | `id` | Referenced by a light path? |
|---|---|---|
| PMT (Ch1) | `detector_1` | yes |
| Cooled PMT (Ch2) | `detector_2` | yes |
| Transmitted light PMT | `detector_3` | yes |
| 32-channel GaAsP spectral array | `detector_4` | **no** |
| 32-channel AiryScan detector (GaAsP) | `detector_5` | **no** |

This is the direct cause of the Airyscan entry having no detection sentence
(1.6): the correct answer exists in the ledger but is not tickable.

> Should the confocal light path gain branches ending at `detector_4` (spectral
> lambda detection) and `detector_5` (Airyscan)? What is the branch structure —
> are the Airyscan and the spectral array selected exclusively against the Ch1/Ch2
> PMTs, or can they be used alongside them?

## 3.4 Acquisition software

| Situation | Records | Question |
|---|---|---|
| `role: acquisition` recorded with `name: Unknown` | Zeiss TIRF, Zeiss LSM 510 JPK AFM, Lambert FLIM | These instruments therefore offer the user **no software checkbox at all**, while still emitting a "software version not recorded" warning. What is the actual acquisition software and version? (ZEN edition for the TIRF, ZEN/AIM for the LSM 510, LI-FLIM for the Lambert?) |
| No software rows at all | Leica DM IRBE, Leica DM RB, Leica DM RE | Is there any acquisition software on these stands, or are they visual/standalone-camera only? If genuinely none, can that be recorded explicitly (`software_status: not_applicable`) so the generator stops asking? |
| Version missing | Abberior Imspector, EVOS on-board interface, Leica Thunder LAS X, MSquared Cubes, NIS-Elements AR (Crest V3), ONI NimOS, Olympus Cell^D, Zeiss ZEN Pro, Leica LAS AF (SP5), and all five STELLARIS LAS X entries | What version is installed? A version recorded as "not tracked" is more useful than an empty string, because the generator can then stop requesting it. |
| Product vs. module structure | **STELLARIS 8** — `LAS X STELLARIS Control Software`, `LAS X Dye Finder`, `LAS X Assay Editor`, `LAS X Live Data Mode`, `LAS X MicroLab` are all `role: acquisition` | These are workflow modules *inside* LAS X, not alternative acquisition software, and the generator currently writes five sentences each claiming to have performed instrument control (1.18). Should they be re-modelled as one product with named modules? |

## 3.5 Light-path topology

| Question | Records |
|---|---|
| The transmitted-light route exposes a detector but **no light source**, so transmitted brightfield / phase contrast / DIC drafts silently describe no illumination. Is the transmitted lamp genuinely absent, or is it just not attached to that route? | 3i CSU-W1 Spinning Disk, 3i Marianas Med C, Leica Thunder |
| The **fluorescence emission filter wheel** is recorded on the transmitted-light route, so brightfield drafts are asked which emission filter was used, and a user can write "mCherry" into a brightfield paragraph. Is that wheel really in the transmitted path, or should it be confocal/widefield only? | Andor BC43 |
| The record exposes a **Multiphoton** light path but no imaging-method option, so the draft never says multiphoton and prose falls back to "with the Multiphoton route". Can the recorded `modalities: [confocal_point, multiphoton]` be surfaced as a method with a publication phrase? | Leica TCS SP5 (retired) |
| `stand_orientation: other` renders literally as "the ONI Nanoimager other microscope". Is there a better vocabulary term (benchtop? enclosed? custom?), or should `other` be suppressed in prose? | ONI Nanoimager, MSquared Aurora Airy Beam |
| The transmitted-light route is completely empty. Is transmitted brightfield actually available on this stand? | Zeiss LSM 510 JPK AFM |

## 3.6 Contrast optics — currently almost entirely unrecorded

The generator can name a `Ph1` objective and a `DIC` objective, but no record
exposes the condenser annulus, the Wollaston/Nomarski prisms or the analyser as
selectable components, so no phase-contrast or DIC draft can describe how the
contrast was generated (1.16). Only five records mention them anywhere, and only
in free-text notes:

| Record | Mentions |
|---|---|
| Leica DM IRBE | condenser |
| Leica DM RE | Wollaston |
| Leica STELLARIS 8 | analyser |
| Leica Thunder | analyser |
| Nikon Eclipse Ti2-E | DIC prism, analyzer |

> For each stand offering phase contrast or DIC: which condenser is fitted, which
> phase annuli does it carry (Ph1/Ph2/Ph3), and which DIC prism/analyser set is
> used with which objectives? Should these become recorded optical-path elements
> so a user can tick them?

## 3.7 Filter positions with no transmission bands

19 positions across 8 records have no `bands`, so the draft emits
`[PLEASE VERIFY: the recorded transmission bands for X are incomplete]`. **This
becomes blocking once filter specs are printed in the prose (§4.2).**

| Record | Positions missing bands |
|---|---|
| Leica STELLARIS 8 | all five reflected-light cubes (405, GFP, TXR, Cy5 narrow, ICR) |
| Olympus BX60 | U-MWU (DAPI), U-MWIB (GFP wide), U-MWIG (Alexa 546/TRITC) |
| Nikon Eclipse Ti2-E | Chroma 89403bs, Chroma 84000v2, Lamp Filter Cubes, DIC Fixed Analyzer |
| Nikon Ti2-E Crest V3 | Crest Excitation Wheel "Neutral Density", DualCam set position 1 |
| MSquared Aurora | GFP longpass, RFP longpass |
| 3i CSU-W1 | "NIR dichroic position" |
| Leica DM IRBE, Leica DM RB | Filter Cube A (DAPI/Hoechst) |

Also reported at run time but not visible in this sweep (composite cubes whose
bands are partially recorded): Leica Thunder `DFT51010` and `CYR71010`, 3i Med C
`LED-TRITC-A-ZHE-Zero`, Agilent eSight "Green Channel".

> For each position: what are the excitation band, dichroic edge and emission
> band, and the manufacturer + catalogue number? For neutral-density positions,
> what is the OD? For "empty" positions, is `empty` the right component type?

## 3.8 Smaller gaps

| Field | Records | Question |
|---|---|---|
| `hardware.scanner.manufacturer` / `model` | 10 records with a real scanner: 3i CSU-W1, 3i Med C, Abberior, Andor BC43, STELLARIS, MSquared, Crest V3, LSM 510, LSM 880, SP5 | The draft asks "manufacturer and model of the Tandem Scanner" on a Leica system, which reads oddly. Is the scanner a named unit (Yokogawa CSU-W1, CrestOptics X-Light V3, Leica tandem galvo/resonant), or should it inherit the instrument's manufacturer? |
| `detectors[].pixel_pitch_um` | 19 detectors across 9 records | Needed for the "Detector pixel pitch" blocker to clear. For PMTs/HyDs/APDs pixel pitch is not applicable — can that be recorded as N/A rather than blank, so the blocker stops firing on point detectors? |
| `modules[].model` | 3i Marianas Med C — `motorized_stage` and `piezo_z_stage`, both ASI | Which ASI models? |
| Module vocabulary | Zeiss AxioZoom.V16 — `type: sim_module`, model ApoTome.2 | The draft writes "The SIM Module was used (Zeiss ApoTome.2)", which suggests super-resolution SIM. Should the vocabulary gain a distinct `optical_sectioning_module` / `apotome` term? |
| FLIM domain | Lambert LIFA (frequency domain), STELLARIS FALCON (TCSPC time domain) | Both are recorded well enough to know, but the draft still asks the user which it was. Should the FLIM domain be a recorded module attribute so the prompt can be narrowed? |

---

# Part 4 — Planned UX changes

Three changes requested after using the system. Each is described with what it
implies for prose assembly, for the review block and for the ledger, and with
which consolidated defects it closes or is blocked by.

## 4.1 Show the acquisition-parameter recommendation once per Methods section

**Today:** every entry repeats the same two generic items — the specimen
preparation prompt and the catch-all acquisition-settings recommendation — plus,
for multi-entry sections, the microscope identity, objective and software
sentences. A three-acquisition section (C08, C10) carries three identical copies.

**Target:** technique-specific prompts stay with the acquisition they belong to
(STED depletion, TIRF angle, SIM reconstruction, spinning-disk exposure — these
differ per entry and must not be merged). Generic, section-level items appear
once, at the end of the whole draft:

* `[PLEASE SPECIFY: Specimen preparation metadata …]`
* `[RECOMMENDED FOR REPORTING: … pixel size, z-step, time interval, tiling overlap …]`
* the "recover settings from image metadata" pointer

**Implementation shape:** `updateOutputText()`
(`methods_generator_app.js:1336-1344`) already concatenates stored entry texts,
so it is the natural place for a section-level renderer. That means
`buildAcquisitionEntry()` should return *structured* prompts (per-entry vs
section-level) rather than a finished string, and the section renderer dedupes
the section-level set across entries. Storing structure rather than text also
makes 1.9 (replace-on-re-add) and 1.19 (hoisting repeated instrument/objective
sentences) straightforward, because entries stop being opaque strings.

**Closes:** 1.19, and part of B's D10. **Related:** do the same deduplication for
the identical `[PLEASE VERIFY: … not recorded for this instrument]` blockers once
1.8 has scoped them.

## 4.2 Light-path components as component-focused, multi-select tick boxes with specs in the text

**Today:** each holder is a checkbox and each position under it is a **radio**,
so only one filter per holder can be selected. Ticking a position auto-ticks its
holder; ticking the holder alone produces `The light path included Emission
Filter Wheel.` (1.21). The prose names the position and the holder but never the
optical specification: *"The light path included 525/25 (catalogue no.
FF01-525/25) in the Emission Filter Wheel."*

**Target:** positions become checkboxes, several filters can be selected, and
the generated text states each filter's specification.

Notes on making this work:

1. **What replaces the exclusivity constraint.** The radios today encode "one
   position per wheel at a time", which is true *per channel* but not *per
   acquisition* — a two-colour spinning-disk experiment genuinely uses two
   emission positions sequentially. So multi-select is the right model, but the
   draft should then say so: with two or more positions on one holder, emit
   `[PLEASE SPECIFY: which emission filter was used for each channel, and whether
   the channels were acquired sequentially or simultaneously]` rather than the
   current generic channel prompt. This also gives 1.14 a better home.
2. **Holder-only selection should stop producing a sentence.** With
   component-focused checkboxes, ticking a wheel without a position means "I used
   this wheel but have not said which position" — that is a review prompt, not a
   prose sentence (1.21).
3. **Specs in the text need the `bands` data.** The target wording is something
   like *"…a 525/25 nm bandpass emission filter (Semrock FF01-525/25) and a
   quad-band dichroic (Semrock Di01-T405/488/568/647)…"*. The band data exist for
   most positions but are missing for the 19 listed in §3.7, and partially
   recorded for several composite cubes. **§3.7 is a prerequisite for this
   change** — otherwise the new prose silently omits the spec for exactly the
   filters whose spec matters most, or prints a bare catalogue code.
4. **Component type matters for wording.** A filter cube, a dichroic, an
   excitation filter, an emission filter and a neutral-density position should
   not all be introduced with "The light path included…". `component_type` is
   already in the records; the prose should use it.
5. **Keep the route scoping.** Multi-select must not reopen the cross-route leak:
   a position is selectable only while it is on a path offered by a selected
   method (see 4.3).

**Closes:** 1.21, and improves 1.13 (specs replace bare catalogue codes) and 1.30.
**Blocked by:** §3.7.

## 4.3 Imaging methods as multi-select tick boxes that only gate component availability

**Today:** the imaging method is a radio, and it does two jobs — it selects which
components are shown, *and* it writes the opening sentence.

**Target:** methods become checkboxes; several can be selected for one
acquisition; their only job is to determine which components are available.

This is the most consequential change and it resolves several defects, but it
needs decisions:

1. **It fixes the clearing model.** The current bug class (1.1, 1.2, 1.5) exists
   because clearing is keyed on "the method changed". With multi-select the
   correct rule is declarative and applies uniformly to every category:
   *a selection survives exactly as long as it is still offered by at least one
   selected method.* Unticking *ISM (AiryScan)* then drops the Airyscan module
   automatically; unticking *Widefield fluorescence* while *TIRF* is still ticked
   drops nothing, because the path is unchanged. This is the single rule that
   should replace the hard-coded prefix list at
   `methods_generator_app.js:1436-1439`, and it should cover `obj`, `module`,
   `scanner`, `magnification-changer`, `optical-modulator` and
   `illumination-logic` as well as the route-scoped prefixes.
2. **The opening sentence needs a policy for several methods.** Options, roughly
   in order of preference:
   * combine when the methods are genuinely simultaneous — *"Correlative
     transmitted-light brightfield and widefield fluorescence imaging was
     performed using …"*;
   * keep the first as the primary and attach the rest — *"…imaging was performed
     …; transmitted-light brightfield images were acquired on the same field."*
   A flat list of technique phrases would read badly. Worth deciding which method
   combinations are expected to be ticked together — brightfield + fluorescence
   and confocal + a readout are common, STED + SMLM is not.
3. **Multiple methods on multiple paths need a rule.** Ticking *TIRF* and
   *Transmitted brightfield* selects two physical paths for one entry. Today that
   produces `[PLEASE VERIFY: 2 optical routes are reported for a single
   acquisition…]`. With deliberate multi-select that prompt becomes wrong for the
   legitimate case and should be replaced by a statement that each path was used,
   with the hardware attributed to the right one. **This is the main risk in the
   change**: the light-path paragraph currently merges all selected components
   into one sentence, so with two paths ticked it would mix a transmitted lamp and
   a TIRF laser into one illumination clause. The paragraph builder needs to group
   by path before it groups by sentence template.
4. **Technique prompts become a union.** Ticking STED + confocal should produce
   the STED prompts and the confocal pinhole/dwell prompt once each, deduped —
   which the existing `uniqueTexts()` pass already handles.
5. **Relationship to separate entries.** Multi-select methods and multiple
   acquisition entries now overlap: a user could describe widefield + confocal
   either as one multi-method entry or as two entries. Both should be supported,
   but the UI should make the distinction clear — roughly, *one entry = one
   image dataset*. This is worth settling before implementation, because it
   determines whether §4.1's section-level renderer merges across entries or
   across methods within an entry.

**Closes:** 1.1, 1.2, 1.5 (via the uniform survival rule), and makes 1.6's
completeness contract expressible per method.
**Watch:** 1.13 — do not let the per-path grouping surface the word "route" in
prose; and 1.11 — per-path grouping is also what lets a two-camera acquisition be
described correctly.

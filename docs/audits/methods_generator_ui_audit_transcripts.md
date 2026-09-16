# Methods generator — full scenario transcripts

Companion to [`methods_generator_ui_audit.md`](methods_generator_ui_audit.md).

Every scenario below was executed against the rendered Methods generator page
(`mkdocs build` output served over HTTP, driven in Chromium through Playwright)
by clicking the same controls a user clicks: the microscope dropdown, the
imaging-method radios, the light-path radios, and the hardware checkboxes. No
DTO was constructed by hand and no generator function was called directly. The
"Exact generated Methods text" blocks are the verbatim contents of the page's
output textarea at the end of the scenario.

Assessments and defect analysis are in the main report; this file exists so that
every claim there can be checked against the text that produced it.


## Batch A — Single acquisitions across the instrument catalogue

### A01 — Abberior STED - two-colour STED, 775 nm depletion

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: 685/35 (catalogue no. ET685/35)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  tick: Hardware modules and environmental control :: Easy3D STED — Abberior
  reference: Figure 3, STED
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Figure 3, STED

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 685/35 (catalogue no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A02 — Abberior STED - plain confocal reference

**Instrument:** Abberior STED  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 60x/1.2 W WATER — Olympus
  tick: Light sources :: 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  tick: Filters and dichroics :: 525/25 (catalogue no. FF01-525/25)
  tick: Detectors :: Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A03 — Abberior STED - confocal user ticks the 775 nm depletion laser (no STED method)

**Instrument:** Abberior STED  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: Confocal point scanning
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: 685/35 (catalogue no. ET685/35)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836).

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 685/35 (catalogue no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A04 — Abberior STED - RESOLFT

**Instrument:** Abberior STED  
**Imaging method:** RESOLFT  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: RESOLFT
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  tick: Filters and dichroics :: 525/25 (catalogue no. FF01-525/25)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A05 — Abberior STED - 3D STED with Easy3D + SLM + adaptive optics

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 561 nm laser (PicoQuant PDL-T 561) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: BrightLine 615/10
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  tick: Hardware modules and environmental control :: Easy3D STED — Abberior
  tick: Hardware modules and environmental control :: Adaptive Optics — Abberior
  tick: Optical modulators :: Spatial Light Modulator — Abberior
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). The Adaptive Optics module was used (Abberior). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 561 nm laser (PicoQuant PDL-T 561). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included BrightLine 615/10 in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR. STED beam shaping used Abberior easy3D SLM.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: which phase mask profile was applied (Vortex, Bottle, and 3D-STED are recorded for this modulator)]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A06 — 3i CSU-W1 - spinning disk live cell, 2 lasers

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Light sources :: 561 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: Quad-band Dichroic (catalogue no. Di01-T405/488/568/647)
  tick: Filters and dichroics :: Cy3 / Alexa 568 (catalogue no. FF01-617/73-25)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  tick: Hardware modules and environmental control :: Incubation — Okolab
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). The Incubation module was used (Okolab Full Enclosure). Instrument control and image acquisition were performed using 3i SlideBook (v6). Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2.

Excitation was provided by 488 nm laser (3i LaserStack v4) and 561 nm laser (3i LaserStack v4). The light path included Quad-band Dichroic (catalogue no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and Cy3 / Alexa 568 (catalogue no. FF01-617/73-25) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A07 — 3i CSU-W1 - widefield fluorescence

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 20x/0.8 AIR — Zeiss
  tick: Light sources :: LED (Excelitas X-Cite XLED1) — Excelitas
  tick: Filters and dichroics :: 485/20 (catalogue no. FF02-485/20-25)
  tick: Filters and dichroics :: Widefield Dichroic
  tick: Filters and dichroics :: Widefield Emission
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by LED (Excelitas X-Cite XLED1). The light path included 485/20 (catalogue no. FF02-485/20-25) in the XLED Excitation Filters, Widefield Dichroic, and Widefield Emission. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A08 — 3i CSU-W1 - transmitted brightfield (no light source offered)

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 10x/0.45 Ph1 M27 AIR — Zeiss
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Zeiss Plan-Apochromat 10x/0.45 Ph1 M27, 420641-9910). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A09 — 3i CSU-W1 - phase contrast

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Phase contrast  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Phase contrast
  tick: Objectives :: Plan-Apochromat 10x/0.45 Ph1 M27 AIR — Zeiss
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Zeiss Plan-Apochromat 10x/0.45 Ph1 M27, 420641-9910).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A10 — 3i CSU-W1 - DIC

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: DIC
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A11 — 3i Med C - spinning disk, piezo z-stack

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i Marianas CSU-W1 Spinning Disk Med C
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using SlideBook (v6).
  tick: Confirmed acquisition actions :: Z-stacks were acquired using an ASI piezo stage.
  tick: Objectives :: Plan-Apochromat 63x/1.4 NA Oil OIL — Zeiss
  tick: Light sources :: 405 nm laser (3i LaserStack v4) — 3i
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: 445/45 (catalogue no. FF01-445/45-25)
  tick: Detectors :: Photometrics Prime BSI — Photometrics
  tick: Hardware modules and environmental control :: Piezo Z-Stage — ASI
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). The Piezo Z-Stage module was used (ASI). Instrument control and image acquisition were performed using SlideBook (v6). Z-stacks were acquired using an ASI piezo stage.

Excitation was provided by 405 nm laser (3i LaserStack v4) and 488 nm laser (3i LaserStack v4). The light path included 445/45 (catalogue no. FF01-445/45-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: model of the Piezo Z-Stage module]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A12 — 3i Med C - widefield fluorescence TRITC

**Instrument:** 3i Marianas CSU-W1 Spinning Disk Med C  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i Marianas CSU-W1 Spinning Disk Med C
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 63x/1.4 NA Oil OIL — Zeiss
  tick: Light sources :: LED (CoolLED pE-300) — CoolLED
  tick: Filters and dichroics :: LED-TRITC-A-ZHE-Zero (catalogue no. LED-TRITC-A-ZHE-Zero)
  tick: Detectors :: Photometrics Prime BSI — Photometrics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). Instrument control and image acquisition were performed using SlideBook (v6).

Illumination was provided by LED (CoolLED pE-300). The light path included LED-TRITC-A-ZHE-Zero (catalogue no. LED-TRITC-A-ZHE-Zero) in the Zeiss Widefield Fluorescence Positions. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE SPECIFY: the role of LED (CoolLED pE-300) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for LED-TRITC-A-ZHE-Zero are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A13 — Andor BC43 - spinning disk GFP

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Andor BC43 Benchtop Confocal
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
  tick: Objectives :: 40X Plan Apo LD Air 40x/0.95 AIR — Nikon
  tick: Light sources :: 488 nm laser (Andor Borealis Illumination) — Andor
  tick: Filters and dichroics :: BC43 Internal Dichroic
  tick: Filters and dichroics :: GFP
  tick: Detectors :: Andor 4.1 MP sCMOS — Andor
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 40x/0.95 Air objective (Nikon 40X Plan Apo LD Air, INS-OBJ-40D-095). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by 488 nm laser (Andor Borealis Illumination). The light path included GFP in the BC43 Internal Emission Filters and BC43 Internal Dichroic. Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A14 — Andor BC43 - transmitted brightfield (fluorescence emission filters still offered)

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Andor BC43 Benchtop Confocal
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
  tick: Objectives :: 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
  tick: Light sources :: LED (Andor Transmitted Light Illuminator) — Andor
  tick: Detectors :: Andor 4.1 MP sCMOS — Andor
  click: Add to methods
```

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

### A15 — Andor BC43 - brightfield where user ticks a fluorescence emission filter

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Andor BC43 Benchtop Confocal
  tick: Imaging method :: Transmitted brightfield
  tick: Objectives :: 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
  tick: Light sources :: LED (Andor Transmitted Light Illuminator) — Andor
  tick: Filters and dichroics :: mCherry
  tick: Detectors :: Andor 4.1 MP sCMOS — Andor
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080).

Transmitted-light illumination was provided by LED (Andor Transmitted Light Illuminator). The light path included mCherry in the BC43 Internal Emission Filters. Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A16 — Deltavision OMX - 3D-SIM

**Instrument:** Deltavision OMX  
**Imaging method:** SIM  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: SIM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: Plan Apo N 60x/1.42 OIL — Olympus
  tick: Light sources :: 488 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Alexa 488
  tick: Detectors :: PCO Edge — PCO
  tick: Hardware modules and environmental control :: 3D-SIM Module — GE Healthcare
  click: Add to methods
```

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

### A17 — Deltavision OMX - TIRF

**Instrument:** Deltavision OMX  
**Imaging method:** TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: TIRF
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: APO N TIRF 60x/1.49 OIL — Olympus
  tick: Light sources :: 642 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Cy5
  tick: Detectors :: PCO Edge — PCO
  tick: Hardware modules and environmental control :: TIRF Module — GE Healthcare
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). The TIRF Module was used (GE Healthcare Ring TIRF with PhotoKinetic Optics). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 642 nm laser (GE Healthcare). The light path included Cy5 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A18 — Deltavision OMX - SMLM / dSTORM

**Instrument:** Deltavision OMX  
**Imaging method:** SMLM  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: SMLM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: APO N TIRF 60x/1.49 OIL — Olympus
  tick: Light sources :: 642 nm laser (GE Healthcare) — GE Healthcare
  tick: Light sources :: 405 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Cy5
  tick: Detectors :: PCO Edge — PCO
  click: Add to methods
```

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

### A19 — Deltavision OMX - conventional widefield

**Instrument:** Deltavision OMX  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: Plan Apo N 60x/1.42 OIL — Olympus
  tick: Light sources :: 405 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: DAPI
  tick: Detectors :: PCO Edge — PCO
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 405 nm laser (GE Healthcare). The light path included DAPI in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A20 — EVOS fl - widefield GFP

**Instrument:** EVOS fl  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: EVOS fl
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using On-board EVOS interface.
  tick: Objectives :: Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
  tick: Light sources :: 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) — Thermo Fisher / AMG
  tick: Filters and dichroics :: GFP/Alexa 488 (catalogue no. ZP-EPI-9002)
  tick: Detectors :: AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD) — AMG (Thermo Fisher)
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included GFP/Alexa 488 (catalogue no. ZP-EPI-9002) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A21 — EVOS fl - phase contrast

**Instrument:** EVOS fl  
**Imaging method:** Phase contrast  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: EVOS fl
  tick: Imaging method :: Phase contrast
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using On-board EVOS interface.
  tick: Objectives :: U Plan FL N 4x/0.13 PhP AIR — Olympus
  tick: Light sources :: LED (Thermo Fisher / AMG Transmitted Light LED) — Thermo Fisher / AMG
  tick: Detectors :: AMG (Thermo Fisher) Sony ICX285AQ Color CCD — AMG (Thermo Fisher)
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 4x/0.13 Air objective (Olympus U Plan FL N 4x/0.13 PhP). Instrument control and image acquisition were performed using On-board EVOS interface.

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

### A22 — Lambert FLIM - widefield FLIM

**Instrument:** Lambert FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** FLIM

**Selections made in the UI (in order):**

```
  select instrument: Lambert FLIM
  tick: Imaging method :: Widefield fluorescence
  tick: Light path and readouts :: FLIM
  tick: Objectives :: Plan APOCHROMAT 63x/1.4 Oil OIL — Zeiss
  tick: Light sources :: 469 nm LED (Multi-LED excitation) — Unknown
  tick: Detectors :: Lambert Instruments LIFA Camera — Lambert Instruments
  tick: Hardware modules and environmental control :: FLIM Module — Lambert Instruments
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert Instruments LIFA (frequency domain FLIM) inverted microscope. FLIM data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900). The FLIM Module was used (Lambert Instruments LIFA).

Illumination was provided by 469 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: the role of 469 nm LED (Multi-LED excitation) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version and Detector pixel pitch (um) are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A23 — Lambert FLIM - FLIM-FRET

**Instrument:** Lambert FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** FLIM, FRET

**Selections made in the UI (in order):**

```
  select instrument: Lambert FLIM
  tick: Imaging method :: Widefield fluorescence
  tick: Light path and readouts :: FLIM
  tick: Light path and readouts :: FRET
  tick: Objectives :: Plan APOCHROMAT 63x/1.4 Oil OIL — Zeiss
  tick: Light sources :: 406 nm LED (Multi-LED excitation) — Unknown
  tick: Detectors :: Lambert Instruments LIFA Camera — Lambert Instruments
  tick: Hardware modules and environmental control :: FLIM Module — Lambert Instruments
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert Instruments LIFA (frequency domain FLIM) inverted microscope. FLIM data were acquired. FRET data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900). The FLIM Module was used (Lambert Instruments LIFA).

Illumination was provided by 406 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: the role of 406 nm LED (Multi-LED excitation) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version and Detector pixel pitch (um) are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A24 — Leica DM IRBE - widefield EGFP with unknown camera

**Instrument:** Leica DM IRBE  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica DM IRBE
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: PL FLUOTAR 40x/0.70 PH2 AIR — Leica
  tick: Light sources :: arc lamp (Leica 50W HBO short arc bulb) — Leica
  tick: Filters and dichroics :: Filter Cube EGFP
  tick: Detectors :: Unknown Camera — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 40x/0.7 Air objective (Leica PL FLUOTAR 40x/0.70 PH2, 506014).

Illumination was provided by arc lamp (Leica 50W HBO short arc bulb). The light path included Filter Cube EGFP in the Fluorescence Turret. Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Leica 50W HBO short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A25 — Leica DM IRBE - darkfield with 1.6x auxiliary lens

**Instrument:** Leica DM IRBE  
**Imaging method:** Darkfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica DM IRBE
  tick: Imaging method :: Darkfield
  tick: Objectives :: PL FLUOTAR 20x/0.50 PH2 AIR — Leica
  tick: Light sources :: halogen lamp (Leica 12V 100W halogen bulb) — Leica
  tick: Detectors :: Unknown Camera — Unknown
  tick: Magnification changers :: 1.6x Auxiliary Lens — Leica
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica Microsystems Leica DM IRBE inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013). An intermediate magnification changer (Leica 1.6x Auxiliary Lens, 1.6x) was used.

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A26 — Leica DM RB - visual darkfield through eyepieces

**Instrument:** Leica DM RB  
**Imaging method:** Darkfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica DM RB
  tick: Imaging method :: Darkfield
  tick: Objectives :: HC PL APO 20x/0.70 CS AIR — Leica
  tick: Light sources :: halogen lamp (Leica 12V 100W halogen bulb) — Leica
  tick: Detectors :: eyepieces
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica Microsystems Leica DM RB upright microscope. Imaging was performed with a 20x/0.7 Air objective (Leica HC PL APO 20x/0.70 CS, 506513).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Samples were observed through eyepieces.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A27 — Leica DM RE - DIC

**Instrument:** Leica DM RE  
**Imaging method:** DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica DM RE
  tick: Imaging method :: DIC
  tick: Objectives :: PL APO 63x/1.32 OIL PH3 OIL — Leica
  tick: Light sources :: halogen lamp (Leica 12V 100W halogen bulb) — Leica
  tick: Detectors :: Unknown Camera — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Leica Microsystems Leica DM RE upright microscope. Imaging was performed with a 63x/1.32 Oil objective (Leica PL APO 63x/1.32 OIL PH3, 506082).

Transmitted-light illumination was provided by halogen lamp (Leica 12V 100W halogen bulb). Images were recorded using Unknown Camera.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A28 — STELLARIS 8 - confocal, spectral detection

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** Spectral Imaging

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Light path and readouts :: Spectral Imaging
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems
  tick: Hardware modules and environmental control :: Acousto-Optical Beam Splitter (AOBS) — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Spectral Imaging data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The Acousto-Optical Beam Splitter (AOBS) module was used (Leica Microsystems). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1 and Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A29 — STELLARIS 8 - FALCON FLIM

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** FLIM

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Light path and readouts :: FLIM
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems
  tick: Hardware modules and environmental control :: FLIM Module — Leica Microsystems
  click: Add to methods
```

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

### A30 — STELLARIS 8 - FCS

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** FCS

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Light path and readouts :: FCS
  tick: Objectives :: HC PL APO 86x/1.20 W motCORR STED W WATER — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP Core Unit pos 3 — Leica Microsystems
  tick: Hardware modules and environmental control :: FCS Module — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FCS data were acquired. Imaging was performed with a 86x/1.2 Water objective (Leica Microsystems HC PL APO 86x/1.20 W motCORR STED W, 15506333). The FCS Module was used (Leica Microsystems STELLARIS 8 FCS). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP Core Unit pos 3.

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

### A31 — STELLARIS 8 - FRET acceptor photobleaching, 2 detectors, resonant scanner

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** FRET

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Light path and readouts :: FRET
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Light sources :: 405 nm laser (Leica Microsystems Laser 405 DMOD) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD R SP pos 5 — Leica Microsystems
  tick: Scanner :: Tandem Scanner (Galvo/Resonant)
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FRET data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser) and 405 nm laser (Leica Microsystems Laser 405 DMOD). Images were recorded using Leica Microsystems Power HyD S SP pos 1 and Leica Microsystems Power HyD R SP pos 5.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of 405 nm laser (Leica Microsystems Laser 405 DMOD) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A32 — STELLARIS 8 - widefield fluorescence on the camera port

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Objectives :: HC PL APO 20x/0.75 CS2 AIR — Leica Microsystems
  tick: Light sources :: LED (Leica Microsystems Leica LED 3) — Leica Microsystems
  tick: Filters and dichroics :: Filter Cube GFP (catalogue no. 15525314)
  tick: Detectors :: Leica Microsystems K5 Microscope Camera — Leica Microsystems
  click: Add to methods
```

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

### A33 — STELLARIS 8 - transmitted brightfield

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Objectives :: HC PL APO 10x/0.40 CS2 AIR — Leica Microsystems
  tick: Light sources :: LED (Leica Microsystems Leica LED 3) — Leica Microsystems
  tick: Detectors :: Leica Microsystems BF detector for DMI — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 10x/0.4 Air objective (Leica Microsystems HC PL APO 10x/0.40 CS2, 15506424). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by LED (Leica Microsystems Leica LED 3). Images were recorded using Leica Microsystems BF detector for DMI.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of LED (Leica Microsystems Leica LED 3) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A34 — Leica TCS SP5 (retired) - multiphoton, no method section

**Instrument:** Leica TCS SP5 Multiphoton (Retired)  
**Imaging method:** (no imaging-method control offered)  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica TCS SP5 Multiphoton (Retired)
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Leica LAS AF.
  tick: Objectives :: HCX IR APO L 25x/0.95 WATER — Leica
  tick: Light sources :: pulsed near-ir laser (Coherent Chameleon Ultra II) — Coherent
  tick: Detectors :: NDD PMT
  tick: Scanner :: Resonant Scanner
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Images were acquired using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). The microscope used a resonant scanner. Instrument control and image acquisition were performed using Leica LAS AF.

Excitation was provided by pulsed near-ir laser (Coherent Chameleon Ultra II). Images were recorded using NDD PMT.

Review before publication:
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: acquisition software version for Leica LAS AF]
- [PLEASE SPECIFY: wavelength used from the recorded 690-1040 nm tunable range of pulsed near-ir laser (Coherent Chameleon Ultra II)]
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the selected route; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Capability axes, Optical path element ID, Optical path element type, Light path route type, Software version, Scanner line rate (Hz), and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A35 — Leica Thunder - widefield, two filter wheels

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica
  tick: Light sources :: 475 nm LED (Leica LED 8) — Leica
  tick: Filters and dichroics :: DFT51010 (catalogue no. 11525418)
  tick: Filters and dichroics :: 535/70
  tick: Detectors :: Leica K8 — Leica
  tick: Hardware modules and environmental control :: Hardware Autofocus — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). The Hardware Autofocus module was used (Leica Microsystems Adaptive Focus Control). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 475 nm LED (Leica LED 8). The light path included DFT51010 (catalogue no. 11525418) in the Filter Turret and 535/70 in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for DFT51010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A36 — Leica Thunder - transmitted brightfield colour camera

**Instrument:** Leica Thunder  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 10x/0.45 AIR — Leica
  tick: Detectors :: Leica K3C — Leica
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Leica HC PL APO 10x/0.45, 11506410). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A37 — MSquared Aurora - Airy-beam light sheet

**Instrument:** MSquared Aurora Airy Beam  
**Imaging method:** Light sheet  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: MSquared Aurora Airy Beam
  tick: Imaging method :: Light sheet
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolutio
  tick: Objectives :: 54-10-12 Airy beam dipping objective 17x/0.4 MULTI-IMMERSION — Special Optics
  tick: Light sources :: 488 nm laser (Coherent OBIS laser) — Coherent OBIS
  tick: Filters and dichroics :: GFP filter
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU) — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Light-sheet imaging was performed using the M Squared Aurora Airy Beam other microscope. Imaging was performed with a 17x/0.4 Multi-Immersion objective (Special Optics 54-10-12 Airy beam dipping objective, 54-10-12). Instrument control and image acquisition were performed using M Squared Cubes Acquisition. Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution.

Illumination was provided by 488 nm laser (Coherent OBIS laser). The light path included GFP filter in the Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for M Squared Cubes Acquisition]
- [PLEASE SPECIFY: the role of 488 nm laser (Coherent OBIS laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A38 — Nikon Crest V3 - dual-camera spinning disk

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE — Nikon
  tick: Light sources :: 476 nm laser (Lumencor Celesta 7ch) — Lumencor
  tick: Light sources :: 545 nm laser (Lumencor Celesta 7ch) — Lumencor
  tick: Filters and dichroics :: Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543)
  tick: Filters and dichroics :: Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543)
  tick: Camera and emission splitters :: MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set
  tick: Detectors :: Photometrics Kinetix — Photometrics
  tick: Detectors :: Photometrics Kinetix — Photometrics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 476 nm laser (Lumencor Celesta 7ch) and 545 nm laser (Lumencor Celesta 7ch). The light path included Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543) in the Crest Excitation Wheel and Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543) in the Crest Dichroic Wheel. Light was directed through MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 545 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: 2 separate components recorded as “Photometrics Kinetix” were selected and this draft cannot tell them apart; state which one was used for each channel]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A39 — Nikon Crest V3 - widefield fluorescence FITC

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon
  tick: Light sources :: LED (Nikon D-LEDI Fluorescence LED Illumination System) — Nikon
  tick: Filters and dichroics :: FITC Ti2 32mm Cube SB LFOV (catalogue no. MXR00716)
  tick: Detectors :: Photometrics Kinetix — Photometrics
  click: Add to methods
```

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

### A40 — Nikon Crest V3 - DIC

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: DIC
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon
  tick: Light sources :: LED (Nikon T12-D-LHLED LED Lamp House) — Nikon
  tick: Detectors :: Photometrics Kinetix — Photometrics
  click: Add to methods
```

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

### A41 — Nikon Eclipse Ti2-E - widefield GFP

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1)
  tick: Objectives :: Plan Apo λ 60x/1.40 Oil OFN25 DIC N2 OIL — Nikon
  tick: Light sources :: 475 nm LED (Lumencor Spectra X LED system) — Lumencor
  tick: Filters and dichroics :: Chroma 89403bs (catalogue no. 89403bs)
  tick: Filters and dichroics :: GFP Emission
  tick: Detectors :: Hamamatsu Orca Flash4.0 V3 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by 475 nm LED (Lumencor Spectra X LED system). The light path included Chroma 89403bs (catalogue no. 89403bs) in the Filter Turret and GFP Emission in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A42 — Nikon Eclipse Ti2-E - phase contrast

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Phase contrast  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Phase contrast
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1)
  tick: Objectives :: Plan Fluor 10x/0.30 OFN 25 Ph1 DL AIR — Nikon
  tick: Light sources :: LED (Nikon Ti2 Transmitted Illuminator) — Nikon
  tick: Detectors :: Nikon DS-Fi3 — Nikon
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 10x/0.3 Air objective (Nikon Plan Fluor 10x/0.30 OFN 25 Ph1 DL, MRH20101). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Nikon DS-Fi3.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A43 — Olympus BX60 - widefield GFP

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Olympus Cell^D.
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

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

### A44 — Olympus BX60 - brightfield histology

**Instrument:** Olympus BX60  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Olympus Cell^D.
  tick: Objectives :: PlanC 4x/0.10 AIR — Olympus
  tick: Light sources :: halogen lamp (Olympus 12V 100W halogen bulb) — Olympus
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A45 — ONI Nanoimager - dSTORM

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: ONI Nanoimager
  tick: Imaging method :: SMLM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NimOS microscope control sof
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using CODI analysis software.
  tick: Objectives :: UPLXAPO100XO 100x/1.45 OIL — Olympus
  tick: Light sources :: 640 nm laser (ONI red) — ONI
  tick: Light sources :: 405 nm laser (ONI violet) — ONI
  tick: Camera and emission splitters :: Internal Emission Splitter
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software. Post-acquisition processing and analysis were performed using CODI analysis software.

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

### A46 — ONI Nanoimager - live TIRF

**Instrument:** ONI Nanoimager  
**Imaging method:** TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: ONI Nanoimager
  tick: Imaging method :: TIRF
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NimOS microscope control sof
  tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp
  tick: Objectives :: UPLXAPO100XO 100x/1.45 OIL — Olympus
  tick: Light sources :: 488 nm laser (ONI blue) — ONI
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software. Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.

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

### A47 — ONI Nanoimager - single-molecule FRET readout

**Instrument:** ONI Nanoimager  
**Imaging method:** TIRF  
**Physical path / readouts:** FRET

**Selections made in the UI (in order):**

```
  select instrument: ONI Nanoimager
  tick: Imaging method :: TIRF
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NimOS microscope control sof
  tick: Light path and readouts :: FRET
  tick: Objectives :: UPLXAPO100XO 100x/1.45 OIL — Olympus
  tick: Light sources :: 561 nm laser (ONI green) — ONI
  tick: Light sources :: 640 nm laser (ONI red) — ONI
  tick: Camera and emission splitters :: Internal Emission Splitter
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. FRET data were acquired. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software.

Illumination was provided by 561 nm laser (ONI green) and 640 nm laser (ONI red). Light was directed through Internal Emission Splitter. Images were recorded using Hamamatsu ORCA-Flash4.0 V3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: acquisition software version for NimOS microscope control software]
- [PLEASE SPECIFY: the role of 561 nm laser (ONI green) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 640 nm laser (ONI red) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A48 — Zeiss AxioZoom - widefield fluorescence whole mount

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss AxioZoom.V16
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN Pro.
  tick: Objectives :: PlanApo Z 1x/0.125 AIR — Zeiss
  tick: Light sources :: arc lamp (Zeiss HXP 200C) — Zeiss
  tick: Filters and dichroics :: Alexa 488 (Filter set 38 HE) (catalogue no. 38 HE)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 1x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

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

### A49 — Zeiss AxioZoom - Apotome optical sectioning

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Optical sectioning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss AxioZoom.V16
  tick: Imaging method :: Optical sectioning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN Pro.
  tick: Objectives :: PlanApo Z 1x/0.125 AIR — Zeiss
  tick: Light sources :: arc lamp (Zeiss HXP 200C) — Zeiss
  tick: Filters and dichroics :: DAPI (Filter set 49) (catalogue no. 49)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 LT+ sCMOS — Hamamatsu
  tick: Hardware modules and environmental control :: SIM Module — Zeiss
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Optical sectioning was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 1x/0.125 Air objective (Zeiss PlanApo Z). The SIM Module was used (Zeiss ApoTome.2). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Illumination was provided by arc lamp (Zeiss HXP 200C). The light path included DAPI (Filter set 49) (catalogue no. 49) in the Fluorescence Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: the role of arc lamp (Zeiss HXP 200C) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A50 — Zeiss AxioZoom - reflected brightfield ring light

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Reflected brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss AxioZoom.V16
  tick: Imaging method :: Reflected brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN Pro.
  tick: Objectives :: PlanApo Z 0.5x/0.125 AIR — Zeiss
  tick: Light sources :: LED (Zeiss CL 9000 LED CAN ring light) — Zeiss
  tick: Detectors :: Zeiss AxioCam 105 Color — Zeiss
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Zeiss AxioCam 105 Color.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A51 — Zeiss LSM 510 JPK - confocal with AFM

**Instrument:** Zeiss LSM 510 JPK AFM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 510 JPK AFM
  tick: Imaging method :: Confocal point scanning
  tick: Objectives :: Placeholder 10x/0.3 AIR — Unknown
  tick: Light sources :: 488 nm laser — Unknown
  tick: Detectors :: Zeiss — Zeiss
  tick: Hardware modules and environmental control :: AFM Module — JPK
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The AFM Module was used (JPK NanoWizard I with CellHesion).

Illumination was provided by 488 nm laser. Images were recorded using Zeiss.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A52 — Zeiss LSM 510 JPK - transmitted brightfield with no recorded hardware

**Instrument:** Zeiss LSM 510 JPK AFM  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 510 JPK AFM
  tick: Imaging method :: Transmitted brightfield
  tick: Objectives :: Placeholder 10x/0.3 AIR — Unknown
  click: Add to methods
```

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

### A53 — Zeiss LSM 880 - Airyscan super-resolution

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan)  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: ISM (AiryScan)
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Hardware modules and environmental control :: AiryScan Detector/Module — Zeiss
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Image scanning microscopy (ISM; Airyscan) was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting detector/reconstruction mode and the reconstruction software/version and settings used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A54 — Zeiss LSM 880 - spectral confocal lambda stack

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** Spectral Imaging

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Light path and readouts :: Spectral Imaging
  tick: Objectives :: C-APOCHROMAT 63x/1.2 W Korr UV-VIS-IR WATER — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Light sources :: 543 nm laser (HeNe) — Unknown
  tick: Detectors :: Cooled PMT (Ch2) — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Spectral Imaging data were acquired. Imaging was performed with a 63x/1.2 Water objective (Zeiss C-APOCHROMAT 63x/1.2 W Korr UV-VIS-IR, 421787-9970). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon) and 543 nm laser (HeNe). Images were recorded using Cooled PMT (Ch2).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 543 nm laser (HeNe) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A55 — Zeiss LSM 880 - DIC transmitted detector

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: DIC
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: LD LCI Plan APOCHROMAT 40x/1.2 Imm Korr DIC (UV)VIS-IR MULTI-IMMERSION — Zeiss
  tick: Light sources :: halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)) — Zeiss
  tick: Detectors :: Transmitted light PMT — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 40x/1.2 Multi-Immersion objective (Zeiss LD LCI Plan APOCHROMAT 40x/1.2 Imm Korr DIC (UV)VIS-IR, 420862-9970). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)). Images were recorded using Transmitted light PMT.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A56 — Zeiss TIRF - TIRF EMCCD

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: TIRF
  tick: Objectives :: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Light sources :: 488 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 38 HE (GFP) (catalogue no. 38 HE)
  tick: Detectors :: Hamamatsu C9100-13 — Hamamatsu
  tick: Hardware modules and environmental control :: Hardware Autofocus — Zeiss
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat). The Hardware Autofocus module was used (Zeiss Definite Focus).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A57 — Zeiss TIRF - epifluorescence comparison

**Instrument:** Zeiss TIRF  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Alpha Plan Apochromat 63x/1.46 OIL — Zeiss
  tick: Light sources :: 561 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 43 HE (DsRed) (catalogue no. 43 HE)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 561 nm laser. The light path included Filter set 43 HE (DsRed) (catalogue no. 43 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 561 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### A58 — Agilent eSight - live fluorescence in incubator

**Instrument:** Agilent xCELLigence RTCA eSight  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Agilent xCELLigence RTCA eSight
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1
  tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp
  tick: Objectives :: 10x Objective 10x/0.3 AIR — Agilent
  tick: Light sources :: 482 nm LED (Agilent High-power LED (Green)) — Agilent
  tick: Filters and dichroics :: Green Channel
  tick: Detectors :: Sony 5.0 MP Monochromatic CMOS — Sony
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Agilent xCELLigence RTCA eSight benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1). Live-cell imaging was performed using an environmental chamber maintaining controlled temperature, controlled CO2, and controlled humidity.

Illumination was provided by 482 nm LED (Agilent High-power LED (Green)). The light path included Green Channel in the Internal Filter Turret. Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 482 nm LED (Agilent High-power LED (Green)) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for Green Channel are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

### A59 — Agilent eSight - brightfield + impedance module

**Instrument:** Agilent xCELLigence RTCA eSight  
**Imaging method:** Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Agilent xCELLigence RTCA eSight
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1
  tick: Objectives :: 10x Objective 10x/0.3 AIR — Agilent
  tick: Light sources :: LED (Agilent Transmitted LED) — Agilent
  tick: Detectors :: Sony 5.0 MP Monochromatic CMOS — Sony
  tick: Hardware modules and environmental control :: Impedance Module — Agilent
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Agilent xCELLigence RTCA eSight benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). The Impedance Module was used (Agilent Impedance Measurement Module). Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).

Transmitted-light illumination was provided by LED (Agilent Transmitted LED). Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

### A60 — Leica Thunder - phase contrast

**Instrument:** Leica Thunder  
**Imaging method:** Phase contrast  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Phase contrast
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL FLUOTAR L 20x/0.40 CORR AIR — Leica
  tick: Detectors :: Leica K3C — Leica
  click: Add to methods
```

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


## Batch B — Checkbox and state semantics

### B01 — Generate without software, then confirm software and generate again

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Plan Apo λ 60x/1.40 Oil OFN25 DIC N2 OIL — Nikon
  tick: Light sources :: 475 nm LED (Lumencor Spectra X LED system) — Lumencor
  tick: Filters and dichroics :: GFP Emission
  tick: Detectors :: Hamamatsu Orca Flash4.0 V3 — Hamamatsu
  click: Add to methods
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1)
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605).

Illumination was provided by 475 nm LED (Lumencor Spectra X LED system). The light path included GFP Emission in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by 475 nm LED (Lumencor Spectra X LED system). The light path included GFP Emission in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B02 — Pick a fluorescence filter, then change method to brightfield and generate

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Widefield fluorescence, Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Plan Apo λ 60x/1.40 Oil OFN25 DIC N2 OIL — Nikon
  tick: Light sources :: 475 nm LED (Lumencor Spectra X LED system) — Lumencor
  tick: Filters and dichroics :: Chroma 89403bs (catalogue no. 89403bs)
  tick: Filters and dichroics :: GFP Emission
  tick: Detectors :: Hamamatsu Orca Flash4.0 V3 — Hamamatsu
  tick: Imaging method :: Transmitted brightfield
  [state] STATE-visible-checked: ["Imaging method|Transmitted brightfield", "Light path and readouts|Transmitted light", "Objectives|Plan Apo \u03bb 60x/1.40 Oil OFN25 DIC N2 OIL \u2014 Nikon"]
  [state] STATE-all-checked: ["Imaging method|Transmitted brightfield|VIS", "Light path and readouts|Transmitted light|VIS", "Objectives|Plan Apo \u03bb 60x/1.40 Oil OFN25 DIC N2 OIL \u2014 Nikon|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605).

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B03 — Pick a detector, then switch to a different physical path

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** Confocal point scanning, DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: Confocal point scanning
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Detectors :: PMT (Ch1) — Unknown
  tick: Imaging method :: DIC
  [state] STATE-visible-checked: ["Imaging method|DIC", "Light path and readouts|Transmitted light", "Objectives|C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL \u2014 Zeiss"]
  [state] STATE-all-checked: ["Imaging method|DIC|VIS", "Light path and readouts|Transmitted light|VIS", "Objectives|C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL \u2014 Zeiss|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900).

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B04 — Tick the objective before choosing the imaging method

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Objectives :: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Imaging method :: TIRF
  [state] STATE-visible-checked: ["Imaging method|TIRF", "Light path and readouts|Widefield fluorescence", "Objectives|Alpha Plan Apochromat 100x/1.46 OIL \u2014 Zeiss"]
  [state] STATE-all-checked: ["Imaging method|TIRF|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|Alpha Plan Apochromat 100x/1.46 OIL \u2014 Zeiss|VIS"]
  tick: Light sources :: 488 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 38 HE (GFP) (catalogue no. 38 HE)
  tick: Detectors :: Hamamatsu C9100-13 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B05 — Four excitation lines on one spinning-disk acquisition

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 405 nm laser (3i LaserStack v4) — 3i
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Light sources :: 561 nm laser (3i LaserStack v4) — 3i
  tick: Light sources :: 640 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: Quad-band Dichroic (catalogue no. Di01-T405/488/568/647)
  tick: Filters and dichroics :: Quad-band emitter (catalogue no. FF01-440/521/607/700-25)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 405 nm laser (3i LaserStack v4), 488 nm laser (3i LaserStack v4), 561 nm laser (3i LaserStack v4), and 640 nm laser (3i LaserStack v4). The light path included Quad-band Dichroic (catalogue no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and Quad-band emitter (catalogue no. FF01-440/521/607/700-25) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B06 — Choose one emission filter position, then change to another

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica
  tick: Light sources :: 475 nm LED (Leica LED 8) — Leica
  tick: Filters and dichroics :: 460/80
  tick: Filters and dichroics :: 535/70
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using LAS X wi", "Imaging method|Widefield fluorescence", "Light path and readouts|Widefield fluorescence", "Objectives|HC PL APO 63x/1.40 OIL CS2 OIL \u2014 Leica", "Light sources|475 nm LED (Leica LED 8) \u2014 Leica", "Filters and dichroics|Standalone Emission Wheel", "Filters and dichroics|535/70"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using LAS X wi|VIS", "Imaging method|Widefield fluorescence|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|HC PL APO 63x/1.40 OIL CS2 OIL \u2014 Leica|VIS", "Light sources|475 nm LED (Leica LED 8) \u2014 Leica|VIS", "Filters and dichroics|Standalone Emission Wheel|VIS", "Filters and dichroics|535/70|VIS"]
  tick: Detectors :: Leica K8 — Leica
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 475 nm LED (Leica LED 8). The light path included 535/70 in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B07 — Switch between exclusive detector branches

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1)
  tick: Objectives :: Plan Apo λ 60x/1.40 Oil OFN25 DIC N2 OIL — Nikon
  tick: Light sources :: 475 nm LED (Lumencor Spectra X LED system) — Lumencor
  tick: Filters and dichroics :: GFP Emission
  tick: Detectors :: Hamamatsu Orca Flash4.0 V3 — Hamamatsu
  tick: Detectors :: Nikon DS-Fi3 — Nikon
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Nikon NI", "Imaging method|Widefield fluorescence", "Light path and readouts|Widefield fluorescence", "Objectives|Plan Apo \u03bb 60x/1.40 Oil OFN25 DIC N2 OIL \u2014 Nikon", "Light sources|475 nm LED (Lumencor Spectra X LED system) \u2014 Lumencor", "Filters and dichroics|Emission Wheel", "Filters and dichroics|GFP Emission", "Detectors|Nikon DS-Fi3 \u2014 Nikon"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Nikon NI|VIS", "Imaging method|Widefield fluorescence|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|Plan Apo \u03bb 60x/1.40 Oil OFN25 DIC N2 OIL \u2014 Nikon|VIS", "Light sources|475 nm LED (Lumencor Spectra X LED system) \u2014 Lumencor|VIS", "Filters and dichroics|Emission Wheel|VIS", "Filters and dichroics|GFP Emission|VIS", "Detectors|Nikon DS-Fi3 \u2014
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by 475 nm LED (Lumencor Spectra X LED system). The light path included GFP Emission in the Emission Wheel. Images were recorded using Nikon DS-Fi3.

Review before publication:
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B08 — Select two modules, then deselect one before generating

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE — Nikon
  tick: Light sources :: 476 nm laser (Lumencor Celesta 7ch) — Lumencor
  tick: Detectors :: Photometrics Kinetix — Photometrics
  tick: Hardware modules and environmental control :: Incubation — Nikon
  tick: Hardware modules and environmental control :: Hardware Triggering — CrestOptics
  untick: Hardware Triggering — CrestOptics
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using NIS-Elem", "Imaging method|Confocal spinning disk", "Light path and readouts|Spinning-disk confocal", "Hardware modules and environmental control|Incubation \u2014 Nikon", "Objectives|CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE \u2014 Nikon", "Light sources|476 nm laser (Lumencor Celesta 7ch) \u2014 Lumencor", "Detectors|Photometrics Kinetix \u2014 Photometrics"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using NIS-Elem|VIS", "Imaging method|Confocal spinning disk|VIS", "Light path and readouts|Spinning-disk confocal|VIS", "Hardware modules and environmental control|Incubation \u2014 Nikon|VIS", "Objectives|CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE \u2014 Nikon|VIS", "Light sources|476 nm laser (Lumencor Celesta 7ch) \u2014 Lumencor|VIS", "Detectors|Photometrics Kinetix \
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). The Incubation module was used (Nikon WarmBox TI2WB-SP400NX-G). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 476 nm laser (Lumencor Celesta 7ch). Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Crest Excitation Wheel (Spinning-disk confocal route), Crest Dichroic Wheel (Spinning-disk confocal route), and Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B09 — Zeiss TIRF: configure widefield, then switch to TIRF (shared hardware)

**Instrument:** Zeiss TIRF  
**Imaging method:** Widefield fluorescence, TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Alpha Plan Apochromat 63x/1.46 OIL — Zeiss
  tick: Light sources :: 561 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 43 HE (DsRed) (catalogue no. 43 HE)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu
  tick: Imaging method :: TIRF
  [state] STATE-visible-checked: ["Imaging method|TIRF", "Light path and readouts|Widefield fluorescence", "Objectives|Alpha Plan Apochromat 63x/1.46 OIL \u2014 Zeiss"]
  [state] STATE-all-checked: ["Imaging method|TIRF|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|Alpha Plan Apochromat 63x/1.46 OIL \u2014 Zeiss|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B10 — Andor BC43: same emission filter reached through two methods

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Confocal spinning disk, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Andor BC43 Benchtop Confocal
  tick: Imaging method :: Confocal spinning disk
  tick: Objectives :: 40X Plan Apo LD Air 40x/0.95 AIR — Nikon
  tick: Light sources :: 488 nm laser (Andor Borealis Illumination) — Andor
  tick: Filters and dichroics :: GFP
  tick: Detectors :: Andor 4.1 MP sCMOS — Andor
  tick: Imaging method :: Widefield fluorescence
  [state] STATE-visible-checked: ["Imaging method|Widefield fluorescence", "Light path and readouts|Widefield fluorescence", "Objectives|40X Plan Apo LD Air 40x/0.95 AIR \u2014 Nikon"]
  [state] STATE-all-checked: ["Imaging method|Widefield fluorescence|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|40X Plan Apo LD Air 40x/0.95 AIR \u2014 Nikon|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 40x/0.95 Air objective (Nikon 40X Plan Apo LD Air, INS-OBJ-40D-095).

Review before publication:
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B11 — Abberior: STED, switch to confocal, then return to STED

**Instrument:** Abberior STED  
**Imaging method:** STED, Confocal point scanning, STED  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: 685/35 (catalogue no. ET685/35)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  tick: Imaging method :: Confocal point scanning
  [state] STATE-visible-checked: ["Imaging method|Confocal point scanning", "Light path and readouts|Point-scanning confocal", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus"]
  [state] STATE-all-checked: ["Imaging method|Confocal point scanning|VIS", "Light path and readouts|Point-scanning confocal|VIS", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus|VIS"]
  tick: Imaging method :: STED
  [state] STATE-visible-checked: ["Imaging method|STED", "Light path and readouts|Point-scanning confocal", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus"]
  [state] STATE-all-checked: ["Imaging method|STED|VIS", "Light path and readouts|Point-scanning confocal|VIS", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus|VIS"]
  click: Add to methods
```

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

### B12 — STED selected but no depletion laser ticked

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  tick: Filters and dichroics :: 525/25 (catalogue no. FF01-525/25)
  tick: Detectors :: Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B13 — Click Add twice without changing anything

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Olympus Cell^D.
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

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

### B14 — Same configuration added twice under two figure references

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Olympus Cell^D.
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  reference: Figure 1
  click: Add to methods
  reference: Figure 4
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Figure 1

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by arc lamp (Osram HBO 103W short arc bulb). The light path included U-MWIB (GFP wide) (catalogue no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Figure 4

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

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

### B15 — Add an entry, clear all, then add a different one

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence, Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
  click: Clear all
  tick: Imaging method :: Transmitted brightfield
  tick: Objectives :: PlanC 4x/0.10 AIR — Olympus
  tick: Light sources :: halogen lamp (Olympus 12V 100W halogen bulb) — Olympus
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10) and a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2).

Transmitted-light illumination was provided by halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B16 — Configure one microscope, then switch instrument before generating

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: TIRF
  tick: Objectives :: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Light sources :: 488 nm laser — Unknown
  tick: Detectors :: Hamamatsu C9100-13 — Hamamatsu
  select instrument: Olympus BX60
  [state] STATE-visible-checked: []
  [state] STATE-all-checked: []
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2).

Illumination was provided by arc lamp (Osram HBO 103W short arc bulb). The light path included U-MWIB (GFP wide) (catalogue no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B17 — Over-ticking: every confirmed action and module on the STELLARIS

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X Dye Finder.
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X Assay Editor.
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X Live Data Mode.
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X MicroLab.
  tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp
  tick: Confirmed acquisition actions :: Z-stacks were acquired using a Leica Microsystems SuperZ Galvo Stage piezo stage.
  tick: Confirmed acquisition actions :: Focal drift was minimized using an Infrared Reflection Autofocus system.
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using LAS X 3D Visualisation.
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using LAS X AiviaMotion.
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using LAS X Lightning Expert.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  tick: Hardware modules and environmental control :: FLIM Module — Leica Microsystems
  tick: Hardware modules and environmental control :: FCS Module — Leica Microsystems
  tick: Hardware modules and environmental control :: Acousto-Optical Beam Splitter (AOBS) — Leica Microsystems
  tick: Hardware modules and environmental control :: Hardware Autofocus — Leica Microsystems
  tick: Hardware modules and environmental control :: Motorized Stage — Leica Microsystems
  tick: Hardware modules and environmental control :: Incubation — Okolab
  tick: Hardware modules and environmental control :: High-Performance Workstation — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON). The FCS Module was used (Leica Microsystems STELLARIS 8 FCS). The Acousto-Optical Beam Splitter (AOBS) module was used (Leica Microsystems). The Hardware Autofocus module was used (Leica Microsystems Closed Loop Focus with AFC). The Motorized Stage module was used (Leica Microsystems Scanning stage inv. universal / SuperZ Galvo Stage). The Incubation module was used (Okolab Black Box Incubator DMi8 with Super Z chamber, CO2 and passive humidity). The High-Performance Workstation module was used (Leica Microsystems Workstation Premium). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software. Instrument control and image acquisition were performed using LAS X Dye Finder. Instrument control and image acquisition were performed using LAS X Assay Editor. Instrument control and image acquisition were performed using LAS X Live Data Mode. Instrument control and image acquisition were performed using LAS X MicroLab. Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2. Z-stacks were acquired using a Leica Microsystems SuperZ Galvo Stage piezo stage. Focal drift was minimized using an Infrared Reflection Autofocus system. Post-acquisition processing and analysis were performed using LAS X 3D Visualisation. Post-acquisition processing and analysis were performed using LAS X AiviaMotion. Post-acquisition processing and analysis were performed using LAS X Lightning Expert.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: acquisition software version for LAS X Dye Finder]
- [PLEASE SPECIFY: acquisition software version for LAS X Assay Editor]
- [PLEASE SPECIFY: acquisition software version for LAS X Live Data Mode]
- [PLEASE SPECIFY: acquisition software version for LAS X MicroLab]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B18 — All five spectral detectors selected

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD X SP pos 2 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP Core Unit pos 3 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD X SP pos 4 — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD R SP pos 5 — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1, Leica Microsystems Power HyD X SP pos 2, Leica Microsystems Power HyD S SP Core Unit pos 3, Leica Microsystems Power HyD X SP pos 4, and Leica Microsystems Power HyD R SP pos 5.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B19 — Deltavision: try to select two of the three identical cameras

**Instrument:** Deltavision OMX  
**Imaging method:** SIM  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: SIM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: Plan Apo N 60x/1.42 OIL — Olympus
  tick: Light sources :: 488 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Alexa 488
  tick: Detectors :: PCO Edge — PCO
  tick: Detectors :: PCO Edge — PCO
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using OMX Acqu", "Imaging method|SIM", "Light path and readouts|Widefield fluorescence", "Objectives|Plan Apo N 60x/1.42 OIL \u2014 Olympus", "Light sources|488 nm laser (GE Healthcare) \u2014 GE Healthcare", "Filters and dichroics|OMX Emission Filters", "Filters and dichroics|Alexa 488", "Detectors|PCO Edge \u2014 PCO"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using OMX Acqu|VIS", "Imaging method|SIM|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|Plan Apo N 60x/1.42 OIL \u2014 Olympus|VIS", "Light sources|488 nm laser (GE Healthcare) \u2014 GE Healthcare|VIS", "Filters and dichroics|OMX Emission Filters|VIS", "Filters and dichroics|Alexa 488|VIS", "Detectors|PCO Edge \u2014 PCO|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B20 — Thunder: explicitly empty filter positions

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica
  tick: Light sources :: 475 nm LED (Leica LED 8) — Leica
  tick: Filters and dichroics :: Empty (no filter) (position EMP_BF)
  tick: Detectors :: Leica K8 — Leica
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 475 nm LED (Leica LED 8). No filter was installed in Filter Turret (position EMP_BF). Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Standalone Emission Wheel (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B21 — Abberior: tick the filter wheel itself but no position

**Instrument:** Abberior STED  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 60x/1.2 W WATER — Olympus
  tick: Light sources :: 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  tick: Filters and dichroics :: Emission Filter Wheel
  tick: Detectors :: Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B22 — LSM 880: select Airyscan, then switch back to plain confocal

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan), Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: ISM (AiryScan)
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Hardware modules and environmental control :: AiryScan Detector/Module — Zeiss
  tick: Imaging method :: Confocal point scanning
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Zeiss ZE", "Imaging method|Confocal point scanning", "Light path and readouts|Point-scanning confocal", "Hardware modules and environmental control|AiryScan Detector/Module \u2014 Zeiss", "Objectives|C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL \u2014 Zeiss"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Zeiss ZE|VIS", "Imaging method|Confocal point scanning|VIS", "Light path and readouts|Point-scanning confocal|VIS", "Hardware modules and environmental control|AiryScan Detector/Module \u2014 Zeiss|VIS", "Objectives|C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL \u2014 Zeiss|VIS"]
  tick: Detectors :: PMT (Ch1) — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B23 — Generate with nothing but the instrument and method chosen

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: TIRF
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B24 — Generate with only an instrument selected

**Instrument:** Leica Thunder  
**Imaging method:** (no imaging-method control offered)  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  click: Add to methods
```

**Exact generated Methods text:**

```text
Select an instrument, then choose “Add to methods”.
```

### B25 — Objective ticked, then unticked before generating

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  untick: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope.

Illumination was provided by arc lamp (Osram HBO 103W short arc bulb). The light path included U-MWIB (GFP wide) (catalogue no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### B26 — Two objectives ticked for one acquisition

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Olympus Cell^D.
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Objectives :: UPlanApo 100x/1.35 Oil Iris Ph3 OIL — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2) and a 100x/1.35 Oil objective (Olympus UPlanApo 100x/1.35 Oil Iris Ph3). Instrument control and image acquisition were performed using Olympus Cell^D.

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


## Batch C — Multi-acquisition Methods sections

### C01 — 3i CSU-W1: widefield overview followed by spinning-disk confocal

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Widefield fluorescence, Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 20x/0.8 AIR — Zeiss
  tick: Light sources :: LED (Excelitas X-Cite XLED1) — Excelitas
  tick: Filters and dichroics :: 485/20 (catalogue no. FF02-485/20-25)
  tick: Filters and dichroics :: Widefield Dichroic
  tick: Filters and dichroics :: Widefield Emission
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  reference: Figure 1, overview
  click: Add to methods
  tick: Imaging method :: Confocal spinning disk
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: Quad-band Dichroic (catalogue no. Di01-T405/488/568/647)
  tick: Filters and dichroics :: GFP
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  reference: Figure 1, detail
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Figure 1, overview

Widefield fluorescence imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by LED (Excelitas X-Cite XLED1). The light path included 485/20 (catalogue no. FF02-485/20-25) in the XLED Excitation Filters, Widefield Dichroic, and Widefield Emission. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Figure 1, detail

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000) and a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). The light path included Quad-band Dichroic (catalogue no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and GFP in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C02 — Zeiss TIRF: TIRF followed by epifluorescence

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: TIRF
  tick: Objectives :: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Light sources :: 488 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 38 HE (GFP) (catalogue no. 38 HE)
  tick: Detectors :: Hamamatsu C9100-13 — Hamamatsu
  reference: Figure 2A
  click: Add to methods
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Alpha Plan Apochromat 63x/1.46 OIL — Zeiss
  tick: Light sources :: 561 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 43 HE (DsRed) (catalogue no. 43 HE)
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu
  reference: Figure 2B
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Figure 2A

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Figure 2B

Widefield fluorescence imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat) and a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 561 nm laser. The light path included Filter set 43 HE (DsRed) (catalogue no. 43 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 561 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C03 — Deltavision OMX: 3D-SIM plus conventional widefield

**Instrument:** Deltavision OMX  
**Imaging method:** SIM, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: SIM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: Plan Apo N 60x/1.42 OIL — Olympus
  tick: Light sources :: 488 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Alexa 488
  tick: Detectors :: PCO Edge — PCO
  tick: Hardware modules and environmental control :: 3D-SIM Module — GE Healthcare
  reference: SIM
  click: Add to methods
  tick: Imaging method :: Widefield fluorescence
  tick: Light sources :: 405 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: DAPI
  reference: widefield reference
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

SIM

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 488 nm laser (GE Healthcare). The light path included Alexa 488 in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

widefield reference

Widefield fluorescence imaging was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module was used (GE Healthcare 3D-SIM Illumination Engine). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by 405 nm laser (GE Healthcare). The light path included DAPI in the OMX Emission Filters.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C04 — Abberior: STED plus matched confocal reference

**Instrument:** Abberior STED  
**Imaging method:** STED, Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: 685/35 (catalogue no. ET685/35)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  tick: Hardware modules and environmental control :: Easy3D STED — Abberior
  reference: STED
  click: Add to methods
  tick: Imaging method :: Confocal point scanning
  untick: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  reference: confocal reference
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

STED

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 685/35 (catalogue no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

confocal reference

Point-scanning confocal imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). Instrument control and image acquisition were performed using Abberior Imspector.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: which position of Emission Filter Wheel (Point-scanning confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C05 — ONI Nanoimager: dSTORM plus live TIRF

**Instrument:** ONI Nanoimager  
**Imaging method:** SMLM, TIRF  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: ONI Nanoimager
  tick: Imaging method :: SMLM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NimOS microscope control sof
  tick: Confirmed acquisition actions :: Post-acquisition processing and analysis were performed using CODI analysis software.
  tick: Objectives :: UPLXAPO100XO 100x/1.45 OIL — Olympus
  tick: Light sources :: 640 nm laser (ONI red) — ONI
  tick: Light sources :: 405 nm laser (ONI violet) — ONI
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 — Hamamatsu
  reference: dSTORM
  click: Add to methods
  tick: Imaging method :: TIRF
  untick: 405 nm laser (ONI violet) — ONI
  untick: 640 nm laser (ONI red) — ONI
  tick: Light sources :: 488 nm laser (ONI blue) — ONI
  reference: live TIRF
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

dSTORM

Single-molecule localization microscopy (SMLM) was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software. Post-acquisition processing and analysis were performed using CODI analysis software.

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

live TIRF

Total internal reflection fluorescence (TIRF) imaging was performed using the ONI Nanoimager other microscope. Imaging was performed with a 100x/1.45 Oil objective (Olympus UPLXAPO100XO). Instrument control and image acquisition were performed using NimOS microscope control software. Post-acquisition processing and analysis were performed using CODI analysis software.

Illumination was provided by 488 nm laser (ONI blue).

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

### C06 — Nikon Eclipse Ti2-E: phase contrast plus fluorescence

**Instrument:** Nikon Eclipse Ti2-E  
**Imaging method:** Phase contrast, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Eclipse Ti2-E
  tick: Imaging method :: Phase contrast
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1)
  tick: Objectives :: Plan Fluor 10x/0.30 OFN 25 Ph1 DL AIR — Nikon
  tick: Light sources :: LED (Nikon Ti2 Transmitted Illuminator) — Nikon
  tick: Detectors :: Nikon DS-Fi3 — Nikon
  reference: phase contrast
  click: Add to methods
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Plan Apo λ 60x/1.40 Oil OFN25 DIC N2 OIL — Nikon
  tick: Light sources :: 475 nm LED (Lumencor Spectra X LED system) — Lumencor
  tick: Filters and dichroics :: GFP Emission
  tick: Detectors :: Hamamatsu Orca Flash4.0 V3 — Hamamatsu
  reference: fluorescence
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

phase contrast

Phase-contrast imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 10x/0.3 Air objective (Nikon Plan Fluor 10x/0.30 OFN 25 Ph1 DL, MRH20101). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Nikon DS-Fi3.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

fluorescence

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E inverted microscope. Imaging was performed with a 10x/0.3 Air objective (Nikon Plan Fluor 10x/0.30 OFN 25 Ph1 DL, MRH20101) and a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by 475 nm LED (Lumencor Spectra X LED system). The light path included GFP Emission in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Filter Turret (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C07 — STELLARIS: confocal imaging plus a FLIM readout entry

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** FLIM

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  reference: confocal
  click: Add to methods
  tick: Light path and readouts :: FLIM
  tick: Hardware modules and environmental control :: FLIM Module — Leica Microsystems
  reference: FLIM
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

confocal

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

FLIM

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. FLIM data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module was used (Leica Microsystems STELLARIS 8 FALCON). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

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

### C08 — Zeiss LSM 880: Airyscan, confocal and DIC in one Methods section

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan), Confocal point scanning, DIC  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: ISM (AiryScan)
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Hardware modules and environmental control :: AiryScan Detector/Module — Zeiss
  reference: Airyscan
  click: Add to methods
  tick: Imaging method :: Confocal point scanning
  tick: Detectors :: PMT (Ch1) — Unknown
  reference: confocal
  click: Add to methods
  tick: Imaging method :: DIC
  tick: Light sources :: halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)) — Zeiss
  tick: Detectors :: Transmitted light PMT — Unknown
  reference: DIC
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Airyscan

Image scanning microscopy (ISM; Airyscan) was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting detector/reconstruction mode and the reconstruction software/version and settings used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

confocal

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

DIC

Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted light illumination (HAL 100 / LED)). Images were recorded using Transmitted light PMT.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C09 — Two different microscopes in one Methods section

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence, Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica
  tick: Light sources :: 475 nm LED (Leica LED 8) — Leica
  tick: Filters and dichroics :: DFT51010 (catalogue no. 11525418)
  tick: Filters and dichroics :: 535/70
  tick: Detectors :: Leica K8 — Leica
  reference: screening
  click: Add to methods
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  reference: high resolution
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

screening

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 475 nm LED (Leica LED 8). The light path included DFT51010 (catalogue no. 11525418) in the Filter Turret and 535/70 in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for DFT51010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

high resolution

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C10 — EVOS: brightfield, phase contrast and fluorescence

**Instrument:** EVOS fl  
**Imaging method:** Transmitted brightfield, Phase contrast, Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: EVOS fl
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using On-board EVOS interface.
  tick: Objectives :: Plan Fluor 10x/0.3 AIR — AMG (Thermo Fisher)
  tick: Light sources :: LED (Thermo Fisher / AMG Transmitted Light LED) — Thermo Fisher / AMG
  tick: Detectors :: AMG (Thermo Fisher) Sony ICX285AQ Color CCD — AMG (Thermo Fisher)
  reference: brightfield
  click: Add to methods
  tick: Imaging method :: Phase contrast
  tick: Objectives :: U Plan FL N 4x/0.13 PhP AIR — Olympus
  reference: phase
  click: Add to methods
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
  tick: Light sources :: 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) — Thermo Fisher / AMG
  tick: Filters and dichroics :: GFP/Alexa 488 (catalogue no. ZP-EPI-9002)
  tick: Detectors :: AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD) — AMG (Thermo Fisher)
  reference: GFP
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

brightfield

Transmitted-light brightfield imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 10x/0.3 Air objective (AMG (Thermo Fisher) Plan Fluor 10x/0.3, AMG-AMEP 4623). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by LED (Thermo Fisher / AMG Transmitted Light LED). Images were recorded using AMG (Thermo Fisher) Sony ICX285AQ Color CCD.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of LED (Thermo Fisher / AMG Transmitted Light LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

phase

Phase-contrast imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 4x/0.13 Air objective (Olympus U Plan FL N 4x/0.13 PhP) and a 10x/0.3 Air objective (AMG (Thermo Fisher) Plan Fluor 10x/0.3, AMG-AMEP 4623). Instrument control and image acquisition were performed using On-board EVOS interface.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

GFP

Widefield fluorescence imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 4x/0.13 Air objective (Olympus U Plan FL N 4x/0.13 PhP), a 10x/0.3 Air objective (AMG (Thermo Fisher) Plan Fluor 10x/0.3, AMG-AMEP 4623), and a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included GFP/Alexa 488 (catalogue no. ZP-EPI-9002) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C11 — Two related spinning-disk systems in the same section

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk, Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: Quad-band Dichroic (catalogue no. Di01-T405/488/568/647)
  tick: Filters and dichroics :: GFP
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  reference: system A
  click: Add to methods
  select instrument: 3i Marianas CSU-W1 Spinning Disk Med C
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 63x/1.4 NA Oil OIL — Zeiss
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: 525/30 (catalogue no. FF01-525/30-25)
  tick: Detectors :: Photometrics Prime BSI — Photometrics
  reference: system B
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

system A

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). The light path included Quad-band Dichroic (catalogue no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and GFP in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

system B

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). Instrument control and image acquisition were performed using SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). The light path included 525/30 (catalogue no. FF01-525/30-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C12 — Same microscope and method, two channels acquired for two figures

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE — Nikon
  tick: Light sources :: 476 nm laser (Lumencor Celesta 7ch) — Lumencor
  tick: Filters and dichroics :: Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543)
  tick: Detectors :: Photometrics Kinetix — Photometrics
  reference: Figure 5
  click: Add to methods
  tick: Light sources :: 636 nm laser (Lumencor Celesta 7ch) — Lumencor
  reference: Figure 6
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Figure 5

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 476 nm laser (Lumencor Celesta 7ch). The light path included Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543) in the Crest Excitation Wheel. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Crest Dichroic Wheel (Spinning-disk confocal route) and Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Figure 6

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 476 nm laser (Lumencor Celesta 7ch) and 636 nm laser (Lumencor Celesta 7ch). The light path included Celesta-DA/FI/TR/Cy5/Cy7-A (catalogue no. MXR00543) in the Crest Excitation Wheel. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 636 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Crest Dichroic Wheel (Spinning-disk confocal route) and Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C13 — Transmitted light and fluorescence on the same benchtop confocal

**Instrument:** Andor BC43 Benchtop Confocal  
**Imaging method:** Transmitted brightfield, Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Andor BC43 Benchtop Confocal
  tick: Imaging method :: Transmitted brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).
  tick: Objectives :: 20X Plan Apo LD Air 20x/0.8 AIR — Nikon
  tick: Light sources :: LED (Andor Transmitted Light Illuminator) — Andor
  tick: Detectors :: Andor 4.1 MP sCMOS — Andor
  reference: brightfield
  click: Add to methods
  tick: Imaging method :: Confocal spinning disk
  tick: Light sources :: 488 nm laser (Andor Borealis Illumination) — Andor
  tick: Filters and dichroics :: GFP
  reference: confocal
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

brightfield

Transmitted-light brightfield imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Transmitted-light illumination was provided by LED (Andor Transmitted Light Illuminator). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: which position of BC43 Internal Emission Filters (Transmitted light route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

confocal

Spinning-disk confocal imaging was performed using the Andor BC43 benchtop microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by 488 nm laser (Andor Borealis Illumination). The light path included GFP in the BC43 Internal Emission Filters.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### C14 — Light sheet plus confocal validation on two instruments

**Instrument:** MSquared Aurora Airy Beam  
**Imaging method:** Light sheet, Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: MSquared Aurora Airy Beam
  tick: Imaging method :: Light sheet
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.
  tick: Objectives :: 54-10-12 Airy beam dipping objective 17x/0.4 MULTI-IMMERSION — Special Optics
  tick: Light sources :: 488 nm laser (Coherent OBIS laser) — Coherent OBIS
  tick: Filters and dichroics :: GFP filter
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU) — Hamamatsu
  reference: light sheet
  click: Add to methods
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Detectors :: PMT (Ch1) — Unknown
  reference: confocal validation
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

light sheet

Light-sheet imaging was performed using the M Squared Aurora Airy Beam other microscope. Imaging was performed with a 17x/0.4 Multi-Immersion objective (Special Optics 54-10-12 Airy beam dipping objective, 54-10-12). Instrument control and image acquisition were performed using M Squared Cubes Acquisition.

Illumination was provided by 488 nm laser (Coherent OBIS laser). The light path included GFP filter in the Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for M Squared Cubes Acquisition]
- [PLEASE SPECIFY: the role of 488 nm laser (Coherent OBIS laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

confocal validation

Point-scanning confocal imaging was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon). Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```


## Batch D — Adversarial but plausible user behaviour

### D01 — Clear all: does the checkbox state reset?

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
  click: Clear all
  [state] STATE-visible-checked: ["Imaging method|Widefield fluorescence", "Light path and readouts|Widefield fluorescence", "Objectives|UPlanFl 40x/0.75 Ph2 AIR \u2014 Olympus", "Light sources|arc lamp (Osram HBO 103W short arc bulb) \u2014 Osram", "Filters and dichroics|Fluorescence Turret", "Filters and dichroics|U-MWIB (GFP wide) (catalogue no. U-MWIB)", "Detectors|Olympus DP71 \u2014 Olympus"]
  [state] STATE-all-checked: ["Imaging method|Widefield fluorescence|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|UPlanFl 40x/0.75 Ph2 AIR \u2014 Olympus|VIS", "Light sources|arc lamp (Osram HBO 103W short arc bulb) \u2014 Osram|VIS", "Filters and dichroics|Fluorescence Turret|VIS", "Filters and dichroics|U-MWIB (GFP wide) (catalogue no. U-MWIB)|VIS", "Detectors|Olympus DP71 \u2014 Olympus|VIS"]
```

**Exact generated Methods text:**

```text
Select an instrument, then choose “Add to methods”.
```

### D02 — Clear all, untick the old objective, then build a new acquisition

**Instrument:** Olympus BX60  
**Imaging method:** Widefield fluorescence, Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Olympus BX60
  tick: Imaging method :: Widefield fluorescence
  tick: Objectives :: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Light sources :: arc lamp (Osram HBO 103W short arc bulb) — Osram
  tick: Filters and dichroics :: U-MWIB (GFP wide) (catalogue no. U-MWIB)
  tick: Detectors :: Olympus DP71 — Olympus
  click: Add to methods
  click: Clear all
  tick: Imaging method :: Transmitted brightfield
  untick: UPlanFl 40x/0.75 Ph2 AIR — Olympus
  tick: Objectives :: PlanC 4x/0.10 AIR — Olympus
  tick: Light sources :: halogen lamp (Olympus 12V 100W halogen bulb) — Olympus
  tick: Detectors :: Olympus DP71 — Olympus
  [state] STATE-visible-checked: ["Imaging method|Transmitted brightfield", "Light path and readouts|Transmitted light", "Objectives|PlanC 4x/0.10 AIR \u2014 Olympus", "Light sources|halogen lamp (Olympus 12V 100W halogen bulb) \u2014 Olympus", "Detectors|Olympus DP71 \u2014 Olympus"]
  [state] STATE-all-checked: ["Imaging method|Transmitted brightfield|VIS", "Light path and readouts|Transmitted light|VIS", "Objectives|PlanC 4x/0.10 AIR \u2014 Olympus|VIS", "Light sources|halogen lamp (Olympus 12V 100W halogen bulb) \u2014 Olympus|VIS", "Detectors|Olympus DP71 \u2014 Olympus|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus/Evident BX60 upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10).

Transmitted-light illumination was provided by halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D03 — Two acquisitions on one instrument where the second forgets the objective

**Instrument:** Zeiss TIRF  
**Imaging method:** TIRF, Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss TIRF
  tick: Imaging method :: TIRF
  tick: Objectives :: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Light sources :: 488 nm laser — Unknown
  tick: Filters and dichroics :: Filter set 38 HE (GFP) (catalogue no. 38 HE)
  tick: Detectors :: Hamamatsu C9100-13 — Hamamatsu
  reference: TIRF
  click: Add to methods
  tick: Imaging method :: Transmitted brightfield
  untick: Alpha Plan Apochromat 100x/1.46 OIL — Zeiss
  tick: Light sources :: halogen lamp (Zeiss Transmitted Halogen Lamp) — Zeiss
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu
  reference: brightfield
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

TIRF

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by 488 nm laser. The light path included Filter set 38 HE (GFP) (catalogue no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

brightfield

Transmitted-light brightfield imaging was performed using the Zeiss TIRF inverted microscope.

Transmitted-light illumination was provided by halogen lamp (Zeiss Transmitted Halogen Lamp). Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D04 — Abberior: RESOLFT after configuring STED (readout of stale state)

**Instrument:** Abberior STED  
**Imaging method:** STED, RESOLFT  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Hardware modules and environmental control :: Easy3D STED — Abberior
  tick: Imaging method :: RESOLFT
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Abberior", "Imaging method|RESOLFT", "Light path and readouts|Point-scanning confocal", "Hardware modules and environmental control|Easy3D STED \u2014 Abberior", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using Abberior|VIS", "Imaging method|RESOLFT|VIS", "Light path and readouts|Point-scanning confocal|VIS", "Hardware modules and environmental control|Easy3D STED \u2014 Abberior|VIS", "Objectives|UPlanSApo 100x/1.40 Oil OIL \u2014 Olympus|VIS"]
  tick: Light sources :: 485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant
  tick: Filters and dichroics :: 525/25 (catalogue no. FF01-525/25)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module was used (Abberior easy3D STED). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 485 nm laser (PicoQuant LDH-D-C-485). The light path included 525/25 (catalogue no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D05 — Lambert FLIM: tick FLIM readout, then untick it and generate

**Instrument:** Lambert FLIM  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** FLIM, FRET

**Selections made in the UI (in order):**

```
  select instrument: Lambert FLIM
  tick: Imaging method :: Widefield fluorescence
  tick: Light path and readouts :: FLIM
  tick: Light path and readouts :: FRET
  untick: FRET
  tick: Objectives :: Plan APOCHROMAT 63x/1.4 Oil OIL — Zeiss
  tick: Light sources :: 469 nm LED (Multi-LED excitation) — Unknown
  tick: Detectors :: Lambert Instruments LIFA Camera — Lambert Instruments
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert Instruments LIFA (frequency domain FLIM) inverted microscope. FLIM data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900).

Illumination was provided by 469 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: the role of 469 nm LED (Multi-LED excitation) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version and Detector pixel pitch (um) are not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D06 — Zeiss AxioZoom: reflected then transmitted brightfield in one section

**Instrument:** Zeiss AxioZoom.V16  
**Imaging method:** Reflected brightfield, Transmitted brightfield  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss AxioZoom.V16
  tick: Imaging method :: Reflected brightfield
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN Pro.
  tick: Objectives :: PlanApo Z 0.5x/0.125 AIR — Zeiss
  tick: Light sources :: LED (Zeiss CL 9000 LED CAN ring light) — Zeiss
  tick: Detectors :: Zeiss AxioCam 105 Color — Zeiss
  reference: reflected
  click: Add to methods
  tick: Imaging method :: Transmitted brightfield
  tick: Light sources :: LED (VisiLED MC1000 LED base light) — VisiLED
  reference: transmitted
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

reflected

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Zeiss AxioCam 105 Color.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

transmitted

Transmitted-light brightfield imaging was performed using the Zeiss AxioZoom.V16 stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Transmitted-light illumination was provided by LED (VisiLED MC1000 LED base light).

Review before publication:
- [PLEASE SPECIFY: acquisition software version for Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D07 — STELLARIS: spectral plus FLIM plus FCS readouts on one acquisition

**Instrument:** Leica STELLARIS 8 FALCON FLIM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** Spectral Imaging, FLIM, FCS, FRET

**Selections made in the UI (in order):**

```
  select instrument: Leica STELLARIS 8 FALCON FLIM
  tick: Imaging method :: Confocal point scanning
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft
  tick: Light path and readouts :: Spectral Imaging
  tick: Light path and readouts :: FLIM
  tick: Light path and readouts :: FCS
  tick: Light path and readouts :: FRET
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica Microsystems
  tick: Light sources :: white light laser (Leica Microsystems STELLARIS White Light Laser) — Leica Microsystems
  tick: Detectors :: Leica Microsystems Power HyD S SP pos 1 — Leica Microsystems
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica Microsystems STELLARIS 8 FALCON inverted microscope. Spectral Imaging data were acquired. FLIM data were acquired. FCS data were acquired. FRET data were acquired. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: FCS measurement duration, number of repeats, how the confocal volume was calibrated, and the fitting model]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: acquisition software version for LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D08 — Deltavision: SMLM then switch to SIM keeping nothing

**Instrument:** Deltavision OMX  
**Imaging method:** SMLM, SIM  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Deltavision OMX
  tick: Imaging method :: SMLM
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using OMX Acquisition (v3.70).
  tick: Objectives :: APO N TIRF 60x/1.49 OIL — Olympus
  tick: Light sources :: 642 nm laser (GE Healthcare) — GE Healthcare
  tick: Filters and dichroics :: Cy5
  tick: Detectors :: PCO Edge — PCO
  tick: Imaging method :: SIM
  [state] STATE-visible-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using OMX Acqu", "Imaging method|SIM", "Light path and readouts|Widefield fluorescence", "Objectives|APO N TIRF 60x/1.49 OIL \u2014 Olympus"]
  [state] STATE-all-checked: ["Confirmed acquisition actions|Instrument control and image acquisition were performed using OMX Acqu|VIS", "Imaging method|SIM|VIS", "Light path and readouts|Widefield fluorescence|VIS", "Objectives|APO N TIRF 60x/1.49 OIL \u2014 Olympus|VIS"]
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the GE Healthcare OMX V4 inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: which position of OMX Emission Filters (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D09 — Zeiss LSM 880: ISM with a PMT detector selected as well

**Instrument:** Zeiss LSM 880 with AiryScan  
**Imaging method:** ISM (AiryScan)  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 880 with AiryScan
  tick: Imaging method :: ISM (AiryScan)
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi
  tick: Objectives :: C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR OIL — Zeiss
  tick: Light sources :: 488 nm laser (Argon) — Unknown
  tick: Hardware modules and environmental control :: AiryScan Detector/Module — Zeiss
  tick: Detectors :: PMT (Ch1) — Unknown
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Image scanning microscopy (ISM; Airyscan) was performed using the Zeiss LSM 880 with AiryScan inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). The AiryScan Detector/Module was used (Zeiss Airyscan). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Illumination was provided by 488 nm laser (Argon). Images were recorded using PMT (Ch1).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting detector/reconstruction mode and the reconstruction software/version and settings used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser (Argon) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D10 — 3i CSU-W1: FRAP module on a spinning-disk acquisition

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 63x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 488 nm laser (3i LaserStack v4) — 3i
  tick: Filters and dichroics :: Quad-band Dichroic (catalogue no. Di01-T405/488/568/647)
  tick: Filters and dichroics :: GFP
  tick: Detectors :: Hamamatsu ORCA-Flash4.0 — Hamamatsu
  tick: Hardware modules and environmental control :: FRAP Module — 3i
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). The FRAP Module was used (3i Vector). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 488 nm laser (3i LaserStack v4). The light path included Quad-band Dichroic (catalogue no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and GFP in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D11 — 3i CSU-W1: NIR imaging with the 730 nm laser and Alexa 750 emitter

**Instrument:** 3i CSU-W1 Spinning Disk  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: 3i CSU-W1 Spinning Disk
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using 3i SlideBook (v6).
  tick: Objectives :: Plan-Apochromat 100x/1.4 Oil DIC M27 OIL — Zeiss
  tick: Light sources :: 730 nm laser (3i SingleLine 730nm Laser Launch) — 3i
  tick: Filters and dichroics :: NIR dichroic position
  tick: Filters and dichroics :: Alexa 750 (catalogue no. FF02-809/81-25)
  tick: Detectors :: Photometrics Evolve — Photometrics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Zeiss Plan-Apochromat 100x/1.4 Oil DIC M27, 420792-9901). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by 730 nm laser (3i SingleLine 730nm Laser Launch). The light path included NIR dichroic position in the CSU-W1 Dichroic Slider and Alexa 750 (catalogue no. FF02-809/81-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Evolve.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D12 — Leica Thunder: full eight-LED source selection

**Instrument:** Leica Thunder  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Leica Thunder
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X with Navigator.
  tick: Objectives :: HC PL APO 63x/1.40 OIL CS2 OIL — Leica
  tick: Light sources :: 395 nm LED (Leica LED 8) — Leica
  tick: Light sources :: 475 nm LED (Leica LED 8) — Leica
  tick: Light sources :: 555 nm LED (Leica LED 8) — Leica
  tick: Light sources :: 635 nm LED (Leica LED 8) — Leica
  tick: Filters and dichroics :: CYR71010 (catalogue no. 11525416)
  tick: Detectors :: Leica K8 — Leica
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Microsystems Leica THUNDER Imager 3D Live Cell inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by 395 nm LED (Leica LED 8), 475 nm LED (Leica LED 8), 555 nm LED (Leica LED 8), and 635 nm LED (Leica LED 8). The light path included CYR71010 (catalogue no. 11525416) in the Filter Turret. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: acquisition software version for LAS X with Navigator]
- [PLEASE SPECIFY: the role of 395 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 555 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: the role of 635 nm LED (Leica LED 8) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE VERIFY: the recorded transmission bands for CYR71010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of Standalone Emission Wheel (Widefield fluorescence route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D13 — Abberior: RESCue STED illumination control selected

**Instrument:** Abberior STED  
**Imaging method:** STED  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Abberior STED
  tick: Imaging method :: STED
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using Abberior Imspector.
  tick: Objectives :: UPlanSApo 100x/1.40 Oil OIL — Olympus
  tick: Light sources :: 640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant
  tick: Light sources :: 775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics
  tick: Filters and dichroics :: 685/35 (catalogue no. ET685/35)
  tick: Detectors :: Excelitas Technologies SPCM-AQRH-14-TR — Excelitas Technologies
  tick: Illumination control :: RESCue STED
  tick: Hardware modules and environmental control :: RESCue STED — Abberior
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED/RESOLFT inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The RESCue STED module was used (Abberior). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by 640 nm laser (PicoQuant LDH-D-C-640). Stimulated-emission depletion was provided by 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included 685/35 (catalogue no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR. Adaptive illumination used RESCue STED.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for Abberior Imspector]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D14 — Nikon Crest V3: single camera with the dual-camera splitter still ticked

**Instrument:** Nikon Ti2-E Crest V3  
**Imaging method:** Confocal spinning disk  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Nikon Ti2-E Crest V3
  tick: Imaging method :: Confocal spinning disk
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.
  tick: Objectives :: CFI Plan Apochromat Lambda S 60XC Sil DIC N2 60x/1.3 SILICONE — Nikon
  tick: Light sources :: 476 nm laser (Lumencor Celesta 7ch) — Lumencor
  tick: Camera and emission splitters :: MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set
  tick: Detectors :: Photometrics Kinetix — Photometrics
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by 476 nm laser (Lumencor Celesta 7ch). Light was directed through MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: acquisition software version for NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: which position of Crest Excitation Wheel (Spinning-disk confocal route), Crest Dichroic Wheel (Spinning-disk confocal route), and Crest Emission Wheel (Spinning-disk confocal route) was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D15 — Zeiss LSM 510: confocal acquisition with the AFM but no detector ticked

**Instrument:** Zeiss LSM 510 JPK AFM  
**Imaging method:** Confocal point scanning  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: Zeiss LSM 510 JPK AFM
  tick: Imaging method :: Confocal point scanning
  tick: Objectives :: Placeholder 10x/0.3 AIR — Unknown
  tick: Light sources :: 488 nm laser — Unknown
  tick: Hardware modules and environmental control :: AFM Module — JPK
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The AFM Module was used (JPK NanoWizard I with CellHesion).

Illumination was provided by 488 nm laser.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

### D16 — EVOS: fluorescence where the user picks a cube that does not match the LED

**Instrument:** EVOS fl  
**Imaging method:** Widefield fluorescence  
**Physical path / readouts:** (auto-selected: the only compatible path)

**Selections made in the UI (in order):**

```
  select instrument: EVOS fl
  tick: Imaging method :: Widefield fluorescence
  tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using On-board EVOS interface.
  tick: Objectives :: Plan Fluor 20x/0.45 AIR — AMG (Thermo Fisher)
  tick: Light sources :: 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) — Thermo Fisher / AMG
  tick: Filters and dichroics :: Cy5/Alexa 647 (catalogue no. AMEP-4656)
  tick: Detectors :: AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD) — AMG (Thermo Fisher)
  click: Add to methods
```

**Exact generated Methods text:**

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Thermo Fisher / AMG FL inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included Cy5/Alexa 647 (catalogue no. AMEP-4656) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: acquisition software version for On-board EVOS interface]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition, for example excitation, transmitted illumination, or depletion; it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Software version is not recorded for this instrument; confirm the exact values with facility staff]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```


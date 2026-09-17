# PR #460 — original 116-scenario replay

Scenarios recovered: **116**  
Executed to completion: **103**  
All controls resolved exactly: **82**

## A01 — Abberior STED - two-colour STED, 775 nm depletion

```text
Light Microscopy Methods:

Figure 3, STED

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module (Abberior easy3D STED) was used. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 640 nm laser (PicoQuant LDH-D-C-640). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 640 nm laser (PicoQuant LDH-D-C-640) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A02 — Abberior STED - plain confocal reference

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 485 nm laser (PicoQuant LDH-D-C-485). The light path included a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 485 nm laser (PicoQuant LDH-D-C-485) is reported with a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A03 — Abberior STED - confocal user ticks the 775 nm depletion laser (no STED method)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 640 nm laser (PicoQuant LDH-D-C-640). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 640 nm laser (PicoQuant LDH-D-C-640) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: a depletion source is reported for an acquisition described as point-scanning confocal imaging; confirm the method and the sources that were used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A04 — Abberior STED - RESOLFT

```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 485 nm laser (PicoQuant LDH-D-C-485). The light path included a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the on/off switching wavelengths and illumination doses, the switching cycle timing, and the number of switching cycles per pixel. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 485 nm laser (PicoQuant LDH-D-C-485) is reported with a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: RESOLFT imaging is reported but no source recorded as depletion was selected; confirm the depletion source and the power used at the sample]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A05 — Abberior STED - 3D STED with Easy3D + SLM + adaptive optics

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module (Abberior easy3D STED) and Adaptive Optics module (Abberior) were used. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 561 nm laser (PicoQuant PDL-T 561). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a BrightLine 615/10 emission bandpass filter (615/10 nm; Semrock) in the Emission Filter Wheel. STED beam shaping used Abberior easy3D SLM. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 561 nm laser (PicoQuant PDL-T 561) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a BrightLine 615/10 emission bandpass filter (615/10 nm; Semrock), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE SPECIFY: which phase mask profile was applied (Vortex, Bottle, and 3D-STED are recorded for this modulator)]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A06 — 3i CSU-W1 - spinning disk live cell, 2 lasers

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp` → `Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2.` (0.96)

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). The Incubation module (Okolab Full Enclosure) was used. Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2. Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 488 nm laser (3i LaserStack v4) and a 561 nm laser (3i LaserStack v4). The light path included a Quad-band Dichroic (440/25, 521/25, 607/25, 700/25 nm; cat. no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and a Cy3 / Alexa 568 emission bandpass filter (617/73 nm; cat. no. FF01-617/73-25) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (3i LaserStack v4) and 561 nm laser (3i LaserStack v4) are reported with a Cy3 / Alexa 568 emission bandpass filter (617/73 nm; cat. no. FF01-617/73-25), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A07 — 3i CSU-W1 - widefield fluorescence

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by an LED (Excelitas X-Cite XLED1). The light path included a 485/20 nm excitation bandpass filter (cat. no. FF02-485/20-25) in the XLED Excitation Filters. The light path included Widefield Dichroic and Widefield Emission. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A08 — 3i CSU-W1 - transmitted brightfield (no light source offered)

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Zeiss Plan-Apochromat 10x/0.45 Ph1 M27, 420641-9910). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A09 — 3i CSU-W1 - phase contrast

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Zeiss Plan-Apochromat 10x/0.45 Ph1 M27, 420641-9910). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A10 — 3i CSU-W1 - DIC

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the DIC prism/Wollaston set, the polariser and analyser, and the condenser setting used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A11 — 3i Med C - spinning disk, piezo z-stack

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i Marianas CSU-W1 Spinning Disk Med C (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). The Piezo Z-Stage module (ASI) was used. Z-stacks were acquired using an ASI piezo stage. Instrument control and image acquisition were performed using SlideBook (v6).

Excitation was provided by a 405 nm laser (3i LaserStack v4) and a 488 nm laser (3i LaserStack v4). The light path included a 445/45 nm emission bandpass filter (cat. no. FF01-445/45-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: model of the Piezo Z-Stage module]
- [PLEASE VERIFY: 405 nm laser (3i LaserStack v4) and 488 nm laser (3i LaserStack v4) are reported with a 445/45 nm emission bandpass filter (cat. no. FF01-445/45-25), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE VERIFY: Module model is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A12 — 3i Med C - widefield fluorescence TRITC

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the 3i Marianas CSU-W1 Spinning Disk Med C (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). Instrument control and image acquisition were performed using SlideBook (v6).

Illumination was provided by an LED (CoolLED pE-300). The light path included a filter cube (cat. no. LED-TRITC-A-ZHE-Zero) in the Zeiss Widefield Fluorescence Positions. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [PLEASE VERIFY: the recorded transmission bands for LED-TRITC-A-ZHE-Zero are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: the role of LED (CoolLED pE-300) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A13 — Andor BC43 - spinning disk GFP

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Andor BC43 Benchtop Confocal. Imaging was performed with a 40x/0.95 Air objective (Nikon 40X Plan Apo LD Air, INS-OBJ-40D-095). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by a 488 nm laser (Andor Borealis Illumination). The light path included a GFP emission bandpass filter (525/50 nm) in the BC43 Internal Emission Filters. The light path included BC43 Internal Dichroic. Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (Andor Borealis Illumination) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A14 — Andor BC43 - transmitted brightfield (fluorescence emission filters still offered)

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Andor BC43 Benchtop Confocal. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Transmitted-light illumination was provided by an LED (Andor Transmitted Light Illuminator). Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A15 — Andor BC43 - brightfield where user ticks a fluorescence emission filter

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Filters and dichroics': 'mCherry'; best=[(0.21621621621621623, {'id': 'filter-1', 'value': 'optical_path_element:bc43_internal_emission_filters', 'checked': False, 'disabled': False, 'visible': True, 'category': 'filter', 'label': 'BC43 Internal Emission Filters'}), (0.20689655172413793, {'id': 'filter-0', 'value': 'optical_path_element:bc43_internal_dichroic', 'checked': False, 'disabled': False, 'visible': True, 'category': 'filter', 'label': 'BC43 Internal Dichroic'})]; available=['BC43 Internal Dichroic', 'BC43 Internal Emission Filters']`

```text
Select an instrument, then choose “Add to methods”.
```

## A16 — Deltavision OMX - 3D-SIM

```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module (GE Healthcare 3D-SIM Illumination Engine) was used. Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 488 nm laser (GE Healthcare). The light path included an Alexa 488 emission bandpass filter (528/45 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (GE Healthcare) is reported with an Alexa 488 emission bandpass filter (528/45 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A17 — Deltavision OMX - TIRF

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). The TIRF Module (GE Healthcare Ring TIRF with PhotoKinetic Optics) was used. Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 642 nm laser (GE Healthcare). The light path included a Cy5 emission bandpass filter (683/40 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 642 nm laser (GE Healthcare) is reported with a Cy5 emission bandpass filter (683/40 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A18 — Deltavision OMX - SMLM / dSTORM

```text
Light Microscopy Methods:

Single-molecule localization microscopy (SMLM) was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 405 nm laser (GE Healthcare) and a 642 nm laser (GE Healthcare). The light path included a Cy5 emission bandpass filter (683/40 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 405 nm laser (GE Healthcare) and 642 nm laser (GE Healthcare) are reported with a Cy5 emission bandpass filter (683/40 nm), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A19 — Deltavision OMX - conventional widefield

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 405 nm laser (GE Healthcare). The light path included a DAPI emission bandpass filter (436/31 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [PLEASE VERIFY: 405 nm laser (GE Healthcare) is reported with a DAPI emission bandpass filter (436/31 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A20 — EVOS fl - widefield GFP

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by a 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included a GFP/Alexa 488 filter cube (excitation 470/22 nm, 495 nm dichroic, emission 510/42 nm; cat. no. ZP-EPI-9002) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A21 — EVOS fl - phase contrast

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 4x/0.13 Air objective (Olympus U Plan FL N 4x/0.13 PhP). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by an LED (Thermo Fisher / AMG Transmitted Light LED). Images were recorded using AMG (Thermo Fisher) Sony ICX285AQ Color CCD.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE SPECIFY: the role of LED (Thermo Fisher / AMG Transmitted Light LED) in this acquisition (for example transmitted illumination); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A22 — Lambert FLIM - widefield FLIM

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert FLIM (Lambert Instruments LIFA (frequency domain FLIM)), an inverted microscope, with FLIM data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900). The FLIM Module (Lambert Instruments LIFA) was used.

Illumination was provided by a 469 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: the role of 469 nm LED (Multi-LED excitation) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A23 — Lambert FLIM - FLIM-FRET

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert FLIM (Lambert Instruments LIFA (frequency domain FLIM)), an inverted microscope, with FLIM and FRET data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900). The FLIM Module (Lambert Instruments LIFA) was used.

Illumination was provided by a 406 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: the role of 406 nm LED (Multi-LED excitation) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A24 — Leica DM IRBE - widefield EGFP with unknown camera

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica DM IRBE, an inverted microscope. Imaging was performed with a 40x/0.7 Air objective (Leica PL FLUOTAR 40x/0.70 PH2, 506014).

Illumination was provided by an arc lamp (Leica 50W HBO short arc bulb). The light path included a Filter Cube EGFP (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm) in the Fluorescence Turret.

Review before publication:
- [PLEASE SPECIFY: the detector or camera used for this acquisition (manufacturer and model); the facility record does not identify it]
- [PLEASE SPECIFY: the role of arc lamp (Leica 50W HBO short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A25 — Leica DM IRBE - darkfield with 1.6x auxiliary lens

```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica DM IRBE, an inverted microscope. Imaging was performed with a 20x/0.5 Air objective (Leica PL FLUOTAR 20x/0.50 PH2, 506013). An intermediate magnification changer (Leica 1.6x Auxiliary Lens, 1.6x) was used.

Transmitted-light illumination was provided by a halogen lamp (Leica 12V 100W halogen bulb).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the darkfield condenser used and its numerical-aperture range. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the detector or camera used for this acquisition (manufacturer and model); the facility record does not identify it]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A26 — Leica DM RB - visual darkfield through eyepieces

```text
Light Microscopy Methods:

Darkfield imaging was performed using the Leica DM RB, an upright microscope. Imaging was performed with a 20x/0.7 Air objective (Leica HC PL APO 20x/0.70 CS, 506513).

Transmitted-light illumination was provided by a halogen lamp (Leica 12V 100W halogen bulb). Samples were observed through eyepieces.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the darkfield condenser used and its numerical-aperture range. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A27 — Leica DM RE - DIC

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Leica DM RE, an upright microscope. Imaging was performed with a 63x/1.32 Oil objective (Leica PL APO 63x/1.32 OIL PH3, 506082).

Transmitted-light illumination was provided by a halogen lamp (Leica 12V 100W halogen bulb).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the DIC prism/Wollaston set, the polariser and analyser, and the condenser setting used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the detector or camera used for this acquisition (manufacturer and model); the facility record does not identify it]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A28 — STELLARIS 8 - confocal, spectral detection

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope, with spectral imaging data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The Acousto-Optical Beam Splitter (AOBS) module (Leica Microsystems) was used. Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1 and Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A29 — STELLARIS 8 - FALCON FLIM

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope, with FLIM data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module (Leica Microsystems STELLARIS 8 FALCON) was used. Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD X SP pos 2.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A30 — STELLARIS 8 - FCS

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope, with FCS data acquired on the same light path. Imaging was performed with a 86x/1.2 Water objective (Leica Microsystems HC PL APO 86x/1.20 W motCORR STED W, 15506333). The FCS Module (Leica Microsystems STELLARIS 8 FCS) was used. Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP Core Unit pos 3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: FCS measurement duration, number of repeats, how the confocal volume was calibrated, and the fitting model]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A31 — STELLARIS 8 - FRET acceptor photobleaching, 2 detectors, resonant scanner

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope, with FRET data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The microscope used a tandem scanner (galvo/resonant, line rate 8000 Hz). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser) and a 405 nm laser (Leica Microsystems Laser 405 DMOD). Images were recorded using Leica Microsystems Power HyD S SP pos 1 and Leica Microsystems Power HyD R SP pos 5.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: manufacturer and model of the Tandem Scanner (Galvo/Resonant)]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) and 405 nm laser (Leica Microsystems Laser 405 DMOD) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for these sources]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A32 — STELLARIS 8 - widefield fluorescence on the camera port

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 20x/0.75 Air objective (Leica Microsystems HC PL APO 20x/0.75 CS2, 15506517). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by an LED (Leica Microsystems Leica LED 3). The light path included a Filter Cube GFP (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; Leica Microsystems; cat. no. 15525314) in the LED/filter-cube observation path. Images were recorded using Leica Microsystems K5 Microscope Camera.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of LED (Leica Microsystems Leica LED 3) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A33 — STELLARIS 8 - transmitted brightfield

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 10x/0.4 Air objective (Leica Microsystems HC PL APO 10x/0.40 CS2, 15506424). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by an LED (Leica Microsystems Leica LED 3). Images were recorded using Leica Microsystems BF detector for DMI.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: the role of LED (Leica Microsystems Leica LED 3) in this acquisition (for example transmitted illumination); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A34 — Leica TCS SP5 (retired) - multiphoton, no method section

```text
Light Microscopy Methods:

Multiphoton imaging was performed using the Leica TCS SP5 Multiphoton (Leica Microsystems TCS SP5 Multiphoton), an upright microscope. Imaging was performed with a 25x/0.95 Water objective (Leica HCX IR APO L). The microscope used a resonant scanner. Instrument control and image acquisition were performed using Leica LAS AF.

Excitation was provided by a pulsed near-ir laser (Coherent Chameleon Ultra II). Images were recorded using NDD PMT.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting excitation wavelength, mean power at the sample, and pulse width. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Resonant Scanner]
- [PLEASE SPECIFY: the version of Leica LAS AF]
- [PLEASE SPECIFY: wavelength used from the recorded 690-1040 nm tunable range of pulsed near-ir laser (Coherent Chameleon Ultra II)]
- [PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration that was in use at the time of acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE VERIFY: Scanner line rate (Hz) and Detector manufacturer are not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A35 — Leica Thunder - widefield, two filter wheels

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). The Hardware Autofocus module (Leica Microsystems Adaptive Focus Control) was used. Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by a 475 nm LED (Leica LED 8). The light path included a DFT51010 filter cube (cat. no. 11525418) in the Filter Turret and a 535/70 nm emission bandpass filter in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE VERIFY: the recorded transmission bands for DFT51010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE VERIFY: 475 nm LED (Leica LED 8) is reported with a 535/70 nm emission bandpass filter, which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A36 — Leica Thunder - transmitted brightfield colour camera

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 10x/0.45 Air objective (Leica HC PL APO 10x/0.45, 11506410). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A37 — MSquared Aurora - Airy-beam light sheet

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolutio'; best=[(0.3723404255319149, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.']`

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.` → `Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution.` (0.637)

```text
Select an instrument, then choose “Add to methods”.
```

## A38 — Nikon Crest V3 - dual-camera spinning disk

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by a 476 nm laser (Lumencor Celesta 7ch) and a 545 nm laser (Lumencor Celesta 7ch). The light path included a Celesta-DA/FI/TR/Cy5/Cy7-A excitation multi-bandpass filter (391/54.4, 477/20.4, 549/25.7, 638.5/27.6, 741/45.1 nm; cat. no. MXR00543) in the Crest Excitation Wheel and a Celesta-DA/FI/TR/Cy5/Cy7-A multi-band dichroic mirror (441/36.1, 511/34.3, 592.5/45.2, 684/44.4, 817/78.8 nm; cat. no. MXR00543) in the Crest Dichroic Wheel. Light was directed through MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set. Images were recorded using Photometrics Kinetix (master) and Photometrics Kinetix (slave).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) and 545 nm laser (Lumencor Celesta 7ch) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for these sources]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A39 — Nikon Crest V3 - widefield fluorescence FITC

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon CFI Plan Apochromat Lambda D 20X DIC N2, MRD70270). Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by an LED (Nikon D-LEDI Fluorescence LED Illumination System). The light path included an FITC Ti2 32mm Cube SB LFOV (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; cat. no. MXR00716) in the Epi Turret. Images were recorded using Photometrics Kinetix.

Review before publication:
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the role of LED (Nikon D-LEDI Fluorescence LED Illumination System) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A40 — Nikon Crest V3 - DIC

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Nikon CFI Plan Apochromat Lambda D 20X DIC N2, MRD70270). Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Transmitted-light illumination was provided by an LED (Nikon T12-D-LHLED LED Lamp House). Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the DIC prism/Wollaston set, the polariser and analyser, and the condenser setting used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A41 — Nikon Eclipse Ti2-E - widefield GFP

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by a 475 nm LED (Lumencor Spectra X LED system). The light path included a Chroma 89403bs multi-band dichroic mirror (cat. no. 89403bs) in the Filter Turret and a GFP Emission bandpass filter (515/30 nm) in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE VERIFY: 475 nm LED (Lumencor Spectra X LED system) is reported with a GFP Emission bandpass filter (515/30 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A42 — Nikon Eclipse Ti2-E - phase contrast

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 10x/0.3 Air objective (Nikon Plan Fluor 10x/0.30 OFN 25 Ph1 DL, MRH20101). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by an LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Nikon DS-Fi3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A43 — Olympus BX60 - widefield GFP

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A44 — Olympus BX60 - brightfield histology

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by a halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A45 — ONI Nanoimager - dSTORM

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A46 — ONI Nanoimager - live TIRF

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A47 — ONI Nanoimager - single-molecule FRET readout

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A48 — Zeiss AxioZoom - widefield fluorescence whole mount

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss AxioZoom.V16, a stereo microscope. Imaging was performed with a 1x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Illumination was provided by an arc lamp (Zeiss HXP 200C). The light path included an Alexa 488 (Filter set 38 HE) (cat. no. 38 HE) in the Fluorescence Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: the version of Zeiss ZEN Pro]
- [PLEASE SPECIFY: the role of arc lamp (Zeiss HXP 200C) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A49 — Zeiss AxioZoom - Apotome optical sectioning

```text
Light Microscopy Methods:

Optical sectioning was performed using the Zeiss AxioZoom.V16, a stereo microscope. Imaging was performed with a 1x/0.125 Air objective (Zeiss PlanApo Z). The SIM Module (Zeiss ApoTome.2) was used. Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Illumination was provided by an arc lamp (Zeiss HXP 200C). The light path included a DAPI (Filter set 49) (cat. no. 49) in the Fluorescence Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 LT+ sCMOS.

Review before publication:
- [PLEASE SPECIFY: the version of Zeiss ZEN Pro]
- [PLEASE SPECIFY: the role of arc lamp (Zeiss HXP 200C) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A50 — Zeiss AxioZoom - reflected brightfield ring light

```text
Light Microscopy Methods:

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16, a stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by an LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Zeiss AxioCam 105 Color.

Review before publication:
- [PLEASE SPECIFY: the version of Zeiss ZEN Pro]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A51 — Zeiss LSM 510 JPK - confocal with AFM

**Fuzzy control resolutions:**

- `tick: Detectors :: Zeiss — Zeiss` → `Unknown PMT — Zeiss` (0.95)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM, an inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The AFM Module (JPK NanoWizard I with CellHesion) was used.

Illumination was provided by a 488 nm laser.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: the detector or camera used for this acquisition (manufacturer and model); the facility record does not identify it]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A52 — Zeiss LSM 510 JPK - transmitted brightfield with no recorded hardware

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Zeiss LSM 510 JPK AFM, an inverted microscope. Imaging was performed with a 10x/0.3 Air objective.

Review before publication:
- [PLEASE VERIFY: the recorded hardware for the transmitted light path is incomplete; confirm the illumination and detection components used]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A53 — Zeiss LSM 880 - Airyscan super-resolution

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A54 — Zeiss LSM 880 - spectral confocal lambda stack

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A55 — Zeiss LSM 880 - DIC transmitted detector

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## A56 — Zeiss TIRF - TIRF EMCCD

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat). The Hardware Autofocus module (Zeiss Definite Focus) was used.

Illumination was provided by a 488 nm laser. The light path included a Filter set 38 HE (GFP) (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; cat. no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A57 — Zeiss TIRF - epifluorescence comparison

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 561 nm laser. The light path included a Filter set 43 HE (DsRed) (excitation 550/25 nm, 570 nm dichroic, emission 605/70 nm; cat. no. 43 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 561 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## A58 — Agilent eSight - live fluorescence in incubator

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp` → `Live-cell imaging was performed using an environmental chamber maintaining controlled temperature, controlled CO2, and controlled humidity.` (0.96)

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Agilent xCELLigence RTCA eSight, a benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). Live-cell imaging was performed using an environmental chamber maintaining controlled temperature, controlled CO2, and controlled humidity. Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).

Illumination was provided by a 482 nm LED (Agilent High-power LED (Green)). The light path included a Green Channel filter cube in the Internal Filter Turret. Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE VERIFY: the recorded transmission bands for Green Channel are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: the role of 482 nm LED (Agilent High-power LED (Green)) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

## A59 — Agilent eSight - brightfield + impedance module

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Agilent xCELLigence RTCA eSight, a benchtop microscope. Imaging was performed with a 10x/0.3 Air objective (Agilent 10x Objective). The Impedance Module (Agilent Impedance Measurement Module) was used. Instrument control and image acquisition were performed using RTCA eSight Software (v1.5.1).

Transmitted-light illumination was provided by an LED (Agilent Transmitted LED). Images were recorded using Sony 5.0 MP Monochromatic CMOS.

Review before publication:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577. Testament funds from Henna Ruusunen also supported this work.
```

## A60 — Leica Thunder - phase contrast

```text
Light Microscopy Methods:

Phase-contrast imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 20x/0.4 Air objective (Leica HC PL FLUOTAR L 20x/0.40 CORR, 11506242). Instrument control and image acquisition were performed using LAS X with Navigator.

Images were recorded using Leica K3C.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B01 — Generate without software, then confirm software and generate again

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by a 475 nm LED (Lumencor Spectra X LED system). The light path included a GFP Emission bandpass filter (515/30 nm) in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE VERIFY: 475 nm LED (Lumencor Spectra X LED system) is reported with a GFP Emission bandpass filter (515/30 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Filter Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B02 — Pick a fluorescence filter, then change method to brightfield and generate

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B03 — Pick a detector, then switch to a different physical path

```text
Light Microscopy Methods:

Differential interference contrast (DIC) imaging was performed using the Zeiss LSM 880 with AiryScan, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss C-Plan-APOCHROMAT 63x/1.4 Oil DIC UV-VIS-IR, 421782-9900). Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edition) (version FP3 HF 30 FP3 (build 14.0.30.201)).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the DIC prism/Wollaston set, the polariser and analyser, and the condenser setting used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B04 — Tick the objective before choosing the imaging method

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 488 nm laser. The light path included a Filter set 38 HE (GFP) (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; cat. no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B05 — Four excitation lines on one spinning-disk acquisition

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 405 nm laser (3i LaserStack v4), a 488 nm laser (3i LaserStack v4), a 561 nm laser (3i LaserStack v4), and a 640 nm laser (3i LaserStack v4). The light path included a Quad-band Dichroic (440/25, 521/25, 607/25, 700/25 nm; cat. no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and a Quad-band emitter (440/25, 521/25, 607/25, 700/25 nm; cat. no. FF01-440/521/607/700-25) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 405 nm laser (3i LaserStack v4), 488 nm laser (3i LaserStack v4), 561 nm laser (3i LaserStack v4), and 640 nm laser (3i LaserStack v4) are reported with a Quad-band emitter (440/25, 521/25, 607/25, 700/25 nm; cat. no. FF01-440/521/607/700-25), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B06 — Choose one emission filter position, then change to another

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by a 475 nm LED (Leica LED 8). The light path included a 460/80 nm emission bandpass filter and a 535/70 nm emission bandpass filter in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE SPECIFY: 2 positions of the Standalone Emission Wheel are reported, and it holds one at a time; state which filter was used for which channel]
- [PLEASE VERIFY: 475 nm LED (Leica LED 8) is reported with a 535/70 nm emission bandpass filter, which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Filter Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B07 — Switch between exclusive detector branches

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by a 475 nm LED (Lumencor Spectra X LED system). The light path included a GFP Emission bandpass filter (515/30 nm) in the Emission Wheel. Images were recorded using Nikon DS-Fi3.

Review before publication:
- [PLEASE VERIFY: 475 nm LED (Lumencor Spectra X LED system) is reported with a GFP Emission bandpass filter (515/30 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Filter Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B08 — Select two modules, then deselect one before generating

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). The Incubation module (Nikon WarmBox TI2WB-SP400NX-G) was used. Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by a 476 nm laser (Lumencor Celesta 7ch). Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Crest Excitation Wheel and Crest Dichroic Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B09 — Zeiss TIRF: configure widefield, then switch to TIRF (shared hardware)

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 561 nm laser. The light path included a Filter set 43 HE (DsRed) (excitation 550/25 nm, 570 nm dichroic, emission 605/70 nm; cat. no. 43 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 561 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B10 — Andor BC43: same emission filter reached through two methods

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Andor BC43 Benchtop Confocal. Imaging was performed with a 40x/0.95 Air objective (Nikon 40X Plan Apo LD Air, INS-OBJ-40D-095). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by a 488 nm laser (Andor Borealis Illumination). The light path included a GFP emission bandpass filter (525/50 nm) in the BC43 Internal Emission Filters. Images were recorded using Andor 4.1 MP sCMOS.

Review before publication:
- [PLEASE VERIFY: 488 nm laser (Andor Borealis Illumination) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B11 — Abberior: STED, switch to confocal, then return to STED

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 640 nm laser (PicoQuant LDH-D-C-640). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 640 nm laser (PicoQuant LDH-D-C-640) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B12 — STED selected but no depletion laser ticked

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 485 nm laser (PicoQuant LDH-D-C-485). The light path included a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 485 nm laser (PicoQuant LDH-D-C-485) is reported with a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: STED imaging is reported but no source recorded as depletion was selected; confirm the depletion source and the power used at the sample]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B13 — Click Add twice without changing anything

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B14 — Same configuration added twice under two figure references

```text
Light Microscopy Methods:

Figure 1

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Figure 4

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Instrument control and image acquisition were performed using Olympus Cell^D.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: which position of the Fluorescence Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B15 — Add an entry, clear all, then add a different one

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by a halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B16 — Configure one microscope, then switch instrument before generating

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B17 — Over-ticking: every confirmed action and module on the STELLARIS

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)
- `tick: Confirmed acquisition actions :: Live-cell imaging was performed using an environmental chamber maintaining controlled temp` → `Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). The FLIM Module (Leica Microsystems STELLARIS 8 FALCON), FCS Module (Leica Microsystems STELLARIS 8 FCS), Acousto-Optical Beam Splitter (AOBS) module (Leica Microsystems), Hardware Autofocus module (Leica Microsystems Closed Loop Focus with AFC), Motorized Stage module (Leica Microsystems Scanning stage inv. universal / SuperZ Galvo Stage), Incubation module (Okolab Black Box Incubator DMi8 with Super Z chamber, CO2 and passive humidity), and High-Performance Workstation module (Leica Microsystems Workstation Premium) were used. Instrument control and image acquisition were performed using LAS X STELLARIS Control Software, LAS X Dye Finder, LAS X Assay Editor, LAS X Live Data Mode, and LAS X MicroLab. Live-cell imaging was performed using an environmental chamber maintaining controlled temperature and controlled CO2. Z-stacks were acquired using a Leica Microsystems SuperZ Galvo Stage piezo stage. Focal drift was minimized using an Infrared Reflection Autofocus system. Post-acquisition processing and analysis were performed using LAS X 3D Visualisation, LAS X AiviaMotion, and LAS X Lightning Expert.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of LAS X 3D Visualisation used]
- [PLEASE SPECIFY: the version of LAS X AiviaMotion used]
- [PLEASE SPECIFY: the version of LAS X Lightning Expert used]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software, LAS X Dye Finder, LAS X Assay Editor, LAS X Live Data Mode, and LAS X MicroLab]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: the FLIM Module module is reported but FLIM is not among the methods selected for this acquisition; confirm the methods and the modules that were used]
- [PLEASE VERIFY: the FCS Module module is reported but FCS is not among the methods selected for this acquisition; confirm the methods and the modules that were used]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B18 — All five spectral detectors selected

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1, Leica Microsystems Power HyD X SP pos 2, Leica Microsystems Power HyD S SP Core Unit pos 3, Leica Microsystems Power HyD X SP pos 4, and Leica Microsystems Power HyD R SP pos 5.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B19 — Deltavision: try to select two of the three identical cameras

```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 488 nm laser (GE Healthcare). The light path included an Alexa 488 emission bandpass filter (528/45 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (GE Healthcare) is reported with an Alexa 488 emission bandpass filter (528/45 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B20 — Thunder: explicitly empty filter positions

**Fuzzy control resolutions:**

- `tick: Filters and dichroics :: Empty (no filter) (position EMP_BF)` → `Empty (no filter)` (0.96)

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by a 475 nm LED (Leica LED 8). No filter was installed in Filter Turret. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Standalone Emission Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B21 — Abberior: tick the filter wheel itself but no position

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 60x/1.2 Water objective (Olympus UPlanSApo 60x/1.2 W, N6432600). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 485 nm laser (PicoQuant LDH-D-C-485). Images were recorded using Hamamatsu Photonics Photomultiplier Tube.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B22 — LSM 880: select Airyscan, then switch back to plain confocal

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## B23 — Generate with nothing but the instrument and method chosen

```text
Light Microscopy Methods:

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: which position of the Filter Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B24 — Generate with only an instrument selected

```text
Select an instrument, then choose “Add to methods”.
```

## B25 — Objective ticked, then unticked before generating

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## B26 — Two objectives ticked for one acquisition

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 40x/0.75 Air objective (Olympus UPlanFl 40x/0.75 Ph2) and a 100x/1.35 Oil objective (Olympus UPlanApo 100x/1.35 Oil Iris Ph3). Instrument control and image acquisition were performed using Olympus Cell^D.

Illumination was provided by an arc lamp (Osram HBO 103W short arc bulb). The light path included a U-MWIB (GFP wide) filter cube (excitation 475/30 nm, 505 nm dichroic, emission 515 nm longpass; cat. no. U-MWIB) in the Fluorescence Turret. Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: the role of arc lamp (Osram HBO 103W short arc bulb) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C01 — 3i CSU-W1: widefield overview followed by spinning-disk confocal

```text
Light Microscopy Methods:

Figure 1, overview

Widefield fluorescence imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 20x/0.8 Air objective (Zeiss Plan-Apochromat 20x/0.8, 440640-9903-000). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Illumination was provided by an LED (Excelitas X-Cite XLED1). The light path included a 485/20 nm excitation bandpass filter (cat. no. FF02-485/20-25) in the XLED Excitation Filters. The light path included Widefield Dichroic and Widefield Emission. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [PLEASE SPECIFY: the role of LED (Excelitas X-Cite XLED1) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Figure 1, detail

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 488 nm laser (3i LaserStack v4). The light path included a Quad-band Dichroic (440/25, 521/25, 607/25, 700/25 nm; cat. no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and a GFP emission bandpass filter (525/50 nm) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (3i LaserStack v4) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C02 — Zeiss TIRF: TIRF followed by epifluorescence

```text
Light Microscopy Methods:

Figure 2A

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 488 nm laser. The light path included a Filter set 38 HE (GFP) (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; cat. no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Figure 2B

Widefield fluorescence imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 63x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 561 nm laser. The light path included a Filter set 43 HE (DsRed) (excitation 550/25 nm, 570 nm dichroic, emission 605/70 nm; cat. no. 43 HE) in the Filter Turret. Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the role of 561 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C03 — Deltavision OMX: 3D-SIM plus conventional widefield

```text
Light Microscopy Methods:

SIM

Structured illumination microscopy (SIM) was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.42 Oil objective (Olympus Plan Apo N). The 3D-SIM Module (GE Healthcare 3D-SIM Illumination Engine) was used. Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 488 nm laser (GE Healthcare). The light path included an Alexa 488 emission bandpass filter (528/45 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (GE Healthcare) is reported with an Alexa 488 emission bandpass filter (528/45 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]

widefield reference

Widefield fluorescence imaging was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 405 nm laser (GE Healthcare). The light path included a DAPI emission bandpass filter (436/31 nm) in the OMX Emission Filters.

Review before publication:
- [PLEASE VERIFY: 405 nm laser (GE Healthcare) is reported with a DAPI emission bandpass filter (436/31 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C04 — Abberior: STED plus matched confocal reference

```text
Light Microscopy Methods:

STED

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The Easy3D STED module (Abberior easy3D STED) was used. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 640 nm laser (PicoQuant LDH-D-C-640). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 640 nm laser (PicoQuant LDH-D-C-640) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]

confocal reference

Point-scanning confocal imaging was performed using the Abberior STED, an inverted microscope. Instrument control and image acquisition were performed using Abberior Imspector.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C05 — ONI Nanoimager: dSTORM plus live TIRF

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']`

```text
Select an instrument, then choose “Add to methods”.
```

## C06 — Nikon Eclipse Ti2-E: phase contrast plus fluorescence

```text
Light Microscopy Methods:

phase contrast

Phase-contrast imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 10x/0.3 Air objective (Nikon Plan Fluor 10x/0.30 OFN 25 Ph1 DL, MRH20101). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Transmitted-light illumination was provided by an LED (Nikon Ti2 Transmitted Illuminator). Images were recorded using Nikon DS-Fi3.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

fluorescence

Widefield fluorescence imaging was performed using the Nikon Eclipse Ti2-E, an inverted microscope. Imaging was performed with a 60x/1.4 Oil objective (Nikon Plan Apo λ 60x/1.40 Oil OFN25 DIC N2, MRD01605). Instrument control and image acquisition were performed using Nikon NIS-Elements AR (v6.1).

Illumination was provided by a 475 nm LED (Lumencor Spectra X LED system). The light path included a GFP Emission bandpass filter (515/30 nm) in the Emission Wheel. Images were recorded using Hamamatsu Orca Flash4.0 V3.

Review before publication:
- [PLEASE VERIFY: 475 nm LED (Lumencor Spectra X LED system) is reported with a GFP Emission bandpass filter (515/30 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Lumencor Spectra X LED system) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Filter Turret was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C07 — STELLARIS: confocal imaging plus a FLIM readout entry

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

confocal

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

FLIM

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C08 — Zeiss LSM 880: Airyscan, confocal and DIC in one Methods section

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## C09 — Two different microscopes in one Methods section

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

screening

Widefield fluorescence imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by a 475 nm LED (Leica LED 8). The light path included a DFT51010 filter cube (cat. no. 11525418) in the Filter Turret and a 535/70 nm emission bandpass filter in the Standalone Emission Wheel. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE VERIFY: the recorded transmission bands for DFT51010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE VERIFY: 475 nm LED (Leica LED 8) is reported with a 535/70 nm emission bandpass filter, which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 475 nm LED (Leica LED 8) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

high resolution

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C10 — EVOS: brightfield, phase contrast and fluorescence

```text
Light Microscopy Methods:

brightfield

Transmitted-light brightfield imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 10x/0.3 Air objective (AMG (Thermo Fisher) Plan Fluor 10x/0.3, AMG-AMEP 4623). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by an LED (Thermo Fisher / AMG Transmitted Light LED). Images were recorded using AMG (Thermo Fisher) Sony ICX285AQ Color CCD.

Review before publication:
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE SPECIFY: the role of LED (Thermo Fisher / AMG Transmitted Light LED) in this acquisition (for example transmitted illumination); it is not recorded for this source]

phase

Phase-contrast imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 4x/0.13 Air objective (Olympus U Plan FL N 4x/0.13 PhP). Instrument control and image acquisition were performed using On-board EVOS interface.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]

GFP

Widefield fluorescence imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by a 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included a GFP/Alexa 488 filter cube (excitation 470/22 nm, 495 nm dichroic, emission 510/42 nm; cat. no. ZP-EPI-9002) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C11 — Two related spinning-disk systems in the same section

```text
Light Microscopy Methods:

system A

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 488 nm laser (3i LaserStack v4). The light path included a Quad-band Dichroic (440/25, 521/25, 607/25, 700/25 nm; cat. no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and a GFP emission bandpass filter (525/50 nm) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (3i LaserStack v4) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]

system B

Spinning-disk confocal imaging was performed using the 3i Marianas CSU-W1 Spinning Disk Med C (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 NA Oil, 420780-9900-000). Instrument control and image acquisition were performed using SlideBook (v6).

Excitation was provided by a 488 nm laser (3i LaserStack v4). The light path included a 525/30 nm emission bandpass filter (cat. no. FF01-525/30-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Prime BSI.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (3i LaserStack v4) is reported with a 525/30 nm emission bandpass filter (cat. no. FF01-525/30-25), which the record says does not pass that wavelength; confirm the illumination and the filter used]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C12 — Same microscope and method, two channels acquired for two figures

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Figure 5

Spinning-disk confocal imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by a 476 nm laser (Lumencor Celesta 7ch). The light path included a Celesta-DA/FI/TR/Cy5/Cy7-A excitation multi-bandpass filter (391/54.4, 477/20.4, 549/25.7, 638.5/27.6, 741/45.1 nm; cat. no. MXR00543) in the Crest Excitation Wheel. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: which position of the Crest Dichroic Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]

Figure 6

Spinning-disk confocal imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Instrument control and image acquisition were performed using NIS-Elements AR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: which position of the Crest Excitation Wheel and Crest Dichroic Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C13 — Transmitted light and fluorescence on the same benchtop confocal

```text
Light Microscopy Methods:

brightfield

Transmitted-light brightfield imaging was performed using the Andor BC43 Benchtop Confocal. Imaging was performed with a 20x/0.8 Air objective (Nikon 20X Plan Apo LD Air, INS-OBJ-20D-080). Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Transmitted-light illumination was provided by an LED (Andor Transmitted Light Illuminator). Images were recorded using Andor 4.1 MP sCMOS.

confocal

Spinning-disk confocal imaging was performed using the Andor BC43 Benchtop Confocal. Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).

Illumination was provided by a 488 nm laser (Andor Borealis Illumination). The light path included a GFP emission bandpass filter (525/50 nm) in the BC43 Internal Emission Filters.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (Andor Borealis Illumination) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 488 nm laser (Andor Borealis Illumination) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## C14 — Light sheet plus confocal validation on two instruments

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.` → `Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution.` (0.637)

```text
Light Microscopy Methods:

light sheet

Light-sheet imaging was performed using the MSquared Aurora Airy Beam. Imaging was performed with a 17x/0.4 Multi-Immersion objective (Special Optics 54-10-12 Airy beam dipping objective, 54-10-12). Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution. Instrument control and image acquisition were performed using M Squared Cubes Acquisition.

Illumination was provided by a 488 nm laser (Coherent OBIS laser). The light path included a GFP filter (520/40 nm) in the Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0 V3 (C11440-22CU).

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of M Squared Cubes Deconvolution used]
- [PLEASE SPECIFY: the version of M Squared Cubes Acquisition]
- [PLEASE VERIFY: 488 nm laser (Coherent OBIS laser) is reported with a GFP filter (520/40 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 488 nm laser (Coherent OBIS laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D01 — Clear all: does the checkbox state reset?

```text
Select an instrument, then choose “Add to methods”.
```

## D02 — Clear all, untick the old objective, then build a new acquisition

```text
Light Microscopy Methods:

Transmitted-light brightfield imaging was performed using the Olympus BX60 (Olympus/Evident BX60), an upright microscope. Imaging was performed with a 4x/0.1 Air objective (Olympus PlanC 4x/0.10). Instrument control and image acquisition were performed using Olympus Cell^D.

Transmitted-light illumination was provided by a halogen lamp (Olympus 12V 100W halogen bulb). Images were recorded using Olympus DP71.

Review before publication:
- [PLEASE SPECIFY: the version of Olympus Cell^D]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D03 — Two acquisitions on one instrument where the second forgets the objective

```text
Light Microscopy Methods:

TIRF

Total internal reflection fluorescence (TIRF) imaging was performed using the Zeiss TIRF, an inverted microscope. Imaging was performed with a 100x/1.46 Oil objective (Zeiss Alpha Plan Apochromat).

Illumination was provided by a 488 nm laser. The light path included a Filter set 38 HE (GFP) (excitation 470/40 nm, 495 nm dichroic, emission 525/50 nm; cat. no. 38 HE) in the Filter Turret. Images were recorded using Hamamatsu C9100-13.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]

brightfield

Transmitted-light brightfield imaging was performed using the Zeiss TIRF, an inverted microscope.

Transmitted-light illumination was provided by a halogen lamp (Zeiss Transmitted Halogen Lamp). Images were recorded using Hamamatsu ORCA-Flash4.0 CMOS.

Review before publication:
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D04 — Abberior: RESOLFT after configuring STED (readout of stale state)

```text
Light Microscopy Methods:

RESOLFT imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 485 nm laser (PicoQuant LDH-D-C-485). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting the on/off switching wavelengths and illumination doses, the switching cycle timing, and the number of switching cycles per pixel. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 485 nm laser (PicoQuant LDH-D-C-485) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 525/25 nm emission bandpass filter (Semrock; cat. no. FF01-525/25), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D05 — Lambert FLIM: tick FLIM readout, then untick it and generate

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Lambert FLIM (Lambert Instruments LIFA (frequency domain FLIM)), an inverted microscope, with FLIM data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan APOCHROMAT 63x/1.4 Oil, 420780-9900).

Illumination was provided by a 469 nm LED (Multi-LED excitation). Images were recorded using Lambert Instruments LIFA Camera.

Review before publication:
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: the role of 469 nm LED (Multi-LED excitation) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: Detector pixel pitch (um) is not recorded for this instrument; confirm the exact values with facility staff]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D06 — Zeiss AxioZoom: reflected then transmitted brightfield in one section

```text
Light Microscopy Methods:

reflected

Reflected-light brightfield imaging was performed using the Zeiss AxioZoom.V16, a stereo microscope. Imaging was performed with a 0.5x/0.125 Air objective (Zeiss PlanApo Z). Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Reflected-light illumination was provided by an LED (Zeiss CL 9000 LED CAN ring light). Images were recorded using Zeiss AxioCam 105 Color.

Review before publication:
- [PLEASE SPECIFY: the version of Zeiss ZEN Pro]

transmitted

Transmitted-light brightfield imaging was performed using the Zeiss AxioZoom.V16, a stereo microscope. Instrument control and image acquisition were performed using Zeiss ZEN Pro.

Transmitted-light illumination was provided by an LED (VisiLED MC1000 LED base light).

Review before publication:
- [PLEASE SPECIFY: the version of Zeiss ZEN Pro]
- [PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]

Review before publication — applies to every acquisition above:
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D07 — STELLARIS: spectral plus FLIM plus FCS readouts on one acquisition

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using LAS X STELLARIS Control Soft` → `Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.` (0.96)

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Leica STELLARIS 8 FALCON FLIM (Leica Microsystems STELLARIS 8 FALCON), an inverted microscope, with spectral imaging, FLIM, FCS, and FRET data acquired on the same light path. Imaging was performed with a 63x/1.4 Oil objective (Leica Microsystems HC PL APO 63x/1.40 OIL CS2, 15506350). Instrument control and image acquisition were performed using LAS X STELLARIS Control Software.

Illumination was provided by a white light laser (Leica Microsystems STELLARIS White Light Laser). Images were recorded using Leica Microsystems Power HyD S SP pos 1.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]
- [PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]
- [PLEASE SPECIFY: FCS measurement duration, number of repeats, how the confocal volume was calibrated, and the fitting model]
- [PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]
- [PLEASE SPECIFY: the version of LAS X STELLARIS Control Software]
- [PLEASE SPECIFY: wavelength used from the recorded 440-790 nm tunable range of white light laser (Leica Microsystems STELLARIS White Light Laser)]
- [PLEASE SPECIFY: the role of white light laser (Leica Microsystems STELLARIS White Light Laser) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D08 — Deltavision: SMLM then switch to SIM keeping nothing

```text
Light Microscopy Methods:

Structured illumination microscopy (SIM) was performed using the Deltavision OMX (GE Healthcare OMX V4), an inverted microscope. Imaging was performed with a 60x/1.49 Oil objective (Olympus APO N TIRF). Instrument control and image acquisition were performed using OMX Acquisition (v3.70).

Excitation was provided by a 642 nm laser (GE Healthcare). The light path included a Cy5 emission bandpass filter (683/40 nm) in the OMX Emission Filters. Images were recorded using PCO Edge.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting SIM pattern/orientation settings and the reconstruction software/version and parameters used. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 642 nm laser (GE Healthcare) is reported with a Cy5 emission bandpass filter (683/40 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D09 — Zeiss LSM 880: ISM with a PMT detector selected as well

**EXECUTION ERROR:** `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']`

```text
Select an instrument, then choose “Add to methods”.
```

## D10 — 3i CSU-W1: FRAP module on a spinning-disk acquisition

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Zeiss Plan-Apochromat 63x/1.4 Oil DIC M27, 420782-9900). The FRAP Module (3i Vector) was used. Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 488 nm laser (3i LaserStack v4). The light path included a Quad-band Dichroic (440/25, 521/25, 607/25, 700/25 nm; cat. no. Di01-T405/488/568/647) in the CSU-W1 Dichroic Slider and a GFP emission bandpass filter (525/50 nm) in the CSU-W1 Emission Wheel. Images were recorded using Hamamatsu ORCA-Flash4.0.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 488 nm laser (3i LaserStack v4) is reported with a GFP emission bandpass filter (525/50 nm), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D11 — 3i CSU-W1: NIR imaging with the 730 nm laser and Alexa 750 emitter

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the 3i CSU-W1 Spinning Disk (3i / Zeiss Marianas CSU-W1 Spinning Disk Confocal), an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Zeiss Plan-Apochromat 100x/1.4 Oil DIC M27, 420792-9901). Instrument control and image acquisition were performed using 3i SlideBook (v6).

Excitation was provided by a 730 nm laser (3i SingleLine 730nm Laser Launch). The light path included an NIR dichroic in the CSU-W1 Dichroic Slider and an Alexa 750 emission bandpass filter (809/81 nm; cat. no. FF02-809/81-25) in the CSU-W1 Emission Wheel. Images were recorded using Photometrics Evolve.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE VERIFY: 730 nm laser (3i SingleLine 730nm Laser Launch) is reported with an Alexa 750 emission bandpass filter (809/81 nm; cat. no. FF02-809/81-25), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D12 — Leica Thunder: full eight-LED source selection

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the Leica Thunder, an inverted microscope. Imaging was performed with a 63x/1.4 Oil objective (Leica HC PL APO 63x/1.40 OIL CS2, 11506350). Instrument control and image acquisition were performed using LAS X with Navigator.

Illumination was provided by a 395 nm LED (Leica LED 8), a 475 nm LED (Leica LED 8), a 555 nm LED (Leica LED 8), and a 635 nm LED (Leica LED 8). The light path included a CYR71010 filter cube (cat. no. 11525416) in the Filter Turret. Images were recorded using Leica K8.

Review before publication:
- [PLEASE SPECIFY: the version of LAS X with Navigator]
- [PLEASE VERIFY: the recorded transmission bands for CYR71010 are incomplete; confirm its excitation filter, dichroic and emission filter]
- [PLEASE SPECIFY: the role of 395 nm LED (Leica LED 8), 475 nm LED (Leica LED 8), 555 nm LED (Leica LED 8), and 635 nm LED (Leica LED 8) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for these sources]
- [PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]
- [PLEASE SPECIFY: which position of the Standalone Emission Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D13 — Abberior: RESCue STED illumination control selected

```text
Light Microscopy Methods:

Stimulated emission depletion (STED) imaging was performed using the Abberior STED, an inverted microscope. Imaging was performed with a 100x/1.4 Oil objective (Olympus UPlanSApo 100x/1.40 Oil, 1-U2B836). The RESCue STED module (Abberior) was used. Instrument control and image acquisition were performed using Abberior Imspector.

Excitation was provided by a 640 nm laser (PicoQuant LDH-D-C-640). Depletion was provided by a 775 nm laser (OneFive / NKT Photonics Katana HP 775). The light path included a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35) in the Emission Filter Wheel. Images were recorded using Excelitas Technologies SPCM-AQRH-14-TR.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of Abberior Imspector]
- [PLEASE VERIFY: 640 nm laser (PicoQuant LDH-D-C-640) and 775 nm laser (OneFive / NKT Photonics Katana HP 775) are reported with a 685/35 nm emission bandpass filter (Chroma; cat. no. ET685/35), which the record says does not pass those wavelengths; confirm the illumination and the filter used]
- [PLEASE VERIFY: no filters, dichroics or splitters are recorded on the light path being reported; report each optical element (manufacturer + model/catalog number) used for acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D14 — Nikon Crest V3: single camera with the dual-camera splitter still ticked

**Fuzzy control resolutions:**

- `tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` → `Post-acquisition processing and analysis were performed using NIS-Elements AR.` (0.654)

```text
Light Microscopy Methods:

Spinning-disk confocal imaging was performed using the Nikon Ti2-E Crest V3 (Nikon / CrestOptics Eclipse Ti2-E with X-Light V3 HTDS), an inverted microscope. Imaging was performed with a 60x/1.3 Silicone objective (Nikon CFI Plan Apochromat Lambda S 60XC Sil DIC N2, MRD73600). Post-acquisition processing and analysis were performed using NIS-Elements AR. Instrument control and image acquisition were performed using NIS-Elements AR.

Illumination was provided by a 476 nm laser (Lumencor Celesta 7ch). Light was directed through MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set. Images were recorded using Photometrics Kinetix.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice). These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: the version of NIS-Elements AR used]
- [PLEASE SPECIFY: the version of NIS-Elements AR]
- [PLEASE SPECIFY: the role of 476 nm laser (Lumencor Celesta 7ch) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE VERIFY: MXR00547 V3 DualCam-GFP/mCherry 2 Bands Celesta Set is reported and the record says it feeds 2 branches at once, but only one detector is reported; confirm which branches were recorded and which detector each one reached]
- [PLEASE SPECIFY: which position of the Crest Excitation Wheel and Crest Dichroic Wheel was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D15 — Zeiss LSM 510: confocal acquisition with the AFM but no detector ticked

```text
Light Microscopy Methods:

Point-scanning confocal imaging was performed using the Zeiss LSM 510 JPK AFM, an inverted microscope. Imaging was performed with a 10x/0.3 Air objective. The AFM Module (JPK NanoWizard I with CellHesion) was used.

Illumination was provided by a 488 nm laser.

Review before publication:
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]
- [PLEASE SPECIFY: manufacturer and model of the Placeholder 10x/0.3 AIR]
- [PLEASE SPECIFY: the role of 488 nm laser in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

## D16 — EVOS: fluorescence where the user picks a cube that does not match the LED

```text
Light Microscopy Methods:

Widefield fluorescence imaging was performed using the EVOS fl (Thermo Fisher / AMG FL), an inverted microscope. Imaging was performed with a 20x/0.45 Air objective (AMG (Thermo Fisher) Plan Fluor 20x/0.45, AMG-AMEP 4624). Instrument control and image acquisition were performed using On-board EVOS interface.

Illumination was provided by a 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED). The light path included a Cy5/Alexa 647 filter cube (excitation 628/40 nm, 660 nm dichroic, emission 692/40 nm; cat. no. AMEP-4656) in the Light Cube Turret. Images were recorded using AMG (Thermo Fisher) AMF-4302 (Sony ICX285AL Monochrome CCD).

Review before publication:
- [PLEASE SPECIFY: the version of On-board EVOS interface]
- [PLEASE VERIFY: 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) is reported with a Cy5/Alexa 647 filter cube (excitation 628/40 nm, 660 nm dichroic, emission 692/40 nm; cat. no. AMEP-4656), which the record says does not pass that wavelength; confirm the illumination and the filter used]
- [PLEASE SPECIFY: the role of 470 nm LED (Thermo Fisher / AMG EVOS GFP Light Cube LED) in this acquisition (for example excitation or, on a depletion-based system, depletion); it is not recorded for this source]
- [PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)]
- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting acquisition software/version (if applicable), exposure time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable. These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.]

Acknowledgements:

Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.
```

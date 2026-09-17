# Full Methods Generator audit — current main

Pinned product commit: `68efc3041ae8ddf314c1d1c574aed6d7a48bb598`

## Execution integrity

- Historical scenarios recovered: **116**
- Historical replay process exit code: **2**
- Browser/execution-error scenarios: **13**
- Low-confidence control mappings (<0.90): **8**
- Acquisition software selected by default is **accepted as desired behavior** and is not classified as a defect.

### Browser/execution errors

- `A15`: `RuntimeError: Control not found in 'Filters and dichroics': 'mCherry'; best=[(0.21621621621621623, {'id': 'filter-1', 'value': 'optical_path_element:bc43_internal_emission_filters', 'checked': False, 'disabled': False, 'visible': True, 'category': 'filter', 'label': 'BC43 Internal Emission Filters'}), (0.20689655172413793, {'id': 'filter-0', 'value': 'optical_path_element:bc43_internal_dichroic', 'checked': False, 'disabled': False, 'visible': True, 'category': 'filter', 'label': 'BC43 Internal Dichroic'})]; available=['BC43 Internal Dichroic', 'BC43 Internal Emission Filters']` page=[] console=[]
- `A37`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolutio'; best=[(0.3723404255319149, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.']` page=[] console=[]
- `A45`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']` page=[] console=[]
- `A46`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']` page=[] console=[]
- `A47`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']` page=[] console=[]
- `A53`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `A54`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `A55`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `B22`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `C05`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using NimOS microscope control sof'; best=[(0.5028571428571429, {'id': 'confirmed-3', 'value': 'action-processing-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Post-acquisition processing and analysis were performed using CODI analysis software.'}), (0.43617021276595747, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.4025974025974026, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using an ONI Closed-loop Piezo XYZ Stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.', 'Post-acquisition processing and analysis were performed using CODI analysis software.']` page=[] console=[]
- `C08`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `C14`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]
- `D09`: `RuntimeError: Control not found in 'Confirmed acquisition actions': 'Instrument control and image acquisition were performed using Zeiss ZEN 2.3 SP1 (black edi'; best=[(0.4148936170212766, {'id': 'confirmed-0', 'value': 'action-0', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.'}), (0.41134751773049644, {'id': 'confirmed-1', 'value': 'action-1', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Z-stacks were acquired using a Zeiss Piezo Z-stage.'}), (0.24691358024691357, {'id': 'confirmed-2', 'value': 'action-2', 'checked': False, 'disabled': False, 'visible': True, 'category': 'confirmed', 'label': 'Focal drift was minimized using an Infrared Reflection Autofocus system.'})]; available=['Live-cell imaging was performed using an environmental chamber maintaining controlled temperature.', 'Z-stacks were acquired using a Zeiss Piezo Z-stage.', 'Focal drift was minimized using an Infrared Reflection Autofocus system.']` page=[] console=[]

### Low-confidence mappings

- `A37` score=0.637 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.` resolved=`Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution.`
- `A38` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`
- `A39` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`
- `A40` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`
- `B08` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`
- `C12` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`
- `C14` score=0.637 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using M Squared Cubes Acquisition.` resolved=`Post-acquisition processing and analysis were performed using M Squared Cubes Deconvolution.`
- `D14` score=0.654 action=`tick: Confirmed acquisition actions :: Instrument control and image acquisition were performed using NIS-Elements AR.` resolved=`Post-acquisition processing and analysis were performed using NIS-Elements AR.`

## Automated adversarial pattern scan

- implementation vocabulary: **0** hit(s): `[]`
- placeholder hardware in finished prose: **0** hit(s): `[]`
- BC43 fluorescence filter on brightfield: **1** hit(s): `['C13']`
- STED module asserted outside STED: **0** hit(s): `[]`
- Airyscan module asserted in plain confocal: **0** hit(s): `[]`
- EVOS 470nm with Cy5 cube: **1** hit(s): `['D16']`
- duplicate exact review line: **0** hit(s): `[]`

## Focus-scenario generated text

### A03

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

### A08

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

### A09

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

### A10

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

### A14

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

### A15

```text
Select an instrument, then choose “Add to methods”.
```

### A24

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

### A27

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

### A34

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

### A38

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

### A51

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

### A53

```text
Select an instrument, then choose “Add to methods”.
```

### A60

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

### B01

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

### B09

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

### B10

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

### B11

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

### B12

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

### B17

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

### B20

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

### B21

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

### B22

```text
Select an instrument, then choose “Add to methods”.
```

### B23

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

### B25

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

### C01

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

### C02

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

### C05

```text
Select an instrument, then choose “Add to methods”.
```

### C06

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

### C08

```text
Select an instrument, then choose “Add to methods”.
```

### C11

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

### C13

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

### D01

```text
Select an instrument, then choose “Add to methods”.
```

### D04

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

### D06

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

### D08

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

### D09

```text
Select an instrument, then choose “Add to methods”.
```

### D13

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

### D14

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

### D15

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

### D16

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


## All 116 scenario outputs

See `methods-116-main.md` in this output branch.
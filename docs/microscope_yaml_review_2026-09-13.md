# Microscope YAML review and evidence register

Reviewed 13 September 2026 against `f605168ef38c4970fd7647dd6a73a84d8f34a42a`. Scope: **all 24 instrument YAML files: 22 active instruments, the retired SP5 and the retired synthetic Test Scope X1**. This is a source/metadata review, not physical inspection or certification of the simulator.

The review covers instrument identity/location, software, objectives, sources, detectors, optical components, route connectivity, branches and contradictions between notes and structured fields. Optional blank URLs, unknown measured transmission curves and experiment-specific settings are not automatically treated as inventory defects. Missing local facts remain unknown.

## Evidence-backed corrections

| Instrument | Proposed correction | Evidence and boundary |
|---|---|---|
| Nikon Eclipse Ti2-E | Correct ORCA-Flash4.0 V3 native array from 2048 x 2044 to 2048 x 2048 | Exact already-recorded model; Hamamatsu [S1]. Not a session ROI. |
| Olympus BX60 | Set DP71 native effective array to 1360 x 1024; retain 4080 x 3072 as pixel-shift output | Olympus [S2], consistent with existing pixel-shift notes. |
| Aurora Airy Beam | Convert 500 and 570 nm longpass cut-ons from one-element lists to scalars | Exact existing values; encoding correction, not new hardware. |
| BioCity CSU-W1 | Replace false empty classification of installed NIR dichroic | Existing notes identify an installed dichroic. Spectra and part number remain unknown/unsupported. |
| Med C CSU-W1 | Identify three named widefield cubes and structure existing emission bands | Existing product IDs and values only. Excitation/dichroic gaps remain open. |
| Leica Thunder | Structure the existing excitation/emission values of CYR71010 and DFT51010 | Existing notes only. Do not invent multiband dichroic windows from cutoff lists. |
| Zeiss TIRF | Complete nominal EX/DI/EM for standard filter sets 38 HE and 43 HE | Exact set identifiers and matching EX/EM already recorded; ZEISS [S3] confirms FT495/FT570. Nominal, not measured curves. |
| eSight | Structure three existing emission bands | LED excitation ranges do not establish separate excitation-filter specifications. EX/DI remain unknown. |

### Primary sources

- **S1:** Hamamatsu ORCA-Flash4.0 V3 C13440-20CU, effective pixels 2048 x 2048: <https://www.hamamatsu.com/us/en/product/cameras/cmos-cameras/C13440-20CU.html>
- **S2:** Olympus DP71 announcement, 27 April 2006, native/live 1360 x 1024 versus pixel-shift output 4080 x 3072: <https://www.olympus.co.jp/jp/news/2006a/nr060427dp71j.html>
- **S3:** ZEISS catalogue: 38 HE (489038-9901-000), EX470/40 FT495 EM525/50; 43 HE (489043-9901-000), EX550/25 FT570 EM605/70: <https://www.micro-shop.zeiss.com/fr/ch/system/axio%2Bobserver-axio%2Bobserver%2B7-microscopes/10303/>

Sources checked 13 September 2026. Manufacturer specifications do not prove an undocumented component is installed locally or provide measured local transmission.

## Complete instrument coverage

The numbered entries correspond to [the copy-ready Slack messages](slack_microscope_questions_2026-09-13.md). No messages have been posted. Keep replies and supporting documents linked to the affected YAML fields. Ask when configuration changes took effect separately from when records were entered in Git.

### 1. 3i CSU-W1 Spinning Disk

ID: `scope-3i-csu-w1-spinning-disk`. File: `instruments/3i CSU-W1 Spinning Disk.yaml`.

High priority: NIR dichroic was falsely encoded as empty; part number/spectra and IR/VIS combining optics are missing. Transmitted-light route has no source. Some quad-band values disagree with Med C. Vector FRAP has no separately documented optical configuration. Ask for exact optics, lamp, XLED1 modules and dated filter changes. SlideBook 6, main objectives and location are already recorded.

### 2. 3i Marianas CSU-W1 Spinning Disk Med C

ID: `scope-3i-csu-w1-spinning-disk-med-c`. File: `instruments/3i CSU-W1 Spinning Disk Med C.yaml`.

High priority: three widefield cubes lacked component types and structured internals; emission values are known but excitation/dichroic details remain absent. Transmitted-light source and ASI stage/piezo models are missing. Reconcile quad-band data with the BioCity system using original data sheets. SlideBook 6 and room C242 are recorded; a broadband source does not need an invented single wavelength.

### 3. Abberior STED

ID: `scope-1e33f909`. File: `instruments/Abberior STED.yaml`.

High priority: Imspector version, exact camera/PMT/APD identities and complete excitation/depletion routing are missing. Notes mention two APDs but only one APD record is present. Confirm confocal/STED/RESOLFT configurations and whether gating numbers are examples or documented defaults. Installed depletion hardware does not establish that a particular experiment used STED.

### 4. Andor BC43 Benchtop Confocal

ID: `scope-andor-bc43`. File: `instruments/Andor BC43 Benchtop Confocal.yaml`.

High priority: Imaris version is missing. Brightfield uses fluorescence optics in the recorded route without a documented bypass; internal filter/dichroic identities need evidence. Confirm DPC versus conventional phase contrast and the recorded 50 micrometre pinhole. FusionBC43 2.7.0 is already recorded.

### 5. Deltavision OMX

ID: `scope-deltavision-omx`. File: `instruments/Deltavision OMX.yaml`.

High priority: softWoRx is only specified as 6.0 or newer. Camera native size may be confused with an acquisition region. Three cameras are represented as exclusive alternatives although channel-specific simultaneous operation needs confirmation. Ask about camera models, splitters and mode changes for widefield/SIM/TIRF. Acquisition software 3.70 is recorded.

### 6. EVOS fl

ID: `scope-evos-fl`. File: `instruments/EVOS fl.yaml`.

Routine: onboard software/firmware version and exact room are missing. Confirm which of the five cubes are installed versus stored for staff swaps. Their excitation, dichroic and emission specifications are present; do not ask staff to re-enter them or invent external software.

### 7. Lambert FLIM

ID: `scope-lambert-flim-frequency-domain`. File: `instruments/Lambert FLIM.yaml`.

High priority: software is Unknown; camera identity is explicitly assumed. The stand description combines inverted with AxioImager and needs clarification. No excitation filters, dichroics or emission filters are recorded. Identify the actual stand, camera, LIFA/modulation unit and frequency capabilities before using this record as verified methods metadata.

### 8. Leica DM IRBE

ID: `scope-leica-dm-irbe`. File: `instruments/Leica DM IRBE.yaml`.

Medium priority: standalone USB camera is Unknown; its CCD classification, sensor dimensions and pitch require a model. Camera-adapter magnification and interaction with the 1.6x auxiliary lens are unclear. Objective working distances and condenser/contrast accessories need documentation. No external acquisition software is currently claimed; lamp and cubes are specified.

### 9. Leica DM RB

ID: `scope-leica-dm-rb`. File: `instruments/Leica DM RB.yaml`.

Medium priority: an Unknown CCD conflicts with an optional-camera-port description. First establish whether a camera exists, then identify its model, adapter and acquisition interface. Objective working distances and contrast accessories remain incompletely documented. A camera port alone is not a camera.

### 10. Leica DM RE

ID: `scope-leica-dmre`. File: `instruments/Leica DMRE.yaml`.

Medium priority: Unknown CCD versus optional port needs clarification. DIC/phase-contrast capabilities need the actual condenser, prisms, polariser/analyser and compatible objectives. Working distances are missing. This is a transmitted-light instrument: missing fluorescence lasers/cubes are not a defect to fill.

### 11. Leica STELLARIS 8 FALCON FLIM

ID: `scope-leica-stellaris-8-falcon-flim-resonant`. File: `instruments/Leica STELLARIS 8 FALCON FLIM.yaml`.

High priority: LAS X/module versions, actual transmitted-light source, LED3 channels and locally verified observation-cube labels are needed. Obtain routing evidence for spectral detectors, BF PMT, K5 and eyepieces. Five HyD identities, WLL range and scanner are already documented. AOBS/prism models are developer work, not a reason to request an invented fixed dichroic. The BF detector QE is explicitly a placeholder, not a measurement.

### 12. Leica Thunder

ID: `scope-leica-thunder`. File: `instruments/Leica Thunder.yaml`.

High priority: location, LAS X version and transmitted-light source are missing. Two quad-band cubes remain incomplete after structuring their known EX/EM values because dichroic windows are unknown. Clarify emission-wheel placement, K8/K3C/eyepiece switching and actual incubation controllers.

### 13. MSquared Aurora Airy Beam

ID: `scope-msquared-aurora-airy-beam`. File: `instruments/MSquared Aurora Airy Beam.yaml`.

High priority: Cubes versions are missing; camera name V3 conflicts with C11440-22CU. One objective row combines illumination/detection roles. Clarify actual separate objectives, beam layout and heating equipment. A safety enclosure does not prove temperature control. Fixing scalar cut-on encoding does not resolve these local facts; do not force an epi-fluorescence layout onto light-sheet optics.

### 14. Nikon Eclipse Ti2-E

ID: `scope-nikon-eclipse-ti2-e`. File: `instruments/Nikon Eclipse Ti2-E.yaml`.

High priority: location is missing; five cubes are collapsed into Standard Cubes. Cube/dichroic/emission-wheel topology and Cy7 filter placement need confirmation. Ask which channels/objectives are installed, where DIC optics sit, and which equipment controls CO2/humidity. NIS-Elements AR 6.1 is recorded; native ORCA dimensions are corrected from the exact model specification.

### 15. Nikon Ti2-E Crest V3

ID: `scope-nikon-crest-v3`. File: `instruments/Nikon Ti2-E Crest V3 Spinning Disk.yaml`.

High priority: NIS-Elements versions are missing. Dual-camera splitting conflicts with exclusive route branches. MXR00545 has no spectra or route reference; MXR00547 has cutoff values without full windows. NIR/PFS bypass is only a note and NIR wavelengths conflict. Both cameras have distinct IDs. The ND position already says 5% transmission; its missing attenuation behaviour is a model defect.

### 16. ONI Nanoimager

ID: `scope-oni-nanoimager`. File: `instruments/ONI Nanoimager.yaml`.

High priority: location and NimOS/CODI versions are missing. The split image reaches one physical camera; branch spectra and laser-rejection optics are absent. Confirm illumination modes and suspicious 20/20/10 mm piezo travel units. Do not invent a second camera for the second image half.

### 17. Olympus BX60

ID: `scope-olympus-bx60`. File: `instruments/Olympus BX60.yaml`.

Medium priority: location and Cell^D version are missing. Confirm optional narrow GFP cube/60x objective availability, working distance and phase condenser configuration. Main fluorescence cubes and lamps are documented. The DP71 sensor-versus-pixel-shift-output error is corrected with manufacturer evidence.

### 18. Zeiss AxioZoom.V16

ID: `scope-zeiss-axiozoom-v16`. File: `instruments/Zeiss AxioZoom V16.yaml`.

High priority: ZEN Pro version and cube internals are missing. Confirm whether the named filters are stereo/Lumar assemblies or standard reflector cubes before borrowing catalogue internals. Reflected-light ring LED has no route. Clarify camera/eyepiece switching and ApoTome configuration. G365 glass is not an invented narrow bandpass.

### 19. Zeiss LSM 510 JPK AFM

ID: `scope-zeiss-lsm-510-jpk-afm`. File: `instruments/Zeiss LSM 510 JPK AFM.yaml`.

High priority: the 488 nm laser, 10x/0.3 objective and Unknown PMT are explicitly placeholders. Software is Unknown. Confocal optics are missing and transmitted sequences are empty. Ask for the actual software, lasers, objectives, detectors, complete paths, AFM module and temperature-controller identities. Do not treat a generic LSM510 brochure as proof of the local installation.

### 20. Zeiss LSM 880 with AiryScan

ID: `scope-zeiss-lsm-880-with-airyscan`. File: `instruments/Zeiss LSM 880 with AiryScan.yaml`.

High priority: spectral/Airyscan detectors and the Airyscan wheel are inventoried but disconnected from canonical routes. Main beam separation/routing is incomplete. Confirm the recorded 8 kHz resonant scanner, installed lasers and HAL100/LED ambiguity. ZEN 2.3 SP1 black build 14.0.30.201 / FP3 HF30 is already recorded. Existing BP-plus-LP thresholds require parser work rather than staff reinvention.

### 21. Zeiss TIRF

ID: `scope-zeiss-tirf`. File: `instruments/Zeiss TIRF.yaml`.

High priority: software identity/version are unknown. 76 HE/77 HE excitation widths and dichroic spectra remain absent. TIRF entry optics are not distinguished from widefield. Confirm some objective part numbers/working distances and the ORCA camera variant. This PR only completes the exact named 38 HE/43 HE standard sets; it does not infer a TIRF layout.

### 22. Agilent xCELLigence RTCA eSight

ID: `scope-agilent-rtca-esight`. File: `instruments/xCELLigence RTCA eSight.yaml`.

High priority: emission bands are known, but excitation-filter and dichroic identities are not. Camera is only Sony 5 MP CMOS; its pitch needs an exact model. Objective working distance and external incubator identity are missing. RTCA eSight 1.5.1 is recorded. Keep external incubation distinct from built-in hardware and LED ranges distinct from actual filter specifications.

### 23. Leica TCS SP5 Multiphoton (retired)

ID: `scope-leica-tcs-sp5-multiphoton`. File: `instruments/retired/Leica TCS SP5 Multiphoton.yaml`.

Historical priority: location/LAS AF version are absent. Two Chameleon models and an OPO may describe different periods, not concurrent installations. Legacy filter inventory is not connected to canonical detector paths. Request historical configurations, detector routing, scanner details and effective dates supported by service records. Git dates are not installation dates.

### 24. Test Scope X1 (synthetic)

ID: `scope-testx1`. File: `instruments/retired/Test_Scope_X1.yaml`.

Reviewed as test data only. Placeholder location, legacy detector/endpoint overlap and artificial optics belong to test maintenance. This fixture is deliberately excluded from staff messages.

## Implementation boundaries

Branch-generated splitter/audit-count mismatches, AOBS/spectral-slider support, combined BP-plus-LP modelling and neutral-density attenuation are developer issues. Do not ask staff to invent hardware to compensate for those defects. Once topology is confirmed, encode the actual simultaneous versus exclusive branching. Unreferenced inventory does not justify silently deleting a feature or guessing its physical path.

PR #430 has been merged into main. This data-review branch is based on that updated main and preserves its application fixes. The PR description records validation actually performed. Schema success does not prove complete optics. Intentionally incomplete cubes retain diagnostics. No historical installation dates or experiment-specific settings have been invented.

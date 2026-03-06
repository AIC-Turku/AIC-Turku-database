# LLM Microscopy Assistant Context

This page is generated from files under `vocab/`. Do not edit manually.

## System Prompt

> You are an expert bioimaging facility AI assistant. Your job is to help researchers map their experimental needs to the exact terminology used in our facility's database.

## Assistant Rules

- Always prefer canonical term IDs shown below when translating user intent.
- Explain recommendations in plain language, but include exact database IDs in backticks.
- If users provide ambiguous language, ask one clarifying question and still provide best-match IDs.
- Never invent IDs that are not listed in this document.

## Intent Mapping Guidance

- When a user asks for **"fast live cell"**, recommend `confocal_spinning_disk`. Use for low-phototoxicity, high-speed 3D imaging in living samples.
- When a user asks for **"deep tissue"**, recommend `multiphoton`. Prefer for deeper penetration and reduced out-of-plane photodamage.
- When a user asks for **"membrane events near coverslip"**, recommend `tirf`. Ideal for sub-200 nm interface processes such as membrane trafficking.
- When a user asks for **"highest spatial resolution"**, recommend `sted`. Recommend when users need sub-diffraction super-resolution and can tolerate specialized workflows.
- When a user asks for **"label-free live cell morphology"**, recommend `phase_contrast`. Best first choice for unlabeled transparent cells in routine culture vessels.

## Controlled Vocabulary (Canonical IDs)

### Modalities (`modalities`)

- **Atomic Force Microscopy**
  - ID: `afm`
  - Synonyms: `AFM`
  - Definition: Uses a nanoscale cantilever probe to measure topography and mechanical properties at high spatial resolution. Can be combined with optical microscopy workflows.
- **Darkfield**
  - ID: `darkfield`
  - Synonyms: `dark field`
  - Definition: Collects only scattered light while excluding directly transmitted illumination. Highlights small structures and edges on a dark background.
- **Differential Interference Contrast**
  - ID: `dic`
  - Synonyms: `DIC`, `nomarski`
  - Definition: Uses polarized beam shearing to create relief-like contrast from optical path gradients. Useful for high-contrast imaging of unstained live samples.
- **Fluorescence Correlation Spectroscopy**
  - ID: `fcs`
  - Synonyms: `FCS`
  - Definition: Analyzes fluorescence intensity fluctuations in a tiny observation volume. Used to estimate concentration, diffusion, and molecular kinetics.
- **Fluorescence Lifetime Imaging**
  - ID: `flim`
  - Synonyms: `FLIM`
  - Definition: Measures fluorescence decay timing rather than only intensity. Useful for environmental sensing and interaction readouts such as FRET changes.
- **Fluorescence Recovery After Photobleaching**
  - ID: `frap`
  - Synonyms: `FRAP`
  - Definition: Photobleaches a region and measures fluorescence recovery over time. Used to quantify mobility, exchange, and binding dynamics.
- **Förster Resonance Energy Transfer**
  - ID: `fret`
  - Synonyms: `FRET`
  - Definition: Measures non-radiative energy transfer between donor and acceptor fluorophores at nanometer distances. Used as a readout of molecular proximity or conformational change.
- **Image Scanning Microscopy**
  - ID: `ism`
  - Synonyms: `ISM`, `airyscan`
  - Definition: Uses detector array information in scanning microscopy to improve resolution and signal usage. Airyscan implementations are a common form.
- **Impedance Cytometry**
  - ID: `impedance_cytometry`
  - Synonyms: `electrical cytometry`
  - Definition: Measures electrical impedance changes as cells pass sensing regions to infer size and biophysical properties. Often used for label-free cell phenotyping.
- **Light Sheet**
  - ID: `light_sheet`
  - Synonyms: `SPIM`, `LSFM`
  - Definition: Illuminates samples with a thin sheet orthogonal to detection. Supports gentle, rapid volumetric imaging with reduced out-of-focus exposure.
- **Live Cell Imaging**
  - ID: `live_cell_imaging`
  - Synonyms: `live imaging`, `time-lapse live imaging`
  - Definition: Refers to imaging workflows optimized for viable cells over time with controlled environment and low phototoxicity. Can be combined with multiple optical modalities.
- **Multiphoton**
  - ID: `multiphoton`
  - Synonyms: `two-photon`, `2p`
  - Definition: Uses nonlinear excitation, typically with pulsed near-infrared lasers, to excite fluorophores only at the focal volume. Improves deep-tissue imaging and reduces out-of-plane photodamage.
- **Phase Contrast**
  - ID: `phase_contrast`
  - Synonyms: `phase`, `ph`
  - Definition: Converts phase shifts from transparent specimens into intensity differences. Useful for live, unlabeled cells on standard culture plastic.
- **Photoactivation**
  - ID: `photoactivation`
  - Synonyms: `pa`, `photo-activation`
  - Definition: Activates photoactivatable fluorophores in selected regions or times. Supports pulse-chase imaging, sparse labeling, and dynamic experiments.
- **Point-Scanning Confocal**
  - ID: `confocal_point`
  - Synonyms: `laser scanning confocal`, `lsm`
  - Definition: Scans a focused laser spot with a pinhole to reject out-of-focus light. Provides optical sectioning and improved contrast in thick specimens.
- **Polarized Light**
  - ID: `polarized_light`
  - Synonyms: `polarization`
  - Definition: Uses crossed polarizers to generate contrast from birefringent materials like crystals, amyloid fibrils, or muscle fibers.
- **RESOLFT**
  - ID: `resolft`
  - Synonyms: `RESOLFT`
  - Definition: Achieves super-resolution using reversibly switchable fluorophores and targeted on/off control. Often allows lower light intensities than depletion-based methods.
- **Second Harmonic Generation**
  - ID: `shg`
  - Synonyms: `SHG`, `THG`
  - Definition: Label-free multiphoton modality that generates signal from highly ordered, non-centrosymmetric structures like collagen fibers.
- **Single-Molecule Localization Microscopy**
  - ID: `smlm`
  - Synonyms: `SMLM`, `PALM/STORM`
  - Definition: Builds super-resolved images by localizing sparse single emitters over many frames. Includes methods such as PALM and STORM.
- **Single-Particle Tracking**
  - ID: `spt`
  - Synonyms: `SPT`, `single molecule tracking`
  - Definition: Tracks individual particles or molecules over time to quantify motion and dynamics. Used for diffusion, transport, and interaction studies.
- **Spectral Imaging**
  - ID: `spectral_imaging`
  - Synonyms: `lambda imaging`, `spectral detection`
  - Definition: Records fluorescence across wavelength bands rather than fixed channels. Enables unmixing of overlapping fluorophores and autofluorescence separation.
- **Spinning-Disk Confocal**
  - ID: `confocal_spinning_disk`
  - Synonyms: `SDC`, `spinning disk`
  - Definition: Uses a rotating pinhole disk to image many points in parallel. Enables fast, lower-phototoxicity 3D optical sectioning in live samples.
- **Stimulated Emission Depletion**
  - ID: `sted`
  - Synonyms: `STED`
  - Definition: Shrinks the effective fluorescence spot using a depletion beam around the excitation focus. Enables sub-diffraction super-resolution imaging.
- **Structured Illumination Microscopy**
  - ID: `sim`
  - Synonyms: `SIM`, `structured illumination`
  - Definition: Uses shifted illumination patterns and reconstruction to increase resolution and sectioning performance. Suitable for super-resolution with moderate light dose.
- **Structured Optical Sectioning**
  - ID: `optical_sectioning`
  - Synonyms: `apotome`, `grid projection`
  - Definition: Uses patterned illumination and computational processing to suppress out-of-focus signal. Common examples include ApoTome or grid-projection approaches.
- **Total Internal Reflection Fluorescence**
  - ID: `tirf`
  - Synonyms: `TIRF`
  - Definition: Excites fluorophores with an evanescent field near the coverslip interface. Ideal for membrane-proximal events within roughly the first 100–200 nm.
- **Transmitted Brightfield**
  - ID: `transmitted_brightfield`
  - Synonyms: `brightfield`, `bf`
  - Definition: Uses transmitted white light to image absorption and scattering contrast in unstained specimens. Common for routine morphology and context imaging.
- **Widefield Fluorescence**
  - ID: `widefield_fluorescence`
  - Synonyms: `epifluorescence`, `widefield epi`
  - Definition: Illuminates and captures fluorescence from the full field of view without optical sectioning. Best for fast imaging of bright samples and thin specimens.

### Objective Immersion (`objective_immersion`)

- **Air**
  - ID: `air`
  - Synonyms: `dry`
  - Definition: Objective is used without immersion liquid, with air between front lens and coverslip. Common for lower magnification or long working distance imaging.
- **Dipping**
  - ID: `dipping`
  - Synonyms: `water dipping`, `dipping objective`
  - Definition: Front lens is dipped directly into sample medium without coverslip contact. Common in electrophysiology and in vivo preparations.
- **Glycerol**
  - ID: `glycerol`
  - Synonyms: `glycerin`
  - Definition: Uses glycerol immersion to better match intermediate refractive indices. Useful for some cleared or thick biological specimens.
- **Multi-Immersion**
  - ID: `multi`
  - Synonyms: `multi immersion`
  - Definition: Objective is designed to operate with multiple immersion media, often with correction adjustments. Provides flexibility across sample types.
- **Oil**
  - ID: `oil`
  - Synonyms: `oil immersion`
  - Definition: Uses immersion oil to better match refractive index and increase numerical aperture. Common for high-resolution fluorescence objectives.
- **Silicone**
  - ID: `silicone`
  - Synonyms: `silicone oil`
  - Definition: Uses silicone oil immersion with refractive index close to tissue, improving deep imaging stability. Often used in live or thick sample imaging.
- **Water**
  - ID: `water`
  - Synonyms: `water immersion`
  - Definition: Uses water as immersion medium for improved index matching in aqueous samples. Useful for live-cell and deeper tissue imaging.

### Detectors (`detector_kinds`)

- **Avalanche Photodiode**
  - ID: `apd`
  - Synonyms: `APD`
  - Definition: Semiconductor point detector with internal gain and fast timing response. Used in photon counting and correlation-based measurements.
- **Charge-Coupled Device**
  - ID: `ccd`
  - Synonyms: `CCD`
  - Definition: Area detector technology with historically strong image quality and uniformity. Still used in some fluorescence and brightfield setups.
- **Electron-Multiplying CCD**
  - ID: `emccd`
  - Synonyms: `EMCCD`
  - Definition: CCD detector with on-chip gain for very low-light imaging. Useful for single-molecule and fast, dim signal applications.
- **GaAsP Photomultiplier Tube**
  - ID: `gaasp_pmt`
  - Synonyms: `GaAsP_PMT`, `gaasp detector`
  - Definition: PMT using gallium arsenide phosphide photocathodes with improved quantum efficiency over conventional PMTs. Useful for low-light confocal imaging.
- **Hybrid Detector**
  - ID: `hyd`
  - Synonyms: `HyD`, `hybrid pmt`
  - Definition: Combines features of PMTs and avalanche gain to provide high sensitivity and fast response. Frequently used in modern confocal systems.
- **Photomultiplier Tube**
  - ID: `pmt`
  - Synonyms: `PMT`
  - Definition: Highly sensitive point detector that amplifies photoelectrons through a dynode chain. Common in confocal detection paths.
- **Scientific CMOS**
  - ID: `scmos`
  - Synonyms: `sCMOS`
  - Definition: Low-noise, high-speed area detector with large field of view and high dynamic range. Common for widefield, spinning-disk, and fast live imaging.
- **SPAD Array**
  - ID: `spad`
  - Synonyms: none
  - Definition: Single-Photon Avalanche Diode array. Provides exceptional timing resolution and single-photon sensitivity, crucial for advanced FLIM.
- **Standard CMOS**
  - ID: `cmos`
  - Synonyms: none
  - Definition: Standard digital camera sensor. Commonly used in routine brightfield, color histology, or basic fluorescence.

### Scanner Types (`scanner_types`)

- **Acousto-Optic Scanner**
  - ID: `acousto_optic`
  - Synonyms: `AOD`, `acousto-optic deflector`
  - Definition: Deflects beams using acousto-optic elements for rapid, inertia-free positioning. Useful for fast random-access scanning patterns.
- **Galvanometric Scanner**
  - ID: `galvo`
  - Synonyms: `galvanometer`, `galvo mirrors`
  - Definition: Uses galvanometer mirrors to steer the excitation beam across the sample. Common in point-scanning confocal systems with flexible scan control.
- **No Scanner**
  - ID: `none`
  - Synonyms: `camera-based`
  - Definition: No dedicated beam scanner is used for image formation. Typical of camera-based widefield modalities.
- **Polygon Scanner**
  - ID: `polygon`
  - Synonyms: `polygon mirror`
  - Definition: Uses a rotating polygon mirror for rapid beam deflection. Often used in high-speed scanning implementations.
- **Resonant Scanner**
  - ID: `resonant`
  - Synonyms: `resonant galvo`
  - Definition: Uses a resonant oscillating mirror for very high line rates. Enables faster imaging than standard galvo scanning, often with reduced dwell time.
- **Spinning Disk Scanner**
  - ID: `spinning_disk`
  - Synonyms: `nipkow disk`, `sdc scanner`
  - Definition: Uses rotating pinhole disks to scan multiple points in parallel. Supports high-speed confocal imaging with lower phototoxicity.
- **Stage Scanning**
  - ID: `stage_scanning`
  - Synonyms: `sample scanning`
  - Definition: Forms images by moving the sample stage relative to fixed optics or beam position. Common in slide scanning and some large-area acquisitions.
- **Tandem Scanner (Galvo/Resonant)**
  - ID: `tandem`
  - Synonyms: `tandem`
  - Definition: Dual-mode scanning configuration that supports switching between galvanometric and resonant scanning behavior.

### Light Sources (`light_source_kinds`)

- **Arc Lamp**
  - ID: `arc_lamp`
  - Synonyms: `mercury lamp`, `xenon lamp`
  - Definition: Broad-spectrum lamp, such as mercury or xenon, used with filter sets for fluorescence excitation. Historically common on epifluorescence microscopes.
- **Halogen Lamp**
  - ID: `halogen_lamp`
  - Synonyms: `tungsten-halogen`, `quartz halogen`
  - Definition: Continuous-spectrum tungsten-halogen illumination, primarily for transmitted light imaging. Common for brightfield and contrast techniques.
- **Laser**
  - ID: `laser`
  - Synonyms: `single-line laser`
  - Definition: Provides coherent, narrowband excitation at specific wavelengths. Common for fluorescence imaging requiring high irradiance and precise line selection.
- **LED**
  - ID: `led`
  - Synonyms: `light-emitting diode`
  - Definition: Solid-state light source with stable output and fast switching. Widely used for widefield fluorescence and transmitted illumination.
- **Metal Halide Lamp**
  - ID: `metal_halide`
  - Synonyms: `hxp`, `x-cite`
  - Definition: Broad-spectrum lamp coupled via a liquid light guide. Provides intense, stable excitation for standard widefield fluorescence.
- **Pulsed Near-IR Laser**
  - ID: `multiphoton_laser`
  - Synonyms: `ti:sapphire`, `fs laser`
  - Definition: Femtosecond pulsed laser tunable in the near-infrared. Used for deep-tissue multiphoton excitation.
- **Supercontinuum Source**
  - ID: `supercontinuum`
  - Synonyms: `white supercontinuum laser`
  - Definition: Broadband laser-like source generated by nonlinear spectral broadening. Provides highly flexible, selectable excitation bands.
- **White Light Laser**
  - ID: `white_light_laser`
  - Synonyms: `WLL`, `tunable laser`
  - Definition: Broadband laser source with tunable output wavelengths selected by software or optics. Supports flexible excitation across many fluorophores.

### Modules (`modules`)

- **Adaptive Optics**
  - ID: `adaptive_optics`
  - Synonyms: `ao`
  - Definition: Corrects sample- or system-induced aberrations using deformable elements and feedback. Improves resolution and signal quality, especially in deep or heterogeneous samples.
- **FCS Module**
  - ID: `fcs`
  - Synonyms: `correlation module`
  - Definition: Instrumentation support for fluorescence fluctuation measurements and autocorrelation analysis. Enables diffusion and concentration quantification in tiny volumes.
- **FLIM Module**
  - ID: `flim`
  - Synonyms: `lifetime module`
  - Definition: Adds lifetime-resolved detection and analysis to fluorescence imaging. Enables contrast based on fluorophore decay kinetics.
- **FRAP Module**
  - ID: `frap`
  - Synonyms: `photobleach module`
  - Definition: Hardware or software capability to perform targeted photobleaching for recovery measurements. Typically controls ROI bleaching power and timing.
- **Hardware Autofocus**
  - ID: `hardware_autofocus`
  - Synonyms: `focus lock`, `z-drift compensation`
  - Definition: Active focus stabilization that compensates focus drift during acquisition. Common implementations include reflected-light focus locks such as Definite Focus or PFS.
- **Incubation**
  - ID: `incubation`
  - Synonyms: `environmental chamber`, `temp/co2 control`
  - Definition: Environmental control module for temperature, CO2, and often humidity around the specimen. Supports physiologic conditions during long-term live imaging.
- **Microfluidics / Perfusion**
  - ID: `microfluidics`
  - Synonyms: `perfusion pump`
  - Definition: Hardware for controlled delivery of media or drugs to the sample during live imaging.
- **Motorized Stage**
  - ID: `motorized_stage`
  - Synonyms: `multiposition`, `xy stage`
  - Definition: Automated XY stage enabling multi-position imaging, large-area tiling, and multi-well plate screening.
- **Optogenetics**
  - ID: `optogenetics`
  - Synonyms: `photo-stimulation`
  - Definition: Provides patterned or wavelength-specific stimulation for light-controlled biological perturbations. Used to control signaling or neural activity during imaging.
- **Photoactivation Module**
  - ID: `photoactivation`
  - Synonyms: `photo-manipulation`, `pa module`
  - Definition: Capability to activate or uncage photoresponsive probes in defined regions. Used for selective labeling and dynamic tracking experiments.

### Objective Corrections (`objective_corrections`)

- **Achromat**
  - ID: `achromat`
  - Synonyms: `achro`
  - Definition: Basic objective correction class with limited chromatic and spherical correction. Often used for standard, non-demanding imaging tasks.
- **Apochromat**
  - ID: `apochromat`
  - Synonyms: `apo`
  - Definition: Objective with strong chromatic and spherical aberration correction, typically over multiple colors. May not guarantee full field flatness.
- **Fluorite**
  - ID: `fluorite`
  - Synonyms: `semi-apo`, `fluor`
  - Definition: Objective class with improved color correction and transmission relative to basic achromats. Common compromise between performance and cost.
- **Plan Achromat**
  - ID: `plan_achromat`
  - Synonyms: `plan achro`
  - Definition: Objective with flat field correction and basic chromatic correction for two wavelengths. Suitable for routine brightfield and general imaging.
- **Plan Apochromat**
  - ID: `plan_apochromat`
  - Synonyms: `plan-apo`, `plan apo`, `super apochromat`, `uplsapo`
  - Definition: High-end objective with flat field correction and strong chromatic/spherical correction across wavelengths. Preferred for quantitative, multicolor imaging.
- **Plan Fluorite**
  - ID: `plan_fluorite`
  - Synonyms: `plan fluor`, `plan fluorite`
  - Definition: Objective with flat field correction and moderate-to-high aberration correction, typically between achromat and apochromat classes.

### Maintenance Reasons (`maintenance_reason`)

- **Check**
  - ID: `check`
  - Synonyms: `inspection`, `diagnostic`
  - Definition: Focused verification or inspection to confirm system status without major intervention. Includes diagnostic visits and quick health checks.
- **Install**
  - ID: `install`
  - Synonyms: `commissioning`, `setup`
  - Definition: Triggered by initial installation of a system, add-on module, or newly delivered component. Use for setup and commissioning events.
- **Other**
  - ID: `other`
  - Synonyms: `misc`
  - Definition: Reason does not fit the predefined categories. Document the rationale in free-text details.
- **Problem**
  - ID: `problem`
  - Synonyms: `issue`, `breakdown`
  - Definition: Triggered by a reported fault, performance issue, or unexpected behavior. Use when intervention is reactive to a defect.
- **Scheduled**
  - ID: `scheduled`
  - Synonyms: `preventive maintenance`, `pm`
  - Definition: Planned preventive maintenance performed at regular intervals. Includes routine service contracts and periodic inspections.
- **Upgrade**
  - ID: `upgrade`
  - Synonyms: `enhancement`
  - Definition: Initiated to improve capability, performance, or feature set beyond baseline operation. Can include hardware or software enhancement projects.

### Maintenance Actions (`maintenance_action`)

- **Align**
  - ID: `align`
  - Synonyms: `realignment`, `alignment`
  - Definition: Adjusts optical or mechanical alignment to restore expected performance. Typical examples include beam path or stage alignment.
- **Calibrate**
  - ID: `calibrate`
  - Synonyms: `calibration`
  - Definition: Performs calibration against known references to ensure accurate measurement or positioning. Use for intensity, stage, focus, or scaling calibration events.
- **Clean**
  - ID: `clean`
  - Synonyms: `cleaning`
  - Definition: Removes contamination from optics, mechanics, or enclosures to recover performance and reliability. Includes routine cleaning of lenses and filters.
- **Other**
  - ID: `other`
  - Synonyms: `misc`
  - Definition: Action does not match the predefined categories. Provide specific context in free-text details.
- **Repair**
  - ID: `repair`
  - Synonyms: `fix`
  - Definition: Fixes a confirmed fault or malfunction by restoring or replacing failing parts. Use when resolving a broken or degraded subsystem.
- **Replace**
  - ID: `replace`
  - Synonyms: `part replacement`
  - Definition: Substitutes a component with a new or refurbished part. Use when parts are worn, failed, or upgraded directly.
- **Service**
  - ID: `service`
  - Synonyms: `maintenance`
  - Definition: General maintenance intervention including inspection and routine adjustments. Used when work does not fit a more specific action type.
- **Update**
  - ID: `update`
  - Synonyms: `upgrade software`, `firmware update`
  - Definition: Applies software, firmware, or configuration updates to the instrument ecosystem. Use for non-hardware-change version or settings updates.

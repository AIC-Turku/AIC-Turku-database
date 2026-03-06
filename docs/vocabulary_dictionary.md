# Vocabulary Dictionary

This page is generated from files under `vocab/`. Do not edit manually.

## Modalities

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Atomic Force Microscopy | `afm` | AFM | Uses a nanoscale cantilever probe to measure topography and mechanical properties at high spatial resolution. Can be combined with optical microscopy workflows. |
| Darkfield | `darkfield` | dark field | Collects only scattered light while excluding directly transmitted illumination. Highlights small structures and edges on a dark background. |
| Differential Interference Contrast | `dic` | DIC, nomarski | Uses polarized beam shearing to create relief-like contrast from optical path gradients. Useful for high-contrast imaging of unstained live samples. |
| Fluorescence Correlation Spectroscopy | `fcs` | FCS | Analyzes fluorescence intensity fluctuations in a tiny observation volume. Used to estimate concentration, diffusion, and molecular kinetics. |
| Fluorescence Lifetime Imaging | `flim` | FLIM | Measures fluorescence decay timing rather than only intensity. Useful for environmental sensing and interaction readouts such as FRET changes. |
| Fluorescence Recovery After Photobleaching | `frap` | FRAP | Photobleaches a region and measures fluorescence recovery over time. Used to quantify mobility, exchange, and binding dynamics. |
| Förster Resonance Energy Transfer | `fret` | FRET | Measures non-radiative energy transfer between donor and acceptor fluorophores at nanometer distances. Used as a readout of molecular proximity or conformational change. |
| Image Scanning Microscopy | `ism` | ISM, airyscan | Uses detector array information in scanning microscopy to improve resolution and signal usage. Airyscan implementations are a common form. |
| Impedance Cytometry | `impedance_cytometry` | electrical cytometry | Measures electrical impedance changes as cells pass sensing regions to infer size and biophysical properties. Often used for label-free cell phenotyping. |
| Light Sheet | `light_sheet` | SPIM, LSFM | Illuminates samples with a thin sheet orthogonal to detection. Supports gentle, rapid volumetric imaging with reduced out-of-focus exposure. |
| Live Cell Imaging | `live_cell_imaging` | live imaging, time-lapse live imaging | Refers to imaging workflows optimized for viable cells over time with controlled environment and low phototoxicity. Can be combined with multiple optical modalities. |
| Multiphoton | `multiphoton` | two-photon, 2p | Uses nonlinear excitation, typically with pulsed near-infrared lasers, to excite fluorophores only at the focal volume. Improves deep-tissue imaging and reduces out-of-plane photodamage. |
| Phase Contrast | `phase_contrast` | phase, ph | Converts phase shifts from transparent specimens into intensity differences. Useful for live, unlabeled cells on standard culture plastic. |
| Photoactivation | `photoactivation` | pa, photo-activation | Activates photoactivatable fluorophores in selected regions or times. Supports pulse-chase imaging, sparse labeling, and dynamic experiments. |
| Point-Scanning Confocal | `confocal_point` | laser scanning confocal, lsm | Scans a focused laser spot with a pinhole to reject out-of-focus light. Provides optical sectioning and improved contrast in thick specimens. |
| Polarized Light | `polarized_light` | polarization | Uses crossed polarizers to generate contrast from birefringent materials like crystals, amyloid fibrils, or muscle fibers. |
| RESOLFT | `resolft` | RESOLFT | Achieves super-resolution using reversibly switchable fluorophores and targeted on/off control. Often allows lower light intensities than depletion-based methods. |
| Second Harmonic Generation | `shg` | SHG, THG | Label-free multiphoton modality that generates signal from highly ordered, non-centrosymmetric structures like collagen fibers. |
| Single-Molecule Localization Microscopy | `smlm` | SMLM, PALM/STORM | Builds super-resolved images by localizing sparse single emitters over many frames. Includes methods such as PALM and STORM. |
| Single-Particle Tracking | `spt` | SPT, single molecule tracking | Tracks individual particles or molecules over time to quantify motion and dynamics. Used for diffusion, transport, and interaction studies. |
| Spectral Imaging | `spectral_imaging` | lambda imaging, spectral detection | Records fluorescence across wavelength bands rather than fixed channels. Enables unmixing of overlapping fluorophores and autofluorescence separation. |
| Spinning-Disk Confocal | `confocal_spinning_disk` | SDC, spinning disk | Uses a rotating pinhole disk to image many points in parallel. Enables fast, lower-phototoxicity 3D optical sectioning in live samples. |
| Stimulated Emission Depletion | `sted` | STED | Shrinks the effective fluorescence spot using a depletion beam around the excitation focus. Enables sub-diffraction super-resolution imaging. |
| Structured Illumination Microscopy | `sim` | SIM, structured illumination | Uses shifted illumination patterns and reconstruction to increase resolution and sectioning performance. Suitable for super-resolution with moderate light dose. |
| Structured Optical Sectioning | `optical_sectioning` | apotome, grid projection | Uses patterned illumination and computational processing to suppress out-of-focus signal. Common examples include ApoTome or grid-projection approaches. |
| Total Internal Reflection Fluorescence | `tirf` | TIRF | Excites fluorophores with an evanescent field near the coverslip interface. Ideal for membrane-proximal events within roughly the first 100–200 nm. |
| Transmitted Brightfield | `transmitted_brightfield` | brightfield, bf | Uses transmitted white light to image absorption and scattering contrast in unstained specimens. Common for routine morphology and context imaging. |
| Widefield Fluorescence | `widefield_fluorescence` | epifluorescence, widefield epi | Illuminates and captures fluorescence from the full field of view without optical sectioning. Best for fast imaging of bright samples and thin specimens. |

## Objective Immersion

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Air | `air` | dry | Objective is used without immersion liquid, with air between front lens and coverslip. Common for lower magnification or long working distance imaging. |
| Dipping | `dipping` | water dipping, dipping objective | Front lens is dipped directly into sample medium without coverslip contact. Common in electrophysiology and in vivo preparations. |
| Glycerol | `glycerol` | glycerin | Uses glycerol immersion to better match intermediate refractive indices. Useful for some cleared or thick biological specimens. |
| Multi-Immersion | `multi` | multi immersion | Objective is designed to operate with multiple immersion media, often with correction adjustments. Provides flexibility across sample types. |
| Oil | `oil` | oil immersion | Uses immersion oil to better match refractive index and increase numerical aperture. Common for high-resolution fluorescence objectives. |
| Silicone | `silicone` | silicone oil | Uses silicone oil immersion with refractive index close to tissue, improving deep imaging stability. Often used in live or thick sample imaging. |
| Water | `water` | water immersion | Uses water as immersion medium for improved index matching in aqueous samples. Useful for live-cell and deeper tissue imaging. |

## Detectors

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Avalanche Photodiode | `apd` | APD | Semiconductor point detector with internal gain and fast timing response. Used in photon counting and correlation-based measurements. |
| Charge-Coupled Device | `ccd` | CCD | Area detector technology with historically strong image quality and uniformity. Still used in some fluorescence and brightfield setups. |
| Electron-Multiplying CCD | `emccd` | EMCCD | CCD detector with on-chip gain for very low-light imaging. Useful for single-molecule and fast, dim signal applications. |
| GaAsP Photomultiplier Tube | `gaasp_pmt` | GaAsP_PMT, gaasp detector | PMT using gallium arsenide phosphide photocathodes with improved quantum efficiency over conventional PMTs. Useful for low-light confocal imaging. |
| Hybrid Detector | `hyd` | HyD, hybrid pmt | Combines features of PMTs and avalanche gain to provide high sensitivity and fast response. Frequently used in modern confocal systems. |
| Photomultiplier Tube | `pmt` | PMT | Highly sensitive point detector that amplifies photoelectrons through a dynode chain. Common in confocal detection paths. |
| Scientific CMOS | `scmos` | sCMOS | Low-noise, high-speed area detector with large field of view and high dynamic range. Common for widefield, spinning-disk, and fast live imaging. |
| SPAD Array | `spad` | — | Single-Photon Avalanche Diode array. Provides exceptional timing resolution and single-photon sensitivity, crucial for advanced FLIM. |
| Standard CMOS | `cmos` | — | Standard digital camera sensor. Commonly used in routine brightfield, color histology, or basic fluorescence. |

## Scanner Types

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Acousto-Optic Scanner | `acousto_optic` | AOD, acousto-optic deflector | Deflects beams using acousto-optic elements for rapid, inertia-free positioning. Useful for fast random-access scanning patterns. |
| Galvanometric Scanner | `galvo` | galvanometer, galvo mirrors | Uses galvanometer mirrors to steer the excitation beam across the sample. Common in point-scanning confocal systems with flexible scan control. |
| No Scanner | `none` | camera-based | No dedicated beam scanner is used for image formation. Typical of camera-based widefield modalities. |
| Polygon Scanner | `polygon` | polygon mirror | Uses a rotating polygon mirror for rapid beam deflection. Often used in high-speed scanning implementations. |
| Resonant Scanner | `resonant` | resonant galvo | Uses a resonant oscillating mirror for very high line rates. Enables faster imaging than standard galvo scanning, often with reduced dwell time. |
| Spinning Disk Scanner | `spinning_disk` | nipkow disk, sdc scanner | Uses rotating pinhole disks to scan multiple points in parallel. Supports high-speed confocal imaging with lower phototoxicity. |
| Stage Scanning | `stage_scanning` | sample scanning | Forms images by moving the sample stage relative to fixed optics or beam position. Common in slide scanning and some large-area acquisitions. |
| Tandem Scanner (Galvo/Resonant) | `tandem` | tandem | Dual-mode scanning configuration that supports switching between galvanometric and resonant scanning behavior. |

## Light Sources

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Arc Lamp | `arc_lamp` | mercury lamp, xenon lamp | Broad-spectrum lamp, such as mercury or xenon, used with filter sets for fluorescence excitation. Historically common on epifluorescence microscopes. |
| Halogen Lamp | `halogen_lamp` | tungsten-halogen, quartz halogen | Continuous-spectrum tungsten-halogen illumination, primarily for transmitted light imaging. Common for brightfield and contrast techniques. |
| Laser | `laser` | single-line laser | Provides coherent, narrowband excitation at specific wavelengths. Common for fluorescence imaging requiring high irradiance and precise line selection. |
| LED | `led` | light-emitting diode | Solid-state light source with stable output and fast switching. Widely used for widefield fluorescence and transmitted illumination. |
| Metal Halide Lamp | `metal_halide` | hxp, x-cite | Broad-spectrum lamp coupled via a liquid light guide. Provides intense, stable excitation for standard widefield fluorescence. |
| Pulsed Near-IR Laser | `multiphoton_laser` | ti:sapphire, fs laser | Femtosecond pulsed laser tunable in the near-infrared. Used for deep-tissue multiphoton excitation. |
| Supercontinuum Source | `supercontinuum` | white supercontinuum laser | Broadband laser-like source generated by nonlinear spectral broadening. Provides highly flexible, selectable excitation bands. |
| White Light Laser | `white_light_laser` | WLL, tunable laser | Broadband laser source with tunable output wavelengths selected by software or optics. Supports flexible excitation across many fluorophores. |

## Modules

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Adaptive Optics | `adaptive_optics` | ao | Corrects sample- or system-induced aberrations using deformable elements and feedback. Improves resolution and signal quality, especially in deep or heterogeneous samples. |
| FCS Module | `fcs` | correlation module | Instrumentation support for fluorescence fluctuation measurements and autocorrelation analysis. Enables diffusion and concentration quantification in tiny volumes. |
| FLIM Module | `flim` | lifetime module | Adds lifetime-resolved detection and analysis to fluorescence imaging. Enables contrast based on fluorophore decay kinetics. |
| FRAP Module | `frap` | photobleach module | Hardware or software capability to perform targeted photobleaching for recovery measurements. Typically controls ROI bleaching power and timing. |
| Hardware Autofocus | `hardware_autofocus` | focus lock, z-drift compensation | Active focus stabilization that compensates focus drift during acquisition. Common implementations include reflected-light focus locks such as Definite Focus or PFS. |
| Incubation | `incubation` | environmental chamber, temp/co2 control | Environmental control module for temperature, CO2, and often humidity around the specimen. Supports physiologic conditions during long-term live imaging. |
| Microfluidics / Perfusion | `microfluidics` | perfusion pump | Hardware for controlled delivery of media or drugs to the sample during live imaging. |
| Motorized Stage | `motorized_stage` | multiposition, xy stage | Automated XY stage enabling multi-position imaging, large-area tiling, and multi-well plate screening. |
| Optogenetics | `optogenetics` | photo-stimulation | Provides patterned or wavelength-specific stimulation for light-controlled biological perturbations. Used to control signaling or neural activity during imaging. |
| Photoactivation Module | `photoactivation` | photo-manipulation, pa module | Capability to activate or uncage photoresponsive probes in defined regions. Used for selective labeling and dynamic tracking experiments. |

## Objective Corrections

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Achromat | `achromat` | achro | Basic objective correction class with limited chromatic and spherical correction. Often used for standard, non-demanding imaging tasks. |
| Apochromat | `apochromat` | apo | Objective with strong chromatic and spherical aberration correction, typically over multiple colors. May not guarantee full field flatness. |
| Fluorite | `fluorite` | semi-apo, fluor | Objective class with improved color correction and transmission relative to basic achromats. Common compromise between performance and cost. |
| Plan Achromat | `plan_achromat` | plan achro | Objective with flat field correction and basic chromatic correction for two wavelengths. Suitable for routine brightfield and general imaging. |
| Plan Apochromat | `plan_apochromat` | plan-apo, plan apo, super apochromat, uplsapo | High-end objective with flat field correction and strong chromatic/spherical correction across wavelengths. Preferred for quantitative, multicolor imaging. |
| Plan Fluorite | `plan_fluorite` | plan fluor, plan fluorite | Objective with flat field correction and moderate-to-high aberration correction, typically between achromat and apochromat classes. |

## Maintenance Reasons

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Check | `check` | inspection, diagnostic | Focused verification or inspection to confirm system status without major intervention. Includes diagnostic visits and quick health checks. |
| Install | `install` | commissioning, setup | Triggered by initial installation of a system, add-on module, or newly delivered component. Use for setup and commissioning events. |
| Other | `other` | misc | Reason does not fit the predefined categories. Document the rationale in free-text details. |
| Problem | `problem` | issue, breakdown | Triggered by a reported fault, performance issue, or unexpected behavior. Use when intervention is reactive to a defect. |
| Scheduled | `scheduled` | preventive maintenance, pm | Planned preventive maintenance performed at regular intervals. Includes routine service contracts and periodic inspections. |
| Upgrade | `upgrade` | enhancement | Initiated to improve capability, performance, or feature set beyond baseline operation. Can include hardware or software enhancement projects. |

## Maintenance Actions

| Label | ID | Synonyms | Description |
| --- | --- | --- | --- |
| Align | `align` | realignment, alignment | Adjusts optical or mechanical alignment to restore expected performance. Typical examples include beam path or stage alignment. |
| Calibrate | `calibrate` | calibration | Performs calibration against known references to ensure accurate measurement or positioning. Use for intensity, stage, focus, or scaling calibration events. |
| Clean | `clean` | cleaning | Removes contamination from optics, mechanics, or enclosures to recover performance and reliability. Includes routine cleaning of lenses and filters. |
| Other | `other` | misc | Action does not match the predefined categories. Provide specific context in free-text details. |
| Repair | `repair` | fix | Fixes a confirmed fault or malfunction by restoring or replacing failing parts. Use when resolving a broken or degraded subsystem. |
| Replace | `replace` | part replacement | Substitutes a component with a new or refurbished part. Use when parts are worn, failed, or upgraded directly. |
| Service | `service` | maintenance | General maintenance intervention including inspection and routine adjustments. Used when work does not fit a more specific action type. |
| Update | `update` | upgrade software, firmware update | Applies software, firmware, or configuration updates to the instrument ecosystem. Use for non-hardware-change version or settings updates. |

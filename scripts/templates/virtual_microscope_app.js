(function () {
  const VM = window.VirtualMicroscopeRuntime;
  if (!VM) {
    console.error('Virtual microscope runtime is missing.');
    return;
  }

  let globalData = {};
  try {
    const raw = document.getElementById('lightpath-data').textContent.trim();
    if (raw) globalData = JSON.parse(raw);
  } catch (err) {
    console.error('Failed to parse virtual microscope payload', err);
  }

  const state = {
    allInstruments: globalData,
    activeInstrumentRaw: null,
    activeInstrument: null,
    loadedProteins: new Map(),
    preferTwoPhoton: false,
    activeRoute: null,
    spectralBandsByMechanism: new Map(),
    detectorSettings: new Map(),
    sourceSettings: new Map(),
    splitterBranchSelections: new Map(),
    lastSelection: null,
    lastSimulation: null,
    activeInspectorStage: null,
    routeTopology: null,
  };

  let currentInstrumentId = null;
  let referenceChart = null;
  let propagationChart = null;
  let detectionChart = null;

  const DOM = {
    referenceChart: document.getElementById('referenceSpectraChart'),
    propagationChart: document.getElementById('propagationSpectraChart'),
    detectionChart: document.getElementById('detectionChart'),
    scopeSel: document.getElementById('microscopeSelector'),
    routeWrap: document.getElementById('opticalRouteChooserWrap'),
    routeSel: document.getElementById('opticalRouteSelector'),
    graph: document.getElementById('lightPathGraph'),
    localQuery: document.getElementById('localFluorophoreQuery'),
    localSearchBtn: document.getElementById('localSearchBtn'),
    localSearchStatus: document.getElementById('localSearchStatus'),
    localResults: document.getElementById('localSearchResults'),
    fpQuery: document.getElementById('fluorophoreQuery'),
    searchBtn: document.getElementById('searchBtn'),
    searchStatus: document.getElementById('searchStatus'),
    fpResults: document.getElementById('searchResults'),
    referenceStatus: document.getElementById('referenceStatus'),
    emissionStatus: document.getElementById('emissionStatus'),
    use2Photon: document.getElementById('use2Photon'),
    activeDyes: document.getElementById('selectedDyes'),
    summary: document.getElementById('pathSummary'),
    scoreboard: document.getElementById('signalSimulator'),
    autoConfigBtn: document.getElementById('vm-btn-autoconfig'),
    autoConfigStatus: document.getElementById('vm-autoconfig-status'),
  };

  const LOCAL_FLUOROPHORE_INDEX_URL = '../assets/data/spectra/fluorophores/index.json';
  const LOCAL_FLUOROPHORE_BY_ID_URL = '../assets/data/spectra/fluorophores/by_id.json';
  const LOCAL_FLUOROPHORE_BASE_URL = '../assets/data/spectra/fluorophores';

  const localLibraryCache = {
    index: null,
    byId: null,
    indexPromise: null,
    byIdPromise: null,
  };

  function cleanString(value) {
    return typeof value === 'string' ? value.trim() : '';
  }

  function numberOrNull(value) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string') {
      const numeric = Number(value.trim());
      return Number.isFinite(numeric) ? numeric : null;
    }
    return null;
  }

  function rgbaFromHex(hex, alpha) {
    const cleaned = String(hex || '').replace('#', '');
    if (cleaned.length !== 6) return `rgba(59, 130, 246, ${alpha})`;
    const r = Number.parseInt(cleaned.slice(0, 2), 16);
    const g = Number.parseInt(cleaned.slice(2, 4), 16);
    const b = Number.parseInt(cleaned.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function colorHex(wavelength) {
    const wl = numberOrNull(wavelength) ?? 520;
    let r = 0;
    let g = 0;
    let b = 0;
    if (wl < 380) {
      r = 0.5;
      b = 1;
    } else if (wl >= 380 && wl < 440) {
      r = -(wl - 440) / 60;
      b = 1;
    } else if (wl >= 440 && wl < 490) {
      g = (wl - 440) / 50;
      b = 1;
    } else if (wl >= 490 && wl < 510) {
      g = 1;
      b = -(wl - 510) / 20;
    } else if (wl >= 510 && wl < 580) {
      r = (wl - 510) / 70;
      g = 1;
    } else if (wl >= 580 && wl < 645) {
      r = 1;
      g = -(wl - 645) / 65;
    } else if (wl >= 645 && wl <= 780) {
      r = 1;
    } else if (wl > 780) {
      r = 0.5;
    }
    const toHex = (value) => Math.round(Math.max(0, Math.min(1, value)) * 255).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }


  function stagePipeKey(leftStage, rightStage) {
    return `${leftStage}->${rightStage}`;
  }

  function pipelineFlowOrigin(stageId) {
    const normalized = cleanString(stageId).toLowerCase();
    if (normalized === 'illumination-controls') return 'illumination-controls';
    if (normalized === 'detection-controls') return 'detection-controls';
    return normalized;
  }

  function pipelineSpectrumForOrigin(origin, spectra) {
    const normalized = pipelineFlowOrigin(origin);
    if (normalized === 'sources') return spectra.sourceMixed;
    if (normalized === 'illumination-controls' || normalized === 'illumination' || normalized === 'excitation' || normalized === 'dichroic') return spectra.excitationAtSample;
    if (normalized === 'sample') return spectra.generatedEmission;
    if (normalized === 'detection-controls' || normalized === 'detection' || normalized === 'emission' || normalized === 'splitters' || normalized === 'detectors') {
      return spectra.branchEmission.some((value) => value > 1e-9) ? spectra.branchEmission : spectra.postEmission;
    }
    return spectra.empty;
  }

  function buildPipelineStages(derivedControlGroups) {
    return (Array.isArray(derivedControlGroups) ? derivedControlGroups : [])
      .map((group) => ({
        id: cleanString(group && group.id),
        label: cleanString(group && group.label) || 'Stage',
        flowOrigin: pipelineFlowOrigin(group && group.id),
      }))
      .filter((group) => group.id);
  }

  function setStatusMessage(message, tone = 'info') {
    if (!DOM.autoConfigStatus) return;
    DOM.autoConfigStatus.textContent = cleanString(message);
    DOM.autoConfigStatus.dataset.tone = tone;
  }

  function setInlineStatus(node, message, tone = 'info') {
    if (!node) return;
    node.textContent = cleanString(message);
    if (tone && tone !== 'info') node.dataset.tone = tone;
    else delete node.dataset.tone;
  }

  function formatNumericNm(value) {
    const numeric = numberOrNull(value);
    return numeric === null ? null : `${Math.round(numeric)} nm`;
  }

  function formatComponentMetadata(component, context = {}) {
    if (!component || typeof component !== 'object') return [];
    const type = cleanString(component.component_type || component.type || context.stage || '').replace(/_/g, ' ');
    const rows = [];
    if (type) rows.push(`Type: ${type}`);
    const manufacturer = cleanString(component.manufacturer);
    const model = cleanString(component.model);
    const productCode = cleanString(component.product_code);
    if (manufacturer) rows.push(`Manufacturer: ${manufacturer}`);
    if (model) rows.push(`Model: ${model}`);
    if (productCode) rows.push(`Product code: ${productCode}`);
    if (numberOrNull(component.center_nm) !== null) rows.push(`Center: ${formatNumericNm(component.center_nm)}`);
    if (numberOrNull(component.width_nm) !== null) rows.push(`Bandwidth: ${Math.round(numberOrNull(component.width_nm))} nm`);
    if (numberOrNull(component.cut_on_nm) !== null) rows.push(`Cut-on: ${formatNumericNm(component.cut_on_nm)}`);
    if (numberOrNull(component.cut_off_nm) !== null) rows.push(`Cut-off: ${formatNumericNm(component.cut_off_nm)}`);
    if (Array.isArray(component.cutoffs_nm) && component.cutoffs_nm.length) {
      rows.push(`Cutoffs: ${component.cutoffs_nm.map((value) => formatNumericNm(value)).filter(Boolean).join(', ')}`);
    }
    const renderBandList = (bands, defaultLabel) => (Array.isArray(bands) ? bands : []).map((band) => {
      const center = numberOrNull(band && band.center_nm);
      const width = numberOrNull(band && band.width_nm);
      if (center === null || width === null) return cleanString(band && band.label) || defaultLabel;
      const low = Math.round(center - (width / 2));
      const high = Math.round(center + (width / 2));
      return `${cleanString(band && band.label) || defaultLabel} ${low}-${high} nm`;
    }).filter(Boolean);

    const passBands = renderBandList(component.bands, 'Band');
    if (passBands.length) {
      rows.push(`Bands: ${passBands.join(' • ')}`);
    }

    const transmissionBands = renderBandList(component.transmission_bands, 'Transmission');
    if (transmissionBands.length) {
      rows.push(`Transmission bands: ${transmissionBands.join(' • ')}`);
    }

    const reflectionBands = renderBandList(component.reflection_bands, 'Reflection');
    if (reflectionBands.length) {
      rows.push(`Reflection bands: ${reflectionBands.join(' • ')}`);
    }
    if (numberOrNull(component.wavelength_nm) !== null) rows.push(`Wavelength: ${formatNumericNm(component.wavelength_nm)}`);
    if (numberOrNull(component.selected_wavelength_nm) !== null) rows.push(`Selected λ: ${formatNumericNm(component.selected_wavelength_nm)}`);
    if (numberOrNull(component.tunable_min_nm) !== null && numberOrNull(component.tunable_max_nm) !== null) {
      rows.push(`Tunable range: ${Math.round(numberOrNull(component.tunable_min_nm))}-${Math.round(numberOrNull(component.tunable_max_nm))} nm`);
    }
    const roleLabel = cleanString(component.role_label || component.role);
    const kindLabel = cleanString(component.kind_label || component.kind);
    if (roleLabel) rows.push(`Role: ${roleLabel}`);
    if (kindLabel) rows.push(`Kind: ${kindLabel}`);
    if (component.detector_class) rows.push(`Detector: ${component.detector_class}`);
    if (numberOrNull(component.collection_min_nm) !== null && numberOrNull(component.collection_max_nm) !== null) {
      rows.push(`Collection: ${Math.round(numberOrNull(component.collection_min_nm))}-${Math.round(numberOrNull(component.collection_max_nm))} nm`);
    }
    return rows;
  }

  function createMetadataBlock() {
    const meta = document.createElement('div');
    meta.className = 'vm-component-meta';
    return meta;
  }

  function updateMetadataBlock(metaNode, component, context = {}) {
    if (!metaNode) return;
    const rows = formatComponentMetadata(component, context);
    metaNode.innerHTML = rows.length
      ? rows.map((row) => `<div>${row}</div>`).join('')
      : '<span>No component metadata available.</span>';
  }

  function parseJsonValue(value) {
    try {
      return value ? JSON.parse(value) : null;
    } catch (error) {
      return null;
    }
  }

  function createLinkedStageNote(titleText, message, component) {
    const wrap = document.createElement('div');
    wrap.className = 'vm-linked-note';
    const title = document.createElement('div');
    title.className = 'vm-linked-note-title';
    title.textContent = titleText;
    wrap.appendChild(title);
    const text = document.createElement('div');
    text.className = 'vm-mini';
    text.textContent = message;
    wrap.appendChild(text);
    if (component) {
      const meta = createMetadataBlock();
      updateMetadataBlock(meta, component, {});
      wrap.appendChild(meta);
    }
    return wrap;
  }

  function appendLinkedCubeNotes(panel, kind, titlePrefix, description) {
    const cubeSelects = Array.from(DOM.graph.querySelectorAll('select[data-stage="cube"]'));
    cubeSelects.forEach((cubeSelect, index) => {
      const cubeValue = parseJsonValue(cubeSelect && cubeSelect.value);
      const linked = cubeValue && (
        kind === 'dichroic'
          ? (cubeValue.dichroic_filter || cubeValue.dichroic || cubeValue.di)
          : (cubeValue.emission_filter || cubeValue.emission || cubeValue.em)
      );
      if (linked) {
        panel.appendChild(
          createLinkedStageNote(
            `${titlePrefix} ${cubeSelects.length > 1 ? index + 1 : ''}`.trim(),
            description,
            linked
          )
        );
      }
    });
  }

  function createPipelineBadge(stageId, label) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'vm-stage-tab';
    button.dataset.stageId = stageId;
    button.textContent = label;
    button.addEventListener('click', () => setInspectorStage(stageId));
    return button;
  }

  function createPipeSegment(pipeKey) {
    const pipe = document.createElement('div');
    pipe.className = 'optical-pipe';
    pipe.dataset.pipeKey = pipeKey;
    const light = document.createElement('div');
    light.className = 'flowing-light';
    light.dataset.pipeKey = pipeKey;
    pipe.appendChild(light);
    return pipe;
  }

  function createInspectorPanel(stageId, label, subtitle = '') {
    const panel = document.createElement('div');
    panel.className = 'vm-stage-panel';
    panel.dataset.stageId = stageId;
    const title = document.createElement('div');
    title.className = 'vm-stage-panel-title';
    title.textContent = label;
    panel.appendChild(title);
    if (subtitle) {
      const copy = document.createElement('div');
      copy.className = 'vm-mini';
      copy.textContent = subtitle;
      panel.appendChild(copy);
    }
    return panel;
  }

  function setInspectorStage(stageId) {
    state.activeInspectorStage = stageId;
    Array.from(DOM.graph.querySelectorAll('.vm-stage-tab')).forEach((button) => {
      button.classList.toggle('active', button.dataset.stageId === stageId);
    });
    Array.from(DOM.graph.querySelectorAll('.vm-stage-panel')).forEach((panel) => {
      panel.classList.toggle('active', panel.dataset.stageId === stageId);
    });
  }

  function setPipeSpectrumColor(pipeKey, spectrum, grid) {
    if (!pipeKey || typeof pipeKey !== 'string') return;
    const light = DOM.graph.querySelector(`.flowing-light[data-pipe-key="${CSS.escape(pipeKey)}"]`);
    if (!light) return;
    const color = VM.spectrumToCSSColor(spectrum, grid);
    light.style.setProperty('--beam-color', color);
    light.dataset.empty = color === 'rgba(0,0,0,0)' ? 'true' : 'false';
  }

  function updatePipelineBeamColors(selection, simulation) {
    const grid = Array.isArray(simulation && simulation.grid)
      ? simulation.grid
      : VM.wavelengthGrid({ min_nm: 350, max_nm: determineChartMax(selection), step_nm: 2 });

    const sourceMixed = currentSourceSpectrum(grid);
    const excitationFiltered = applyComponentsToSpectrum(sourceMixed, selection.excitation, grid, 'excitation');
    const excitationAtSample = Array.isArray(simulation && simulation.excitationAtSample) ? simulation.excitationAtSample : excitationFiltered;

    const generatedEmission = sumSpectra(Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [], 'generatedSpectrum', grid);
    const postEmission = sumSpectra(Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [], 'postOpticsSpectrum', grid);
    const branchEmission = sumSpectra(Array.isArray(simulation && simulation.pathSpectra) ? simulation.pathSpectra : [], 'preDetectorSpectrum', grid);
    const spectra = {
      sourceMixed,
      excitationAtSample,
      generatedEmission,
      postEmission,
      branchEmission,
      empty: grid.map(() => 0),
    };

    const pipes = Array.from(DOM.graph.querySelectorAll('.optical-pipe'));

    pipes.forEach((pipe) => {
      const key = pipe.dataset.pipeKey;
      if (!key) return;
      const fromNode = key.split('->')[0];
      setPipeSpectrumColor(key, pipelineSpectrumForOrigin(fromNode, spectra), grid);
    });
  }

  function activeFilterMaskDatasets(selection, grid) {
    const datasets = [];
    const addMaskSet = (components, stage, color, alpha) => {
      (Array.isArray(components) ? components : []).forEach((component, index) => {
        const label = component.display_label || component.label || `${stage} ${index + 1}`;
        const mode = stage === 'excitation' ? 'excitation' : 'emission';
        const values = VM.componentMask(component, grid, { mode });
        if (!Array.isArray(values) || !values.some((value) => value > 1e-6)) return;
        datasets.push(chartDatasetFromGrid(`${label} mask`, grid, asPercentArray(values, 1), {
          borderColor: color,
          backgroundColor: alpha,
          borderDash: [6, 4],
          borderWidth: 1.4,
          fill: true,
          tension: 0,
          pointRadius: 0,
          order: -20,
        }));
      });
    };
    addMaskSet(selection.excitation, 'excitation', 'rgba(37, 99, 235, 0.75)', 'rgba(37, 99, 235, 0.08)');
    addMaskSet(selection.dichroic, 'dichroic', 'rgba(168, 85, 247, 0.75)', 'rgba(168, 85, 247, 0.07)');
    addMaskSet(selection.emission, 'emission', 'rgba(5, 150, 105, 0.75)', 'rgba(5, 150, 105, 0.08)');
    return datasets;
  }

  function applyOptimizedConfiguration(config) {
    if (!config || !state.activeInstrument) return false;
    const instrument = state.activeInstrument;
    const route = cleanString(config.route).toLowerCase() || state.activeRoute || instrument.defaultRoute || null;
    state.activeRoute = route;
    if (DOM.routeSel) DOM.routeSel.value = route || '';

    const enabledSourceRefs = new Map((Array.isArray(config.sources) ? config.sources : []).map((entry) => [`${entry.mechanismId}::${entry.slot}`, entry]));
    mechanismsForRoute(instrument.lightSources, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((source) => {
        const setting = ensureSourceSetting(source);
        const ref = enabledSourceRefs.get(`${mechanism.id}::${source.slot}`);
        setting.enabled = Boolean(ref);
        if (ref && numberOrNull(ref.selected_wavelength_nm) !== null) {
          setting.selected_wavelength_nm = numberOrNull(ref.selected_wavelength_nm);
        }
      });
    });

    const enabledDetectorRefs = new Map((Array.isArray(config.detectors) ? config.detectors : []).map((entry) => [`${entry.mechanismId}::${entry.slot}`, entry]));
    mechanismsForRoute(instrument.detectors, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((detector) => {
        const setting = ensureDetectorSetting(mechanism, detector);
        const ref = enabledDetectorRefs.get(`${mechanism.id}::${detector.slot}`);
        setting.enabled = Boolean(ref);
        if (ref && numberOrNull(ref.collection_min_nm) !== null) setting.collection_min_nm = numberOrNull(ref.collection_min_nm);
        if (ref && numberOrNull(ref.collection_max_nm) !== null) setting.collection_max_nm = numberOrNull(ref.collection_max_nm);
      });
    });

    renderGraphFlow();
    const selectionMap = config.selectionMap && typeof config.selectionMap === 'object' ? config.selectionMap : {};
    Array.from(DOM.graph.querySelectorAll('select[data-stage][data-mechanism-id]')).forEach((select) => {
      const mechanismId = select.dataset.mechanismId;
      const desiredSlot = selectionMap[mechanismId];
      if (!Number.isFinite(Number(desiredSlot))) return;
      const match = Array.from(select.options).find((option) => Number(option.dataset.slot) === Number(desiredSlot));
      if (match) {
        select.value = match.value;
        select.dataset.userSet = 'true';
      }
    });
    refreshOutputs();
    return true;
  }

  function runAutoConfigure() {
    if (!state.activeInstrumentRaw || !state.loadedProteins.size) {
      setStatusMessage('Load at least one fluorophore before auto-configuring.', 'warning');
      return;
    }
    const result = VM.optimizeLightPath(mapToArray(state.loadedProteins), state.activeInstrumentRaw, {
      preferTwoPhoton: state.preferTwoPhoton,
      currentRoute: state.activeRoute,
    });
    if (!result) {
      setStatusMessage('No compatible zero-leakage configuration was found for the current fluorophores.', 'warning');
      return;
    }
    applyOptimizedConfiguration(result);
    setStatusMessage(
      result.strictLeakageSatisfied === false ? 'Optimized the best near-zero-leakage configuration.' : 'Configuration Optimized!',
      result.strictLeakageSatisfied === false ? 'warning' : 'success'
    );
  }

  function mapToArray(map) {
    return Array.from(map.values());
  }

  function routeSelectionIsExplicit() {
    return Boolean(state.activeInstrument && Array.isArray(state.activeInstrument.routeOptions) && state.activeInstrument.routeOptions.length > 1);
  }

  function strictHardwareTruthMode() {
    return Boolean(state.activeInstrument && state.activeInstrument.strictHardwareTruth);
  }

  function uniqueTexts(values) {
    return Array.from(new Set((Array.isArray(values) ? values : [])
      .map((value) => cleanString(value))
      .filter(Boolean)));
  }

  function sourceSettingKey(source) {
    const routes = normalizeSourceRoutes(source).join('|') || 'any-route';
    const stableId = cleanString(source && (source.id || source.inventory_id || source.hardware_inventory_id || source.display_label || source.name || source.model)) || 'source';
    const slot = cleanString(source && source.slot) || '0';
    const wavelength = numberOrNull(source && (source.selected_wavelength_nm ?? source.wavelength_nm));
    const tuning = [numberOrNull(source && source.tunable_min_nm), numberOrNull(source && source.tunable_max_nm)].filter((value) => value !== null).join('-') || 'fixed';
    return [currentInstrumentId || 'scope', stableId, slot, routes, wavelength === null ? 'na' : String(Math.round(wavelength)), tuning].join('::');
  }

  function detectorSettingKey(mechanism, detector) {
    return `${mechanism.id || 'detector'}::${detector.display_label || detector.name || detector.channel_name || 'detector'}`;
  }

  function splitterBranchSelectionKey(mechanism) {
    return [
      currentInstrumentId || 'scope',
      cleanString(state.activeRoute) || 'route',
      cleanString(mechanism && (mechanism.id || mechanism.name || mechanism.display_label)) || 'splitter',
    ].join('::');
  }

  function ensureSplitterBranchSelection(mechanism) {
    const key = splitterBranchSelectionKey(mechanism);
    if (!state.splitterBranchSelections.has(key)) {
      const branches = Array.isArray(mechanism && mechanism.branches) ? mechanism.branches : [];
      const defaults = mechanism && mechanism.branch_selection_required && branches.length
        ? [cleanString(branches[0].id || '')]
        : [];
      state.splitterBranchSelections.set(key, defaults.filter(Boolean));
    }
    return state.splitterBranchSelections.get(key);
  }

  function knownEndpointEntries() {
    const entries = [];
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.detectors, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((detector) => {
        entries.push({
          id: detector.id || detector.terminal_id || detector.display_label || detector.name,
          label: detector.display_label || detector.name || mechanism.display_label || 'Endpoint',
          endpoint_type: detector.endpoint_type || detector.detector_class || detector.kind || 'detector',
        });
      });
    });
    (Array.isArray(state.activeInstrument && state.activeInstrument.terminals) ? state.activeInstrument.terminals : []).forEach((terminal) => {
      entries.push({
        id: terminal.id || terminal.terminal_id || terminal.display_label || terminal.name,
        label: terminal.display_label || terminal.name || 'Endpoint',
        endpoint_type: terminal.endpoint_type || terminal.kind || 'detector',
      });
    });
    const seen = new Set();
    return entries.filter((entry) => {
      const key = cleanString(entry.id).toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function endpointLabelForTargetId(targetId) {
    const normalized = cleanString(targetId).toLowerCase();
    if (!normalized) return 'Endpoint';
    const match = knownEndpointEntries().find((entry) => cleanString(entry.id).toLowerCase() === normalized);
    return match ? match.label : targetId;
  }

  function ensureSourceSetting(source) {
    const key = sourceSettingKey(source);
    if (!state.sourceSettings.has(key)) {
      const tunableMin = numberOrNull(source.tunable_min_nm);
      const tunableMax = numberOrNull(source.tunable_max_nm);
      const selectedWavelength = numberOrNull(source.wavelength_nm)
        ?? ((tunableMin !== null && tunableMax !== null) ? Math.round((tunableMin + tunableMax) / 2) : null);
      state.sourceSettings.set(key, {
        enabled: false,
        selected_wavelength_nm: selectedWavelength,
        user_weight: numberOrNull(source.power_weight) ?? 1,
      });
    }
    return state.sourceSettings.get(key);
  }


  function parseCollectionWindow(textValue) {
    const text = cleanString(textValue);
    if (!text) return { min: null, max: null };
    const bandMatch = text.match(/(\d{3,4})\s*[-–]\s*(\d{3,4})/);
    if (bandMatch) {
      const low = Number(bandMatch[1]);
      const high = Number(bandMatch[2]);
      return { min: low, max: high };
    }
    const singleMatch = text.match(/(\d{3,4})\s*nm/i);
    if (singleMatch) {
      return { min: Number(singleMatch[1]) - 20, max: Number(singleMatch[1]) + 20 };
    }
    return { min: null, max: null };
  }

  function defaultDetectorCollection(detector) {
    const parsed = [detector && detector.channel_name, detector && detector.display_label, detector && detector.name]
      .map(parseCollectionWindow)
      .find((entry) => entry.min !== null && entry.max !== null) || { min: null, max: null };
    const explicitMin = numberOrNull(detector && (detector.collection_min_nm ?? detector.min_nm));
    const explicitMax = numberOrNull(detector && (detector.collection_max_nm ?? detector.max_nm));
    if (explicitMin !== null && explicitMax !== null) {
      return { min: Math.min(explicitMin, explicitMax), max: Math.max(explicitMin, explicitMax) };
    }
    const center = numberOrNull(detector && (detector.collection_center_nm ?? detector.channel_center_nm ?? detector.wavelength_nm)) ?? ((parsed.min !== null && parsed.max !== null) ? ((parsed.min + parsed.max) / 2) : 550);
    const width = numberOrNull(detector && (detector.collection_width_nm ?? detector.bandwidth_nm ?? detector.width_nm)) ?? ((parsed.min !== null && parsed.max !== null) ? (parsed.max - parsed.min) : 40);
    const halfWidth = Math.max(2, width / 2);
    return { min: center - halfWidth, max: center + halfWidth };
  }

  function ensureDetectorSetting(mechanism, detector) {
    const key = detectorSettingKey(mechanism, detector);
    if (!state.detectorSettings.has(key)) {
      const detectorClass = detector.detector_class || VM.detectorClass(detector.kind || detector.endpoint_type);
      const defaults = defaultDetectorCollection(detector);
      const defaultEnabled = detector.default_enabled === undefined ? true : Boolean(detector.default_enabled);
      state.detectorSettings.set(key, {
        enabled: defaultEnabled,
        collection_enabled: !['camera', 'camera_port'].includes(detectorClass),
        collection_min_nm: defaults.min,
        collection_max_nm: defaults.max,
      });
    }
    return state.detectorSettings.get(key);
  }

  function mechanismsForRoute(mechanisms, activeRoute) {
    return (Array.isArray(mechanisms) ? mechanisms : []).filter((mechanism) => VM.routeMatches(mechanism.__routes, activeRoute));
  }

  function positionsForRoute(mechanism, activeRoute) {
    const entries = Object.entries(mechanism && mechanism.positions ? mechanism.positions : {});
    return Object.fromEntries(
      entries.filter(([, component]) => VM.routeMatches(component.__routes || mechanism.__routes, activeRoute))
    );
  }

  function routeRecordForInstrument(instrument, route) {
    const routeId = cleanString(route).toLowerCase();
    const authoritativeRoutes = instrument && instrument.routeTopology && Array.isArray(instrument.routeTopology.routes)
      ? instrument.routeTopology.routes
      : [];
    const routes = authoritativeRoutes.length
      ? authoritativeRoutes
      : (Array.isArray(instrument && instrument.lightPaths) ? instrument.lightPaths : []);
    if (routeId) {
      const explicit = routes.find((entry) => cleanString(entry && entry.id).toLowerCase() === routeId);
      if (explicit) return explicit;
    }
    const fallbackId = cleanString(instrument && instrument.defaultRoute).toLowerCase();
    if (fallbackId) {
      const fallback = routes.find((entry) => cleanString(entry && entry.id).toLowerCase() === fallbackId);
      if (fallback) return fallback;
    }
    return routes[0] || null;
  }

  function detectorMechanismsForEndpointIds(instrument, endpointIds, route) {
    const wanted = new Set((Array.isArray(endpointIds) ? endpointIds : []).map((value) => cleanString(value).toLowerCase()).filter(Boolean));
    const mechanisms = mechanismsForRoute(instrument && instrument.detectors, route);
    if (!wanted.size) return mechanisms;
    return mechanisms.filter((mechanism) => Object.values(positionsForRoute(mechanism, route)).some((detector) => wanted.has(cleanString(detector && (detector.id || detector.terminal_id)).toLowerCase())));
  }

  function sourceMechanismsForSourceIds(instrument, sourceIds, route) {
    const wanted = new Set((Array.isArray(sourceIds) ? sourceIds : []).map((value) => cleanString(value).toLowerCase()).filter(Boolean));
    const mechanisms = mechanismsForRoute(instrument && instrument.lightSources, route);
    if (!wanted.size) return mechanisms;
    return mechanisms.filter((mechanism) => Object.values(positionsForRoute(mechanism, route)).some((source) => wanted.has(cleanString(source && source.id).toLowerCase())));
  }

  function opticalMechanismCatalog(instrument, route) {
    const catalog = new Map();
    ['cube', 'excitation', 'dichroic', 'emission', 'splitters'].forEach((key) => {
      mechanismsForRoute(instrument && instrument[key], route).forEach((mechanism) => {
        const mechanismId = cleanString(mechanism && mechanism.id).toLowerCase();
        if (!mechanismId) return;
        catalog.set(mechanismId, { stageKey: key, mechanism });
      });
    });
    return catalog;
  }

  function buildRouteTraversalEntries(instrument, routeRecord, route) {
    const catalog = opticalMechanismCatalog(instrument, route);
    const seenControlIds = new Set();
    const buildResolvedTraversal = (steps, phase, prefix) => (Array.isArray(steps) ? steps : []).flatMap((step, index) => {
      if (!(step && typeof step === 'object')) return [];
      if (step.kind === 'branch_block') {
        return [{
          kind: 'branch-block',
          key: `${prefix}:${phase}:branches:${index}`,
          phase,
          title: `Branches (${step.selection_mode || 'exclusive'})`,
          selectionMode: step.selection_mode || 'exclusive',
          branches: (Array.isArray(step.branches) ? step.branches : []).map((branch, branchIndex) => ({
            key: `${prefix}:${phase}:branch:${index}:${branchIndex}`,
            title: cleanString(branch && branch.label) || `Branch ${branchIndex + 1}`,
            sequence: buildResolvedTraversal(branch && branch.sequence, phase, `${prefix}:${index}:${branchIndex}`),
          })),
          message: 'This route forks explicitly here; each branch sequence is declared directly in the DTO route graph.',
        }];
      }
      const elementId = cleanString(step.id).toLowerCase();
      if (step.kind === 'endpoint') {
        return [{
          kind: 'endpoint',
          key: `${prefix}:${phase}:endpoint:${index}`,
          phase,
          endpointId: step.id,
          title: cleanString(step.display_label) || endpointLabelForTargetId(step.id),
          message: '',
        }];
      }
      if (step.kind === 'source') {
        return [];
      }
      const match = catalog.get(elementId);
      if (!match) {
        return [{
          kind: 'missing',
          key: `${prefix}:${phase}:${elementId}:${index}`,
          title: step.display_label || step.id,
          message: `This DTO route references optical path element "${step.id}", but no interactive UI control was derived for it.`,
        }];
      }
      const firstUse = !seenControlIds.has(elementId);
      seenControlIds.add(elementId);
      return [{
        kind: firstUse ? 'control' : 'linked',
        key: `${prefix}:${phase}:${elementId}:${index}`,
        stageKey: match.stageKey,
        mechanism: match.mechanism,
        phase,
        title: match.mechanism.display_label || match.mechanism.name || step.display_label || step.id,
        message: firstUse
          ? ''
          : `This route reuses the same ${match.stageKey.replace(/_/g, ' ')} selector later in the traversal; the active selection above is applied here as well.`,
      }];
    });
    const buildPhase = (steps, phase, prefix) => (Array.isArray(steps) ? steps : []).flatMap((step, index) => {
      const branchBlock = step && step.branches && typeof step.branches === 'object' ? step.branches : null;
      if (branchBlock) {
        return [{
          kind: 'branch-block',
          key: `${prefix}:${phase}:branches:${index}`,
          phase,
          title: `Branches (${branchBlock.selection_mode || 'exclusive'})`,
          selectionMode: branchBlock.selection_mode || 'exclusive',
          branches: (Array.isArray(branchBlock.items) ? branchBlock.items : []).map((branch, branchIndex) => ({
            key: `${prefix}:${phase}:branch:${index}:${branchIndex}`,
            title: cleanString(branch && (branch.label || branch.branch_id)) || `Branch ${branchIndex + 1}`,
            sequence: buildPhase(branch && branch.sequence, phase, `${prefix}:${index}:${branchIndex}`),
          })),
          message: 'This route forks explicitly here; each branch sequence is declared in light_paths.',
        }];
      }
      const elementId = cleanString(step && step.optical_path_element_id).toLowerCase();
      if (!elementId) {
        if (step && step.endpoint_id) {
          return [{
            kind: 'endpoint',
            key: `${prefix}:${phase}:endpoint:${index}`,
            phase,
            endpointId: step.endpoint_id,
            title: endpointLabelForTargetId(step.endpoint_id),
            message: '',
          }];
        }
        return [];
      }
      const match = catalog.get(elementId);
      if (!match) {
        return [{
          kind: 'missing',
          key: `${prefix}:${phase}:${elementId}:${index}`,
          title: step.optical_path_element_id,
          message: `This canonical route references optical path element "${step.optical_path_element_id}", but no interactive UI control was derived for it.`,
        }];
      }
      const firstUse = !seenControlIds.has(elementId);
      seenControlIds.add(elementId);
      return [{
        kind: firstUse ? 'control' : 'linked',
        key: `${prefix}:${phase}:${elementId}:${index}`,
        stageKey: match.stageKey,
        mechanism: match.mechanism,
        phase,
        title: match.mechanism.display_label || match.mechanism.name || step.optical_path_element_id,
        message: firstUse
          ? ''
          : `This route reuses the same ${match.stageKey.replace(/_/g, ' ')} selector later in the traversal; the active selection above is applied here as well.`,
      }];
    });

    const resolvedIlluminationTraversal = Array.isArray(routeRecord && routeRecord.illuminationTraversal) && routeRecord.illuminationTraversal.length
      ? routeRecord.illuminationTraversal
      : Array.isArray(routeRecord && routeRecord.illumination_traversal) && routeRecord.illumination_traversal.length
        ? routeRecord.illumination_traversal
        : null;
    const resolvedDetectionTraversal = Array.isArray(routeRecord && routeRecord.detectionTraversal) && routeRecord.detectionTraversal.length
      ? routeRecord.detectionTraversal
      : Array.isArray(routeRecord && routeRecord.detection_traversal) && routeRecord.detection_traversal.length
        ? routeRecord.detection_traversal
        : null;

    return {
      illumination: resolvedIlluminationTraversal
        ? buildResolvedTraversal(resolvedIlluminationTraversal, 'illumination', 'illumination')
        : buildPhase((routeRecord && (routeRecord.record && routeRecord.record.illumination_sequence)) || (routeRecord && routeRecord.illumination_sequence), 'illumination', 'illumination'),
      detection: resolvedDetectionTraversal
        ? buildResolvedTraversal(resolvedDetectionTraversal, 'detection', 'detection')
        : buildPhase((routeRecord && (routeRecord.record && routeRecord.record.detection_sequence)) || (routeRecord && routeRecord.detection_sequence), 'detection', 'detection'),
    };
  }

  function endpointIdsFromSequence(sequence) {
    const ids = [];
    (Array.isArray(sequence) ? sequence : []).forEach((step) => {
      if (!(step && typeof step === 'object')) return;
      if (step.endpoint_id) ids.push(step.endpoint_id);
      if (step.branches && typeof step.branches === 'object') {
        (Array.isArray(step.branches.items) ? step.branches.items : []).forEach((branch) => {
          ids.push(...endpointIdsFromSequence(branch && branch.sequence));
        });
      }
    });
    return ids;
  }

  function deriveRouteTopology(instrument, route) {
    const routeRecord = routeRecordForInstrument(instrument, route);
    const sourceIds = Array.isArray(routeRecord && routeRecord.explicitSourceIds) && routeRecord.explicitSourceIds.length
      ? routeRecord.explicitSourceIds.slice()
      : (Array.isArray(routeRecord && (routeRecord.illumination_traversal || routeRecord.illumination_sequence))
        ? (routeRecord.illumination_traversal || routeRecord.illumination_sequence)
        : [])
        .filter((step) => cleanString(step && (step.kind || (step.source_id ? 'source' : ''))).toLowerCase() === 'source' || Boolean(step && step.source_id))
        .map((step) => step && (step.id || step.source_id))
        .filter(Boolean);
    const usage = (routeRecord && routeRecord.routeHardwareUsage)
      || (Array.isArray(instrument && instrument.routeHardwareUsage) ? instrument.routeHardwareUsage : [])
        .find((entry) => cleanString(entry && entry.route_id).toLowerCase() === cleanString(routeRecord && routeRecord.id).toLowerCase())
      || null;
    const endpointIds = Array.isArray(routeRecord && routeRecord.explicitEndpointIds) && routeRecord.explicitEndpointIds.length
      ? routeRecord.explicitEndpointIds.slice()
      : usage && Array.isArray(usage.endpoint_inventory_ids)
      ? usage.endpoint_inventory_ids.map((value) => cleanString(value).split(':').pop()).filter(Boolean)
      : endpointIdsFromSequence((routeRecord && (routeRecord.record && routeRecord.record.detection_sequence)) || (routeRecord && routeRecord.detection_sequence));
    return {
      route: cleanString(routeRecord && routeRecord.id).toLowerCase() || cleanString(route).toLowerCase() || null,
      routeRecord,
      routeUsage: usage,
      routeLocalHardwareUsage: routeRecord && routeRecord.routeLocalHardwareUsage ? routeRecord.routeLocalHardwareUsage : { hardware_inventory_ids: [], endpoint_inventory_ids: [] },
      sourceMechanisms: sourceMechanismsForSourceIds(instrument, sourceIds, route),
      traversal: buildRouteTraversalEntries(instrument, routeRecord, route),
      endpointMechanisms: detectorMechanismsForEndpointIds(instrument, endpointIds, route),
      endpointIds,
      graphNodes: Array.isArray(routeRecord && routeRecord.graphNodes)
        ? routeRecord.graphNodes
        : (Array.isArray(routeRecord && routeRecord.graph_nodes) ? routeRecord.graph_nodes : []),
      graphEdges: Array.isArray(routeRecord && routeRecord.graphEdges)
        ? routeRecord.graphEdges
        : (Array.isArray(routeRecord && routeRecord.graph_edges) ? routeRecord.graph_edges : []),
      branchBlocks: Array.isArray(routeRecord && routeRecord.branchBlocks) ? routeRecord.branchBlocks : [],
    };
  }

  function routeGraphNodeNumber(node) {
    const direct = numberOrNull(node && (node.inventory_display_number ?? node.display_number));
    return direct === null ? null : Math.round(direct);
  }

  function routeGraphNodeLabel(node) {
    return cleanString(node && (node.label || node.display_label || node.id)) || 'Route node';
  }

  function stageGroupForNodeKind(kindLabel) {
    const kind = cleanString(kindLabel).toLowerCase();
    if (kind.includes('source') || kind.includes('laser') || kind.includes('led') || kind.includes('lamp')) return 'sources';
    if (kind.includes('excitation') || kind.includes('cube')) return 'illumination-controls';
    if (kind.includes('dichroic')) return 'illumination-controls';
    if (kind.includes('emission') || kind.includes('splitter')) return 'detection-controls';
    if (kind.includes('detector') || kind.includes('camera') || kind.includes('pmt') || kind.includes('apd') || kind.includes('hyd') || kind.includes('eyepiece') || kind.includes('endpoint')) return 'detectors';
    if (kind === 'sample') return 'sample';
    return null;
  }

  function buildDerivedControlGroups(inst, topology, route) {
    // UI-only compatibility layer: these groups are projections/adapters derived
    // from the already-selected authoritative route graph and traversal payload.
    const lightSourceMechanisms = topology && Array.isArray(topology.sourceMechanisms) ? topology.sourceMechanisms : mechanismsForRoute(inst.lightSources, route);
    const illuminationEntries = topology && topology.traversal ? topology.traversal.illumination : [];
    const detectionEntries = topology && topology.traversal ? topology.traversal.detection : [];
    const detectorMechanisms = topology && Array.isArray(topology.endpointMechanisms) ? topology.endpointMechanisms : mechanismsForRoute(inst.detectors, route);

    const groups = [];

    if (lightSourceMechanisms.length) {
      groups.push({
        id: 'sources',
        label: 'Sources',
        subtitle: 'Derived control group layered on top of the active route graph.',
        build(panel) {
          lightSourceMechanisms.forEach((mechanism) => panel.appendChild(createLightSourceControl(mechanism)));
        },
      });
    }

    if (illuminationEntries.length) {
      groups.push({
        id: 'illumination-controls',
        label: 'Illumination Controls',
        subtitle: 'Derived selectors aligned to route-local illumination traversal.',
        build(panel) {
          appendTraversalEntries(panel, illuminationEntries);
        },
      });
    }

    groups.push({
      id: 'sample',
      label: 'Sample',
      subtitle: 'Emission generation remains between illumination and detection traversal.',
      build(panel) {
        panel.appendChild(createLinkedStageNote('Emission generation', 'Loaded fluorophores absorb the excitation spectrum here and emit according to their reference spectra.'));
      },
    });

    if (detectionEntries.length) {
      groups.push({
        id: 'detection-controls',
        label: 'Detection Controls',
        subtitle: 'Derived selectors aligned to route-local detection traversal and explicit branch semantics.',
        build(panel) {
          appendTraversalEntries(panel, detectionEntries);
        },
      });
    }

    if (detectorMechanisms.length) {
      groups.push({
        id: 'detectors',
        label: 'Detectors & Endpoints',
        subtitle: 'Derived control widgets for explicit route endpoints.',
        build(panel) {
          detectorMechanisms.forEach((mechanism) => {
            createDetectorControls(mechanism).forEach((block) => panel.appendChild(block));
          });
        },
      });
    }

    return groups;
  }

  function activeRouteOrder() {
    return ['confocal', 'epi', 'tirf', 'multiphoton', 'transmitted'];
  }

  function inferRouteFromSourceSettings() {
    const tags = new Set();
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((source) => {
        const setting = ensureSourceSetting(source);
        if (!setting.enabled) return;
        VM.normalizeRouteTags(source.routes || source.path || source.__routes || []).forEach((tag) => tags.add(tag));
      });
    });
    for (const candidate of activeRouteOrder()) {
      if (tags.has(candidate)) return candidate;
    }
    return null;
  }

  function normalizeRouteLabel(route) {
    if (!route) return 'Any compatible route';
    return VM.routeLabel ? VM.routeLabel(route) : route.toUpperCase();
  }

  function describeSpectraSource(sourceId) {
    const sourceMap = {
      api: 'FPbase spectra API',
      detail: 'FPbase detail spectra',
      'detail+api': 'FPbase detail + API spectra',
      bundled_cache: 'Bundled FP cache',
      local: 'Local spectra library',
      synthetic: 'Synthetic fallback',
      'api+synthetic': 'FPbase API + synthetic fallback',
      'detail+synthetic': 'FPbase detail + synthetic fallback',
      'detail+api+synthetic': 'FPbase detail + API + synthetic fallback',
      'bundled_cache+synthetic': 'Bundled cache + synthetic fallback',
      none: 'No spectra available',
    };
    return sourceMap[cleanString(sourceId)] || cleanString(sourceId) || 'Unknown source';
  }

  function seedSettingsFromInstrument() {
    state.sourceSettings.clear();
    state.detectorSettings.clear();
    state.splitterBranchSelections.clear();
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((source) => ensureSourceSetting(source));
    });
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.detectors, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((detector) => ensureDetectorSetting(mechanism, detector));
    });
  }

  function populateScopeSelector() {
    DOM.scopeSel.innerHTML = '';
    Object.entries(state.allInstruments || {}).forEach(([id, payload]) => {
      const option = document.createElement('option');
      option.value = id;
      option.textContent = (payload && (payload.display_label || payload.display_name)) || id;
      DOM.scopeSel.appendChild(option);
    });
  }

  async function fetchInstrumentsFromDataJson() {
    const candidates = ['../assets/instruments_data.json', 'assets/instruments_data.json'];
    for (const url of candidates) {
      try {
        const data = await requestJSON(url);
        const rows = Array.isArray(data) ? data : (Array.isArray(data && data.instruments) ? data.instruments : []);
        const loaded = {};
        rows.forEach((inst) => {
          const id = cleanString((inst && inst.id) || (inst && inst.identity && inst.identity.id));
          if (id) loaded[id] = inst;
        });
        if (Object.keys(loaded).length) {
          if (!state.allInstruments || typeof state.allInstruments !== 'object' || Array.isArray(state.allInstruments)) {
            state.allInstruments = {};
          }
          Object.assign(state.allInstruments, loaded);
          return;
        }
      } catch (err) {
        // try next URL
      }
    }
  }

  function initInstrumentList() {
    const entries = Object.entries(state.allInstruments || {});
    if (!entries.length) {
      fetchInstrumentsFromDataJson()
        .then(() => {
          const loaded = Object.entries(state.allInstruments || {});
          if (!loaded.length) return;
          populateScopeSelector();
          const requestedScope = new URLSearchParams(window.location.search).get('scope');
          currentInstrumentId = (requestedScope && state.allInstruments[requestedScope]) ? requestedScope : loaded[0][0];
          DOM.scopeSel.value = currentInstrumentId;
          loadInstrument();
        })
        .catch((err) => console.error('Could not load instrument data', err));
      return;
    }
    populateScopeSelector();
    const requestedScope = new URLSearchParams(window.location.search).get('scope');
    currentInstrumentId = (requestedScope && state.allInstruments[requestedScope]) ? requestedScope : entries[0][0];
    DOM.scopeSel.value = currentInstrumentId;
    loadInstrument();
  }

  function init() {
    initCharts();

    DOM.scopeSel.addEventListener('change', (event) => {
      currentInstrumentId = event.target.value;
      state.activeInstrumentRaw = state.allInstruments[currentInstrumentId] || {};
      state.activeInstrument = VM.normalizeInstrumentPayload(state.activeInstrumentRaw);
      loadInstrument();
    });
    DOM.routeSel.addEventListener('change', (event) => {
      state.activeRoute = cleanString(event.target.value).toLowerCase() || null;
      state.spectralBandsByMechanism.clear();
      state.routeTopology = deriveRouteTopology(state.activeInstrument, state.activeRoute);
      renderGraphFlow();
      refreshOutputs();
    });
    DOM.localSearchBtn.addEventListener('click', () => searchLocalLibrary(DOM.localQuery.value));
    DOM.localQuery.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') searchLocalLibrary(DOM.localQuery.value);
    });
    DOM.localQuery.addEventListener('input', debounce(() => searchLocalLibrary(DOM.localQuery.value), 150));
    DOM.searchBtn.addEventListener('click', () => searchFPbase(DOM.fpQuery.value));
    DOM.fpQuery.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') searchFPbase(DOM.fpQuery.value);
    });
    DOM.fpQuery.addEventListener('input', debounce(() => searchFPbase(DOM.fpQuery.value), 300));
    DOM.use2Photon.addEventListener('change', (event) => {
      state.preferTwoPhoton = Boolean(event.target.checked);
      refreshOutputs();
    });
    if (DOM.autoConfigBtn) {
      DOM.autoConfigBtn.addEventListener('click', runAutoConfigure);
    }
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.fp-search-wrap')) {
        if (DOM.fpResults) DOM.fpResults.style.display = 'none';
        if (DOM.localResults) DOM.localResults.style.display = 'none';
      }
    });

    loadLocalFluorophoreIndex().catch((error) => {
      console.error('Failed to preload local fluorophore index', error);
      setInlineStatus(DOM.localSearchStatus, `Local spectra index unavailable: ${error.message}`, 'error');
    });

    initInstrumentList();
  }

  function loadInstrument() {
    state.activeInstrumentRaw = state.allInstruments[currentInstrumentId] || {};
    state.activeInstrument = VM.normalizeInstrumentPayload(state.activeInstrumentRaw);
    state.activeRoute = state.activeInstrument.defaultRoute || null;
    state.routeTopology = deriveRouteTopology(state.activeInstrument, state.activeRoute);
    state.spectralBandsByMechanism.clear();
    seedSettingsFromInstrument();
    renderRouteSelector();
    renderGraphFlow();
    refreshOutputs();
  }

  function renderRouteSelector() {
    const explicitOptions = Array.isArray(state.activeInstrument && state.activeInstrument.routeOptions)
      ? state.activeInstrument.routeOptions
      : [];
    const catalogFallback = Array.isArray(
      state.activeInstrument && state.activeInstrument.routeTopology && state.activeInstrument.routeTopology.routeCatalog
    ) ? state.activeInstrument.routeTopology.routeCatalog : [];
    const options = explicitOptions.length ? explicitOptions : catalogFallback;
    DOM.routeSel.innerHTML = '';

    if (options.length <= 1) {
      DOM.routeWrap.style.display = 'none';
      const singleRoute = options[0] ? cleanString(options[0].id).toLowerCase() : null;
      state.activeRoute = singleRoute || state.activeRoute || state.activeInstrument.defaultRoute || null;
      state.routeTopology = deriveRouteTopology(state.activeInstrument, state.activeRoute);
      return;
    }

    options.forEach((option) => {
      const entry = option && typeof option === 'object' ? option : { id: option, label: normalizeRouteLabel(option) };
      const opt = document.createElement('option');
      opt.value = cleanString(entry.id).toLowerCase();
      opt.textContent = cleanString(entry.label) || normalizeRouteLabel(entry.id);
      DOM.routeSel.appendChild(opt);
    });
    const selectedRoute = state.activeRoute || state.activeInstrument.defaultRoute || (strictHardwareTruthMode() ? '' : ((options[0] && options[0].id) || ''));
    DOM.routeSel.value = selectedRoute;
    state.activeRoute = cleanString(DOM.routeSel.value).toLowerCase() || null;
    state.routeTopology = deriveRouteTopology(state.activeInstrument, state.activeRoute);
    DOM.routeWrap.style.display = 'flex';
  }


  function snapshotStageSelections() {
    return Array.from(DOM.graph.querySelectorAll('select[data-stage]')).map((select) => ({
      stage: select.dataset.stage,
      mechanismId: select.dataset.mechanismId || '',
      value: select.value,
    }));
  }

  function restoreStageSelections(snapshot) {
    (Array.isArray(snapshot) ? snapshot : []).forEach((saved) => {
      const selector = `select[data-stage="${saved.stage}"][data-mechanism-id="${CSS.escape(saved.mechanismId || '')}"]`;
      const select = DOM.graph.querySelector(selector);
      if (!select) return;
      if (Array.from(select.options).some((option) => option.value === saved.value)) {
        select.value = saved.value;
      }
    });
  }

  function normalizeSourceRoutes(source) {

    return VM.normalizeRouteTags(source.routes || source.path || source.__routes || []);
  }

  function pruneConflictingSources() {
    if (routeSelectionIsExplicit()) return;
    const chosenRoute = inferRouteFromSourceSettings();
    if (!chosenRoute) return;
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((source) => {
        const setting = ensureSourceSetting(source);
        if (!setting.enabled) return;
        if (!VM.routeMatches(normalizeSourceRoutes(source), chosenRoute)) {
          setting.enabled = false;
        }
      });
    });
  }

  function appendTraversalEntries(panel, entries) {
    (Array.isArray(entries) ? entries : []).forEach((entry, index) => {
      if (entry.kind === 'control') {
        if (entry.stageKey === 'splitters') panel.appendChild(createSplitterControl(entry.mechanism));
        else panel.appendChild(createMechanismControl(entry.stageKey, entry.mechanism, index));
        return;
      }
      if (entry.kind === 'branch-block') {
        const container = document.createElement('div');
        container.className = 'vm-branch-block';
        container.appendChild(createLinkedStageNote(entry.title, entry.message));
        (Array.isArray(entry.branches) ? entry.branches : []).forEach((branch) => {
          const branchPanel = document.createElement('div');
          branchPanel.className = 'vm-branch-sequence';
          branchPanel.appendChild(createLinkedStageNote(branch.title, 'Branch-local optics and endpoint(s) declared directly in light_paths.'));
          appendTraversalEntries(branchPanel, branch.sequence || []);
          container.appendChild(branchPanel);
        });
        panel.appendChild(container);
        return;
      }
      panel.appendChild(createLinkedStageNote(entry.title, entry.message, entry.mechanism));
    });
  }

  function renderGraphFlow() {
    const snapshot = snapshotStageSelections();
    DOM.graph.innerHTML = '';
    if (!state.activeInstrument) return;

    const inst = state.activeInstrument;
    const route = state.activeRoute;
    state.routeTopology = deriveRouteTopology(inst, route);
    const topology = state.routeTopology;
    const derivedControlGroups = buildDerivedControlGroups(inst, topology, route);

    const shell = document.createElement('div');
    shell.className = 'vm-pipeline-shell';
    const pipeline = document.createElement('div');
    pipeline.className = 'vm-pipeline';
    const inspector = document.createElement('div');
    inspector.className = 'vm-inspector';
    shell.appendChild(pipeline);
    shell.appendChild(inspector);
    DOM.graph.appendChild(shell);

    if (route === 'transmitted' || route === 'brightfield' || route === 'phase') {
      const warningPanel = document.createElement('div');
      warningPanel.className = 'vm-info-card';
      warningPanel.style.borderLeft = '4px solid var(--warning)';
      warningPanel.style.margin = '10px 0';
      warningPanel.innerHTML = `
        <div class="vm-info-card-title" style="color: var(--warning);">Transmitted Light Mode Active</div>
        <div class="vm-info-card-subtitle">
          Fluorescence filter cubes and epifluorescence lasers are disabled because transmitted white-light illumination (brightfield/phase) will overpower any fluorescence emission.
        </div>
      `;
      inspector.prepend(warningPanel);
    }

    if (!derivedControlGroups.length) return;

    const pipelineStages = buildPipelineStages(derivedControlGroups);
    pipeline.innerHTML = '';
    pipeline.style.display = pipelineStages.length ? 'flex' : 'none';
    pipelineStages.forEach((stage, index) => {
      if (index > 0) {
        pipeline.appendChild(createPipeSegment(stagePipeKey(pipelineStages[index - 1].flowOrigin, stage.flowOrigin)));
      }
      pipeline.appendChild(createPipelineBadge(stage.id, stage.label));
    });

    derivedControlGroups.forEach((group) => {
      const panel = createInspectorPanel(group.id, group.label, group.subtitle);
      group.build(panel);
      inspector.appendChild(panel);
    });

    restoreStageSelections(snapshot);
    enforceValidStageOptions();
    const availableDerivedGroupIds = derivedControlGroups.map((group) => group.id);
    const preferredDerivedGroup = availableDerivedGroupIds.includes(state.activeInspectorStage) ? state.activeInspectorStage : availableDerivedGroupIds[0];
    setInspectorStage(preferredDerivedGroup);
  }

  function createLightSourceControl(mechanism) {

    const block = document.createElement('div');
    block.className = 'vm-stack vm-source-grid';
    block.dataset.stage = 'lightSources';
    block.dataset.mechanismId = mechanism.id || '';

    const title = document.createElement('div');
    title.className = 'vm-source-group-title';
    title.style.fontSize = '11px';
    title.style.fontWeight = '700';
    title.style.color = 'var(--muted)';
    title.textContent = mechanism.display_label || mechanism.name || 'Light Sources';
    block.appendChild(title);

    Object.values(positionsForRoute(mechanism, state.activeRoute)).forEach((source) => {
      const setting = ensureSourceSetting(source);
      const sourceKey = sourceSettingKey(source);
      const card = document.createElement('div');
      card.className = 'tunable-control';

      const label = document.createElement('label');
      label.style.display = 'flex';
      label.style.alignItems = 'center';
      label.style.gap = '8px';
      label.style.fontSize = '12px';
      label.style.fontWeight = '600';
      label.style.cursor = 'pointer';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = Boolean(setting.enabled);
      checkbox.dataset.routes = normalizeSourceRoutes(source).join(',');
      checkbox.addEventListener('change', () => {
        setting.enabled = checkbox.checked;
        pruneConflictingSources();
        renderGraphFlow();
        refreshOutputs();
      });
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(source.display_label || source.name || 'Source'));
      card.appendChild(label);

      const meta = document.createElement('div');
      meta.className = 'vm-mini';
      meta.textContent = [
        source.role_label ? `role: ${source.role_label}` : (source.role ? `role: ${source.role}` : ''),
        source.kind_label ? `kind: ${source.kind_label}` : (source.kind ? `kind: ${source.kind}` : ''),
        source.route_label ? `route: ${source.route_label}` : '',
        normalizeSourceRoutes(source).length ? `routes: ${normalizeSourceRoutes(source).join(', ')}` : '',
      ].filter(Boolean).join(' • ');
      if (meta.textContent) card.appendChild(meta);

      const tunableMin = numberOrNull(source.tunable_min_nm);
      const tunableMax = numberOrNull(source.tunable_max_nm);
      if (tunableMin !== null && tunableMax !== null) {
        const readout = document.createElement('div');
        readout.className = 'tunable-range-label';
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = String(Math.round(tunableMin));
        slider.max = String(Math.round(tunableMax));
        slider.step = '1';
        slider.value = String(Math.round(numberOrNull(setting.selected_wavelength_nm) ?? ((tunableMin + tunableMax) / 2)));
        slider.disabled = !setting.enabled;
        slider.addEventListener('input', () => {
          setting.selected_wavelength_nm = Number(slider.value);
          readout.textContent = `Tuned to ${slider.value} nm`;
          refreshOutputs();
        });
        readout.textContent = `Tuned to ${slider.value} nm`;
        card.appendChild(readout);
        card.appendChild(slider);
      } else if (numberOrNull(source.wavelength_nm) !== null) {
        const fixed = document.createElement('div');
        fixed.className = 'vm-mini';
        fixed.textContent = `λ = ${source.wavelength_nm} nm`;
        card.appendChild(fixed);
      }

      const powerReadout = document.createElement('div');
      powerReadout.className = 'tunable-range-label';
      const powerSlider = document.createElement('input');
      powerSlider.type = 'range';
      powerSlider.min = '0';
      powerSlider.max = '1';
      powerSlider.step = '0.01';
      powerSlider.value = String(numberOrNull(setting.user_weight) ?? 1);
      powerSlider.disabled = !setting.enabled;
      powerSlider.addEventListener('input', () => {
        setting.user_weight = Number(powerSlider.value);
        powerReadout.textContent = `Relative source power: ${Math.round(Number(powerSlider.value) * 100)}%`;
        refreshOutputs();
      });
      const syncPowerDisabled = () => {
        powerSlider.disabled = !setting.enabled;
      };
      checkbox.addEventListener('change', syncPowerDisabled);
      powerReadout.textContent = `Relative source power: ${Math.round(Number(powerSlider.value) * 100)}%`;
      card.appendChild(powerReadout);
      card.appendChild(powerSlider);

      const simultaneousLines = numberOrNull(source.simultaneous_lines_max);
      if (simultaneousLines !== null) {
        const note = document.createElement('div');
        note.className = 'vm-mini';
        note.textContent = `Supports up to ${simultaneousLines} simultaneous tuned lines.`;
        card.appendChild(note);
      }

      card.dataset.sourceKey = sourceKey;
      block.appendChild(card);
    });

    return block;
  }

  function spectralMechanismKey(stageKey, mechanism, index) {
    return `${currentInstrumentId || 'scope'}::${stageKey}::${mechanism && (mechanism.id || mechanism.name || index)}`;
  }

  function spectralArrayBounds(mechanism) {
    const min = numberOrNull(mechanism && (mechanism.band_min_nm ?? mechanism.min_nm)) ?? 350;
    const max = numberOrNull(mechanism && (mechanism.band_max_nm ?? mechanism.max_nm)) ?? 800;
    return { min, max: Math.max(max, min + 5) };
  }

  function defaultSpectralBand(mechanism, idx) {
    const bounds = spectralArrayBounds(mechanism);
    const width = Math.max(5, numberOrNull(mechanism && mechanism.default_band_width_nm) ?? 20);
    const start = Math.min(bounds.max - 1, bounds.min + (idx * 10));
    return {
      label: `Band ${idx + 1}`,
      min_nm: Math.round(start),
      max_nm: Math.round(Math.min(bounds.max, start + width)),
    };
  }

  function getSpectralBands(stageKey, mechanism, index) {
    const key = spectralMechanismKey(stageKey, mechanism, index);
    if (!state.spectralBandsByMechanism.has(key)) {
      state.spectralBandsByMechanism.set(key, [defaultSpectralBand(mechanism, 0)]);
    }
    return { key, bands: state.spectralBandsByMechanism.get(key) || [] };
  }

  function createMechanismControl(stageKey, mechanism, index) {
    if (mechanism.control_kind === 'spectral_array') {
      return createSpectralArrayControl(stageKey, mechanism, index);
    }

    if (mechanism.control_kind === 'tunable_slider') {
      const block = document.createElement('div');
      block.className = 'tunable-control';
      block.dataset.stage = stageKey;
      block.dataset.mechanismName = mechanism.name || '';
      block.dataset.mechanismId = mechanism.id || '';

      const readout = document.createElement('div');
      readout.className = 'tunable-range-label';
      const row = document.createElement('div');
      row.className = 'slider-row';
      const minInput = document.createElement('input');
      minInput.type = 'range';
      minInput.min = String(mechanism.min_nm ?? 400);
      minInput.max = String(mechanism.max_nm ?? 800);
      minInput.value = String(mechanism.default_min_nm ?? mechanism.min_nm ?? 450);
      const maxInput = document.createElement('input');
      maxInput.type = 'range';
      maxInput.min = String(mechanism.min_nm ?? 400);
      maxInput.max = String(mechanism.max_nm ?? 800);
      maxInput.value = String(mechanism.default_max_nm ?? mechanism.max_nm ?? 550);

      const update = () => {
        if (Number(minInput.value) > Number(maxInput.value)) minInput.value = maxInput.value;
        block.dataset.value = JSON.stringify({
          component_type: 'tunable',
          type: 'tunable',
          render_kind: 'tunable',
          label: `${mechanism.name || stageKey} ${minInput.value}-${maxInput.value}`,
          display_label: `${mechanism.name || stageKey} ${minInput.value}-${maxInput.value}`,
          band_start_nm: Number(minInput.value),
          band_end_nm: Number(maxInput.value),
        });
        readout.textContent = `${mechanism.control_label || mechanism.name || stageKey}: ${minInput.value}–${maxInput.value} nm`;
        refreshOutputs();
      };

      minInput.addEventListener('input', update);
      maxInput.addEventListener('input', update);
      row.appendChild(minInput);
      row.appendChild(maxInput);
      block.appendChild(readout);
      block.appendChild(row);
      update();
      return block;
    }

    const block = document.createElement('div');
    block.className = 'vm-field';
    const label = document.createElement('label');
    label.textContent = mechanism.control_label || mechanism.display_label || mechanism.name || stageKey;
    const select = document.createElement('select');
    select.dataset.stage = stageKey;
    select.dataset.mechanismName = mechanism.name || '';
    select.dataset.mechanismId = mechanism.id || '';

    const options = Array.isArray(mechanism.options) && mechanism.options.length
      ? mechanism.options.filter((option) => VM.routeMatches((option.value && option.value.__routes) || mechanism.__routes, state.activeRoute))
      : Object.entries(positionsForRoute(mechanism, state.activeRoute)).map(([slot, component]) => ({
          slot: Number(slot),
          display_label: component.display_label || component.label || `Slot ${slot}`,
          value: component,
        }));

    options.forEach((option) => {
      const opt = document.createElement('option');
      opt.value = JSON.stringify(option.value);
      opt.textContent = option.display_label || option.value && (option.value.display_label || option.value.label) || `Slot ${option.slot}`;
      if (Number.isFinite(Number(option.slot))) {
        opt.dataset.slot = String(option.slot);
      } else if (Number.isFinite(Number(option.value && option.value.slot))) {
        opt.dataset.slot = String(option.value.slot);
      }
      select.appendChild(opt);
    });
    const metadata = createMetadataBlock();
    const syncMetadata = () => updateMetadataBlock(metadata, parseJsonValue(select.value), { stage: stageKey });
    select.addEventListener('change', () => {
      select.dataset.userSet = 'true';
      syncMetadata();
      refreshOutputs();
    });
    block.appendChild(label);
    block.appendChild(select);
    block.appendChild(metadata);
    syncMetadata();
    return block;
  }


  function createSplitterControl(mechanism) {
    const block = document.createElement('div');
    block.className = 'tunable-control vm-splitter-card';
    block.dataset.stage = 'splitters';
    block.dataset.mechanismId = mechanism.id || '';

    const title = document.createElement('div');
    title.className = 'vm-stage-panel-title';
    title.style.fontSize = '12px';
    title.style.textTransform = 'none';
    title.textContent = mechanism.control_label || mechanism.display_label || mechanism.name || 'Splitter';
    block.appendChild(title);

    if (mechanism.notes) {
      const notes = document.createElement('div');
      notes.className = 'vm-mini';
      notes.textContent = mechanism.notes;
      block.appendChild(notes);
    }

    const metadata = createMetadataBlock();
    updateMetadataBlock(metadata, (mechanism.dichroic && mechanism.dichroic.positions && (mechanism.dichroic.positions[1] || mechanism.dichroic.positions['1'])) || { label: 'No splitter dichroic declared.' }, { stage: 'splitter' });
    block.appendChild(metadata);

    const branches = Array.isArray(mechanism.branches) ? mechanism.branches : [];
    const selectedBranches = ensureSplitterBranchSelection(mechanism);
    const branchList = document.createElement('div');
    branchList.className = 'vm-branch-list';

    branches.forEach((branch) => {
      const row = document.createElement('div');
      row.className = 'vm-branch-row';
      const heading = document.createElement('div');
      heading.className = 'vm-info-row';
      const titleCell = document.createElement('strong');
      titleCell.textContent = branch.label || branch.name || 'Branch';
      heading.appendChild(titleCell);
      const modeCell = document.createElement('span');
      modeCell.className = 'vm-mini';
      modeCell.textContent = cleanString(branch.mode) || 'branch';
      heading.appendChild(modeCell);
      row.appendChild(heading);

      const componentMeta = document.createElement('div');
      componentMeta.className = 'vm-mini';
      componentMeta.textContent = (branch.component && (branch.component.display_label || branch.component.label))
        ? `Filter: ${branch.component.display_label || branch.component.label}`
        : 'No branch filter declared';
      row.appendChild(componentMeta);

      const targetIds = Array.isArray(branch.target_ids) ? branch.target_ids : [];
      const targetText = targetIds.length
        ? targetIds.map((targetId) => endpointLabelForTargetId(targetId)).join(', ')
        : 'Manual branch selection';
      const targetMeta = document.createElement('div');
      targetMeta.className = 'vm-mini';
      targetMeta.textContent = `Targets: ${targetText}`;
      row.appendChild(targetMeta);

      if (mechanism.branch_selection_required) {
        const chooser = document.createElement('label');
        chooser.className = 'vm-mini';
        chooser.style.display = 'flex';
        chooser.style.alignItems = 'center';
        chooser.style.gap = '6px';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = selectedBranches.includes(cleanString(branch.id || ''));
        input.addEventListener('change', () => {
          const active = ensureSplitterBranchSelection(mechanism).slice();
          const branchId = cleanString(branch.id || '');
          const idx = active.indexOf(branchId);
          if (input.checked && idx === -1) active.push(branchId);
          if (!input.checked && idx >= 0) active.splice(idx, 1);
          if (!active.length && branchId) active.push(branchId);
          state.splitterBranchSelections.set(splitterBranchSelectionKey(mechanism), active);
          refreshOutputs();
        });
        chooser.appendChild(input);
        chooser.appendChild(document.createTextNode('Enable this branch'));
        row.appendChild(chooser);
      }

      branchList.appendChild(row);
    });

    block.appendChild(branchList);
    return block;
  }

  function createSpectralArrayControl(stageKey, mechanism, index) {
    const block = document.createElement('div');
    block.className = 'tunable-control';
    block.dataset.stage = stageKey;
    block.dataset.mechanismName = mechanism.name || '';
    block.dataset.mechanismId = mechanism.id || '';
    block.dataset.mechanismType = 'spectral_array';

    const title = document.createElement('div');
    title.className = 'tunable-range-label';
    title.textContent = `${mechanism.control_label || mechanism.name || 'Spectral Array'} Bands`;
    block.appendChild(title);

    const bounds = spectralArrayBounds(mechanism);
    const stateRef = getSpectralBands(stageKey, mechanism, index);
    const maxBands = Math.max(1, numberOrNull(mechanism && mechanism.max_bands) ?? 4);
    block.dataset.mechanismKey = stateRef.key;

    const bandWrap = document.createElement('div');
    bandWrap.style.display = 'grid';
    bandWrap.style.gap = '8px';

    stateRef.bands.forEach((band, bandIndex) => {
      const row = document.createElement('div');
      row.style.border = '1px solid var(--border)';
      row.style.borderRadius = '6px';
      row.style.padding = '6px';
      row.style.display = 'grid';
      row.style.gap = '6px';

      const top = document.createElement('div');
      top.style.display = 'flex';
      top.style.gap = '6px';
      top.style.alignItems = 'center';

      const nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.value = band.label;
      nameInput.placeholder = `Band ${bandIndex + 1}`;
      nameInput.style.flex = '1';
      nameInput.style.fontSize = '12px';
      nameInput.addEventListener('input', () => {
        stateRef.bands[bandIndex].label = nameInput.value;
        refreshOutputs();
      });
      top.appendChild(nameInput);

      if (stateRef.bands.length > 1) {
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'vm-btn';
        removeButton.style.background = 'var(--danger)';
        removeButton.style.padding = '4px 8px';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
          stateRef.bands.splice(bandIndex, 1);
          renderGraphFlow();
          refreshOutputs();
        });
        top.appendChild(removeButton);
      }
      row.appendChild(top);

      const readout = document.createElement('div');
      readout.className = 'tunable-range-label';
      row.appendChild(readout);

      const sliders = document.createElement('div');
      sliders.className = 'slider-row';
      const minInput = document.createElement('input');
      minInput.type = 'range';
      minInput.min = String(bounds.min);
      minInput.max = String(bounds.max);
      minInput.value = String(band.min_nm ?? bounds.min);
      const maxInput = document.createElement('input');
      maxInput.type = 'range';
      maxInput.min = String(bounds.min);
      maxInput.max = String(bounds.max);
      maxInput.value = String(band.max_nm ?? (Number(minInput.value) + 20));

      const updateBand = (source) => {
        let minVal = Number(minInput.value);
        let maxVal = Number(maxInput.value);
        if (minVal > maxVal) {
          if (source === 'min') maxVal = minVal;
          else minVal = maxVal;
        }
        minVal = Math.max(bounds.min, Math.min(minVal, bounds.max - 1));
        maxVal = Math.max(minVal + 1, Math.min(maxVal, bounds.max));
        minInput.value = String(Math.round(minVal));
        maxInput.value = String(Math.round(maxVal));
        stateRef.bands[bandIndex].min_nm = Number(minInput.value);
        stateRef.bands[bandIndex].max_nm = Number(maxInput.value);
        readout.textContent = `${stateRef.bands[bandIndex].label || `Band ${bandIndex + 1}`}: ${minInput.value}–${maxInput.value} nm`;
        refreshOutputs();
      };

      minInput.addEventListener('input', () => updateBand('min'));
      maxInput.addEventListener('input', () => updateBand('max'));
      sliders.appendChild(minInput);
      sliders.appendChild(maxInput);
      row.appendChild(sliders);
      updateBand('init');
      bandWrap.appendChild(row);
    });

    block.appendChild(bandWrap);

    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'vm-btn';
    addButton.style.marginTop = '4px';
    addButton.textContent = 'Add Detector Band';
    addButton.disabled = stateRef.bands.length >= maxBands;
    addButton.addEventListener('click', () => {
      if (stateRef.bands.length >= maxBands) return;
      stateRef.bands.push(defaultSpectralBand(mechanism, stateRef.bands.length));
      renderGraphFlow();
      refreshOutputs();
    });
    block.appendChild(addButton);
    return block;
  }


  function createDetectorControls(mechanism) {
    return Object.values(positionsForRoute(mechanism, state.activeRoute)).map((detector) =>
      createDetectorControl(mechanism, detector)
    );
  }

  function createDetectorControl(mechanism, detector) {
    if (!detector) return document.createElement('div');
    const setting = ensureDetectorSetting(mechanism, detector);
    const detectorClass = detector.detector_class || VM.detectorClass(detector.kind || detector.endpoint_type);
    const endpointType = cleanString(detector.kind_label || detector.endpoint_type_label || detector.endpoint_type || detectorClass || detector.kind || 'detector').replace(/_/g, ' ');
    const labelText = mechanism.display_label || detector.display_label || detector.name || 'Detector';
    const block = document.createElement('div');
    block.className = 'tunable-control';
    block.dataset.stage = 'detectors';
    block.dataset.mechanismId = mechanism.id || '';

    const label = document.createElement('label');
    label.style.display = 'flex';
    label.style.alignItems = 'center';
    label.style.gap = '8px';
    label.style.fontSize = '12px';
    label.style.fontWeight = '600';
    label.style.cursor = 'pointer';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = Boolean(setting.enabled);
    checkbox.addEventListener('change', () => {
      setting.enabled = checkbox.checked;
      syncDetectorMetadata();
      refreshOutputs();
    });
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(labelText));
    block.appendChild(label);

    const meta = document.createElement('div');
    meta.className = 'vm-mini';
    meta.textContent = `${endpointType}${detector.supports_time_gating ? ' • time-gated' : ''}`;
    block.appendChild(meta);
    const metadata = createMetadataBlock();
    const syncDetectorMetadata = () => updateMetadataBlock(metadata, {
      ...detector,
      detector_class: detectorClass,
      collection_min_nm: setting.collection_min_nm,
      collection_max_nm: setting.collection_max_nm,
    }, { stage: 'detector' });
    block.appendChild(metadata);

    const showsWindowControls = !['camera', 'camera_port', 'eyepiece'].includes(detectorClass);
    if (showsWindowControls) {
      setting.collection_enabled = true;
      const collectionToggle = document.createElement('label');
      collectionToggle.className = 'vm-mini';
      collectionToggle.style.display = 'flex';
      collectionToggle.style.alignItems = 'center';
      collectionToggle.style.gap = '6px';
      collectionToggle.style.marginTop = '4px';
      const toggleInput = document.createElement('input');
      toggleInput.type = 'checkbox';
      toggleInput.checked = true;
      toggleInput.disabled = true;
      collectionToggle.appendChild(toggleInput);
      collectionToggle.appendChild(document.createTextNode('Detector collection window (always applied)'));
      block.appendChild(collectionToggle);

      const minReadout = document.createElement('div');
      minReadout.className = 'vm-mini';
      const minSlider = document.createElement('input');
      minSlider.type = 'range';
      minSlider.min = '350';
      minSlider.max = '850';
      minSlider.step = '1';
      minSlider.value = String(Math.round(numberOrNull(setting.collection_min_nm) ?? 500));
      minSlider.addEventListener('input', () => {
        const proposedMin = Number(minSlider.value);
        const currentMax = numberOrNull(setting.collection_max_nm) ?? 700;
        setting.collection_min_nm = Math.min(proposedMin, currentMax - 1);
        minSlider.value = String(Math.round(setting.collection_min_nm));
        if (numberOrNull(setting.collection_max_nm) !== null && Number(setting.collection_max_nm) <= setting.collection_min_nm) {
          setting.collection_max_nm = setting.collection_min_nm + 1;
          maxSlider.value = String(Math.round(setting.collection_max_nm));
        }
        minReadout.textContent = `Collection min: ${Math.round(Number(minSlider.value))} nm`;
        maxReadout.textContent = `Collection max: ${Math.round(Number(maxSlider.value))} nm`;
        syncDetectorMetadata();
        refreshOutputs();
      });
      minReadout.textContent = `Collection min: ${Math.round(Number(minSlider.value))} nm`;
      block.appendChild(minReadout);
      block.appendChild(minSlider);

      const maxReadout = document.createElement('div');
      maxReadout.className = 'vm-mini';
      const maxSlider = document.createElement('input');
      maxSlider.type = 'range';
      maxSlider.min = '351';
      maxSlider.max = '900';
      maxSlider.step = '1';
      maxSlider.value = String(Math.round(numberOrNull(setting.collection_max_nm) ?? 540));
      maxSlider.addEventListener('input', () => {
        const proposedMax = Number(maxSlider.value);
        const currentMin = numberOrNull(setting.collection_min_nm) ?? 350;
        setting.collection_max_nm = Math.max(proposedMax, currentMin + 1);
        maxSlider.value = String(Math.round(setting.collection_max_nm));
        if (numberOrNull(setting.collection_min_nm) !== null && Number(setting.collection_min_nm) >= setting.collection_max_nm) {
          setting.collection_min_nm = setting.collection_max_nm - 1;
          minSlider.value = String(Math.round(setting.collection_min_nm));
        }
        minReadout.textContent = `Collection min: ${Math.round(Number(minSlider.value))} nm`;
        maxReadout.textContent = `Collection max: ${Math.round(Number(maxSlider.value))} nm`;
        syncDetectorMetadata();
        refreshOutputs();
      });
      maxReadout.textContent = `Collection max: ${Math.round(Number(maxSlider.value))} nm`;
      block.appendChild(maxReadout);
      block.appendChild(maxSlider);
    } else if (detectorClass === 'eyepiece') {
      const info = document.createElement('div');
      info.className = 'vm-mini';
      info.textContent = 'Visual endpoint • fixed visible-band collection';
      block.appendChild(info);
    } else if (detectorClass === 'camera_port') {
      const info = document.createElement('div');
      info.className = 'vm-mini';
      info.textContent = 'Passive camera port endpoint • no extra collection window';
      block.appendChild(info);
    }

    syncDetectorMetadata();

    if (detector.supports_time_gating) {
      const gate = document.createElement('div');
      gate.className = 'vm-mini';
      const delay = numberOrNull(detector.default_gating_delay_ns) ?? 0;
      const width = numberOrNull(detector.default_gate_width_ns) ?? 0;
      gate.textContent = `Default gate: delay ${delay} ns, width ${width} ns`;
      block.appendChild(gate);
    }

    return block;
  }

  function buildSelectionMapFromDom() {
    const selectionMap = {};
    Array.from(DOM.graph.querySelectorAll('select[data-stage][data-mechanism-id]')).forEach((select) => {
      const mechanismId = select.dataset.mechanismId;
      const slot = Number(select.selectedOptions[0] && select.selectedOptions[0].dataset.slot);
      if (mechanismId && Number.isFinite(slot)) {
        selectionMap[mechanismId] = slot;
      }
    });
    return selectionMap;
  }

  function enforceValidStageOptions() {
    if (!state.activeInstrument || !Array.isArray(state.activeInstrument.validPaths) || !state.activeInstrument.validPaths.length) {
      return;
    }
    for (let pass = 0; pass < 3; pass += 1) {
      let changed = false;
      const currentSelection = buildSelectionMapFromDom();
      Array.from(DOM.graph.querySelectorAll('select[data-stage][data-mechanism-id]')).forEach((select) => {
        const mechanismId = select.dataset.mechanismId;
        if (!mechanismId) return;
        Array.from(select.options).forEach((option) => {
          const slot = Number(option.dataset.slot);
          if (!Number.isFinite(slot)) {
            option.disabled = false;
            return;
          }
          const trialSelection = { ...currentSelection, [mechanismId]: slot };
          option.disabled = !VM.selectionIsValid(state.activeInstrument.validPaths, trialSelection);
        });
        const chosen = select.selectedOptions[0];
        if (chosen && chosen.disabled) {
          const replacement = Array.from(select.options).find((option) => !option.disabled);
          if (replacement) {
            select.value = replacement.value;
            changed = true;
          }
        }
      });
      if (!changed) break;
    }
  }

  function expandCubeSelection(cubePosition, mechanismName) {
    const expanded = [];
    const excitation = cubePosition.excitation_filter || cubePosition.excitation || cubePosition.ex;
    const dichroic = cubePosition.dichroic_filter || cubePosition.dichroic || cubePosition.di || cubePosition.dichroic;
    const emission = cubePosition.emission_filter || cubePosition.emission || cubePosition.em;
    if (excitation) expanded.push({ stage: 'excitation', name: `${mechanismName} (Cube Ex)`, component: excitation });
    if (dichroic) expanded.push({ stage: 'dichroic', name: `${mechanismName} (Cube Di)`, component: dichroic });
    if (emission) expanded.push({ stage: 'emission', name: `${mechanismName} (Cube Em)`, component: emission });
    return expanded;
  }

  function collectRuntimeSelection() {
    const topology = state.routeTopology || deriveRouteTopology(state.activeInstrument, state.activeRoute);
    const selection = {
      sources: [],
      excitation: [],
      dichroic: [],
      emission: [],
      splitters: [],
      detectors: [],
      selectionMap: buildSelectionMapFromDom(),
      debugSelections: [],
    };

    const sourceMechanisms = topology && Array.isArray(topology.sourceMechanisms)
      ? topology.sourceMechanisms
      : mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, state.activeRoute);
    sourceMechanisms.forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, state.activeRoute)).forEach((source) => {
        const setting = ensureSourceSetting(source);
        if (!setting.enabled) return;
        selection.sources.push({
          ...source,
          selected_wavelength_nm: numberOrNull(setting.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm),
          user_weight: numberOrNull(setting.user_weight) ?? numberOrNull(source.power_weight) ?? 1,
        });
      });
    });

    const pushStageComponent = (stage, name, component) => {
      if (!component || typeof component !== 'object') return;
      const enriched = {
        ...component,
        label: component.label || component.display_label || name,
        display_label: component.display_label || component.label || name,
      };
      if (stage === 'excitation') selection.excitation.push(enriched);
      else if (stage === 'dichroic') selection.dichroic.push(enriched);
      else if (stage === 'emission') selection.emission.push(enriched);
      else if (stage === 'splitters') selection.splitters.push(enriched);
      selection.debugSelections.push({ stage, name, component: enriched });
    };

    Array.from(DOM.graph.querySelectorAll('select[data-stage]')).forEach((select) => {
      if (!select.value) return;
      let value;
      try {
        value = JSON.parse(select.value);
      } catch (error) {
        return;
      }
      const stage = select.dataset.stage;
      const mechanismName = select.dataset.mechanismName || stage;
      if (stage === 'cube') {
        selection.debugSelections.push({ stage: 'cube', name: mechanismName, component: value });
        expandCubeSelection(value, mechanismName).forEach((entry) => pushStageComponent(entry.stage, entry.name, entry.component));
      } else if (stage !== 'detectors' && stage !== 'splitters') {
        pushStageComponent(stage, mechanismName, value);
      }
    });

    Array.from(DOM.graph.querySelectorAll('.tunable-control[data-stage]')).forEach((block) => {
      const stage = block.dataset.stage;
      const mechanismName = block.dataset.mechanismName || stage;
      if (block.dataset.mechanismType === 'spectral_array') {
        const bands = state.spectralBandsByMechanism.get(block.dataset.mechanismKey || '') || [];
        if (!bands.length) return;
        pushStageComponent(stage, mechanismName, {
          component_type: 'multiband_bandpass',
          type: 'multiband_bandpass',
          render_kind: 'band',
          label: `${mechanismName} spectral array`,
          display_label: `${mechanismName} spectral array`,
          bands: bands.map((band) => ({
            center_nm: (Number(band.min_nm) + Number(band.max_nm)) / 2,
            width_nm: Math.max(1, Number(band.max_nm) - Number(band.min_nm)),
            label: band.label,
          })),
        });
      } else if (block.dataset.value) {
        try {
          pushStageComponent(stage, mechanismName, JSON.parse(block.dataset.value));
        } catch (error) {
          // ignore invalid tunable payloads
        }
      }
    });


    const splitterMechanisms = ((topology && topology.traversal ? topology.traversal.detection : []) || [])
      .filter((entry) => entry && entry.kind === 'control' && entry.stageKey === 'splitters' && entry.mechanism)
      .map((entry) => entry.mechanism);
    splitterMechanisms.forEach((mechanism) => {
      const selectedBranchIds = ensureSplitterBranchSelection(mechanism);
      selection.splitters.push({
        id: mechanism.id,
        label: mechanism.display_label || mechanism.name || 'Splitter',
        dichroic: mechanism.dichroic,
        branches: Array.isArray(mechanism.branches) ? mechanism.branches.map((branch) => ({ ...branch })) : [],
        branch_selection_required: Boolean(mechanism.branch_selection_required),
        selected_branch_ids: Array.isArray(selectedBranchIds) ? selectedBranchIds.slice() : [],
      });
      selection.debugSelections.push({ stage: 'splitters', name: mechanism.name || mechanism.display_label || 'Splitter', component: mechanism });
    });

    const detectorMechanisms = topology && Array.isArray(topology.endpointMechanisms)
      ? topology.endpointMechanisms
      : mechanismsForRoute(state.activeInstrument && state.activeInstrument.detectors, state.activeRoute);
    detectorMechanisms.forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, state.activeRoute)).forEach((detector) => {
        const setting = ensureDetectorSetting(mechanism, detector);
        if (!setting.enabled) return;
        selection.detectors.push({
          ...detector,
          collection_enabled: Boolean(setting.collection_enabled),
          collection_min_nm: numberOrNull(setting.collection_min_nm),
          collection_max_nm: numberOrNull(setting.collection_max_nm),
        });
      });
    });

    return selection;
  }


  function initLineChart(canvas, yTitle) {
    return new Chart(canvas, {
      type: 'line',
      data: { datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          tooltip: { enabled: true },
          legend: { position: 'bottom', labels: { boxWidth: 12 } },
        },
        scales: {
          x: { type: 'linear', min: 350, max: 800, title: { display: true, text: 'Wavelength (nm)' } },
          y: { min: 0, max: 105, title: { display: true, text: yTitle } },
        },
      },
    });
  }

  function initBarChart(canvas) {
    return new Chart(canvas, {
      type: 'bar',
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { enabled: true },
        },
        scales: {
          x: { ticks: { autoSkip: false } },
          y: { beginAtZero: true, title: { display: true, text: 'Detected intensity (a.u.)' } },
        },
      },
    });
  }

  function initCharts() {
    referenceChart = initLineChart(DOM.referenceChart, 'Relative absorption / excitation (%)');
    propagationChart = initLineChart(DOM.propagationChart, 'Relative emission / collection (%)');
    detectionChart = initBarChart(DOM.detectionChart);
  }

  function chartDatasetFromGrid(label, grid, values, style) {
    return {
      label,
      data: grid.map((wavelength, index) => ({ x: wavelength, y: Math.min(105, Math.max(0, values[index] || 0)) })),
      fill: false,
      pointRadius: 0,
      tension: 0.15,
      borderWidth: 2,
      ...style,
    };
  }

  function maxWavelengthFromPoints(points) {
    if (!Array.isArray(points) || !points.length) return null;
    return Math.max(...points.map((point) => numberOrNull(point.x) ?? 0));
  }

  function determineChartMax(selection) {
    let maxWavelength = 800;
    selection.sources.forEach((source) => {
      maxWavelength = Math.max(
        maxWavelength,
        numberOrNull(source.selected_wavelength_nm) ?? 0,
        numberOrNull(source.wavelength_nm) ?? 0,
        numberOrNull(source.tunable_max_nm) ?? 0
      );
    });
    mapToArray(state.loadedProteins).forEach((fluorophore) => {
      const spectra = VM.fluorophoreSpectra(fluorophore, { preferTwoPhoton: state.preferTwoPhoton });
      maxWavelength = Math.max(
        maxWavelength,
        maxWavelengthFromPoints(spectra.ex) ?? 0,
        maxWavelengthFromPoints(spectra.em) ?? 0
      );
    });
    return Math.min(1700, Math.max(800, Math.ceil(maxWavelength / 50) * 50));
  }

  function spectrumScale(curves) {
    const globalMax = Math.max(0.001, ...curves.flatMap((values) => Array.isArray(values) ? values : []));
    return globalMax;
  }

  function asPercentArray(values, scale) {
    const denominator = Math.max(0.001, scale || 1);
    return (Array.isArray(values) ? values : []).map((value) => (Number(value || 0) / denominator) * 100);
  }

  function sumSpectra(entries, field, grid) {
    return (Array.isArray(entries) ? entries : []).reduce((accumulator, entry) => {
      const values = Array.isArray(entry && entry[field]) ? entry[field] : [];
      return accumulator.map((current, index) => current + (values[index] || 0));
    }, grid.map(() => 0));
  }

  function aggregateSpectraByLabel(entries, field, grid, dedupeKeyField = null) {
    const grouped = new Map();
    const seenKeys = new Set();
    (Array.isArray(entries) ? entries : []).forEach((entry) => {
      const dedupeKey = dedupeKeyField ? cleanString(entry && entry[dedupeKeyField]) : '';
      if (dedupeKeyField && dedupeKey && seenKeys.has(dedupeKey)) return;
      if (dedupeKeyField && dedupeKey) seenKeys.add(dedupeKey);
      const key = entry.pathLabel || entry.label || entry.detectorLabel || 'Path';
      if (!grouped.has(key)) {
        grouped.set(key, { label: key, values: grid.map(() => 0), entry });
      }
      const target = grouped.get(key);
      const values = Array.isArray(entry && entry[field]) ? entry[field] : [];
      target.values = target.values.map((current, index) => current + (values[index] || 0));
    });
    return Array.from(grouped.values());
  }

  function combinedMask(components, grid, mode) {
    return (Array.isArray(components) ? components : []).reduce((accumulator, component) => {
      const mask = VM.componentMask(component, grid, { mode });
      return accumulator.map((value, index) => value * (mask[index] || 0));
    }, grid.map(() => 1));
  }

  function baselineMaskDataset(label, grid, maskValues, color, rowIndex = 0) {
    const baseline = 3 + (rowIndex * 4);
    return {
      label,
      data: grid.map((wavelength, index) => ({
        x: wavelength,
        y: (maskValues[index] || 0) > 0.05 ? baseline : null,
      })),
      fill: false,
      pointRadius: 0,
      tension: 0,
      borderWidth: 6,
      borderColor: color,
      spanGaps: false,
      order: -30,
    };
  }

  function sourceReferenceDatasets(selection, grid) {
    const datasets = [];
    const excitationMask = combinedMask([...(selection.excitation || []), ...(selection.dichroic || [])], grid, 'excitation');
    selection.sources.forEach((source) => {
      const wavelength = numberOrNull(source.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm);
      const color = source.role === 'depletion' ? '#dc2626' : colorHex(wavelength || 520);
      const atSample = VM.sourceSpectrum(source, grid).map((value, index) => value * (excitationMask[index] || 0));
      if (!atSample.some((value) => value > 1e-6)) return;
      datasets.push(chartDatasetFromGrid(`${source.display_label || source.name || 'Source'} at sample`, grid, asPercentArray(atSample, 1), {
        borderColor: color,
        backgroundColor: rgbaFromHex(color, 0.12),
        borderWidth: 2,
        fill: false,
        tension: 0,
      }));
    });
    return datasets;
  }

  function bestPathEntriesByFluorophore(simulation) {
    const pathEntries = Array.isArray(simulation && simulation.pathSpectra) ? simulation.pathSpectra : [];
    const results = Array.isArray(simulation && simulation.results) ? simulation.results : [];
    const bestByFluor = new Map();
    results.forEach((row) => {
      const current = bestByFluor.get(row.fluorophoreKey);
      if (!current || Number(row.detectorWeightedIntensity || 0) > Number(current.detectorWeightedIntensity || 0)) {
        bestByFluor.set(row.fluorophoreKey, row);
      }
    });
    return Array.from(bestByFluor.values()).map((result) => {
      const path = pathEntries.find((entry) => entry.fluorophoreKey === result.fluorophoreKey && entry.pathKey === result.pathKey);
      return path ? { result, path } : null;
    }).filter(Boolean);
  }

  function renderReferenceSpectra(selection, simulation) {
    if (!referenceChart) return;
    const chartMax = determineChartMax(selection);
    const grid = Array.isArray(simulation && simulation.grid)
      ? simulation.grid
      : VM.wavelengthGrid({ min_nm: 350, max_nm: chartMax, step_nm: 2 });
    const emissionEntries = Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [];
    const excitationMask = combinedMask([...(selection.excitation || []), ...(selection.dichroic || [])], grid, 'excitation');
    const datasets = [baselineMaskDataset('Excitation passband', grid, excitationMask, 'rgba(37, 99, 235, 0.9)', 0), ...sourceReferenceDatasets(selection, grid)];

    emissionEntries.forEach((entry) => {
      const fluor = mapToArray(state.loadedProteins).find((item) => item.key === entry.fluorophoreKey);
      const color = colorHex((fluor && fluor.exMax) || 520);
      const absorptionSpectrum = Array.isArray(entry.absorptionSpectrum) ? entry.absorptionSpectrum : [];
      if (absorptionSpectrum.some((value) => value > 1e-6)) {
        datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} absorption`, grid, asPercentArray(absorptionSpectrum, 1), {
          borderColor: color,
          borderDash: [4, 3],
          borderWidth: 2,
          fill: false,
          backgroundColor: rgbaFromHex(color, 0.04),
        }));
      }
    });

    const excitationAtSample = Array.isArray(simulation && simulation.excitationAtSample) ? simulation.excitationAtSample : [];
    if (selection.sources.length && !excitationAtSample.some((value) => value > 1e-6)) {
      setInlineStatus(DOM.referenceStatus, 'Selected excitation optics block the current source before it reaches the sample.', 'warning');
    } else if (!selection.sources.length) {
      setInlineStatus(DOM.referenceStatus, 'Enable an excitation source to see light at the sample.');
    } else {
      setInlineStatus(DOM.referenceStatus, '');
    }

    referenceChart.data.datasets = datasets;
    referenceChart.options.scales.x.max = chartMax;
    referenceChart.update();
  }

  function renderPropagationPanel(selection, simulation) {
    if (!propagationChart) return;
    const chartMax = determineChartMax(selection);
    const grid = Array.isArray(simulation && simulation.grid) ? simulation.grid : VM.wavelengthGrid({ min_nm: 350, max_nm: chartMax, step_nm: 2 });
    const emissionEntries = Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [];
    const bestPaths = bestPathEntriesByFluorophore(simulation);
    const emissionMask = combinedMask([...(selection.dichroic || []), ...(selection.emission || [])], grid, 'emission');
    const datasets = [baselineMaskDataset('Emission passband', grid, emissionMask, 'rgba(5, 150, 105, 0.85)', 0)];

    bestPaths.forEach(({ result, path }, index) => {
      datasets.push(baselineMaskDataset(`${result.detectorLabel} collection`, grid, path.collectionMask || grid.map(() => 0), 'rgba(148, 163, 184, 0.95)', index + 1));
    });

    emissionEntries.forEach((entry) => {
      const fluor = mapToArray(state.loadedProteins).find((item) => item.key === entry.fluorophoreKey);
      const color = colorHex((fluor && fluor.emMax) || 520);
      const fullEmission = Array.isArray(entry.generatedSpectrum) ? entry.generatedSpectrum : [];
      const postOptics = Array.isArray(entry.postOpticsSpectrum) ? entry.postOpticsSpectrum : [];
      if (fullEmission.some((value) => value > 1e-6)) {
        datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} full emission`, grid, asPercentArray(fullEmission, 1), {
          borderColor: color,
          borderDash: [4, 3],
          borderWidth: 1.8,
          fill: false,
        }));
      }
      if (postOptics.some((value) => value > 1e-6)) {
        datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} after collection filters`, grid, asPercentArray(postOptics, 1), {
          borderColor: color,
          backgroundColor: rgbaFromHex(color, 0.18),
          borderWidth: 2,
          fill: true,
          tension: 0.1,
        }));
      }
    });

    bestPaths.forEach(({ result, path }) => {
      const fluor = mapToArray(state.loadedProteins).find((item) => item.key === result.fluorophoreKey);
      const color = colorHex((fluor && fluor.emMax) || 520);
      const collected = Array.isArray(path.spectrum) ? path.spectrum : [];
      if (collected.some((value) => value > 1e-6)) {
        datasets.push(chartDatasetFromGrid(`${result.fluorophoreName} collected at ${result.detectorLabel}`, grid, asPercentArray(collected, 1), {
          borderColor: color,
          backgroundColor: rgbaFromHex(color, 0.34),
          borderWidth: 2.2,
          fill: true,
          tension: 0.1,
        }));
      }
    });

    if (!bestPaths.length && emissionEntries.length) {
      setInlineStatus(DOM.emissionStatus, 'No detector path is currently collecting emitted light.', 'warning');
    } else if (!emissionEntries.length) {
      setInlineStatus(DOM.emissionStatus, 'Load a fluorophore and enable excitation to display emission.', 'info');
    } else {
      const blocked = bestPaths.every(({ path }) => !Array.isArray(path.spectrum) || !path.spectrum.some((value) => value > 1e-6));
      setInlineStatus(DOM.emissionStatus, blocked ? 'Emission is generated but blocked by the collection path.' : '', blocked ? 'warning' : 'info');
    }

    propagationChart.data.datasets = datasets;
    propagationChart.options.scales.x.max = chartMax;
    propagationChart.update();
  }

  function averageSpectrumCurves(curves, grid) {
    if (!Array.isArray(curves) || !curves.length) return grid.map(() => 0);
    const sum = grid.map(() => 0);
    curves.forEach((curve) => {
      curve.forEach((value, index) => {
        sum[index] += value || 0;
      });
    });
    return sum.map((value) => value / curves.length);
  }

  function currentSourceSpectrum(grid) {
    const spectra = [];

    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, state.activeRoute).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, state.activeRoute)).forEach((source) => {
        const setting = ensureSourceSetting(source);
        if (!setting.enabled) return;

        const raw = VM.sourceSpectrum({
          ...source,
          selected_wavelength_nm: numberOrNull(setting.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm),
        }, grid);

        const weight = Math.max(0, numberOrNull(setting.user_weight) ?? numberOrNull(source.power_weight) ?? 1);
        spectra.push({ values: raw.map((value) => value * weight) });
      });
    });

    return sumSpectra(spectra, 'values', grid);
  }

  function meanFluorophoreCurve(grid, type) {
    const curves = mapToArray(state.loadedProteins).map((fluorophore) => {
      const spectra = VM.fluorophoreSpectra(fluorophore, { preferTwoPhoton: state.preferTwoPhoton });
      const points = type === 'emission' ? spectra.em : spectra.ex;
      return VM.normalizePoints(points).length ? grid.map((wavelength) => 0) : null;
    }).filter(Boolean);
    const normalized = mapToArray(state.loadedProteins).map((fluorophore) => {
      const spectra = VM.fluorophoreSpectra(fluorophore, { preferTwoPhoton: state.preferTwoPhoton });
      const points = type === 'emission' ? spectra.em : spectra.ex;
      const max = Math.max(1, ...VM.normalizePoints(points).map((point) => point.y || 0));
      return grid.map((wavelength) => {
        const pts = VM.normalizePoints(points);
        if (!pts.length) return 0;
        let value = pts[0].y;
        if (wavelength <= pts[0].x) value = pts[0].y;
        else if (wavelength >= pts[pts.length - 1].x) value = pts[pts.length - 1].y;
        else {
          for (let index = 0; index < pts.length - 1; index += 1) {
            const left = pts[index];
            const right = pts[index + 1];
            if (wavelength < left.x || wavelength > right.x) continue;
            const ratio = (wavelength - left.x) / Math.max(1e-9, right.x - left.x);
            value = left.y + ((right.y - left.y) * ratio);
            break;
          }
        }
        return value / max;
      });
    }).filter(Boolean);
    return averageSpectrumCurves(normalized, grid);
  }

  function integrated(values, grid) {
    if (!Array.isArray(values) || values.length !== grid.length || values.length < 2) return 0;
    let area = 0;
    for (let index = 0; index < values.length - 1; index += 1) {
      area += ((values[index] || 0) + (values[index + 1] || 0)) * (grid[index + 1] - grid[index]) / 2;
    }
    return area;
  }

  function multiply(left, right) {
    return left.map((value, index) => value * (right[index] || 0));
  }

  function optionComponentsForStage(stage, optionValue, mechanismName) {
    if (!optionValue || typeof optionValue !== 'object') return [];
    if (stage === 'cube') {
      return expandCubeSelection(optionValue, mechanismName).map((entry) => ({ ...entry.component, __stage: entry.stage }));
    }
    return [{ ...optionValue, __stage: stage }];
  }

  function applyComponentsToSpectrum(spectrum, components, grid, mode) {
    let values = spectrum.slice();
    (Array.isArray(components) ? components : []).forEach((component) => {
      values = values.map((value, index) => value * ((VM.componentMask(component, grid, { mode })[index]) || 0));
    });
    return values;
  }

  function scoreStageOption(stage, mechanismName, optionValue, excitationSpectrum, emissionSpectrum, grid) {
    const components = optionComponentsForStage(stage, optionValue, mechanismName);
    if (!components.length) return -1;
    let excitationScore = 0;
    let emissionScore = 0;
    const exComponents = components.filter((component) => component.__stage === 'excitation' || component.__stage === 'dichroic');
    const emComponents = components.filter((component) => component.__stage === 'dichroic' || component.__stage === 'emission');
    if (excitationSpectrum) {
      const output = applyComponentsToSpectrum(excitationSpectrum, exComponents, grid, 'excitation');
      excitationScore = integrated(output, grid);
    }
    if (emissionSpectrum) {
      const output = applyComponentsToSpectrum(emissionSpectrum, emComponents, grid, 'emission');
      emissionScore = integrated(output, grid);
    }
    if (stage === 'excitation' || stage === 'cube' || stage === 'dichroic') {
      return (excitationScore * 3) + emissionScore;
    }
    return emissionScore + (excitationScore * 0.25);
  }

  function autoRepairBlockedPath(selection, simulation) {
    if (!state.activeInstrument || !state.loadedProteins.size || !selection.sources.length) return false;
    const noExcitation = !Array.isArray(simulation && simulation.excitationAtSample) || !simulation.excitationAtSample.some((value) => value > 1e-6);
    const noDetection = !Array.isArray(simulation && simulation.results) || !simulation.results.some((result) => Number(result.detectorWeightedIntensity || 0) > 1e-6);
    if (!noExcitation && !noDetection) return false;

    const grid = Array.isArray(simulation && simulation.grid) && simulation.grid.length
      ? simulation.grid
      : VM.wavelengthGrid(state.activeInstrument.metadata && state.activeInstrument.metadata.wavelength_grid);
    const sourceSpectrum = currentSourceSpectrum(grid);
    if (!sourceSpectrum.some((value) => value > 0)) return false;
    const exCurve = meanFluorophoreCurve(grid, 'excitation');
    const emCurve = meanFluorophoreCurve(grid, 'emission');
    let excitationProbe = multiply(sourceSpectrum, exCurve);
    let emissionProbe = emCurve.slice();
    let changed = false;

    Array.from(DOM.graph.querySelectorAll('select[data-stage]')).forEach((select) => {
      if (select.dataset.userSet === 'true' || !select.options.length) return;
      const stage = select.dataset.stage;
      if (stage === 'detectors' || stage === 'splitters') return;
      const mechanismName = select.dataset.mechanismName || stage;
      let bestValue = select.value;
      let bestScore = -Infinity;
      Array.from(select.options).forEach((option) => {
        let parsed;
        try {
          parsed = JSON.parse(option.value);
        } catch (error) {
          return;
        }
        const score = scoreStageOption(stage, mechanismName, parsed, excitationProbe, emissionProbe, grid);
        if (score > bestScore) {
          bestScore = score;
          bestValue = option.value;
        }
      });
      if (bestValue && select.value !== bestValue) {
        select.value = bestValue;
        changed = true;
      }
      let parsedCurrent = null;
      try {
        parsedCurrent = JSON.parse(select.value);
      } catch (error) {
        parsedCurrent = null;
      }
      const components = optionComponentsForStage(stage, parsedCurrent, mechanismName);
      const exComponents = components.filter((component) => component.__stage === 'excitation' || component.__stage === 'dichroic');
      const emComponents = components.filter((component) => component.__stage === 'dichroic' || component.__stage === 'emission');
      if (exComponents.length) excitationProbe = applyComponentsToSpectrum(excitationProbe, exComponents, grid, 'excitation');
      if (emComponents.length) emissionProbe = applyComponentsToSpectrum(emissionProbe, emComponents, grid, 'emission');
    });

    return changed;
  }

  function renderSummary(selection, simulation) {
    const fluorText = mapToArray(state.loadedProteins).map((fluorophore) => {
      const stateSuffix = fluorophore.activeStateName && fluorophore.states && fluorophore.states.length > 1
        ? ` (${fluorophore.activeStateName})`
        : '';
      const spectraSuffix = fluorophore.spectraSource ? ` • spectra ${describeSpectraSource(fluorophore.spectraSource)}` : '';
      return `${fluorophore.name}${stateSuffix}${spectraSuffix}`;
    }).join(', ') || 'None';
    const sourceText = selection.sources.map((source) => {
      const wavelength = numberOrNull(source.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm);
      const lambdaText = wavelength !== null ? ` @ ${Math.round(wavelength)} nm` : '';
      return `${source.display_label || source.name || 'Source'}${lambdaText}`;
    }).join(', ') || 'None';
    const detectorText = selection.detectors.map((detector) => {
      const minNm = numberOrNull(detector.collection_min_nm);
      const maxNm = numberOrNull(detector.collection_max_nm);
      const window = detector.collection_enabled && minNm !== null && maxNm !== null
        ? ` • ${Math.round(minNm)}-${Math.round(maxNm)} nm`
        : '';
      return `${detector.display_label || detector.name || 'Endpoint'}${window}`;
    }).join(', ') || 'None';
    const opticalStages = selection.debugSelections.map((entry) => entry.name).join(' → ') || 'No stage optics selected';
    const results = Array.isArray(simulation && simulation.results) ? simulation.results : [];
    const stedText = uniqueTexts(results
      .filter((result) => result.sted && result.sted.applied)
      .map((result) => `${result.fluorophoreName}: ${result.sted.label} via ${result.sted.sourceLabel}`))
      .join('; ') || 'No depletion source selected';
    const recommendationsText = uniqueTexts(results
      .slice()
      .sort((left, right) => (right.planningScore || 0) - (left.planningScore || 0))
      .filter((result, index, rows) => rows.findIndex((candidate) => candidate.fluorophoreKey === result.fluorophoreKey) === index)
      .map((result) => `${result.fluorophoreName}: ${result.pathLabel} (${result.qualityLabel})`))
      .join('; ') || 'Load a fluorophore to rank detector paths';
    const leakageWarnings = uniqueTexts(results
      .filter((result) => result.excitationLeakageWarningLevel === 'high' || result.excitationLeakageWarningLevel === 'moderate')
      .map((result) => `${result.pathLabel}: ${result.laserLeakageNote}`))
      .join(' ');
    const validity = simulation && simulation.validSelection === false
      ? '<span style="color:var(--danger);font-weight:700;">Invalid mechanical path</span>'
      : '<span style="color:var(--primary);font-weight:700;">Valid path</span>';

    DOM.summary.innerHTML = [
      `<div><strong>Route:</strong> ${normalizeRouteLabel(state.activeRoute)} • ${validity}</div>`,
      `<div><strong>Fluorophores:</strong> ${fluorText}</div>`,
      `<div><strong>Sources:</strong> ${sourceText}</div>`,
      `<div><strong>Detectors / endpoints:</strong> ${detectorText}</div>`,
      `<div><strong>Optical path:</strong> ${opticalStages}</div>`,
      `<div><strong>STED pairing:</strong> ${stedText}</div>`,
      `<div><strong>Recommended paths:</strong> ${recommendationsText}</div>`,
      leakageWarnings ? `<div><strong>Leakage warning:</strong> <span style="color:var(--danger);font-weight:600;">${leakageWarnings}</span></div>` : '',
    ].filter(Boolean).join('');
  }

  function renderDetectionChart(simulation) {
    if (!detectionChart) return;
    const results = Array.isArray(simulation && simulation.results) ? simulation.results : [];
    if (!results.length) {
      detectionChart.data.labels = [];
      detectionChart.data.datasets = [];
      detectionChart.update();
      return;
    }
    const fluorLabels = Array.from(new Set(results.map((row) => row.fluorophoreName)));
    const pathLabels = Array.from(new Set(results.map((row) => row.pathLabel)));
    const palette = ['rgba(37, 99, 235, 0.75)', 'rgba(124, 58, 237, 0.75)', 'rgba(234, 88, 12, 0.75)', 'rgba(15, 118, 110, 0.75)', 'rgba(190, 24, 93, 0.75)'];
    detectionChart.data.labels = fluorLabels;
    detectionChart.data.datasets = pathLabels.map((pathLabel, index) => ({
      label: pathLabel,
      data: fluorLabels.map((fluorName) => results.filter((row) => row.fluorophoreName === fluorName && row.pathLabel === pathLabel).reduce((sum, row) => sum + Number(row.detectorWeightedIntensity || 0), 0)),
      backgroundColor: palette[index % palette.length],
      borderWidth: 0,
    }));
    detectionChart.update();
  }

  function renderScoreboard(simulation) {
    DOM.scoreboard.innerHTML = '';
    if (!state.loadedProteins.size) {
      DOM.scoreboard.innerHTML = `
        <div class="vm-info-card">
          <div class="vm-info-card-title">No fluorophores loaded</div>
          <div class="vm-info-card-subtitle">Load a fluorophore to evaluate collection paths.</div>
        </div>`;
      return;
    }
    if (!simulation || !Array.isArray(simulation.results) || !simulation.results.length) {
      DOM.scoreboard.innerHTML = `
        <div class="vm-info-card">
          <div class="vm-info-card-title">No collection path yet</div>
          <div class="vm-info-card-subtitle">Select at least one excitation source and one detector or endpoint to compute collected light.</div>
        </div>`;
      return;
    }

    const qualityColors = { good: 'var(--primary)', usable: '#ca8a04', poor: 'var(--danger)', blocked: 'var(--muted)' };
    simulation.results
      .slice()
      .sort((left, right) => (right.correctnessScore || 0) - (left.correctnessScore || 0))
      .forEach((result) => {
        const dyeColor = colorHex(mapToArray(state.loadedProteins).find((item) => item.key === result.fluorophoreKey)?.emMax || 520);
        const card = document.createElement('div');
        card.className = 'vm-info-card';
        card.style.borderLeft = `4px solid ${dyeColor}`;
        const depletionText = Number(result.depletionOverlap || 0) > 0 ? `${Math.round((result.depletionOverlap || 0) * 100)}%` : '0%';
        const leakPct = ((result.excitationLeakageThroughput || 0) * 100).toFixed(1);
        card.innerHTML = `
          <div class="vm-info-card-title" style="color:${dyeColor};">${result.fluorophoreName}</div>
          <div class="vm-info-card-subtitle">${result.fluorophoreState} • ${result.pathLabel}</div>
          <div class="vm-info-grid">
            <div class="vm-info-row"><span>Endpoint</span><strong>${result.detectorLabel}</strong></div>
            <div class="vm-info-row"><span>Quality</span><strong style="color:${qualityColors[result.qualityLabel] || 'var(--text)'}; text-transform:uppercase;">${result.qualityLabel}</strong></div>
            <div class="vm-info-row"><span>Recorded</span><strong>${Number(result.recordedIntensity || 0).toFixed(3)}</strong></div>
            <div class="vm-info-row"><span>Path benchmark</span><strong>${Number(result.benchmarkPct || 0).toFixed(1)}%</strong></div>
            <div class="vm-info-row"><span>Theoretical benchmark</span><strong>${Number(result.theoreticalBenchmarkPct || 0).toFixed(1)}%</strong></div>
            <div class="vm-info-row"><span>Generated → detector</span><strong>${((result.emissionPathThroughput || 0) * 100).toFixed(1)}%</strong></div>
            <div class="vm-info-row"><span>Excitation</span><strong>${((result.excitationEfficiency || 0) * 100).toFixed(1)}%</strong></div>
            <div class="vm-info-row"><span>Crosstalk</span><strong>${Number(result.pairwiseCrosstalkPct || result.crosstalkPct || 0).toFixed(1)}%</strong></div>
            <div class="vm-info-row"><span>Leakage</span><strong>${leakPct}%</strong></div>
            <div class="vm-info-row"><span>Depletion overlap</span><strong>${depletionText}</strong></div>
            <div class="vm-info-row"><span>Score</span><strong>${Number(result.correctnessScore || 0).toFixed(1)}</strong></div>
          </div>
          ${result.laserLeakageNote ? `<div class="vm-mini" style="color:var(--danger); font-weight:700;">${result.laserLeakageNote}</div>` : ''}
        `;
        DOM.scoreboard.appendChild(card);
      });
  }

  function refreshOutputs() {

    if (!state.activeInstrumentRaw || !state.activeInstrument) return;
    if (strictHardwareTruthMode()) {
      if (!routeSelectionIsExplicit()) {
        state.activeRoute = state.activeInstrument.defaultRoute || null;
      }
    } else if (!routeSelectionIsExplicit()) {
      state.activeRoute = inferRouteFromSourceSettings() || state.activeInstrument.defaultRoute || null;
    } else if (!state.activeRoute) {
      state.activeRoute = state.activeInstrument.defaultRoute || null;
    }
    enforceValidStageOptions();
    const selection = collectRuntimeSelection();
    const fluorophores = mapToArray(state.loadedProteins);
    let simulation = VM.simulateInstrument(state.activeInstrumentRaw, selection, fluorophores, {
      preferTwoPhoton: state.preferTwoPhoton,
      currentRoute: state.activeRoute,
    });
    if (!strictHardwareTruthMode() && autoRepairBlockedPath(selection, simulation)) {
      enforceValidStageOptions();
      const repairedSelection = collectRuntimeSelection();
      simulation = VM.simulateInstrument(state.activeInstrumentRaw, repairedSelection, fluorophores, {
        preferTwoPhoton: state.preferTwoPhoton,
        currentRoute: state.activeRoute,
      });
      state.lastSelection = repairedSelection;
      state.lastSimulation = simulation;
      renderReferenceSpectra(repairedSelection, simulation);
      renderPropagationPanel(repairedSelection, simulation);
      updatePipelineBeamColors(repairedSelection, simulation);
      renderSummary(repairedSelection, simulation);
      renderDetectionChart(simulation);
      renderScoreboard(simulation);
      return;
    }
    state.lastSelection = selection;
    state.lastSimulation = simulation;
    renderReferenceSpectra(selection, simulation);
    renderPropagationPanel(selection, simulation);
    updatePipelineBeamColors(selection, simulation);
    renderSummary(selection, simulation);
    renderDetectionChart(simulation);
    renderScoreboard(simulation);
  }


  async function requestJSON(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }

  async function requestJSONFirst(urls) {
    let lastError = null;
    for (const url of (Array.isArray(urls) ? urls : [])) {
      try {
        return await requestJSON(url);
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError || new Error('No FPbase endpoint could be reached.');
  }

  function dedupeFluorophoreResults(rows) {
    const byKey = new Map();
    (Array.isArray(rows) ? rows : []).forEach((row) => {
      if (!row || !row.key || byKey.has(row.key)) return;
      byKey.set(row.key, row);
    });
    return Array.from(byKey.values());
  }

  function fpbaseSearchUrls(query) {
    const q = encodeURIComponent(query);
    return [
      `https://www.fpbase.org/api/proteins/?name__iexact=${q}&format=json`,
      `https://www.fpbase.org/api/proteins/?name__istartswith=${q}&format=json`,
      `https://www.fpbase.org/api/proteins/?name__icontains=${q}&format=json`,
      `https://www.fpbase.org/api/proteins/basic/?name__iexact=${q}&format=json`,
      `https://www.fpbase.org/api/proteins/basic/?name__icontains=${q}&format=json`,
    ];
  }

  function proteinIdentifiers(protein) {
    return uniqueTexts([protein.slug, protein.uuid, protein.id, protein.name]);
  }

  function fpbaseDetailUrls(protein) {
    const urls = [];
    proteinIdentifiers(protein).forEach((identifier) => {
      urls.push(`https://www.fpbase.org/api/proteins/${encodeURIComponent(identifier)}/?format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/?slug__iexact=${encodeURIComponent(identifier)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/basic/?slug__iexact=${encodeURIComponent(identifier)}&format=json`);
    });
    if (protein.name) {
      urls.push(`https://www.fpbase.org/api/proteins/?name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/?name__icontains=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/basic/?name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/basic/?name__icontains=${encodeURIComponent(protein.name)}&format=json`);
    }
    return uniqueTexts(urls);
  }

  function fpbaseSpectraUrls(protein) {
    const urls = [];
    if (protein.slug) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__slug__iexact=${encodeURIComponent(protein.slug)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__slug=${encodeURIComponent(protein.slug)}&format=json`);
      urls.push(`https://www.fpbase.org/api/spectra/?protein__slug__iexact=${encodeURIComponent(protein.slug)}&format=json`);
    }
    if (protein.uuid) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__uuid=${encodeURIComponent(protein.uuid)}&format=json`);
    }
    if (protein.id) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein=${encodeURIComponent(protein.id)}&format=json`);
    }
    if (protein.name) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__name__icontains=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/spectra/?protein__name__iexact=${encodeURIComponent(protein.name)}&format=json`);
    }
    return uniqueTexts(urls);
  }

  function normalizedLocalSummary(row) {
    if (!row || typeof row !== 'object') return null;
    return {
      key: cleanString(row.slug || row.id || row.name),
      canonicalKey: cleanString(row.slug || row.id || row.name),
      id: cleanString(row.id),
      slug: cleanString(row.slug || row.id),
      name: cleanString(row.name || row.slug || row.id),
      uuid: '',
      aliases: Array.isArray(row.aliases) ? row.aliases : [],
      exMax: numberOrNull(row.exMax),
      emMax: numberOrNull(row.emMax),
      brightness: numberOrNull(row.brightness),
      ec: numberOrNull(row.ec),
      qy: numberOrNull(row.qy),
      source: 'local',
      source_library: cleanString(row.source_library || 'Local'),
      raw: row,
    };
  }

  async function loadLocalFluorophoreIndex() {
    if (Array.isArray(localLibraryCache.index)) return localLibraryCache.index;
    if (!localLibraryCache.indexPromise) {
      localLibraryCache.indexPromise = requestJSON(LOCAL_FLUOROPHORE_INDEX_URL)
        .then((rows) => {
          localLibraryCache.index = Array.isArray(rows) ? rows.map(normalizedLocalSummary).filter(Boolean) : [];
          return localLibraryCache.index;
        })
        .finally(() => {
          localLibraryCache.indexPromise = null;
        });
    }
    return localLibraryCache.indexPromise;
  }

  async function loadLocalFluorophoreById() {
    if (localLibraryCache.byId && typeof localLibraryCache.byId === 'object') return localLibraryCache.byId;
    if (!localLibraryCache.byIdPromise) {
      localLibraryCache.byIdPromise = requestJSON(LOCAL_FLUOROPHORE_BY_ID_URL)
        .then((rows) => {
          localLibraryCache.byId = rows && typeof rows === 'object' ? rows : {};
          return localLibraryCache.byId;
        })
        .finally(() => {
          localLibraryCache.byIdPromise = null;
        });
    }
    return localLibraryCache.byIdPromise;
  }

  function searchTokens(row) {
    return uniqueTexts([
      row && row.name,
      row && row.slug,
      row && row.id,
      ...(Array.isArray(row && row.aliases) ? row.aliases : []),
    ]).map((value) => cleanString(value).toLowerCase()).filter(Boolean);
  }

  function renderSearchResultList(listNode, rows, onPick) {
    if (!listNode) return;
    listNode.innerHTML = '';
    rows.forEach((row) => {
      const item = document.createElement('li');
      item.textContent = `${row.name} (Ex:${row.exMax || '?'} Em:${row.emMax || '?'}) [${row.source === 'local' ? 'local' : 'FPbase'}]`;
      item.addEventListener('click', () => onPick(row));
      listNode.appendChild(item);
    });
    listNode.style.display = rows.length ? 'block' : 'none';
  }

  async function searchLocalFluorophores(query) {
    const q = cleanString(query).toLowerCase();
    if (q.length < 1) return [];
    const index = await loadLocalFluorophoreIndex();
    return index
      .filter((row) => searchTokens(row).some((token) => token.includes(q)))
      .sort((left, right) => {
        const leftExact = searchTokens(left).some((token) => token === q) ? 0 : 1;
        const rightExact = searchTokens(right).some((token) => token === q) ? 0 : 1;
        if (leftExact !== rightExact) return leftExact - rightExact;
        return cleanString(left.name).localeCompare(cleanString(right.name));
      })
      .slice(0, 10);
  }

  async function searchLocalLibrary(query) {
    const q = cleanString(query);
    if (q.length < 1) {
      if (DOM.localResults) DOM.localResults.style.display = 'none';
      setInlineStatus(DOM.localSearchStatus, '');
      return;
    }
    setInlineStatus(DOM.localSearchStatus, 'Searching local dye library…');
    try {
      const results = await searchLocalFluorophores(q);
      if (!results.length) {
        if (DOM.localResults) DOM.localResults.style.display = 'none';
        setInlineStatus(DOM.localSearchStatus, `No local dye found for “${q}”.`, 'warning');
        return;
      }
      renderSearchResultList(DOM.localResults, results, (row) => {
        loadProtein({ ...row, source: 'local' });
        DOM.localResults.style.display = 'none';
        DOM.localQuery.value = '';
      });
      setInlineStatus(DOM.localSearchStatus, `${results.length} local dye candidate${results.length === 1 ? '' : 's'} loaded from the local spectra library.`, 'success');
    } catch (error) {
      console.error('Local fluorophore search failed', error);
      if (DOM.localResults) DOM.localResults.style.display = 'none';
      setInlineStatus(DOM.localSearchStatus, `Local spectra index unavailable: ${error.message}`, 'error');
    }
  }

  async function searchFPbase(query) {
    const q = cleanString(query);
    if (q.length < 2) {
      DOM.fpResults.style.display = 'none';
      setInlineStatus(DOM.searchStatus, '');
      return;
    }
    setInlineStatus(DOM.searchStatus, 'Searching FPbase…');
    let results = [];

    try {
      const normalized = [];
      for (const endpoint of fpbaseSearchUrls(q)) {
        try {
          const data = await requestJSON(endpoint);
          normalized.push(...VM.normalizeFPbaseSearchResults(data).map((row) => ({ ...row, source: 'fpbase' })));
        } catch (error) {
          // continue to next documented lookup
        }
      }
      results = dedupeFluorophoreResults(normalized)
        .filter((protein) => [protein.name, protein.slug, protein.uuid].some((value) => cleanString(value).toLowerCase().includes(q.toLowerCase())))
        .slice(0, 10);
    } catch (error) {
      console.error('FPbase search completely failed', error);
    }

    if (!results.length) {
      DOM.fpResults.style.display = 'none';
      // Output a clear error telling them the API failed or no matches were found
      setInlineStatus(DOM.searchStatus, `No remote FPbase proteins found for “${q}” or the API is currently unavailable. Try searching your Local dye library instead.`, 'error');
      return;
    }

    renderSearchResultList(DOM.fpResults, results, (protein) => {
      loadProtein({ ...protein, source: 'fpbase' });
      DOM.fpResults.style.display = 'none';
      DOM.fpQuery.value = '';
    });
    setInlineStatus(DOM.searchStatus, `${results.length} candidate fluorophore${results.length === 1 ? '' : 's'} loaded from FPbase.`, 'success');
  }
  function exactMatchFromRows(rows, protein) {
    const slug = cleanString(protein && protein.slug).toLowerCase();
    const uuid = cleanString(protein && protein.uuid).toLowerCase();
    const name = cleanString(protein && protein.name).toLowerCase();
    const candidates = Array.isArray(rows) ? rows : [];
    return candidates.find((row) => cleanString(row && row.slug).toLowerCase() === slug)
      || candidates.find((row) => cleanString(row && row.uuid).toLowerCase() === uuid)
      || candidates.find((row) => cleanString(row && row.name).toLowerCase() === name)
      || candidates[0]
      || null;
  }

  async function fetchProteinBundle(protein) {
    let detail = null;
    let spectra = null;

    try {
      const detailResponse = await requestJSONFirst(fpbaseDetailUrls(protein));
      const detailRows = VM.normalizeResultsShape(detailResponse);
      detail = Array.isArray(detailRows) && detailRows.length
        ? exactMatchFromRows(detailRows, protein)
        : detailResponse;
    } catch (error) {
      detail = protein.raw || protein;
    }

    for (const url of fpbaseSpectraUrls(protein)) {
      try {
        const response = await requestJSON(url);
        const parsedRows = VM.normalizeFPbaseSpectraResponse(response);
        if (parsedRows && parsedRows.length > 0) {
          spectra = response;
          break;
        }
      } catch (error) {
        // Network or parsing error, continue to the next fallback URL
      }
    }

    return { detail, spectra };
  }
  async function loadLocalFluorophoreRecord(summary) {
    const slugMap = await loadLocalFluorophoreById();
    const candidates = [summary.slug, summary.id, summary.name].map((value) => cleanString(value).toLowerCase()).filter(Boolean);
    const slug = candidates.map((token) => slugMap[token]).find(Boolean) || cleanString(summary.slug || summary.id || summary.name).toLowerCase();
    if (!slug) throw new Error('Local fluorophore slug could not be resolved');
    return requestJSON(`${LOCAL_FLUOROPHORE_BASE_URL}/${encodeURIComponent(slug)}.json`);
  }

  function fluorophoreIdentity(summary) {
    return cleanString(summary && (summary.slug || summary.id || summary.uuid || summary.name)).toLowerCase();
  }

  function hydrateLoadedFluorophore(fluorophore, summary) {
    const source = cleanString(summary && summary.source).toLowerCase() || 'fpbase';
    const identityKey = fluorophoreIdentity(summary || fluorophore);
    return {
      ...fluorophore,
      source,
      sourceLibrary: cleanString(summary && summary.source_library) || (source === 'local' ? 'Local spectra library' : 'FPbase'),
      identityKey,
    };
  }

  async function loadProtein(summary) {
    const source = cleanString(summary && summary.source).toLowerCase() || 'fpbase';
    const identityKey = fluorophoreIdentity(summary);
    const cacheKey = `${source}:${identityKey || cleanString(summary.name)}`;
    if (state.loadedProteins.has(cacheKey)) return;

    if (source === 'fpbase' && identityKey) {
      const localLoaded = mapToArray(state.loadedProteins).find((entry) => entry.source === 'local' && entry.identityKey === identityKey);
      if (localLoaded) {
        setInlineStatus(DOM.searchStatus, `${localLoaded.name} is already loaded from the local spectra library; keeping the local entry.`, 'warning');
        return;
      }
    }

    if (summary.states && summary.spectra) {
      state.loadedProteins.set(cacheKey, hydrateLoadedFluorophore(summary, summary));
      renderActiveDyes();
      refreshOutputs();
      return;
    }

    const statusNode = source === 'local' ? DOM.localSearchStatus : DOM.searchStatus;
    setInlineStatus(statusNode, `Loading ${summary.name}…`);
    try {
      let fluorophore = null;
      if (source === 'local') {
        const detail = await loadLocalFluorophoreRecord(summary);
        fluorophore = hydrateLoadedFluorophore(VM.normalizeFluorophoreDetail(detail, { ...summary, sourceOrigin: 'local' }, detail), summary);
        if (identityKey) {
          Array.from(state.loadedProteins.entries()).forEach(([key, entry]) => {
            if (entry && entry.identityKey === identityKey && entry.source !== 'local') {
              state.loadedProteins.delete(key);
            }
          });
        }
      } else {
        const bundle = await fetchProteinBundle(summary);
        fluorophore = hydrateLoadedFluorophore(VM.normalizeFluorophoreDetail(bundle.detail, summary, bundle.spectra), summary);
      }
      state.loadedProteins.set(cacheKey, fluorophore);
      setInlineStatus(statusNode, `${fluorophore.name} loaded (${describeSpectraSource(fluorophore.spectraSource || fluorophore.source || 'detail')}).`, 'success');
      renderActiveDyes();
      refreshOutputs();
    } catch (error) {
      console.error('Failed to load fluorophore detail', error);
      setInlineStatus(statusNode, `Error loading fluorophore: ${error.message}`, 'error');
    }
  }

  function renderActiveDyes() {

    DOM.activeDyes.innerHTML = '';
    if (!state.loadedProteins.size) {
      DOM.activeDyes.innerHTML = '<li style="font-size:12px;color:var(--muted)">No dyes loaded.</li>';
      return;
    }

    state.loadedProteins.forEach((fluorophore, key) => {
      const item = document.createElement('li');
      item.className = 'vm-list-item dye-chip';
      item.style.alignItems = 'center';
      item.style.gap = '10px';
      item.style.borderLeft = `4px solid ${colorHex(fluorophore.emMax || 520)}`;

      const left = document.createElement('div');
      left.style.display = 'grid';
      left.style.gap = '4px';
      const title = document.createElement('span');
      title.textContent = fluorophore.name;
      left.appendChild(title);

      const subtitle = document.createElement('span');
      subtitle.className = 'vm-mini';
      const sourceLabel = fluorophore.source === 'local' ? 'local dye' : 'FPbase';
      subtitle.textContent = `${sourceLabel}${fluorophore.activeStateName ? ` • ${fluorophore.activeStateName}` : ''}${fluorophore.spectraSource ? ` • ${describeSpectraSource(fluorophore.spectraSource)}` : ''}`;
      left.appendChild(subtitle);

      if (Array.isArray(fluorophore.states) && fluorophore.states.length > 1) {
        const select = document.createElement('select');
        select.style.fontSize = '12px';
        fluorophore.states.forEach((entry) => {
          const option = document.createElement('option');
          option.value = entry.key;
          option.textContent = entry.name;
          if (entry.key === fluorophore.activeStateKey) option.selected = true;
          select.appendChild(option);
        });
        select.addEventListener('change', () => {
          const updated = { ...VM.setFluorophoreState(fluorophore, select.value), source: fluorophore.source, sourceLibrary: fluorophore.sourceLibrary, identityKey: fluorophore.identityKey };
          state.loadedProteins.set(key, updated);
          renderActiveDyes();
          refreshOutputs();
        });
        left.appendChild(select);
      }

      item.appendChild(left);

      const remove = document.createElement('button');
      remove.textContent = '✕';
      remove.addEventListener('click', () => {
        state.loadedProteins.delete(key);
        renderActiveDyes();
        refreshOutputs();
      });
      item.appendChild(remove);
      DOM.activeDyes.appendChild(item);
    });
  }

  function debounce(fn, wait) {
    let timeout = null;
    return function debounced(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  window.addEventListener('load', init);
})();

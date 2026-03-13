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
    lastSelection: null,
    lastSimulation: null,
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
    fpQuery: document.getElementById('fluorophoreQuery'),
    searchBtn: document.getElementById('searchBtn'),
    searchStatus: document.getElementById('searchStatus'),
    fpResults: document.getElementById('searchResults'),
    use2Photon: document.getElementById('use2Photon'),
    activeDyes: document.getElementById('selectedDyes'),
    summary: document.getElementById('pathSummary'),
    scoreboard: document.getElementById('signalSimulator'),
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
    if (wl >= 380 && wl < 440) {
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
    }
    const toHex = (value) => Math.round(Math.max(0, Math.min(1, value)) * 255).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }

  function mapToArray(map) {
    return Array.from(map.values());
  }

  function routeSelectionIsExplicit() {
    return Boolean(state.activeInstrument && Array.isArray(state.activeInstrument.routeOptions) && state.activeInstrument.routeOptions.length > 1);
  }

  function uniqueTexts(values) {
    return Array.from(new Set((Array.isArray(values) ? values : [])
      .map((value) => cleanString(value))
      .filter(Boolean)));
  }

  function sourceSettingKey(source) {
    return `${source.slot || 0}::${source.display_label || source.name || source.model || 'source'}`;
  }

  function detectorSettingKey(mechanism, detector) {
    return `${mechanism.id || 'detector'}::${detector.display_label || detector.name || detector.channel_name || 'detector'}`;
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
      const detectorClass = detector.detector_class || VM.detectorClass(detector.kind);
      const defaults = defaultDetectorCollection(detector);
      state.detectorSettings.set(key, {
        enabled: true,
        collection_enabled: detectorClass !== 'camera',
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
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((source) => ensureSourceSetting(source));
    });
    mechanismsForRoute(state.activeInstrument && state.activeInstrument.detectors, null).forEach((mechanism) => {
      Object.values(positionsForRoute(mechanism, null)).forEach((detector) => ensureDetectorSetting(mechanism, detector));
    });
  }

  function init() {
    initCharts();
    const entries = Object.entries(state.allInstruments || {});
    if (!entries.length) return;

    entries.forEach(([id, payload]) => {
      const option = document.createElement('option');
      option.value = id;
      option.textContent = payload && payload.display_name ? payload.display_name : id;
      DOM.scopeSel.appendChild(option);
    });

    const requestedScope = new URLSearchParams(window.location.search).get('scope');
    currentInstrumentId = (requestedScope && state.allInstruments[requestedScope]) ? requestedScope : entries[0][0];
    DOM.scopeSel.value = currentInstrumentId;

    DOM.scopeSel.addEventListener('change', (event) => {
      currentInstrumentId = event.target.value;
      loadInstrument();
    });
    DOM.routeSel.addEventListener('change', (event) => {
      state.activeRoute = cleanString(event.target.value).toLowerCase() || null;
      renderGraphFlow();
      refreshOutputs();
    });
    DOM.searchBtn.addEventListener('click', () => searchFPbase(DOM.fpQuery.value));
    DOM.fpQuery.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') searchFPbase(DOM.fpQuery.value);
    });
    DOM.fpQuery.addEventListener('input', debounce(() => searchFPbase(DOM.fpQuery.value), 300));
    DOM.use2Photon.addEventListener('change', (event) => {
      state.preferTwoPhoton = Boolean(event.target.checked);
      refreshOutputs();
    });
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.fp-search-wrap')) {
        DOM.fpResults.style.display = 'none';
      }
    });

    loadInstrument();
  }

  function loadInstrument() {
    state.activeInstrumentRaw = state.allInstruments[currentInstrumentId] || {};
    state.activeInstrument = VM.normalizeInstrumentPayload(state.activeInstrumentRaw);
    state.activeRoute = state.activeInstrument.defaultRoute || null;
    state.spectralBandsByMechanism.clear();
    seedSettingsFromInstrument();
    renderRouteSelector();
    renderGraphFlow();
    refreshOutputs();
  }

  function renderRouteSelector() {
    const options = Array.isArray(state.activeInstrument && state.activeInstrument.routeOptions)
      ? state.activeInstrument.routeOptions
      : [];
    DOM.routeSel.innerHTML = '';

    if (options.length <= 1) {
      DOM.routeWrap.style.display = 'none';
      const singleRoute = options[0] ? cleanString(options[0].id).toLowerCase() : null;
      state.activeRoute = singleRoute || state.activeRoute || state.activeInstrument.defaultRoute || null;
      return;
    }

    options.forEach((option) => {
      const entry = option && typeof option === 'object' ? option : { id: option, label: normalizeRouteLabel(option) };
      const opt = document.createElement('option');
      opt.value = cleanString(entry.id).toLowerCase();
      opt.textContent = cleanString(entry.label) || normalizeRouteLabel(entry.id);
      DOM.routeSel.appendChild(opt);
    });
    const selectedRoute = state.activeRoute || state.activeInstrument.defaultRoute || (options[0] && options[0].id) || '';
    DOM.routeSel.value = selectedRoute;
    state.activeRoute = cleanString(DOM.routeSel.value).toLowerCase() || null;
    DOM.routeWrap.style.display = 'flex';
  }

  function createNode(title) {
    const node = document.createElement('div');
    node.className = 'graph-node';
    node.innerHTML = `<div class="node-title">${title}</div>`;
    return node;
  }

  function addArrow() {
    const arrow = document.createElement('div');
    arrow.className = 'graph-arrow';
    arrow.innerHTML = '➔';
    DOM.graph.appendChild(arrow);
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

  function renderGraphFlow() {
    const snapshot = snapshotStageSelections();
    DOM.graph.innerHTML = '';
    if (!state.activeInstrument) return;

    const inst = state.activeInstrument;
    const route = state.activeRoute;

    const lightSourceMechanisms = mechanismsForRoute(inst.lightSources, route);
    if (lightSourceMechanisms.length) {
      const node = createNode('1. Light Sources');
      lightSourceMechanisms.forEach((mechanism) => node.appendChild(createLightSourceControl(mechanism)));
      DOM.graph.appendChild(node);
      addArrow();
    }

    const cubeMechanisms = mechanismsForRoute(inst.cube, route);
    const excitationMechanisms = mechanismsForRoute(inst.excitation, route);
    if (cubeMechanisms.length) {
      const node = createNode('2. Filter Cube');
      cubeMechanisms.forEach((mechanism, index) => node.appendChild(createMechanismControl('cube', mechanism, index)));
      DOM.graph.appendChild(node);
      addArrow();
    } else if (route === 'tirf' && excitationMechanisms.length) {
      const node = createNode('2. Excitation');
      node.innerHTML += '<div style="font-size:11px;text-align:center;color:var(--muted)">Bypassed for TIRF route</div>';
      DOM.graph.appendChild(node);
      addArrow();
    } else if (excitationMechanisms.length) {
      const node = createNode('2. Excitation');
      excitationMechanisms.forEach((mechanism, index) => node.appendChild(createMechanismControl('excitation', mechanism, index)));
      DOM.graph.appendChild(node);
      addArrow();
    }

    const dichroicMechanisms = mechanismsForRoute(inst.dichroic, route);
    if (!cubeMechanisms.length && dichroicMechanisms.length) {
      const node = createNode('3. Dichroic');
      dichroicMechanisms.forEach((mechanism, index) => node.appendChild(createMechanismControl('dichroic', mechanism, index)));
      DOM.graph.appendChild(node);
      addArrow();
    }

    const sampleNode = createNode('4. Sample');
    sampleNode.classList.add('sample-node');
    sampleNode.innerHTML += '<div style="font-size:11px;text-align:center;color:var(--muted)">Excitation drives fluorophore emission here</div>';
    DOM.graph.appendChild(sampleNode);
    addArrow();

    const emissionMechanisms = mechanismsForRoute(inst.emission, route);
    if (emissionMechanisms.length) {
      const node = createNode('5. Emission');
      emissionMechanisms.forEach((mechanism, index) => node.appendChild(createMechanismControl('emission', mechanism, index)));
      DOM.graph.appendChild(node);
      addArrow();
    }

    const splitterMechanisms = mechanismsForRoute(inst.splitters, route);
    if (splitterMechanisms.length) {
      const node = createNode('6. Splitters');
      splitterMechanisms.forEach((mechanism, index) => node.appendChild(createMechanismControl('splitters', mechanism, index)));
      DOM.graph.appendChild(node);
      addArrow();
    }

    const detectorMechanisms = mechanismsForRoute(inst.detectors, route);
    if (detectorMechanisms.length) {
      const node = createNode('7. Detectors');
      detectorMechanisms.forEach((mechanism) => node.appendChild(createDetectorControl(mechanism)));
      DOM.graph.appendChild(node);
    } else if (DOM.graph.lastChild && DOM.graph.lastChild.classList.contains('graph-arrow')) {
      DOM.graph.removeChild(DOM.graph.lastChild);
    }

    restoreStageSelections(snapshot);
    enforceValidStageOptions();
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
        source.role ? `role: ${source.role}` : '',
        source.kind ? `kind: ${source.kind}` : '',
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
    select.addEventListener('change', () => { select.dataset.userSet = 'true'; refreshOutputs(); });
    block.appendChild(label);
    block.appendChild(select);
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


  function createDetectorControl(mechanism) {
    const detector = Object.values(positionsForRoute(mechanism, state.activeRoute))[0];
    if (!detector) return document.createElement('div');
    const setting = ensureDetectorSetting(mechanism, detector);
    const labelText = mechanism.display_label || detector.display_label || detector.name || 'Detector';
    const detectorClass = detector.detector_class || VM.detectorClass(detector.kind);

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
      refreshOutputs();
    });
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(labelText));
    block.appendChild(label);

    const meta = document.createElement('div');
    meta.className = 'vm-mini';
    meta.textContent = `${detectorClass}${detector.supports_time_gating ? ' • time-gated' : ''}`;
    block.appendChild(meta);

    if (detectorClass !== 'camera') {
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
      setting.collection_enabled = true;
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
        refreshOutputs();
      });
      maxReadout.textContent = `Collection max: ${Math.round(Number(maxSlider.value))} nm`;
      block.appendChild(maxReadout);
      block.appendChild(maxSlider);
    }

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

    mechanismsForRoute(state.activeInstrument && state.activeInstrument.lightSources, state.activeRoute).forEach((mechanism) => {
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
      } else if (stage === 'splitters') {
        pushStageComponent('splitters', mechanismName, value);
      } else if (stage !== 'detectors') {
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

    mechanismsForRoute(state.activeInstrument && state.activeInstrument.detectors, state.activeRoute).forEach((mechanism) => {
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
    referenceChart = initLineChart(DOM.referenceChart, 'Normalized absorption / emission (%)');
    propagationChart = initLineChart(DOM.propagationChart, 'Propagated light (%)');
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

  function sourceReferenceDatasets(selection) {
    const datasets = [];
    selection.sources.forEach((source) => {
      const wavelength = numberOrNull(source.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm);
      const isLine = ['line', 'tunable_line'].includes(cleanString(source.spectral_mode).toLowerCase()) || cleanString(source.kind).toLowerCase() === 'laser';
      const color = source.role === 'depletion' ? '#dc2626' : colorHex(wavelength || 520);
      if (isLine && wavelength !== null) {
        datasets.push({
          label: `${source.display_label || source.name || 'Source'} line`,
          data: [{ x: wavelength, y: 0 }, { x: wavelength, y: 100 }],
          borderColor: color,
          borderWidth: 2,
          borderDash: source.role === 'depletion' ? [6, 4] : [2, 2],
          fill: false,
          pointRadius: 0,
          tension: 0,
        });
      } else {
        const grid = VM.wavelengthGrid({ min_nm: 350, max_nm: determineChartMax(selection), step_nm: 2 });
        const sourceSpectrum = VM.sourceSpectrum(source, grid);
        const scale = spectrumScale([sourceSpectrum]);
        datasets.push(chartDatasetFromGrid(source.display_label || source.name || 'Source', grid, asPercentArray(sourceSpectrum, scale), {
          borderColor: color,
          backgroundColor: rgbaFromHex(color, 0.08),
        }));
      }
    });
    return datasets;
  }

  function renderReferenceSpectra(selection, simulation) {
    if (!referenceChart) return;
    const chartMax = determineChartMax(selection);
    const grid = Array.isArray(simulation && simulation.grid)
      ? simulation.grid
      : VM.wavelengthGrid({ min_nm: 350, max_nm: chartMax, step_nm: 2 });
    const emissionEntries = Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [];
    const datasets = [...sourceReferenceDatasets(selection)];

    emissionEntries.forEach((entry) => {
      const fluor = mapToArray(state.loadedProteins).find((item) => item.key === entry.fluorophoreKey);
      const color = colorHex((fluor && fluor.emMax) || 520);
      const absorptionSpectrum = Array.isArray(entry.absorptionSpectrum) ? entry.absorptionSpectrum : [];
      if (absorptionSpectrum.some((value) => value > 1e-6)) {
        datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} absorption`, grid, asPercentArray(absorptionSpectrum, 1), {
          borderColor: color,
          borderDash: [5, 4],
          borderWidth: 2,
          backgroundColor: rgbaFromHex(color, 0.02),
        }));
      }

      const generatedSpectrum = Array.isArray(entry.generatedSpectrum) ? entry.generatedSpectrum : [];
      if (generatedSpectrum.some((value) => value > 1e-6)) {
        const exPct = Math.round((Number(entry.excitationEfficiency || 0)) * 100);
        const depPct = Math.round((Number(entry.depletionOverlap || 0)) * 100);
        datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} emission (Ex ${exPct}%, Dep ${depPct}%)`, grid, asPercentArray(generatedSpectrum, 1), {
          borderColor: color,
          backgroundColor: rgbaFromHex(color, 0.14),
          borderWidth: 2,
          fill: true,
        }));
      }
    });

    referenceChart.data.datasets = datasets;
    referenceChart.options.scales.x.max = chartMax;
    referenceChart.update();
  }

  function renderPropagationPanel(selection, simulation) {
    if (!propagationChart) return;
    const chartMax = determineChartMax(selection);
    const grid = Array.isArray(simulation && simulation.grid) ? simulation.grid : VM.wavelengthGrid({ min_nm: 350, max_nm: chartMax, step_nm: 2 });
    const emissionEntries = Array.isArray(simulation && simulation.emittedSpectra) ? simulation.emittedSpectra : [];
    const pathEntries = Array.isArray(simulation && simulation.pathSpectra) ? simulation.pathSpectra : [];
    const totalEmission = sumSpectra(emissionEntries, 'postOpticsSpectrum', grid);
    const aggregatedPaths = aggregateSpectraByLabel(pathEntries, 'spectrum', grid);
    const aggregatedLeakage = aggregateSpectraByLabel(pathEntries, 'excitationLeakageSpectrum', grid, 'pathKey');
    const scale = spectrumScale([
      Array.isArray(simulation && simulation.excitationAtSample) ? simulation.excitationAtSample : [],
      totalEmission,
      ...aggregatedPaths.map((entry) => entry.values),
      ...aggregatedLeakage.map((entry) => entry.values),
    ]);

    const datasets = [];
    if (Array.isArray(simulation && simulation.excitationAtSample) && simulation.excitationAtSample.some((value) => value > 0)) {
      datasets.push(chartDatasetFromGrid('Excitation at sample', grid, asPercentArray(simulation.excitationAtSample, scale), {
        borderColor: '#334155',
        borderWidth: 2,
      }));
    }
    emissionEntries.forEach((entry) => {
      const fluor = mapToArray(state.loadedProteins).find((item) => item.key === entry.fluorophoreKey);
      const color = colorHex((fluor && fluor.emMax) || 520);
      datasets.push(chartDatasetFromGrid(`${entry.fluorophoreName} after optics`, grid, asPercentArray(entry.postOpticsSpectrum, scale), {
        borderColor: color,
        borderDash: [5, 3],
        backgroundColor: rgbaFromHex(color, 0.05),
      }));
    });
    const palette = ['#0f766e', '#7c3aed', '#ea580c', '#2563eb', '#be123c'];
    const pathColorByLabel = new Map();
    aggregatedPaths.forEach((entry, index) => {
      const color = palette[index % palette.length];
      pathColorByLabel.set(entry.label, color);
      datasets.push(chartDatasetFromGrid(entry.label, grid, asPercentArray(entry.values, scale), {
        borderColor: color,
        backgroundColor: rgbaFromHex(color, 0.08),
        borderWidth: 3,
      }));
      const mask = entry.entry && Array.isArray(entry.entry.collectionMask) ? entry.entry.collectionMask : [];
      if (mask.some((value) => value < 0.999)) {
        datasets.push(chartDatasetFromGrid(`${entry.label} window`, grid, asPercentArray(mask, 1), {
          borderColor: color,
          borderDash: [2, 4],
          borderWidth: 1.5,
        }));
      }
    });
    aggregatedLeakage.forEach((entry) => {
      if (!entry.values.some((value) => value > 1e-6)) return;
      const color = pathColorByLabel.get(entry.label) || '#dc2626';
      datasets.push(chartDatasetFromGrid(`${entry.label} excitation leak`, grid, asPercentArray(entry.values, scale), {
        borderColor: color,
        borderDash: [6, 3],
        borderWidth: 1.75,
      }));
    });

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
        spectra.push(VM.sourceSpectrum({
          ...source,
          selected_wavelength_nm: numberOrNull(setting.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm),
        }, grid));
      });
    });
    return sumSpectra(spectra.map((values) => ({ values })), 'values', grid);
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
      return `${detector.display_label || detector.name || 'Detector'}${window}`;
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
      `<div><strong>Detectors:</strong> ${detectorText}</div>`,
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
      DOM.scoreboard.innerHTML = '<li style="font-size:13px;color:var(--muted)">Load a fluorophore to evaluate detector paths.</li>';
      return;
    }
    if (!simulation || !Array.isArray(simulation.results) || !simulation.results.length) {
      DOM.scoreboard.innerHTML = '<li style="font-size:13px;color:var(--muted)">Select at least one excitation source and one detector to evaluate signal.</li>';
      return;
    }

    const qualityColors = { good: 'var(--primary)', usable: '#ca8a04', poor: 'var(--danger)', blocked: 'var(--muted)' };
    simulation.results
      .slice()
      .sort((left, right) => (right.correctnessScore || 0) - (left.correctnessScore || 0))
      .forEach((result) => {
        const dyeColor = colorHex(mapToArray(state.loadedProteins).find((item) => item.key === result.fluorophoreKey)?.emMax || 520);
        const depletionText = Number(result.depletionOverlap || 0) > 0
          ? ` • depletion ${Math.round((result.depletionOverlap || 0) * 100)}%`
          : '';
        const leakageText = result.excitationLeakageWarningLevel !== 'none'
          ? ` • leak ${result.excitationLeakageWarningLevel}`
          : '';
        const item = document.createElement('li');
        item.className = 'vm-list-item';
        item.style.alignItems = 'flex-start';
        item.style.gap = '12px';
        item.innerHTML = `
          <div style="min-width:0;">
            <div style="font-weight:700; color:${dyeColor};">${result.fluorophoreName}</div>
            <div style="font-size:11px; color:var(--muted);">${result.fluorophoreState} • ${result.pathLabel}</div>
            <div style="font-size:11px; color:var(--muted);">Detector: ${result.detectorLabel} (${result.detectorClass})${depletionText}${leakageText}</div>
            ${result.laserLeakageNote ? `<div style="font-size:11px; color:var(--danger); font-weight:700;">${result.laserLeakageNote}</div>` : ''}
          </div>
          <div class="vm-metric">
            <div style="font-weight:700; color:${qualityColors[result.qualityLabel] || 'var(--text)'}; text-transform:uppercase;">${result.qualityLabel}</div>
            <div>Recorded ${Number(result.recordedIntensity || 0).toFixed(3)}</div>
            <div>Generated→detector ${((result.emissionPathThroughput || 0) * 100).toFixed(1)}%</div>
            <div>Crosstalk ${Number(result.crosstalkPct || 0).toFixed(1)}% | Leak ${((result.excitationLeakageFraction || 0) * 100).toFixed(1)}%</div>
            <div>Ex ${((result.excitationEfficiency || 0) * 100).toFixed(1)}% | Score ${Number(result.correctnessScore || 0).toFixed(1)}</div>
          </div>
        `;
        DOM.scoreboard.appendChild(item);
      });
  }

  function refreshOutputs() {

    if (!state.activeInstrumentRaw || !state.activeInstrument) return;
    if (!routeSelectionIsExplicit()) {
      state.activeRoute = inferRouteFromSourceSettings() || state.activeInstrument.defaultRoute || null;
    } else if (!state.activeRoute) {
      state.activeRoute = state.activeInstrument.defaultRoute || null;
    }
    enforceValidStageOptions();
    const selection = collectRuntimeSelection();
    const fluorophores = mapToArray(state.loadedProteins);
    let simulation = VM.simulateInstrument(state.activeInstrumentRaw, selection, fluorophores, {
      preferTwoPhoton: state.preferTwoPhoton,
    });
    if (autoRepairBlockedPath(selection, simulation)) {
      enforceValidStageOptions();
      const repairedSelection = collectRuntimeSelection();
      simulation = VM.simulateInstrument(state.activeInstrumentRaw, repairedSelection, fluorophores, {
        preferTwoPhoton: state.preferTwoPhoton,
      });
      state.lastSelection = repairedSelection;
      state.lastSimulation = simulation;
      renderReferenceSpectra(repairedSelection, simulation);
      renderPropagationPanel(repairedSelection, simulation);
      renderSummary(repairedSelection, simulation);
      renderDetectionChart(simulation);
      renderScoreboard(simulation);
      return;
    }
    state.lastSelection = selection;
    state.lastSimulation = simulation;
    renderReferenceSpectra(selection, simulation);
    renderPropagationPanel(selection, simulation);
    renderSummary(selection, simulation);
    renderDetectionChart(simulation);
    renderScoreboard(simulation);
  }


  async function requestJSON(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`FPbase request failed (${response.status})`);
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
    ];
  }

  function proteinIdentifiers(protein) {
    return uniqueTexts([protein.slug, protein.uuid, protein.id, protein.name]);
  }

  function fpbaseDetailUrls(protein) {
    const urls = [];
    proteinIdentifiers(protein).forEach((identifier) => {
      urls.push(`https://www.fpbase.org/api/proteins/${encodeURIComponent(identifier)}/?format=json`);
    });
    if (protein.name) {
      urls.push(`https://www.fpbase.org/api/proteins/?name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/?name__icontains=${encodeURIComponent(protein.name)}&format=json`);
    }
    return uniqueTexts(urls);
  }

  function fpbaseSpectraUrls(protein) {
    const urls = [];
    if (protein.name) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__name__iexact=${encodeURIComponent(protein.name)}&format=json`);
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?name__iexact=${encodeURIComponent(protein.name)}&format=json`);
    }
    if (protein.slug) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__slug__iexact=${encodeURIComponent(protein.slug)}&format=json`);
    }
    if (protein.uuid) {
      urls.push(`https://www.fpbase.org/api/proteins/spectra/?protein__uuid=${encodeURIComponent(protein.uuid)}&format=json`);
    }
    return uniqueTexts(urls);
  }

  function normalizeSearchFallback(query) {
    return VM.searchFallbackFluorophores(query).map((record) => ({
      key: record.key,
      canonicalKey: record.canonicalKey,
      id: record.id,
      uuid: record.uuid,
      slug: record.slug,
      name: record.name,
      exMax: record.exMax,
      emMax: record.emMax,
      brightness: record.brightness,
      ec: record.ec,
      qy: record.qy,
      fallbackRecord: record,
    }));
  }

  async function searchFPbase(query) {
    const q = cleanString(query);
    if (q.length < 2) {
      DOM.fpResults.style.display = 'none';
      DOM.searchStatus.textContent = '';
      return;
    }
    DOM.searchStatus.textContent = 'Searching FPbase…';
    let results = [];
    let usedFallback = false;
    try {
      const normalized = [];
      for (const endpoint of fpbaseSearchUrls(q)) {
        try {
          const data = await requestJSON(endpoint);
          normalized.push(...VM.normalizeFPbaseSearchResults(data));
        } catch (error) {
          // continue to next documented lookup
        }
      }
      results = dedupeFluorophoreResults(normalized)
        .filter((protein) => [protein.name, protein.slug, protein.uuid].some((value) => cleanString(value).toLowerCase().includes(q.toLowerCase())))
        .slice(0, 10);
      if (!results.length) {
        usedFallback = true;
        results = normalizeSearchFallback(q).slice(0, 10);
      }
    } catch (error) {
      usedFallback = true;
      results = normalizeSearchFallback(q).slice(0, 10);
    }

    DOM.fpResults.innerHTML = '';
    if (!results.length) {
      DOM.fpResults.style.display = 'none';
      DOM.searchStatus.textContent = `No FPbase proteins found for “${q}”.`;
      return;
    }

    results.forEach((protein) => {
      const item = document.createElement('li');
      const sourceTag = protein.fallbackRecord ? 'bundled cache' : 'live';
      item.textContent = `${protein.name} (Ex:${protein.exMax || '?'} Em:${protein.emMax || '?'}) • ${sourceTag}`;
      item.addEventListener('click', () => {
        loadProtein(protein);
        DOM.fpResults.style.display = 'none';
        DOM.fpQuery.value = '';
      });
      DOM.fpResults.appendChild(item);
    });
    DOM.fpResults.style.display = 'block';
    DOM.searchStatus.textContent = usedFallback
      ? `${results.length} fluorophore candidate${results.length === 1 ? '' : 's'} loaded from the bundled FP cache.`
      : `${results.length} candidate fluorophore${results.length === 1 ? '' : 's'} loaded from FPbase.`;
  }

  async function fetchProteinBundle(protein) {
    if (protein.fallbackRecord) {
      return {
        detail: protein.fallbackRecord.raw && protein.fallbackRecord.raw.detail
          ? protein.fallbackRecord.raw.detail
          : (protein.fallbackRecord.raw && protein.fallbackRecord.raw.summary ? protein.fallbackRecord.raw.summary : protein.fallbackRecord),
        spectra: null,
      };
    }
    let detail = null;
    try {
      const detailResponse = await requestJSONFirst(fpbaseDetailUrls(protein));
      const detailRows = VM.normalizeResultsShape(detailResponse);
      detail = Array.isArray(detailRows) && detailRows.length ? detailRows[0] : detailResponse;
    } catch (error) {
      detail = protein.raw || protein;
    }
    // Skip the flaky separate spectra API call; the detail object already contains the states & spectra
    return { detail, spectra: null };
  }

  async function loadProtein(summary) {
    const cacheKey = summary.key || summary.slug || summary.id || summary.name;
    if (state.loadedProteins.has(cacheKey)) return;
    if (summary.states && summary.spectra) {
      state.loadedProteins.set(cacheKey, summary);
      renderActiveDyes();
      refreshOutputs();
      return;
    }
    DOM.searchStatus.textContent = `Loading ${summary.name}…`;
    try {
      const bundle = await fetchProteinBundle(summary);
      const fluorophore = VM.normalizeFluorophoreDetail(bundle.detail, summary, bundle.spectra);
      state.loadedProteins.set(cacheKey, fluorophore);
      DOM.searchStatus.textContent = `${fluorophore.name} loaded (${describeSpectraSource(fluorophore.spectraSource || 'detail')}).`;
      renderActiveDyes();
      refreshOutputs();
    } catch (error) {
      console.error('Failed to load fluorophore detail', error);
      DOM.searchStatus.textContent = `Error loading fluorophore: ${error.message}`;
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
          const updated = VM.setFluorophoreState(fluorophore, select.value);
          state.loadedProteins.set(key, updated);
          renderActiveDyes();
          refreshOutputs();
        });
        left.appendChild(select);
      } else if (fluorophore.activeStateName) {
        const subtitle = document.createElement('span');
        subtitle.className = 'vm-mini';
        subtitle.textContent = `${fluorophore.activeStateName}${fluorophore.spectraSource ? ` • ${describeSpectraSource(fluorophore.spectraSource)}` : ''}`;
        left.appendChild(subtitle);
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

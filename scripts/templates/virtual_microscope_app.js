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
  let chartInstance = null;

  const DOM = {
    chart: document.getElementById('spectraChart'),
    scopeSel: document.getElementById('microscopeSelector'),
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

  function ensureDetectorSetting(mechanism, detector) {
    const key = detectorSettingKey(mechanism, detector);
    if (!state.detectorSettings.has(key)) {
      state.detectorSettings.set(key, {
        enabled: true,
        user_gain: numberOrNull(detector.default_gain) ?? 1,
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
    return ['tirf', 'multiphoton', 'confocal', 'epi'];
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
    return route ? route.toUpperCase() : 'Any compatible route';
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
    initChart();
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
    state.activeRoute = null;
    state.spectralBandsByMechanism.clear();
    seedSettingsFromInstrument();
    renderGraphFlow();
    refreshOutputs();
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
    block.className = 'vm-stack';
    block.dataset.stage = 'lightSources';
    block.dataset.mechanismId = mechanism.id || '';

    const title = document.createElement('div');
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
        state.activeRoute = inferRouteFromSourceSettings();
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
    select.addEventListener('change', () => refreshOutputs());
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
    const gainLabel = detectorClass === 'camera' ? 'Sensitivity' : 'Gain';

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

    const readout = document.createElement('div');
    readout.className = 'tunable-range-label';
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = '0';
    slider.max = '10';
    slider.step = '0.1';
    slider.value = String(setting.user_gain ?? 1);
    slider.addEventListener('input', () => {
      setting.user_gain = Number(slider.value);
      readout.textContent = `${gainLabel}: ${Number(slider.value).toFixed(1)}×`;
      refreshOutputs();
    });
    readout.textContent = `${gainLabel}: ${Number(slider.value).toFixed(1)}×`;
    block.appendChild(readout);
    block.appendChild(slider);

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
          user_gain: numberOrNull(setting.user_gain) ?? 1,
        });
      });
    });

    return selection;
  }

  function initChart() {
    chartInstance = new Chart(DOM.chart, {
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
          y: { min: 0, max: 105, title: { display: true, text: 'Relative transmission / intensity (%)' } },
        },
      },
    });
  }

  function chartDatasetFromGrid(label, grid, values, style) {
    return {
      label,
      data: grid.map((wavelength, index) => ({ x: wavelength, y: Math.min(105, Math.max(0, (values[index] || 0) * 100)) })),
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

  function hardwareDatasetsForComponent(stage, name, component, chartMax) {
    if (!component || typeof component !== 'object') return [];
    const grid = VM.wavelengthGrid({ min_nm: 350, max_nm: chartMax, step_nm: 2 });
    const type = cleanString(component.component_type || component.type || component.render_kind).toLowerCase();
    if (component.render_kind === 'source') {
      const sourceColor = component.role === 'depletion' ? '#dc2626' : '#0f172a';
      return [chartDatasetFromGrid(
        component.display_label || component.name || name,
        grid,
        VM.sourceSpectrum(component, grid),
        { borderColor: sourceColor, backgroundColor: rgbaFromHex(sourceColor, 0.1) }
      )];
    }
    if (!type || type === 'detector' || type === 'empty') return [];
    const context = { mode: stage === 'excitation' ? 'excitation' : 'emission' };
    let color = '#8b5cf6';
    if (stage === 'emission') color = '#16a34a';
    if (type.includes('dichroic')) color = '#f59e0b';
    if (type === 'notch') color = '#ef4444';
    const label = component.display_label || component.label || name;
    return [chartDatasetFromGrid(label, grid, VM.componentMask(component, grid, context), {
      borderColor: color,
      backgroundColor: rgbaFromHex(color, 0.1),
      borderDash: type.includes('dichroic') ? [6, 4] : undefined,
    })];
  }

  function drawHardware(selection, simulation) {
    if (!chartInstance) return;
    const chartMax = determineChartMax(selection);
    const datasets = [];

    selection.sources.forEach((source) => {
      datasets.push(...hardwareDatasetsForComponent('source', source.display_label || source.name || 'Source', source, chartMax));
    });
    selection.excitation.forEach((component) => {
      datasets.push(...hardwareDatasetsForComponent('excitation', component.display_label || component.label || 'Excitation', component, chartMax));
    });
    selection.dichroic.forEach((component) => {
      datasets.push(...hardwareDatasetsForComponent('dichroic', component.display_label || component.label || 'Dichroic', component, chartMax));
    });
    selection.emission.forEach((component) => {
      datasets.push(...hardwareDatasetsForComponent('emission', component.display_label || component.label || 'Emission', component, chartMax));
    });
    selection.splitters.forEach((splitter) => {
      const splitterDichroic = splitter.dichroic && splitter.dichroic.positions ? splitter.dichroic.positions[1] || splitter.dichroic.positions['1'] : null;
      if (splitterDichroic) {
        datasets.push(...hardwareDatasetsForComponent('dichroic', 'Splitter dichroic', splitterDichroic, chartMax));
      }
      (Array.isArray(splitter.branches) ? splitter.branches : []).forEach((branch) => {
        if (branch.component) {
          datasets.push(...hardwareDatasetsForComponent('emission', branch.label || branch.id || 'Splitter branch', branch.component, chartMax));
        }
      });
    });

    mapToArray(state.loadedProteins).forEach((fluorophore) => {
      const color = colorHex(fluorophore.emMax || 520);
      const spectra = VM.fluorophoreSpectra(fluorophore, { preferTwoPhoton: state.preferTwoPhoton });
      if (spectra.ex.length) {
        datasets.push({
          label: `${fluorophore.name} ${spectra.exMode === '2p' ? '2P Ex' : 'Ex'}`,
          data: spectra.ex,
          borderColor: color,
          borderDash: [4, 4],
          borderWidth: 2,
          fill: false,
          pointRadius: 0,
          tension: 0.2,
        });
      }
      if (spectra.em.length) {
        datasets.push({
          label: `${fluorophore.name} Em`,
          data: spectra.em,
          borderColor: color,
          backgroundColor: rgbaFromHex(color, 0.08),
          borderWidth: 2,
          fill: true,
          pointRadius: 0,
          tension: 0.2,
        });
      }
    });

    if (simulation && Array.isArray(simulation.grid) && Array.isArray(simulation.excitationAtSample) && simulation.excitationAtSample.some((value) => value > 0)) {
      datasets.push(chartDatasetFromGrid('Excitation at sample', simulation.grid, simulation.excitationAtSample, {
        borderColor: '#475569',
        borderWidth: 2,
      }));
    }

    chartInstance.data.datasets = datasets;
    chartInstance.options.scales.x.max = chartMax;
    chartInstance.update();
  }

  function uniqueTexts(values) {
    return Array.from(new Set((Array.isArray(values) ? values : []).filter(Boolean)));
  }

  function renderSummary(selection, simulation) {
    const fluorText = mapToArray(state.loadedProteins).map((fluorophore) => {
      const stateSuffix = fluorophore.activeStateName && fluorophore.states && fluorophore.states.length > 1
        ? ` (${fluorophore.activeStateName})`
        : '';
      return `${fluorophore.name}${stateSuffix}`;
    }).join(', ') || 'None';
    const sourceText = selection.sources.map((source) => {
      const wavelength = numberOrNull(source.selected_wavelength_nm) ?? numberOrNull(source.wavelength_nm);
      const lambdaText = wavelength !== null ? ` @ ${Math.round(wavelength)} nm` : '';
      return `${source.display_label || source.name || 'Source'}${lambdaText}`;
    }).join(', ') || 'None';
    const detectorText = selection.detectors.map((detector) => `${detector.display_label || detector.name || 'Detector'} ×${(numberOrNull(detector.user_gain) ?? 1).toFixed(1)}`).join(', ') || 'None';
    const opticalStages = selection.debugSelections.map((entry) => entry.name).join(' → ') || 'No stage optics selected';
    const stedText = uniqueTexts((simulation && simulation.results || []).filter((result) => result.sted && result.sted.applied).map((result) => `${result.fluorophoreName}: ${result.sted.label} via ${result.sted.sourceLabel}`)).join('; ') || 'No depletion source selected';
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
    ].join('');
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

    simulation.results
      .slice()
      .sort((left, right) => right.detectorWeightedIntensity - left.detectorWeightedIntensity)
      .forEach((result) => {
        const dyeColor = colorHex(mapToArray(state.loadedProteins).find((item) => item.key === result.fluorophoreKey)?.emMax || 520);
        const stedText = result.sted && result.sted.applied
          ? ` • STED ${result.sted.label} (${Math.round((result.sted.score || 0) * 100)}%)`
          : '';
        const item = document.createElement('li');
        item.className = 'vm-list-item';
        item.style.alignItems = 'flex-start';
        item.style.gap = '12px';
        item.innerHTML = `
          <div style="min-width:0;">
            <div style="font-weight:700; color:${dyeColor};">${result.fluorophoreName}</div>
            <div style="font-size:11px; color:var(--muted);">${result.fluorophoreState} • ${result.pathLabel}</div>
            <div style="font-size:11px; color:var(--muted);">Detector: ${result.detectorLabel} (${result.detectorClass})${stedText}</div>
          </div>
          <div class="vm-metric">Ex ${((result.excitationStrength || 0) * 100).toFixed(1)}% | Em ${((result.emissionPathThroughput || 0) * 100).toFixed(1)}% | Det ${Number(result.detectorWeightedIntensity || 0).toFixed(3)} | XT ${Number(result.crosstalkPct || 0).toFixed(1)}%</div>
        `;
        DOM.scoreboard.appendChild(item);
      });
  }

  function refreshOutputs() {
    if (!state.activeInstrumentRaw || !state.activeInstrument) return;
    state.activeRoute = inferRouteFromSourceSettings();
    enforceValidStageOptions();
    const selection = collectRuntimeSelection();
    const fluorophores = mapToArray(state.loadedProteins);
    const simulation = VM.simulateInstrument(state.activeInstrumentRaw, selection, fluorophores, {
      preferTwoPhoton: state.preferTwoPhoton,
    });
    state.lastSelection = selection;
    state.lastSimulation = simulation;
    drawHardware(selection, simulation);
    renderSummary(selection, simulation);
    renderScoreboard(simulation);
  }

  async function requestJSON(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`FPbase request failed (${response.status})`);
    return response.json();
  }

  function dedupeFluorophoreResults(rows) {
    const byKey = new Map();
    (Array.isArray(rows) ? rows : []).forEach((row) => {
      if (!row || !row.key || byKey.has(row.key)) return;
      byKey.set(row.key, row);
    });
    return Array.from(byKey.values());
  }

  async function searchFPbase(query) {
    const q = cleanString(query);
    if (q.length < 3) {
      DOM.fpResults.style.display = 'none';
      DOM.searchStatus.textContent = '';
      return;
    }
    DOM.searchStatus.textContent = 'Searching FPbase…';
    try {
      const endpoints = [
        `https://www.fpbase.org/api/proteins/?name__icontains=${encodeURIComponent(q)}&format=json`,
        `https://www.fpbase.org/api/proteins/?q=${encodeURIComponent(q)}&format=json`,
      ];
      const normalized = [];
      for (const endpoint of endpoints) {
        try {
          const data = await requestJSON(endpoint);
          normalized.push(...VM.normalizeFPbaseSearchResults(data));
        } catch (error) {
          // try next endpoint
        }
      }

      const results = dedupeFluorophoreResults(normalized)
        .filter((protein) => cleanString(protein.name).toLowerCase().includes(q.toLowerCase()))
        .slice(0, 10);

      DOM.fpResults.innerHTML = '';
      if (!results.length) {
        DOM.fpResults.style.display = 'none';
        DOM.searchStatus.textContent = `No FPbase proteins found for “${q}”.`;
        return;
      }

      results.forEach((protein) => {
        const item = document.createElement('li');
        item.textContent = `${protein.name} (Ex:${protein.exMax || '?'} Em:${protein.emMax || '?'})`;
        item.addEventListener('click', () => {
          loadProtein(protein);
          DOM.fpResults.style.display = 'none';
          DOM.fpQuery.value = '';
        });
        DOM.fpResults.appendChild(item);
      });
      DOM.fpResults.style.display = 'block';
      DOM.searchStatus.textContent = `${results.length} candidate fluorophore${results.length === 1 ? '' : 's'} loaded.`;
    } catch (error) {
      DOM.fpResults.style.display = 'none';
      DOM.searchStatus.textContent = `Error searching FPbase: ${error.message}`;
    }
  }

  function proteinIdentifiers(protein) {
    return uniqueTexts([protein.slug, protein.uuid, protein.id, protein.name]);
  }

  async function hydrateProteinFromSearch(protein) {
    const query = encodeURIComponent(protein.name || protein.slug || protein.id || protein.key || '');
    if (!query) throw new Error('Protein search result is missing identifiers.');
    const data = await requestJSON(`https://www.fpbase.org/api/proteins/?q=${query}&format=json`);
    const candidates = VM.normalizeResultsShape(data);
    if (!candidates.length) throw new Error('Unable to hydrate FPbase fluorophore detail.');
    return candidates[0];
  }

  async function fetchProteinDetail(protein) {
    for (const identifier of proteinIdentifiers(protein)) {
      try {
        return await requestJSON(`https://www.fpbase.org/api/proteins/${encodeURIComponent(identifier)}/?format=json`);
      } catch (error) {
        // try next identifier
      }
    }
    return hydrateProteinFromSearch(protein);
  }

  async function loadProtein(summary) {
    const cacheKey = summary.key || summary.slug || summary.id || summary.name;
    if (state.loadedProteins.has(cacheKey)) return;
    DOM.searchStatus.textContent = `Loading ${summary.name}…`;
    try {
      const detail = await fetchProteinDetail(summary);
      const fluorophore = VM.normalizeFluorophoreDetail(detail, summary);
      state.loadedProteins.set(cacheKey, fluorophore);
      DOM.searchStatus.textContent = `${fluorophore.name} loaded.`;
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
        subtitle.textContent = fluorophore.activeStateName;
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

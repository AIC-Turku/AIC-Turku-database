(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.VirtualMicroscopeRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const ROUTE_TAGS = new Set(['epi', 'tirf', 'confocal', 'multiphoton', 'shared', 'all']);
  const CAMERA_KINDS = new Set(['camera', 'scmos', 'cmos', 'ccd', 'emccd']);
  const HYBRID_KINDS = new Set(['hyd']);
  const APD_KINDS = new Set(['apd', 'spad']);
  const POINT_KINDS = new Set(['pmt', 'gaasp_pmt', 'hyd', 'apd', 'spad']);


  const FPBASE_FALLBACK_LIBRARY = [
    {
      uuid: 'ZERB6',
      name: 'mCherry',
      slug: 'mcherry',
      states: [
        {
          slug: 'mcherry_default',
          name: 'default',
          is_default: true,
          ex_max: 587,
          em_max: 610,
          ext_coeff: 72000,
          qy: 0.22,
          brightness: 15.84,
          spectra: [
            { spectrum_type: 'excitation', data: [[460, 0], [500, 8], [540, 35], [560, 62], [575, 90], [587, 100], [600, 78], [620, 28], [650, 0]] },
            { spectrum_type: 'emission', data: [[560, 0], [580, 18], [595, 55], [610, 100], [625, 82], [645, 34], [675, 7], [710, 0]] }
          ]
        }
      ],
    },
    {
      uuid: 'ZRKRV',
      name: 'mNeonGreen',
      slug: 'mneongreen',
      states: [
        {
          slug: 'mneongreen_default',
          name: 'default',
          is_default: true,
          ex_max: 506,
          em_max: 517,
          ext_coeff: 116000,
          qy: 0.8,
          brightness: 92.8,
          spectra: [
            { spectrum_type: 'excitation', data: [[420, 0], [455, 18], [480, 62], [495, 90], [506, 100], [520, 74], [545, 12], [575, 0]] },
            { spectrum_type: 'emission', data: [[485, 0], [500, 26], [517, 100], [535, 68], [560, 10], [590, 0]] }
          ]
        }
      ],
    },
  ];

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function cleanString(value) {
    return typeof value === 'string' ? value.trim() : '';
  }

  function numberOrNull(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const cleaned = value.trim();
      if (!cleaned) return null;
      const numeric = Number(cleaned);
      return Number.isFinite(numeric) ? numeric : null;
    }
    return null;
  }

  function normalizePercent(value, fallback = null) {
    const numeric = numberOrNull(value);
    if (numeric === null) return fallback;
    if (numeric > 1.1) return clamp(numeric / 100, 0, 1.25);
    return clamp(numeric, 0, 1.25);
  }

  function normalizeRouteTags(value) {
    const items = Array.isArray(value) ? value : [value];
    const tags = [];
    items.forEach((item) => {
      const cleaned = cleanString(item).toLowerCase();
      if (cleaned && ROUTE_TAGS.has(cleaned) && !tags.includes(cleaned)) {
        tags.push(cleaned);
      }
    });
    return tags;
  }

  function routesFromObject(obj) {
    if (!obj || typeof obj !== 'object') return [];
    return normalizeRouteTags(obj.routes || obj.path || obj.paths || obj.route || obj.tags || obj.__routes || []);
  }

  function routeMatches(itemRoutes, activeRoute) {
    if (!activeRoute) return true;
    if (!Array.isArray(itemRoutes) || itemRoutes.length === 0) return true;
    return itemRoutes.includes(activeRoute) || itemRoutes.includes('shared') || itemRoutes.includes('all');
  }

  function detectorClass(kind) {
    const normalized = cleanString(kind).toLowerCase();
    if (CAMERA_KINDS.has(normalized)) return 'camera';
    if (HYBRID_KINDS.has(normalized)) return 'hybrid';
    if (APD_KINDS.has(normalized)) return 'apd';
    if (POINT_KINDS.has(normalized)) return 'point';
    return 'detector';
  }

  function positionsToObject(positions) {
    if (Array.isArray(positions)) {
      return Object.fromEntries(
        positions
          .filter((entry) => entry && typeof entry === 'object')
          .map((entry, index) => [String(Number.isFinite(entry.slot) ? entry.slot : index + 1), entry])
      );
    }
    if (positions && typeof positions === 'object') {
      return { ...positions };
    }
    return {};
  }

  function normalizeMechanismList(rows) {
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && typeof row === 'object')
      .map((mechanism, index) => {
        const routes = routesFromObject(mechanism);
        const positions = positionsToObject(mechanism.positions);
        const normalizedPositions = Object.fromEntries(
          Object.entries(positions).map(([slot, component]) => {
            const entry = component && typeof component === 'object' ? { ...component } : {};
            entry.slot = Number.isFinite(entry.slot) ? entry.slot : Number(slot);
            entry.__routes = routesFromObject(entry).length ? routesFromObject(entry) : routes;
            if (!entry.display_label && entry.label) entry.display_label = entry.label;
            return [slot, entry];
          })
        );
        const options = Array.isArray(mechanism.options)
          ? mechanism.options.map((option) => ({
              ...option,
              value: option && option.value && typeof option.value === 'object'
                ? {
                    ...option.value,
                    slot: Number.isFinite(option.value.slot) ? option.value.slot : Number(option.slot),
                    __routes: routesFromObject(option.value).length ? routesFromObject(option.value) : routes,
                  }
                : option.value,
            }))
          : Object.values(normalizedPositions).map((entry) => ({
              slot: entry.slot,
              display_label: entry.display_label || entry.label || `Slot ${entry.slot}`,
              value: entry,
            }));
        return {
          ...mechanism,
          id: mechanism.id || `mechanism_${index}`,
          __routes: routes,
          positions: normalizedPositions,
          options,
        };
      });
  }

  function normalizeSplitters(rows) {
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && typeof row === 'object')
      .map((splitter, index) => {
        const routes = routesFromObject(splitter);
        const legacyPath1 = splitter.path1 && splitter.path1.positions ? splitter.path1.positions[1] || splitter.path1.positions['1'] : null;
        const legacyPath2 = splitter.path2 && splitter.path2.positions ? splitter.path2.positions[1] || splitter.path2.positions['1'] : null;
        const branches = Array.isArray(splitter.branches) && splitter.branches.length
          ? splitter.branches.map((branch, branchIndex) => ({
              ...branch,
              id: branch.id || `splitter_${index}_branch_${branchIndex + 1}`,
              component: branch.component && typeof branch.component === 'object' ? { ...branch.component } : {},
              __routes: routesFromObject(branch).length ? routesFromObject(branch) : routes,
            }))
          : [
              {
                id: `splitter_${index}_path1`,
                label: (splitter.path1 && splitter.path1.name) || 'Path 1',
                mode: 'transmitted',
                component: legacyPath1 && typeof legacyPath1 === 'object' ? { ...legacyPath1 } : { component_type: 'mirror', label: 'Mirror' },
                __routes: routes,
              },
              {
                id: `splitter_${index}_path2`,
                label: (splitter.path2 && splitter.path2.name) || 'Path 2',
                mode: 'reflected',
                component: legacyPath2 && typeof legacyPath2 === 'object' ? { ...legacyPath2 } : { component_type: 'mirror', label: 'Mirror' },
                __routes: routes,
              },
            ];
        return {
          ...splitter,
          id: splitter.id || `splitter_${index}`,
          __routes: routes,
          branches,
        };
      });
  }

  function normalizeInstrumentPayload(rawPayload) {
    const payload = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
    return {
      metadata: payload.metadata || {},
      lightSources: normalizeMechanismList(payload.light_sources),
      cube: normalizeMechanismList(payload.stages && payload.stages.cube),
      excitation: normalizeMechanismList(payload.stages && payload.stages.excitation),
      dichroic: normalizeMechanismList(payload.stages && payload.stages.dichroic),
      emission: normalizeMechanismList(payload.stages && payload.stages.emission),
      splitters: normalizeSplitters(payload.runtime_splitters || payload.splitters),
      detectors: normalizeMechanismList(payload.detectors),
      validPaths: Array.isArray(payload.valid_paths) ? payload.valid_paths : [],
    };
  }

  function normalizePoints(rawPoints) {
    if (!Array.isArray(rawPoints)) return [];
    const points = rawPoints
      .map((point) => {
        if (Array.isArray(point)) return { x: Number(point[0]), y: Number(point[1]) };
        const x = Number(point && (point.x ?? point.wl ?? point.wavelength ?? point.nm));
        const y = Number(point && (point.y ?? point.value ?? point.intensity ?? point.v));
        return { x, y };
      })
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .sort((a, b) => a.x - b.x);
    if (!points.length) return [];
    const max = Math.max(...points.map((point) => point.y));
    const scale = max > 0 && max <= 1.05 ? 100 : 1;
    return points.map((point) => ({ x: point.x, y: point.y * scale }));
  }

  function normalizeResultsShape(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data && data.results)) return data.results;
    if (Array.isArray(data && data.proteins)) return data.proteins;
    return [];
  }


  function defaultStateRecord(record) {
    const states = Array.isArray(record && record.states) ? record.states : [];
    return states.find((state) => Boolean(state && (state.is_default || state.default))) || states[0] || null;
  }

  function firstDefinedNumber(...values) {
    for (const value of values) {
      const numeric = numberOrNull(value);
      if (numeric !== null) return numeric;
    }
    return null;
  }

  function findMaxima(record, fallback) {
    const state = defaultStateRecord(record);
    const exMax = firstDefinedNumber(
      record && (record.exMax ?? record.ex_max ?? record.exc_max ?? record.excitation_max),
      state && (state.exMax ?? state.ex_max ?? state.exc_max ?? state.excitation_max),
      record && record.default_state && (record.default_state.exMax ?? record.default_state.ex_max),
    );
    const emMax = firstDefinedNumber(
      record && (record.emMax ?? record.em_max ?? record.emission_max),
      state && (state.emMax ?? state.em_max ?? state.emission_max),
      record && record.default_state && (record.default_state.emMax ?? record.default_state.em_max),
    );
    return {
      exMax: exMax ?? (fallback && fallback.exMax) ?? null,
      emMax: emMax ?? (fallback && fallback.emMax) ?? null,
    };
  }

  function gaussianPointSeries(center, width, minNm, maxNm, stepNm) {
    if (center === null || center === undefined) return [];
    const sigma = Math.max(8, numberOrNull(width) ?? 35);
    const start = Math.max(300, Math.round((numberOrNull(minNm) ?? (center - (sigma * 4))) / 5) * 5);
    const stop = Math.min(1800, Math.round((numberOrNull(maxNm) ?? (center + (sigma * 4))) / 5) * 5);
    const step = Math.max(2, numberOrNull(stepNm) ?? 5);
    const points = [];
    for (let wavelength = start; wavelength <= stop + 1e-9; wavelength += step) {
      const exponent = -0.5 * (((wavelength - center) / sigma) ** 2);
      points.push({ x: Number(wavelength.toFixed(3)), y: Number((Math.exp(exponent) * 100).toFixed(6)) });
    }
    return points;
  }

  function synthesizeSpectrumFromMaxima(kind, maximum) {
    const maxNm = numberOrNull(maximum);
    if (maxNm === null) return [];
    if (kind === 'ex2p') {
      return gaussianPointSeries(maxNm * 2, 80, maxNm * 2 - 260, maxNm * 2 + 260, 10);
    }
    if (kind === 'em') {
      return gaussianPointSeries(maxNm, 42, maxNm - 110, maxNm + 150, 5);
    }
    return gaussianPointSeries(maxNm, 34, maxNm - 130, maxNm + 110, 5);
  }

  function stateScalar(record, keys, fallback = null) {
    const state = defaultStateRecord(record);
    const candidates = [];
    (Array.isArray(keys) ? keys : [keys]).forEach((key) => {
      candidates.push(record && record[key]);
      candidates.push(state && state[key]);
      candidates.push(record && record.default_state && record.default_state[key]);
    });
    const numeric = firstDefinedNumber(...candidates);
    return numeric ?? fallback;
  }

  function normalizeFPbaseSearchResults(data) {
    return normalizeResultsShape(data).map((protein, index) => {
      const maxima = findMaxima(protein, null);
      const key = cleanString(protein && (protein.uuid || protein.slug || protein.id || protein.name)) || `protein_${index + 1}`;
      return {
        key,
        canonicalKey: key,
        id: protein && protein.id != null ? String(protein.id) : '',
        uuid: cleanString(protein && protein.uuid),
        slug: cleanString(protein && protein.slug),
        name: cleanString(protein && protein.name) || key,
        exMax: maxima.exMax,
        emMax: maxima.emMax,
        brightness: stateScalar(protein, ['brightness', 'spectral_brightness']),
        ec: stateScalar(protein, ['ec', 'ext_coeff', 'extinction_coefficient']),
        qy: stateScalar(protein, ['qy', 'quantum_yield']),
        raw: protein,
      };
    });
  }

  function normalizeTypeToken(spectrum) {
    return String(
      (spectrum && (spectrum.spectrum_type || spectrum.type || spectrum.subtype || spectrum.category || spectrum.name)) || ''
    ).toLowerCase();
  }

  function matchSpectrumType(token, aliases) {
    return aliases.some((alias) => token.includes(alias));
  }

  function collectTopLevelSpectra(detail) {
    const collected = [];
    if (Array.isArray(detail && detail.spectra)) collected.push(...detail.spectra);
    if (Array.isArray(detail && detail.spectrum)) collected.push(...detail.spectrum);
    if (detail && Array.isArray(detail.spectral_data)) collected.push(...detail.spectral_data);
    if (Array.isArray(detail && detail.states)) {
      detail.states.forEach((state) => {
        if (Array.isArray(state && state.spectra)) collected.push(...state.spectra);
      });
    }
    return collected;
  }

  function spectrumFromAliases(spectra, aliases) {
    const matched = (Array.isArray(spectra) ? spectra : []).find((spectrum) =>
      matchSpectrumType(normalizeTypeToken(spectrum), aliases)
    );
    return matched ? normalizePoints(matched.data || matched.points || matched.values) : [];
  }

  function spectrumRowCandidates(row) {
    const protein = row && (row.protein || row.fp || row.fluorophore || {});
    const state = row && (row.state || row.fp_state || {});
    const proteinKeys = [
      cleanString(row && row.protein_uuid),
      cleanString(row && row.protein_slug),
      cleanString(row && row.protein_name),
      cleanString(protein && (protein.uuid || protein.slug || protein.name || protein.id)),
    ].filter(Boolean);
    const stateKeys = [
      cleanString(row && row.state_uuid),
      cleanString(row && row.state_slug),
      cleanString(row && row.state_name),
      cleanString(state && (state.uuid || state.slug || state.name || state.id)),
    ].filter(Boolean);
    return { proteinKeys, stateKeys };
  }

  function normalizeFPbaseSpectraResponse(data) {
    const rows = [];
    const enqueue = (row) => {
      if (!row || typeof row !== 'object') return;
      const points = normalizePoints(row.data || row.points || row.values || row.spectrum);
      if (!points.length && Array.isArray(row.spectra)) {
        row.spectra.forEach(enqueue);
        return;
      }
      if (!points.length) return;
      const token = normalizeTypeToken(row);
      const type = matchSpectrumType(token, ['2p', 'two-photon', 'two photon'])
        ? 'ex2p'
        : matchSpectrumType(token, ['emission', ' em'])
          ? 'em'
          : 'ex1p';
      const { proteinKeys, stateKeys } = spectrumRowCandidates(row);
      rows.push({
        type,
        points,
        proteinKeys,
        stateKeys,
      });
    };

    if (Array.isArray(data)) data.forEach(enqueue);
    if (data && typeof data === 'object') {
      [data.results, data.spectra, data.data, data.rows].forEach((collection) => {
        if (Array.isArray(collection)) collection.forEach(enqueue);
      });
      if (Array.isArray(data.states)) {
        data.states.forEach((state) => {
          if (Array.isArray(state && state.spectra)) {
            state.spectra.forEach((spectrum) => enqueue({ ...spectrum, state_slug: state.slug, state_name: state.name }));
          }
        });
      }
      if (Array.isArray(data.proteins)) {
        data.proteins.forEach((protein) => {
          if (Array.isArray(protein && protein.states)) {
            protein.states.forEach((state) => {
              if (Array.isArray(state && state.spectra)) {
                state.spectra.forEach((spectrum) => enqueue({
                  ...spectrum,
                  protein_uuid: protein.uuid,
                  protein_slug: protein.slug,
                  protein_name: protein.name,
                  state_slug: state.slug,
                  state_name: state.name,
                }));
              }
            });
          }
        });
      }
    }
    return rows;
  }

  function stateRecordFromRaw(state, index, detail, fallbackSummary) {
    const spectra = [];
    if (Array.isArray(state && state.spectra)) spectra.push(...state.spectra);
    if (!spectra.length) spectra.push(...collectTopLevelSpectra(detail));
    const maxima = findMaxima(state, findMaxima(detail, fallbackSummary));
    const ec = firstDefinedNumber(
      state && (state.ec ?? state.ext_coeff ?? state.extinction_coefficient),
      detail && (detail.ec ?? detail.ext_coeff ?? detail.extinction_coefficient),
      fallbackSummary && fallbackSummary.ec,
    );
    const qy = firstDefinedNumber(
      state && (state.qy ?? state.quantum_yield),
      detail && (detail.qy ?? detail.quantum_yield),
      fallbackSummary && fallbackSummary.qy,
    );
    const brightness = firstDefinedNumber(
      state && (state.brightness ?? state.spectral_brightness),
      detail && (detail.brightness ?? detail.spectral_brightness),
      fallbackSummary && fallbackSummary.brightness,
    );
    return {
      key: cleanString(state && (state.uuid || state.slug || state.id || state.name)) || `state_${index + 1}`,
      slug: cleanString(state && state.slug),
      name: cleanString(state && (state.name || state.label)) || (index === 0 ? 'Default state' : `State ${index + 1}`),
      isDefault: Boolean(state && (state.is_default || state.default || index === 0)),
      ex1p: spectrumFromAliases(spectra, ['excitation', 'absorption', '1p', ' ex']),
      ex2p: spectrumFromAliases(spectra, ['2p', 'two-photon', 'two photon']),
      em: spectrumFromAliases(spectra, ['emission', ' em']),
      exMax: maxima.exMax,
      emMax: maxima.emMax,
      ec,
      qy,
      brightness,
      spectraSource: 'detail',
    };
  }

  function ensureStateList(detail, summary) {
    const rawStates = Array.isArray(detail && detail.states) && detail.states.length
      ? detail.states
      : [detail && detail.default_state ? detail.default_state : detail || {}];
    const states = rawStates.map((state, index) => stateRecordFromRaw(state, index, detail, summary));
    if (!states.length) {
      states.push({
        key: 'default',
        slug: 'default',
        name: 'Default state',
        isDefault: true,
        ex1p: [],
        ex2p: [],
        em: [],
        exMax: summary && summary.exMax,
        emMax: summary && summary.emMax,
        ec: summary && summary.ec,
        qy: summary && summary.qy,
        brightness: summary && summary.brightness,
        spectraSource: 'none',
      });
    }
    return states;
  }

  function matchStateRecord(states, row) {
    const aliases = new Set((row.stateKeys || []).map((item) => cleanString(item).toLowerCase()).filter(Boolean));
    let matched = null;
    if (aliases.size) {
      matched = states.find((state) => aliases.has(cleanString(state.key).toLowerCase()) || aliases.has(cleanString(state.slug).toLowerCase()) || aliases.has(cleanString(state.name).toLowerCase()));
    }
    return matched || states.find((state) => state.isDefault) || states[0] || null;
  }

  function injectExternalSpectra(states, spectraSeed) {
    const rows = normalizeFPbaseSpectraResponse(spectraSeed);
    rows.forEach((row) => {
      const target = matchStateRecord(states, row);
      if (!target) return;
      if (row.type === 'ex2p' && row.points.length) target.ex2p = row.points;
      if (row.type === 'ex1p' && row.points.length) target.ex1p = row.points;
      if (row.type === 'em' && row.points.length) target.em = row.points;
      target.spectraSource = 'api';
    });
  }

  function ensureUsableStateSpectra(states) {
    (Array.isArray(states) ? states : []).forEach((state) => {
      if (!Array.isArray(state.ex1p) || !state.ex1p.length) {
        state.ex1p = synthesizeSpectrumFromMaxima('ex1p', state.exMax);
        if (state.ex1p.length) state.spectraSource = state.spectraSource === 'api' ? 'api+synthetic' : 'synthetic';
      }
      if (!Array.isArray(state.em) || !state.em.length) {
        state.em = synthesizeSpectrumFromMaxima('em', state.emMax);
        if (state.em.length) state.spectraSource = state.spectraSource === 'api' ? 'api+synthetic' : 'synthetic';
      }
    });
  }

  function normalizeFluorophoreDetail(detail, summarySeed, spectraSeed) {
    const summary = summarySeed && typeof summarySeed === 'object'
      ? summarySeed
      : (normalizeFPbaseSearchResults([detail])[0] || {});
    const states = ensureStateList(detail || {}, summary);
    if (spectraSeed) injectExternalSpectra(states, spectraSeed);
    ensureUsableStateSpectra(states);
    const activeState = states.find((state) => state.isDefault) || states[0];
    const key = summary.key || cleanString(detail && (detail.uuid || detail.slug || detail.id || detail.name)) || 'fluorophore';
    return {
      key,
      canonicalKey: key,
      id: cleanString(detail && detail.id) || summary.id || '',
      slug: cleanString(detail && detail.slug) || summary.slug || '',
      uuid: cleanString(detail && detail.uuid) || summary.uuid || '',
      name: cleanString(detail && detail.name) || summary.name || key,
      activeStateKey: activeState.key,
      activeStateName: activeState.name,
      states,
      spectra: {
        ex1p: activeState.ex1p,
        ex2p: activeState.ex2p,
        em: activeState.em,
      },
      exMax: activeState.exMax ?? summary.exMax ?? null,
      emMax: activeState.emMax ?? summary.emMax ?? null,
      brightness: activeState.brightness ?? summary.brightness ?? null,
      ec: activeState.ec ?? summary.ec ?? null,
      qy: activeState.qy ?? summary.qy ?? null,
      spectraSource: activeState.spectraSource || 'detail',
      raw: {
        summary: summarySeed || {},
        detailId: cleanString(detail && (detail.id || detail.slug || detail.uuid || detail.name)),
      },
    };
  }

  function fallbackFluorophoreRecords() {
    return FPBASE_FALLBACK_LIBRARY.map((entry) => normalizeFluorophoreDetail(entry, normalizeFPbaseSearchResults([entry])[0] || {}, entry));
  }

  function searchFallbackFluorophores(query) {
    const q = cleanString(query).toLowerCase();
    if (!q) return fallbackFluorophoreRecords();
    return fallbackFluorophoreRecords().filter((record) => {
      return [record.name, record.slug, record.uuid].some((value) => cleanString(value).toLowerCase().includes(q));
    });
  }

  function setFluorophoreState(fluorophore, stateKey) {
    const states = Array.isArray(fluorophore && fluorophore.states) ? fluorophore.states : [];
    const nextState = states.find((state) => state.key === stateKey) || states[0];
    if (!nextState) return fluorophore;
    return {
      ...fluorophore,
      activeStateKey: nextState.key,
      activeStateName: nextState.name,
      spectra: {
        ex1p: nextState.ex1p,
        ex2p: nextState.ex2p,
        em: nextState.em,
      },
      exMax: nextState.exMax ?? fluorophore.exMax ?? null,
      emMax: nextState.emMax ?? fluorophore.emMax ?? null,
      brightness: nextState.brightness ?? fluorophore.brightness ?? null,
      ec: nextState.ec ?? fluorophore.ec ?? null,
      qy: nextState.qy ?? fluorophore.qy ?? null,
      spectraSource: nextState.spectraSource ?? fluorophore.spectraSource ?? 'detail',
    };
  }

  function fluorophoreSpectra(fluorophore, options) {

    const preferTwoPhoton = Boolean(options && options.preferTwoPhoton);
    const ex2p = Array.isArray(fluorophore && fluorophore.spectra && fluorophore.spectra.ex2p) ? fluorophore.spectra.ex2p : [];
    const ex1p = Array.isArray(fluorophore && fluorophore.spectra && fluorophore.spectra.ex1p) ? fluorophore.spectra.ex1p : [];
    const em = Array.isArray(fluorophore && fluorophore.spectra && fluorophore.spectra.em) ? fluorophore.spectra.em : [];
    if (preferTwoPhoton && ex2p.length) {
      return { ex: ex2p, em, exMode: '2p', stateName: fluorophore.activeStateName || '' };
    }
    return { ex: ex1p, em, exMode: '1p', stateName: fluorophore.activeStateName || '' };
  }

  function wavelengthGrid(metadata) {
    const gridMeta = metadata && metadata.wavelength_grid ? metadata.wavelength_grid : metadata;
    const min = numberOrNull(gridMeta && (gridMeta.min_nm ?? gridMeta.minNm)) ?? 350;
    const max = numberOrNull(gridMeta && (gridMeta.max_nm ?? gridMeta.maxNm)) ?? 900;
    const step = numberOrNull(gridMeta && (gridMeta.step_nm ?? gridMeta.stepNm)) ?? 2;
    const safeStep = Math.max(1, step);
    const wavelengths = [];
    for (let wavelength = min; wavelength <= max + 1e-9; wavelength += safeStep) {
      wavelengths.push(Number(wavelength.toFixed(6)));
    }
    return wavelengths;
  }

  function interpolatePoints(points, wavelength) {
    if (!Array.isArray(points) || points.length === 0) return 0;
    if (wavelength <= points[0].x) return points[0].y;
    if (wavelength >= points[points.length - 1].x) return points[points.length - 1].y;
    for (let index = 0; index < points.length - 1; index += 1) {
      const left = points[index];
      const right = points[index + 1];
      if (wavelength < left.x || wavelength > right.x) continue;
      const range = right.x - left.x;
      if (range <= 0) return left.y;
      const ratio = (wavelength - left.x) / range;
      return left.y + (right.y - left.y) * ratio;
    }
    return 0;
  }

  function normalizeSpectrumForGrid(points, grid) {
    if (!Array.isArray(points) || !points.length) {
      return grid.map(() => 0);
    }
    const normalizedPoints = normalizePoints(points);
    if (!normalizedPoints.length) {
      return grid.map(() => 0);
    }
    const maxValue = Math.max(...normalizedPoints.map((point) => point.y));
    const divisor = maxValue > 1.01 ? maxValue : 1;
    return grid.map((wavelength) => clamp(interpolatePoints(normalizedPoints, wavelength) / divisor, 0, 1));
  }

  function mapArray(values, fn) {
    return values.map((value, index) => fn(value, index));
  }

  function addArrays(left, right) {
    return left.map((value, index) => value + (right[index] || 0));
  }

  function multiplyArrays(left, right) {
    return left.map((value, index) => value * (right[index] || 0));
  }

  function scaleArray(values, factor) {
    return values.map((value) => value * factor);
  }

  function integrateSpectrum(values, grid) {
    if (!Array.isArray(values) || !Array.isArray(grid) || values.length !== grid.length || values.length < 2) return 0;
    let area = 0;
    for (let index = 0; index < values.length - 1; index += 1) {
      const width = grid[index + 1] - grid[index];
      area += width * ((values[index] + values[index + 1]) / 2);
    }
    return area;
  }

  function safeRatio(numerator, denominator) {
    return denominator > 0 ? numerator / denominator : 0;
  }

  function smoothStep(value, edge, width) {
    const safeWidth = Math.max(1, width || 1);
    if (value <= edge - safeWidth) return 0;
    if (value >= edge + safeWidth) return 1;
    return clamp((value - (edge - safeWidth)) / (2 * safeWidth), 0, 1);
  }

  function bandMask(grid, start, end, edgeWidth) {
    const low = Math.min(start, end);
    const high = Math.max(start, end);
    return grid.map((wavelength) => {
      if (wavelength <= low || wavelength >= high) {
        const lowEdge = smoothStep(wavelength, low, edgeWidth || 2);
        const highEdge = 1 - smoothStep(wavelength, high, edgeWidth || 2);
        return clamp(Math.min(lowEdge, highEdge), 0, 1);
      }
      return 1;
    });
  }

  function gaussianSpectrum(grid, center, fwhm) {
    const sigma = Math.max((fwhm || 2) / 2.355, 0.5);
    return grid.map((wavelength) => Math.exp(-0.5 * ((wavelength - center) / sigma) ** 2));
  }

  function sumMasks(masks, grid) {
    if (!masks.length) return grid.map(() => 1);
    return masks.reduce((accumulator, mask, index) => (index === 0 ? mask : accumulator.map((value, i) => clamp(value + mask[i], 0, 1))), grid.map(() => 0));
  }

  function dichroicTransmitMask(grid, cutoffs) {
    const ordered = (Array.isArray(cutoffs) ? cutoffs : [])
      .map((cutoff) => numberOrNull(cutoff))
      .filter((cutoff) => cutoff !== null)
      .sort((left, right) => left - right);
    if (!ordered.length) return grid.map(() => 1);
    return grid.map((wavelength) => {
      let transmit = false;
      ordered.forEach((cutoff) => {
        if (wavelength >= cutoff) {
          transmit = !transmit;
        }
      });
      return transmit ? 1 : 0;
    });
  }

  function componentMask(component, grid, context) {
    const type = cleanString(component && (component.component_type || component.type)).toLowerCase();
    if (!type || type === 'mirror' || type === 'empty' || type === 'passthrough') {
      return grid.map(() => 1);
    }
    if (type === 'block' || type === 'blocker') {
      return grid.map(() => 0);
    }
    if (type === 'bandpass') {
      const center = numberOrNull(component.center_nm);
      const width = numberOrNull(component.width_nm);
      if (center === null || width === null) return grid.map(() => 1);
      return bandMask(grid, center - (width / 2), center + (width / 2), 2);
    }
    if (type === 'multiband_bandpass') {
      const bands = Array.isArray(component.bands) ? component.bands : [];
      const masks = bands
        .map((band) => {
          const center = numberOrNull(band && band.center_nm);
          const width = numberOrNull(band && band.width_nm);
          if (center === null || width === null) return null;
          return bandMask(grid, center - (width / 2), center + (width / 2), 2);
        })
        .filter(Boolean);
      return sumMasks(masks, grid);
    }
    if (type === 'longpass') {
      const cutoff = numberOrNull(component.cut_on_nm);
      return cutoff === null ? grid.map(() => 1) : grid.map((wavelength) => smoothStep(wavelength, cutoff, 2));
    }
    if (type === 'shortpass') {
      const cutoff = numberOrNull(component.cut_off_nm);
      return cutoff === null ? grid.map(() => 1) : grid.map((wavelength) => 1 - smoothStep(wavelength, cutoff, 2));
    }
    if (type === 'notch') {
      const center = numberOrNull(component.center_nm);
      const width = numberOrNull(component.width_nm);
      if (center === null || width === null) return grid.map(() => 1);
      const blocked = bandMask(grid, center - (width / 2), center + (width / 2), 2);
      return blocked.map((value) => 1 - value);
    }
    if (type === 'tunable') {
      const start = numberOrNull(component.band_start_nm) ?? numberOrNull(component.min_nm);
      const end = numberOrNull(component.band_end_nm) ?? numberOrNull(component.max_nm);
      if (start === null || end === null) return grid.map(() => 1);
      return bandMask(grid, start, end, 2);
    }
    if (type === 'dichroic' || type === 'multiband_dichroic' || type === 'polychroic') {
      const transmit = dichroicTransmitMask(grid, component.cutoffs_nm);
      const mode = cleanString(context && context.mode).toLowerCase();
      const branchMode = cleanString((context && context.branchMode) || component.branch_mode).toLowerCase();
      const wantsReflection = mode === 'excitation' || branchMode === 'reflected';
      return wantsReflection ? transmit.map((value) => 1 - value) : transmit;
    }
    return grid.map(() => 1);
  }

  function sourceCenters(source) {
    const chosen = numberOrNull(source && source.selected_wavelength_nm);
    if (chosen !== null) return [chosen];

    const explicitCenter = numberOrNull(source && source.wavelength_nm);
    if (explicitCenter !== null) return [explicitCenter];

    const values = [];
    const pushCandidate = (value) => {
      const numeric = numberOrNull(value);
      if (numeric !== null && numeric >= 300 && numeric <= 2000) {
        values.push(Number(numeric));
      }
    };

    [source && source.wavelengths_nm, source && source.lines_nm, source && source.lines].forEach((candidate) => {
      if (Array.isArray(candidate)) candidate.forEach(pushCandidate);
    });

    [
      source && source.wavelength_nm,
      source && source.display_label,
      source && source.name,
      source && source.model,
      source && source.product_code,
      source && source.notes,
    ].forEach((candidate) => {
      if (typeof candidate !== 'string') return;
      candidate
        .split(/[;,]/)
        .map((item) => item.trim())
        .filter(Boolean)
        .forEach((token) => {
          const slashLead = token.match(/(\d+(?:\.\d+)?)\s*\//);
          if (slashLead) {
            pushCandidate(slashLead[1]);
            return;
          }
          const nmLead = token.match(/(\d+(?:\.\d+)?)\s*nm/i);
          if (nmLead) {
            pushCandidate(nmLead[1]);
            return;
          }
          const bare = token.match(/^(\d+(?:\.\d+)?)(?:|$)/);
          if (bare) pushCandidate(bare[1]);
        });
    });

    return Array.from(new Set(values));
  }

  function sourceSpectrum(source, grid) {
    const centers = sourceCenters(source);
    const center = centers.length ? centers[0] : null;
    const width = numberOrNull(source && source.width_nm);
    const tunableMin = numberOrNull(source && source.tunable_min_nm);
    const tunableMax = numberOrNull(source && source.tunable_max_nm);
    const mode = cleanString(source && source.spectral_mode).toLowerCase();
    if (centers.length > 1 && (mode === 'line' || mode === 'tunable_line' || !mode)) {
      return centers.reduce((sum, item) => addArrays(sum, gaussianSpectrum(grid, item, width || 2)), grid.map(() => 0));
    }
    if ((mode === 'line' || mode === 'tunable_line') && center !== null) {
      return gaussianSpectrum(grid, center, width || 2);
    }
    if ((mode === 'band' || mode === 'tunable_band') && center !== null) {
      const safeWidth = width || 30;
      return bandMask(grid, center - (safeWidth / 2), center + (safeWidth / 2), 3);
    }
    if (tunableMin !== null && tunableMax !== null) {
      const chosen = center !== null ? center : ((tunableMin + tunableMax) / 2);
      return gaussianSpectrum(grid, chosen, width || 2);
    }
    if (center !== null) {
      return width && width > 2
        ? bandMask(grid, center - (width / 2), center + (width / 2), 3)
        : gaussianSpectrum(grid, center, 2);
    }
    return grid.map((wavelength) => (wavelength >= 350 && wavelength <= 800 ? 1 : 0));
  }

  function sourceWeight(source, selectedSources) {
    const explicit = numberOrNull(source && source.user_weight);
    if (explicit !== null) return Math.max(explicit, 0);
    const allWeights = selectedSources
      .map((item) => numberOrNull(item && item.power_weight))
      .filter((item) => item !== null && item > 0);
    const localWeight = numberOrNull(source && source.power_weight);
    if (localWeight === null || !allWeights.length) return 1;
    return clamp(localWeight / Math.max(...allWeights), 0.1, 2);
  }

  function dominantWavelength(spectrum, grid) {
    let max = -Infinity;
    let wavelength = null;
    spectrum.forEach((value, index) => {
      if (value > max) {
        max = value;
        wavelength = grid[index];
      }
    });
    return wavelength;
  }


  function detectorResponse(detector, grid) {
    const kind = cleanString(detector && detector.kind).toLowerCase();
    const className = detectorClass(kind);
    let center = 550;
    let width = 260;
    let floor = 0.1;
    let peak = normalizePercent(detector && detector.qe_peak_pct, null);

    if (className === 'camera') {
      center = 560;
      width = 280;
      floor = 0.18;
      if (peak === null) peak = kind === 'emccd' ? 0.9 : 0.75;
    } else if (className === 'hybrid') {
      center = 560;
      width = 240;
      floor = 0.12;
      if (peak === null) peak = 0.65;
    } else if (className === 'apd') {
      center = 650;
      width = 170;
      floor = 0.05;
      if (peak === null) peak = 0.55;
    } else if (className === 'point') {
      center = kind === 'gaasp_pmt' ? 540 : 520;
      width = kind === 'gaasp_pmt' ? 230 : 250;
      floor = 0.08;
      if (peak === null) peak = kind === 'gaasp_pmt' ? 0.5 : 0.35;
    } else if (peak === null) {
      peak = 0.5;
    }

    const gaussian = gaussianSpectrum(grid, center, width);
    return gaussian.map((value) => clamp((floor + ((1 - floor) * value)) * peak, 0, 1.25));
  }

  function detectorCollectionMask(detector, grid) {
    const className = detector && detector.detector_class ? detector.detector_class : detectorClass(detector && detector.kind);
    if (className === 'camera') return grid.map(() => 1);
    if (detector && detector.collection_enabled === false) return grid.map(() => 1);
    const center = firstDefinedNumber(
      detector && detector.collection_center_nm,
      detector && detector.channel_center_nm,
      detector && detector.wavelength_nm,
    );
    const width = firstDefinedNumber(
      detector && detector.collection_width_nm,
      detector && detector.bandwidth_nm,
      detector && detector.width_nm,
    );
    if (center === null || width === null) return grid.map(() => 1);
    return componentMask({ component_type: 'bandpass', center_nm: center, width_nm: Math.max(4, width) }, grid, { mode: 'emission' });
  }

  function detectorGainFactor(detector) {

    const gain = numberOrNull(detector && detector.user_gain);
    return gain === null ? 1 : clamp(gain, 0, 20);
  }

  function detectorGatingFactor(detector) {
    if (!detector || detector.supports_time_gating !== true) return 1;
    const delay = numberOrNull(detector.default_gating_delay_ns) ?? 0;
    const width = numberOrNull(detector.default_gate_width_ns) ?? 0;
    if (delay <= 0 && width <= 0) return 1;
    // First-order engineering approximation: narrower gates reduce recorded intensity
    // but are never modeled as complete loss because gating is often used to improve
    // contrast rather than simply block signal.
    return clamp((width + 1) / (width + delay + 1), 0.25, 1);
  }

  function applyMask(spectrum, mask) {
    return spectrum.map((value, index) => value * (mask[index] || 0));
  }

  function applyComponentSeries(inputSpectrum, components, grid, contextFactory) {
    return (Array.isArray(components) ? components : []).reduce((spectrum, component, index) => {
      if (!component || typeof component !== 'object') return spectrum;
      const context = typeof contextFactory === 'function' ? contextFactory(component, index) : contextFactory;
      return applyMask(spectrum, componentMask(component, grid, context || {}));
    }, inputSpectrum.slice());
  }

  function propagateSplitters(inputSpectrum, splitters, grid) {
    let branches = [{ id: 'main', label: 'Main Path', spectrum: inputSpectrum.slice() }];
    (Array.isArray(splitters) ? splitters : []).forEach((splitter) => {
      const nextBranches = [];
      const splitterDichroic = splitter && splitter.dichroic && splitter.dichroic.positions
        ? splitter.dichroic.positions[1] || splitter.dichroic.positions['1']
        : null;
      const branchDefs = Array.isArray(splitter && splitter.branches) ? splitter.branches : [];
      branches.forEach((branch) => {
        const transmittedBase = splitterDichroic
          ? applyMask(branch.spectrum, componentMask(splitterDichroic, grid, { mode: 'emission', branchMode: 'transmitted' }))
          : branch.spectrum.slice();
        const reflectedBase = splitterDichroic
          ? applyMask(branch.spectrum, componentMask(splitterDichroic, grid, { mode: 'emission', branchMode: 'reflected' }))
          : branch.spectrum.slice();

        const transmittedDef = branchDefs.find((item) => cleanString(item.mode).toLowerCase() === 'transmitted') || branchDefs[0] || { id: `${splitter.id}_path1`, label: 'Path 1', component: { component_type: 'mirror' } };
        const reflectedDef = branchDefs.find((item) => cleanString(item.mode).toLowerCase() === 'reflected') || branchDefs[1] || { id: `${splitter.id}_path2`, label: 'Path 2', component: { component_type: 'mirror' } };

        nextBranches.push({
          id: `${branch.id}/${transmittedDef.id}`,
          label: `${branch.label} -> ${transmittedDef.label || 'Path 1'}`,
          spectrum: applyMask(transmittedBase, componentMask(transmittedDef.component || {}, grid, { mode: 'emission', branchMode: 'transmitted' })),
        });
        nextBranches.push({
          id: `${branch.id}/${reflectedDef.id}`,
          label: `${branch.label} -> ${reflectedDef.label || 'Path 2'}`,
          spectrum: applyMask(reflectedBase, componentMask(reflectedDef.component || {}, grid, { mode: 'emission', branchMode: 'reflected' })),
        });
      });
      branches = nextBranches;
    });
    return branches;
  }

  function evaluateStedPair(fluorophore, excitationSources, depletionSources, grid) {
    if (!Array.isArray(depletionSources) || depletionSources.length === 0) {
      return {
        applied: false,
        label: 'off',
        score: 0,
        suppressionFactor: 1,
        sourceLabel: 'No depletion source',
      };
    }
    const spectra = fluorophoreSpectra(fluorophore, { preferTwoPhoton: false });
    const excitationCurve = normalizeSpectrumForGrid(spectra.ex, grid);
    const emissionCurve = normalizeSpectrumForGrid(spectra.em, grid);
    const selectedExcitationWavelengths = (Array.isArray(excitationSources) ? excitationSources : [])
      .map((source) => numberOrNull(source && (source.selected_wavelength_nm ?? source.wavelength_nm)))
      .filter((wavelength) => wavelength !== null);

    let best = null;
    depletionSources.forEach((source) => {
      const depSpectrum = sourceSpectrum(source, grid);
      const depArea = integrateSpectrum(depSpectrum, grid);
      const emissionOverlap = safeRatio(integrateSpectrum(multiplyArrays(depSpectrum, emissionCurve), grid), depArea);
      const excitationOverlap = safeRatio(integrateSpectrum(multiplyArrays(depSpectrum, excitationCurve), grid), depArea);
      const depCenter = dominantWavelength(depSpectrum, grid);
      const redShift = fluorophore.emMax != null && depCenter != null ? clamp((depCenter - fluorophore.emMax) / 220, 0, 1) : 0;
      const targets = Array.isArray(source && source.depletion_targets_nm) ? source.depletion_targets_nm.map((item) => numberOrNull(item)).filter((item) => item !== null) : [];
      const targetMatch = targets.length
        ? (selectedExcitationWavelengths.some((wavelength) => targets.some((target) => Math.abs(target - wavelength) <= 25)) ? 1 : 0)
        : 0.45;
      const timingMode = cleanString(source && source.timing_mode).toLowerCase();
      const timingBonus = timingMode === 'pulsed' ? 1 : timingMode === 'cw' ? 0.75 : 0.6;
      // First-order engineering heuristic: a good depletion line should overlap emission,
      // be red-shifted from the fluorophore emission peak, and avoid strongly driving
      // the fluorophore excitation spectrum.
      const score = clamp((0.48 * emissionOverlap) + (0.2 * redShift) + (0.2 * targetMatch) + (0.12 * timingBonus) - (0.45 * excitationOverlap), 0, 1);
      const suppressionFactor = clamp(1 - (0.8 * score), 0.2, 1);
      const label = score >= 0.65 ? 'good' : score >= 0.4 ? 'usable' : 'poor';
      const candidate = {
        applied: true,
        label,
        score,
        suppressionFactor,
        sourceLabel: source.display_label || source.name || 'Depletion source',
        emissionOverlap,
        excitationPenalty: excitationOverlap,
      };
      if (!best || candidate.score > best.score) {
        best = candidate;
      }
    });
    return best || {
      applied: false,
      label: 'off',
      score: 0,
      suppressionFactor: 1,
      sourceLabel: 'No depletion source',
    };
  }

  function pickPositionValue(mechanism, slot) {
    const positions = mechanism && mechanism.positions ? mechanism.positions : {};
    return positions[String(slot)] || positions[slot] || null;
  }

  function selectionIsValid(validPaths, selectionMap) {
    if (!Array.isArray(validPaths) || !validPaths.length) return true;
    const requiredEntries = Object.entries(selectionMap || {}).filter(([, value]) => Number.isFinite(value));
    if (!requiredEntries.length) return true;
    return validPaths.some((path) => requiredEntries.every(([key, value]) => path[key] === undefined || path[key] === value));
  }


  function simulateInstrument(instrument, selection, fluorophores, options) {
    const normalizedInstrument = normalizeInstrumentPayload(instrument);
    const grid = wavelengthGrid(normalizedInstrument.metadata && normalizedInstrument.metadata.wavelength_grid);
    const selected = selection && typeof selection === 'object' ? selection : {};
    const selectedSources = Array.isArray(selected.sources) ? selected.sources : [];
    const excitationSources = selectedSources.filter((source) => cleanString(source.role).toLowerCase() !== 'depletion');
    const depletionSources = selectedSources.filter((source) => cleanString(source.role).toLowerCase() === 'depletion');
    const excitationComponents = Array.isArray(selected.excitation) ? selected.excitation : [];
    const dichroicComponents = Array.isArray(selected.dichroic) ? selected.dichroic : [];
    const emissionComponents = Array.isArray(selected.emission) ? selected.emission : [];
    const selectedSplitters = Array.isArray(selected.splitters) ? selected.splitters : [];
    const selectedDetectors = Array.isArray(selected.detectors) ? selected.detectors : [];
    const fluorList = Array.isArray(fluorophores) ? fluorophores : [];

    let combinedExcitation = grid.map(() => 0);
    excitationSources.forEach((source) => {
      const weightedSpectrum = scaleArray(sourceSpectrum(source, grid), sourceWeight(source, excitationSources));
      combinedExcitation = addArrays(combinedExcitation, weightedSpectrum);
    });
    const excitationAtSample = applyComponentSeries(
      applyComponentSeries(combinedExcitation, excitationComponents, grid, { mode: 'excitation' }),
      dichroicComponents,
      grid,
      { mode: 'excitation' }
    );

    const results = [];
    const emittedSpectra = [];
    const pathSpectra = [];
    fluorList.forEach((fluorophore) => {
      const { ex, em } = fluorophoreSpectra(fluorophore, { preferTwoPhoton: Boolean(options && options.preferTwoPhoton) });
      const excitationCurve = normalizeSpectrumForGrid(ex, grid);
      const emissionCurve = normalizeSpectrumForGrid(em, grid);
      const excitationStrength = clamp(
        safeRatio(
          integrateSpectrum(multiplyArrays(excitationAtSample, excitationCurve), grid),
          integrateSpectrum(excitationCurve, grid)
        ),
        0,
        1.5
      );
      const sted = evaluateStedPair(fluorophore, excitationSources, depletionSources, grid);
      const generatedEmission = scaleArray(emissionCurve, excitationStrength * sted.suppressionFactor);
      const afterDichroic = applyComponentSeries(generatedEmission, dichroicComponents, grid, { mode: 'emission' });
      const afterEmissionFilters = applyComponentSeries(afterDichroic, emissionComponents, grid, { mode: 'emission' });
      const branches = selectedSplitters.length
        ? propagateSplitters(afterEmissionFilters, selectedSplitters, grid)
        : [{ id: 'main', label: 'Main Path', spectrum: afterEmissionFilters }];
      const emissionArea = integrateSpectrum(generatedEmission, grid);

      emittedSpectra.push({
        fluorophoreKey: fluorophore.key,
        fluorophoreName: fluorophore.name,
        generatedSpectrum: generatedEmission,
        postOpticsSpectrum: afterEmissionFilters,
        sted,
      });

      const detectorTargets = selectedDetectors.length ? selectedDetectors : [{
        id: 'virtual_detector',
        display_label: 'Virtual Detector',
        name: 'Virtual Detector',
        kind: 'detector',
        detector_class: 'detector',
        user_gain: 1,
      }];

      detectorTargets.forEach((detector) => {
        const response = detectorResponse(detector, grid);
        const collectionMask = detectorCollectionMask(detector, grid);
        const gainFactor = detectorGainFactor(detector);
        const gatingFactor = detectorGatingFactor(detector);
        branches.forEach((branch) => {
          const collectedSpectrum = applyMask(branch.spectrum, collectionMask);
          const emissionPathThroughput = safeRatio(integrateSpectrum(collectedSpectrum, grid), emissionArea);
          const detectorWeightedIntensity = integrateSpectrum(multiplyArrays(collectedSpectrum, response), grid) * gainFactor * gatingFactor;
          pathSpectra.push({
            fluorophoreKey: fluorophore.key,
            fluorophoreName: fluorophore.name,
            detectorKey: detector.id || detector.display_label || detector.name,
            detectorLabel: detector.display_label || detector.name || 'Detector',
            detectorClass: detector.detector_class || detectorClass(detector.kind),
            pathKey: `${branch.id}::${detector.id || detector.display_label || detector.name || 'detector'}`,
            pathLabel: `${branch.label} -> ${detector.display_label || detector.name || 'Detector'}`,
            spectrum: collectedSpectrum,
            preDetectorSpectrum: branch.spectrum.slice(),
            collectionMask,
            detectorResponse: response,
            collectionCenterNm: firstDefinedNumber(detector.collection_center_nm, detector.channel_center_nm),
            collectionWidthNm: firstDefinedNumber(detector.collection_width_nm, detector.bandwidth_nm),
          });
          results.push({
            fluorophoreKey: fluorophore.key,
            fluorophoreName: fluorophore.name,
            fluorophoreState: fluorophore.activeStateName || 'Default state',
            detectorKey: detector.id || detector.display_label || detector.name,
            detectorLabel: detector.display_label || detector.name || 'Detector',
            detectorClass: detector.detector_class || detectorClass(detector.kind),
            pathKey: `${branch.id}::${detector.id || detector.display_label || detector.name || 'detector'}`,
            pathLabel: `${branch.label} -> ${detector.display_label || detector.name || 'Detector'}`,
            excitationStrength,
            emissionPathThroughput,
            detectorWeightedIntensity,
            gainFactor,
            gatingFactor,
            sted,
          });
        });
      });
    });

    const totalsByPath = new Map();
    results.forEach((result) => {
      totalsByPath.set(result.pathKey, (totalsByPath.get(result.pathKey) || 0) + result.detectorWeightedIntensity);
    });
    results.forEach((result) => {
      const total = totalsByPath.get(result.pathKey) || 0;
      const bleed = Math.max(0, total - result.detectorWeightedIntensity);
      result.bleedThrough = bleed;
      result.crosstalkPct = total > 0 ? (bleed / total) * 100 : 0;
    });

    return {
      grid,
      excitationAtSample,
      emittedSpectra,
      pathSpectra,
      selectedSources: selectedSources.map((source) => source.display_label || source.name || 'Source'),
      selectedDetectors: selectedDetectors.map((detector) => detector.display_label || detector.name || 'Detector'),
      validSelection: selectionIsValid(normalizedInstrument.validPaths, selected.selectionMap || {}),
      results,
    };
  }

  return {
    normalizeRouteTags,

    routesFromObject,
    routeMatches,
    detectorClass,
    normalizeMechanismList,
    normalizeSplitters,
    normalizeInstrumentPayload,
    normalizeResultsShape,
    normalizeFPbaseSearchResults,
    normalizeFPbaseSpectraResponse,
    normalizeFluorophoreDetail,
    searchFallbackFluorophores,
    setFluorophoreState,
    fluorophoreSpectra,
    normalizePoints,
    wavelengthGrid,
    componentMask,
    sourceCenters,
    sourceSpectrum,
    detectorResponse,
    detectorCollectionMask,
    selectionIsValid,
    simulateInstrument,
  };
});

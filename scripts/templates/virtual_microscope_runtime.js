(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.VirtualMicroscopeRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const ROUTE_TAGS = new Set(['epi', 'widefield_fluorescence', 'tirf', 'confocal', 'confocal_point', 'confocal_spinning_disk', 'multiphoton', 'light_sheet', 'transmitted', 'transmitted_brightfield', 'phase_contrast', 'darkfield', 'dic', 'reflected_brightfield', 'optical_sectioning', 'spectral_imaging', 'flim', 'fcs', 'ism', 'smlm', 'spt', 'fret', 'shared', 'all']);
  const ROUTE_LABELS = {
    confocal: 'Confocal',
    confocal_point: 'Point-Scanning Confocal',
    confocal_spinning_disk: 'Spinning-Disk Confocal',
    epi: 'Epi-fluorescence',
    widefield_fluorescence: 'Epi-fluorescence',
    tirf: 'TIRF',
    multiphoton: 'Multiphoton',
    light_sheet: 'Light Sheet',
    transmitted: 'Transmitted light',
    transmitted_brightfield: 'Transmitted Brightfield',
    phase_contrast: 'Phase Contrast',
    darkfield: 'Darkfield',
    dic: 'DIC',
    reflected_brightfield: 'Reflected Brightfield',
    optical_sectioning: 'Optical Sectioning',
    spectral_imaging: 'Spectral Imaging',
    flim: 'FLIM',
    fcs: 'FCS',
    ism: 'ISM',
    smlm: 'SMLM',
    spt: 'SPT',
    fret: 'FRET',
  };
  const ROUTE_SORT_ORDER = ['confocal', 'confocal_point', 'confocal_spinning_disk', 'epi', 'widefield_fluorescence', 'tirf', 'multiphoton', 'light_sheet', 'transmitted', 'transmitted_brightfield', 'phase_contrast', 'darkfield', 'dic', 'reflected_brightfield', 'optical_sectioning', 'spectral_imaging', 'flim', 'fcs', 'ism', 'smlm', 'spt', 'fret'];
  const CAMERA_KINDS = new Set(['camera', 'scmos', 'cmos', 'ccd', 'emccd']);
  const HYBRID_KINDS = new Set(['hyd']);
  const APD_KINDS = new Set(['apd', 'spad']);
  const POINT_KINDS = new Set(['pmt', 'gaasp_pmt', 'hyd', 'apd', 'spad']);



  const BUNDLED_FALLBACK_FLUOROPHORE_BUNDLES = [
    {
      summary: {
        uuid: 'ZERB6',
        slug: 'mcherry',
        name: 'mCherry',
        sourceOrigin: 'bundled_cache',
        states: [{ slug: 'mcherry_default', name: 'default', ex_max: 587, em_max: 610, ext_coeff: 72000, qy: 0.22, brightness: 15.84 }],
      },
      detail: {
        uuid: 'ZERB6',
        slug: 'mcherry',
        name: 'mCherry',
        states: [{ slug: 'mcherry_default', name: 'default', is_default: true, ex_max: 587, em_max: 610, ext_coeff: 72000, qy: 0.22, brightness: 15.84 }],
      },
      spectra: {
        sourceOrigin: 'bundled_cache',
        results: [
          { protein_uuid: 'ZERB6', protein_slug: 'mcherry', protein_name: 'mCherry', state_slug: 'mcherry_default', state_name: 'default', spectrum_type: 'excitation', data: [[460, 0], [500, 8], [540, 35], [560, 62], [575, 90], [587, 100], [600, 82], [620, 28], [650, 0]] },
          { protein_uuid: 'ZERB6', protein_slug: 'mcherry', protein_name: 'mCherry', state_slug: 'mcherry_default', state_name: 'default', spectrum_type: 'emission', data: [[560, 0], [580, 18], [595, 55], [610, 100], [625, 82], [645, 40], [675, 8], [710, 0]] },
        ],
      },
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

  function routeSortKey(route) {
    const index = ROUTE_SORT_ORDER.indexOf(route);
    return [index >= 0 ? index : ROUTE_SORT_ORDER.length, route];
  }

  function routeLabel(route) {
    const normalized = cleanString(route).toLowerCase();
    if (!normalized) return '';
    return ROUTE_LABELS[normalized] || normalized.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase());
  }

  function normalizeRouteCatalog(rawRoutes) {
    const catalog = [];
    const seen = new Set();
    (Array.isArray(rawRoutes) ? rawRoutes : []).forEach((entry) => {
      const routeId = cleanString(typeof entry === 'string' ? entry : (entry && (entry.id || entry.route || entry.value))).toLowerCase();
      if (!routeId || !ROUTE_TAGS.has(routeId) || routeId === 'shared' || routeId === 'all' || seen.has(routeId)) return;
      seen.add(routeId);
      catalog.push({
        id: routeId,
        label: cleanString(entry && entry.label) || routeLabel(routeId),
      });
    });
    catalog.sort((left, right) => {
      const [leftIndex, leftRoute] = routeSortKey(left.id);
      const [rightIndex, rightRoute] = routeSortKey(right.id);
      if (leftIndex !== rightIndex) return leftIndex - rightIndex;
      return leftRoute.localeCompare(rightRoute);
    });
    return catalog;
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

  function componentMatchesActiveRoute(component, route) {
    if (!route) return true;
    const tags = routesFromObject(component);
    return !tags.length || routeMatches(tags, route);
  }

  function detectorClass(kind) {
    const normalized = cleanString(kind).toLowerCase().replace(/[\s-]+/g, '_');
    if (['eyepiece', 'eyepieces', 'ocular', 'oculars'].includes(normalized)) return 'eyepiece';
    if (['camera_port', 'cameraport', 'camera_ports'].includes(normalized)) return 'camera_port';
    if (CAMERA_KINDS.has(normalized)) return 'camera';
    if (HYBRID_KINDS.has(normalized)) return 'hybrid';
    if (APD_KINDS.has(normalized)) return 'apd';
    if (POINT_KINDS.has(normalized)) return 'point';
    return 'detector';
  }

  function coerceSlotKey(key) {
    if (typeof key === 'number' && Number.isFinite(key)) return String(Math.trunc(key));
    const str = String(key).trim();
    if (/^\d+$/.test(str)) return str;
    const match = str.match(/(\d+)$/);
    return match ? match[1] : str;
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
      return Object.fromEntries(
        Object.entries(positions).map(([key, value]) => [coerceSlotKey(key), value])
      );
    }
    return {};
  }

  function positionDisplayLabel(slot, component) {
    if (component.display_label) return component.display_label;
    const name = cleanString(component.name || component.label);
    const bands = Array.isArray(component.bands) ? component.bands : [];
    if (name) return `Slot ${slot}: ${name}`;
    if (bands.length) {
      const bandStr = bands.map((band) => {
        const center = numberOrNull(band && band.center_nm);
        const width = numberOrNull(band && band.width_nm);
        return center !== null && width !== null ? `${Math.round(center)}/${Math.round(width)}` : null;
      }).filter(Boolean).join(' + ');
      if (bandStr) return `Slot ${slot}: ${bandStr}`;
    }
    const componentType = cleanString(component.component_type || component.type).replace(/_/g, ' ');
    if (componentType && componentType !== 'unknown') return `Slot ${slot}: ${componentType}`;
    return `Slot ${slot}`;
  }

  function normalizeMechanismList(rows) {
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && typeof row === 'object')
      .map((mechanism, index) => {
        const routes = routesFromObject(mechanism);
        const positions = positionsToObject(mechanism.positions);
        const normalizedPositions = Object.fromEntries(
          Object.entries(positions).map(([slot, component], posIndex) => {
            const normalizedSlot = coerceSlotKey(slot);
            const entry = component && typeof component === 'object' ? { ...component } : {};
            const slotNum = Number(normalizedSlot);
            entry.slot = Number.isFinite(entry.slot) ? entry.slot : (Number.isFinite(slotNum) ? slotNum : posIndex + 1);
            entry.__routes = routesFromObject(entry).length ? routesFromObject(entry) : routes;
            if (!entry.display_label) {
              entry.display_label = positionDisplayLabel(entry.slot, entry);
            }
            return [normalizedSlot, entry];
          })
        );
        const options = Array.isArray(mechanism.options)
          ? mechanism.options.map((option) => {
              const rawSlot = Number(option.slot);
              const coercedSlot = Number.isFinite(rawSlot) ? rawSlot : Number(coerceSlotKey(option.slot));
              return {
                ...option,
                slot: coercedSlot,
                value: option && option.value && typeof option.value === 'object'
                  ? {
                      ...option.value,
                      slot: Number.isFinite(option.value.slot) ? option.value.slot : coercedSlot,
                      __routes: routesFromObject(option.value).length ? routesFromObject(option.value) : routes,
                    }
                  : option.value,
              };
            })
          : Object.values(normalizedPositions).map((entry) => ({
              slot: entry.slot,
              display_label: entry.display_label || `Slot ${entry.slot}`,
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

  function normalizeIdentifier(value) {
    return cleanString(value).toLowerCase();
  }

  function normalizeTargetIds(value) {
    const items = Array.isArray(value) ? value : [value];
    const ids = [];
    const seen = new Set();
    items.forEach((item) => {
      const cleaned = normalizeIdentifier(item);
      if (!cleaned || seen.has(cleaned)) return;
      seen.add(cleaned);
      ids.push(cleaned);
    });
    return ids;
  }

  function normalizeEndpointType(value) {
    const normalized = normalizeIdentifier(value).replace(/[\s-]+/g, '_');
    if (!normalized) return 'detector';
    if (['eyepiece', 'eyepieces', 'ocular', 'oculars'].includes(normalized)) return 'eyepiece';
    if (['camera_port', 'cameraport', 'camera_ports'].includes(normalized)) return 'camera_port';
    return normalized;
  }

  function simulatorApproximationModeEnabled(metadata, options) {
    const modeFromOptions = cleanString(options && (options.simulationMode || options.mode)).toLowerCase();
    if (modeFromOptions === 'approximate' || modeFromOptions === 'simulator_approximation') return true;
    if (modeFromOptions === 'strict' || modeFromOptions === 'hardware_truth') return false;

    if (options && Object.prototype.hasOwnProperty.call(options, 'strictHardwareTruth')) {
      return options.strictHardwareTruth === false;
    }

    const modeFromMetadata = cleanString(metadata && (metadata.simulation_mode || metadata.runtime_mode)).toLowerCase();
    if (modeFromMetadata === 'approximate' || modeFromMetadata === 'simulator_approximation') return true;
    if (modeFromMetadata === 'strict' || modeFromMetadata === 'hardware_truth') return false;

    if (metadata && metadata.non_authoritative_simulator_mode === true) return true;
    return false;
  }

  function normalizeTerminals(rows) {
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && typeof row === 'object')
      .map((terminal, index) => {
        const routes = routesFromObject(terminal);
        const endpointType = normalizeEndpointType(terminal.endpoint_type || terminal.type || terminal.kind);
        const baseId = cleanString(terminal.id || terminal.terminal_id || terminal.name || terminal.display_label) || `terminal_${index + 1}`;
        const kind = cleanString(terminal.kind).toLowerCase() || endpointType;
        const out = {
          ...terminal,
          id: baseId,
          terminal_id: baseId,
          endpoint_type: endpointType,
          kind,
          name: cleanString(terminal.name) || cleanString(terminal.display_label) || `Endpoint ${index + 1}`,
          display_label: cleanString(terminal.display_label) || cleanString(terminal.name) || `Endpoint ${index + 1}`,
          detector_class: terminal.detector_class || detectorClass(kind),
          __routes: routes,
          default_enabled: terminal.default_enabled === undefined ? false : Boolean(terminal.default_enabled),
          is_digital: terminal.is_digital === undefined ? endpointType !== 'eyepiece' : Boolean(terminal.is_digital),
        };
        const collectionMin = numberOrNull(out.collection_min_nm);
        const collectionMax = numberOrNull(out.collection_max_nm);
        if (endpointType === 'eyepiece' && collectionMin === null && collectionMax === null) {
          out.collection_min_nm = 390;
          out.collection_max_nm = 700;
        }
        return out;
      });
  }

  function normalizeSplitters(rows, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && typeof row === 'object')
      .map((splitter, index) => {
        const routes = routesFromObject(splitter);
        // `path1` / `path2` are legacy compatibility fields only. Canonical v2 splitters
        // should arrive with explicit `branches`; approximation mode may still read these
        // fields when normalizing older derived payloads.
        const legacyPath1 = (splitter.path1 && splitter.path1.positions ? splitter.path1.positions[1] || splitter.path1.positions['1'] : null)
          || (splitter.path_1 && splitter.path_1.emission_filter ? splitter.path_1.emission_filter : null);
        const legacyPath2 = (splitter.path2 && splitter.path2.positions ? splitter.path2.positions[1] || splitter.path2.positions['1'] : null)
          || (splitter.path_2 && splitter.path_2.emission_filter ? splitter.path_2.emission_filter : null);
        const buildBranch = (branch, branchIndex, fallbackMode) => {
          const mode = cleanString(branch && branch.mode).toLowerCase() || fallbackMode || (branchIndex === 0 ? 'transmitted' : 'reflected');
          let component = branch && branch.component && typeof branch.component === 'object' ? { ...branch.component } : null;
          if (!component && branch && branch.emission_filter && typeof branch.emission_filter === 'object') {
            component = { ...branch.emission_filter };
          }
          if (!component && branch && (branch.component_type || branch.type)) {
            component = { ...branch };
          }
          if (!component && allowApproximation) component = { component_type: 'passthrough', label: 'Pass-through' };
          if (!component) component = {};
          return {
            ...branch,
            id: cleanString(branch && branch.id) || `splitter_${index}_branch_${branchIndex + 1}`,
            label: cleanString(branch && (branch.label || branch.name)) || `Branch ${branchIndex + 1}`,
            mode,
            component,
            target_ids: normalizeTargetIds(branch && (allowApproximation
              ? (branch.target_ids || branch.targets || branch.terminal_ids || branch.endpoint_ids || branch.target || branch.endpoint)
              : branch.target_ids)),
            __routes: routesFromObject(branch).length ? routesFromObject(branch) : routes,
          };
        };

        let branches = [];
        if (Array.isArray(splitter.branches) && splitter.branches.length) {
          branches = splitter.branches.map((branch, branchIndex) => buildBranch(branch, branchIndex, branchIndex === 0 ? 'transmitted' : 'reflected'));
        } else if (allowApproximation && (legacyPath1 || legacyPath2 || splitter.path1 || splitter.path2 || splitter.path_1 || splitter.path_2)) {
          const left = splitter.path1 || splitter.path_1 || {};
          const right = splitter.path2 || splitter.path_2 || {};
          branches = [
            buildBranch({ ...left, component: legacyPath1 || left.component || left.emission_filter }, 0, 'transmitted'),
            buildBranch({ ...right, component: legacyPath2 || right.component || right.emission_filter }, 1, 'reflected'),
          ].filter((branch, branchIndex) => branchIndex === 0 || legacyPath2 || right.component || right.emission_filter || cleanString(right.name || right.label));
        } else if (allowApproximation) {
          branches = [buildBranch({
            id: `splitter_${index}_main`,
            label: cleanString(splitter.name) || 'Primary Path',
            component: { component_type: 'passthrough', label: 'Pass-through' },
          }, 0, 'transmitted')];
        }

        return {
          ...splitter,
          id: splitter.id || `splitter_${index}`,
          __routes: routes,
          branches,
          branch_selection_required: splitter.branch_selection_required === undefined
            ? (branches.length > 1 && branches.some((branch) => !branch.target_ids.length))
            : Boolean(splitter.branch_selection_required),
        };
      });
  }

  function collectRouteCatalogFallback(normalizedPayload) {
    const tags = new Set();
    const collect = (obj) => {
      routesFromObject(obj).forEach((route) => {
        if (route !== 'shared' && route !== 'all') tags.add(route);
      });
      if (obj && typeof obj === 'object') {
        const linkedComponents = obj.linked_components || obj.linkedComponents;
        if (linkedComponents && typeof linkedComponents === 'object') {
          Object.values(linkedComponents).forEach(collect);
        }
        if (Array.isArray(obj.branches)) obj.branches.forEach(collect);
        if (obj.component && typeof obj.component === 'object') collect(obj.component);
      }
    };
    ['lightSources', 'cube', 'excitation', 'dichroic', 'emission', 'detectors', 'splitters', 'terminals'].forEach((key) => {
      (Array.isArray(normalizedPayload[key]) ? normalizedPayload[key] : []).forEach((mechanism) => {
        collect(mechanism);
        if (mechanism && mechanism.positions && typeof mechanism.positions === 'object') {
          Object.values(mechanism.positions).forEach(collect);
        }
      });
    });
    return normalizeRouteCatalog(Array.from(tags));
  }

  function canonicalElements(rows) {
    return (Array.isArray(rows) ? rows : []).filter((row) => row && typeof row === 'object');
  }

  function hasCanonicalDtoContract(payload) {
    if (!payload || typeof payload !== 'object') return false;
    return Array.isArray(payload.sources)
      || Array.isArray(payload.optical_path_elements)
      || Array.isArray(payload.endpoints)
      || Array.isArray(payload.light_paths);
  }

  function canonicalTopologyBindings(payload) {
    const sourceRoutes = new Map();
    const elementBindings = new Map();
    const endpointRoutes = new Map();
    const splitterBranches = new Map();
    const routeCatalog = [];

    const addRoute = (map, id, routeId) => {
      const normalizedId = normalizeIdentifier(id);
      const normalizedRoute = normalizeIdentifier(routeId);
      if (!normalizedId || !normalizedRoute) return;
      if (!map.has(normalizedId)) map.set(normalizedId, new Set());
      map.get(normalizedId).add(normalizedRoute);
    };

    const ensureElementBinding = (id) => {
      const normalizedId = normalizeIdentifier(id);
      if (!normalizedId) return null;
      if (!elementBindings.has(normalizedId)) {
        elementBindings.set(normalizedId, {
          routes: new Set(),
          illumination: [],
          detection: [],
        });
      }
      return elementBindings.get(normalizedId);
    };

    const ensureSplitterBinding = (elementId, selectionMode, routeId) => {
      const normalizedId = normalizeIdentifier(elementId);
      if (!normalizedId) return null;
      if (!splitterBranches.has(normalizedId)) {
        splitterBranches.set(normalizedId, {
          selection_mode: cleanString(selectionMode).toLowerCase() || 'exclusive',
          routes: new Set(),
          branches: [],
          branchIndex: new Map(),
        });
      }
      const binding = splitterBranches.get(normalizedId);
      if (routeId) binding.routes.add(routeId);
      if (cleanString(selectionMode)) binding.selection_mode = cleanString(selectionMode).toLowerCase();
      return binding;
    };

    const walkSequence = (sequence, routeId, phase, trail) => {
      let previousElementId = normalizeIdentifier(trail);
      (Array.isArray(sequence) ? sequence : []).forEach((step, stepIndex) => {
        if (!(step && typeof step === 'object')) return;
        const branchBlock = step.branches && typeof step.branches === 'object' ? step.branches : null;
        if (branchBlock) {
          const splitterBinding = ensureSplitterBinding(previousElementId, branchBlock.selection_mode, routeId);
          (Array.isArray(branchBlock.items) ? branchBlock.items : []).forEach((branch, branchIndex) => {
            if (!(branch && typeof branch === 'object')) return;
            const branchId = normalizeIdentifier(branch.branch_id || branch.id) || `branch_${branchIndex + 1}`;
            const dedupeKey = branchId;
            if (!splitterBinding) {
              walkSequence(branch.sequence, routeId, phase, previousElementId);
              return;
            }
            if (!splitterBinding.branchIndex.has(dedupeKey)) {
              splitterBinding.branchIndex.set(dedupeKey, splitterBinding.branches.length);
              splitterBinding.branches.push({
                id: branchId,
                label: cleanString(branch.label) || routeLabel(branchId),
                mode: cleanString(branch.mode).toLowerCase() || '',
                sequence: Array.isArray(branch.sequence) ? branch.sequence.map((item) => ({ ...item })) : [],
                target_ids: [],
                __routes: new Set(routeId ? [routeId] : []),
              });
            }
            const entry = splitterBinding.branches[splitterBinding.branchIndex.get(dedupeKey)];
            // Prefer an explicit label over the auto-generated routeLabel fallback.
            // The first route to provide a real label wins; subsequent routes keep it.
            if (!entry.label || entry.label === routeLabel(branchId)) {
              const candidateLabel = cleanString(branch.label);
              if (candidateLabel) entry.label = candidateLabel;
            }
            entry.sequence = Array.isArray(branch.sequence) ? branch.sequence.map((item) => ({ ...item })) : [];
            entry.__routes.add(routeId);
            const endpointIds = [];
            (Array.isArray(branch.sequence) ? branch.sequence : []).forEach((branchStep, branchStepIndex) => {
              if (!(branchStep && typeof branchStep === 'object')) return;
              if (branchStep.endpoint_id) {
                addRoute(endpointRoutes, branchStep.endpoint_id, routeId);
                const endpointId = normalizeIdentifier(branchStep.endpoint_id);
                if (endpointId && !endpointIds.includes(endpointId)) endpointIds.push(endpointId);
              }
              const branchElementBinding = ensureElementBinding(branchStep.optical_path_element_id);
              if (branchElementBinding) {
                branchElementBinding.routes.add(routeId);
                branchElementBinding[phase].push({ route: routeId, index: `${stepIndex}.${branchIndex}.${branchStepIndex}` });
              }
            });
            entry.target_ids = endpointIds.slice();
            walkSequence(branch.sequence, routeId, phase, previousElementId);
          });
          return;
        }
        addRoute(sourceRoutes, step.source_id, routeId);
        addRoute(endpointRoutes, step.endpoint_id, routeId);
        const binding = ensureElementBinding(step.optical_path_element_id);
        if (binding) {
          binding.routes.add(routeId);
          binding[phase].push({ route: routeId, index: stepIndex });
        }
        if (step.optical_path_element_id) previousElementId = normalizeIdentifier(step.optical_path_element_id);
      });
    };

    (Array.isArray(payload && payload.light_paths) ? payload.light_paths : []).forEach((route, routeIndex) => {
      const routeId = normalizeIdentifier(route && (route.id || route.route || route.name));
      if (!routeId) return;
      routeCatalog.push({
        id: routeId,
        label: cleanString(route && route.name) || routeLabel(routeId),
        order: routeIndex,
      });

      walkSequence(route && route.illumination_sequence, routeId, 'illumination', null);
      walkSequence(route && route.detection_sequence, routeId, 'detection', null);
    });

    splitterBranches.forEach((value) => {
      value.routes = Array.from(value.routes);
      value.branches = value.branches.map((branch) => ({
        ...branch,
        __routes: Array.from(branch.__routes || []),
      }));
      value.branchIndex = undefined;
    });

    return { sourceRoutes, elementBindings, endpointRoutes, splitterBranches, routeCatalog };
  }

  function orderedRoutesFromSet(routeSet, fallbackValue) {
    const routes = normalizeRouteTags(Array.from(routeSet || []));
    if (routes.length) return routes;
    return normalizeRouteTags(fallbackValue || []);
  }

  function canonicalElementRoutes(element, topologyBindings, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    const binding = topologyBindings && topologyBindings.elementBindings
      ? topologyBindings.elementBindings.get(normalizeIdentifier(element && element.id))
      : null;
    const boundRoutes = orderedRoutesFromSet(binding && binding.routes);
    if (boundRoutes.length) return boundRoutes;
    if (!allowApproximation) return [];
    return normalizeRouteTags((element && (element.modalities || element.routes || element.path || element.route)) || []);
  }

  function sortByRouteOccurrence(left, right) {
    const leftValue = Number.isFinite(left) ? left : Number.MAX_SAFE_INTEGER;
    const rightValue = Number.isFinite(right) ? right : Number.MAX_SAFE_INTEGER;
    return leftValue - rightValue;
  }

  function sequenceStepIds(sequence, key) {
    const ids = [];
    (Array.isArray(sequence) ? sequence : []).forEach((step) => {
      if (!(step && typeof step === 'object')) return;
      if (step[key]) {
        const normalized = normalizeIdentifier(step[key]);
        if (normalized && !ids.includes(normalized)) ids.push(normalized);
      }
      const branchBlock = step.branches && typeof step.branches === 'object' ? step.branches : null;
      if (branchBlock) {
        (Array.isArray(branchBlock.items) ? branchBlock.items : []).forEach((branch) => {
          ids.push(...sequenceStepIds(branch && branch.sequence, key));
        });
      }
    });
    return ids.filter((id, index) => ids.indexOf(id) === index);
  }

  function sequenceBranchBlocks(sequence) {
    const blocks = [];
    (Array.isArray(sequence) ? sequence : []).forEach((step) => {
      if (!(step && typeof step === 'object')) return;
      const branchBlock = step.branches && typeof step.branches === 'object' ? step.branches : null;
      if (!branchBlock) return;
      blocks.push({
        selection_mode: cleanString(branchBlock.selection_mode).toLowerCase() || 'exclusive',
        items: (Array.isArray(branchBlock.items) ? branchBlock.items : []).map((branch) => ({
          ...branch,
          sequence: Array.isArray(branch && branch.sequence) ? branch.sequence.map((branchStep) => ({ ...branchStep })) : [],
        })),
      });
    });
    return blocks;
  }

  function canonicalRouteTopology(payload, topologyBindings) {
    const routeUsageById = new Map(
      (Array.isArray(payload && payload.route_hardware_usage) ? payload.route_hardware_usage : [])
        .filter((entry) => entry && typeof entry === 'object')
        .map((entry) => [normalizeIdentifier(entry.route_id), { ...entry }])
    );

    const routes = (Array.isArray(payload && payload.light_paths) ? payload.light_paths : [])
      .filter((route) => route && typeof route === 'object')
      .map((route, routeIndex) => {
        const routeId = normalizeIdentifier(route.id || route.route || route.name) || `route_${routeIndex + 1}`;
        const graphNodes = Array.isArray(route.graph_nodes) ? route.graph_nodes.map((node) => ({ ...node })) : [];
        const graphEdges = Array.isArray(route.graph_edges) ? route.graph_edges.map((edge) => ({ ...edge })) : [];
        const routeUsage = routeUsageById.get(routeId) || null;
        const explicitSourceIds = sequenceStepIds(route.illumination_sequence, 'source_id');
        const explicitEndpointIds = sequenceStepIds(route.detection_sequence, 'endpoint_id');
        const explicitElementIds = [
          ...sequenceStepIds(route.illumination_sequence, 'optical_path_element_id'),
          ...sequenceStepIds(route.detection_sequence, 'optical_path_element_id'),
        ].filter((value, index, items) => items.indexOf(value) === index);
        return {
          id: routeId,
          label: cleanString(route.name) || routeLabel(routeId),
          order: routeIndex,
          record: { ...route },
          topology: {
            graph_nodes: graphNodes.map((node) => ({ ...node })),
            graph_edges: graphEdges.map((edge) => ({ ...edge })),
          },
          graphNodes,
          graphEdges,
          routeHardwareUsage: routeUsage ? { ...routeUsage } : null,
          routeLocalHardwareUsage: routeUsage
            ? {
                hardware_inventory_ids: Array.isArray(routeUsage.hardware_inventory_ids) ? routeUsage.hardware_inventory_ids.slice() : [],
                endpoint_inventory_ids: Array.isArray(routeUsage.endpoint_inventory_ids) ? routeUsage.endpoint_inventory_ids.slice() : [],
              }
            : { hardware_inventory_ids: [], endpoint_inventory_ids: [] },
          branchBlocks: (
            Array.isArray(route.branch_blocks) && route.branch_blocks.length
              ? route.branch_blocks
              : [
                  ...sequenceBranchBlocks(route.illumination_sequence),
                  ...sequenceBranchBlocks(route.detection_sequence),
                ]
          ).map((block) => ({ ...block })),
          explicitSourceIds,
          explicitEndpointIds,
          explicitElementIds,
          illuminationTraversal: Array.isArray(route.illumination_traversal) ? route.illumination_traversal.map((step) => ({ ...step })) : [],
          detectionTraversal: Array.isArray(route.detection_traversal) ? route.detection_traversal.map((step) => ({ ...step })) : [],
        };
      });

    return {
      routeCatalog: Array.isArray(topologyBindings && topologyBindings.routeCatalog)
        ? topologyBindings.routeCatalog.map((entry) => ({ ...entry }))
        : routes.map((route) => ({ id: route.id, label: route.label, order: route.order })),
      routes,
      routeUsageById: Object.fromEntries(
        routes.map((route) => [route.id, route.routeHardwareUsage ? { ...route.routeHardwareUsage } : null])
      ),
      graphNodesByRoute: Object.fromEntries(routes.map((route) => [route.id, route.graphNodes.map((node) => ({ ...node }))])),
      graphEdgesByRoute: Object.fromEntries(routes.map((route) => [route.id, route.graphEdges.map((edge) => ({ ...edge }))])),
    };
  }

  function canonicalStagePayload(payload, topologyBindings, options) {
    const out = { cube: [], excitation: [], dichroic: [], emission: [], analyzer: [] };
    canonicalElements(payload && payload.optical_path_elements).forEach((element) => {
      const stageRole = cleanString(element && element.stage_role).toLowerCase();
      if (!['cube', 'excitation', 'dichroic', 'emission', 'analyzer'].includes(stageRole)) return;
      const mechanism = { ...element, type: element.element_type || element.type || 'mechanism' };
      const routes = canonicalElementRoutes(element, topologyBindings, options);
      const binding = topologyBindings && topologyBindings.elementBindings
        ? topologyBindings.elementBindings.get(normalizeIdentifier(element && element.id))
        : null;
      if (routes.length) {
        mechanism.routes = routes;
        mechanism.path = routes[0];
      }
      mechanism.__sequence_use = {
        illumination: Array.isArray(binding && binding.illumination) ? binding.illumination.map((entry) => ({ ...entry })) : [],
        detection: Array.isArray(binding && binding.detection) ? binding.detection.map((entry) => ({ ...entry })) : [],
      };
      out[stageRole].push(mechanism);
    });
    Object.keys(out).forEach((stageRole) => {
      out[stageRole].sort((left, right) => {
        const leftUse = left && left.__sequence_use;
        const rightUse = right && right.__sequence_use;
        const leftIllum = Array.isArray(leftUse && leftUse.illumination) && leftUse.illumination.length
          ? Math.min(...leftUse.illumination.map((entry) => entry.index))
          : null;
        const rightIllum = Array.isArray(rightUse && rightUse.illumination) && rightUse.illumination.length
          ? Math.min(...rightUse.illumination.map((entry) => entry.index))
          : null;
        const leftDetect = Array.isArray(leftUse && leftUse.detection) && leftUse.detection.length
          ? Math.min(...leftUse.detection.map((entry) => entry.index))
          : null;
        const rightDetect = Array.isArray(rightUse && rightUse.detection) && rightUse.detection.length
          ? Math.min(...rightUse.detection.map((entry) => entry.index))
          : null;
        const illumOrder = sortByRouteOccurrence(leftIllum, rightIllum);
        if (illumOrder !== 0) return illumOrder;
        const detectOrder = sortByRouteOccurrence(leftDetect, rightDetect);
        if (detectOrder !== 0) return detectOrder;
        return cleanString(left && (left.display_label || left.name || left.id)).localeCompare(cleanString(right && (right.display_label || right.name || right.id)));
      });
    });
    return out;
  }

  function canonicalSourceMechanisms(payload, topologyBindings, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    return canonicalElements(payload && payload.sources).map((source, index) => {
      const routes = orderedRoutesFromSet(
        topologyBindings && topologyBindings.sourceRoutes
          ? topologyBindings.sourceRoutes.get(normalizeIdentifier(source && source.id))
          : null,
        allowApproximation ? (source && (source.modalities || source.routes || source.path || source.route)) : []
      );
      const value = {
        ...(source || {}),
        slot: 1,
        __routes: routes,
      };
      return {
        id: cleanString(source && source.id) || `source_${index + 1}`,
        name: cleanString(source && (source.name || source.display_label)) || `Source ${index + 1}`,
        display_label: cleanString(source && (source.display_label || source.name)) || `Source ${index + 1}`,
        __routes: routes,
        positions: { 1: value },
        options: [{ slot: 1, display_label: value.display_label || value.name || `Source ${index + 1}`, value }],
      };
    });
  }

  function canonicalEndpointPayload(payload, topologyBindings, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    return canonicalElements(payload && payload.endpoints).map((endpoint) => {
      const routes = orderedRoutesFromSet(
        topologyBindings && topologyBindings.endpointRoutes
          ? topologyBindings.endpointRoutes.get(normalizeIdentifier(endpoint && endpoint.id))
          : null,
        allowApproximation ? (endpoint && (endpoint.modalities || endpoint.routes || endpoint.path || endpoint.route)) : []
      );
      return { ...(endpoint || {}), __routes: routes };
    });
  }

  function canonicalSplitterPayload(payload, topologyBindings, options) {
    return canonicalElements(payload && payload.optical_path_elements)
      .filter((element) => cleanString(element && element.stage_role).toLowerCase() === 'splitter')
      .map((element, index) => {
        const routes = canonicalElementRoutes(element, topologyBindings, options);
        const routeBranchBinding = topologyBindings && topologyBindings.splitterBranches
          ? topologyBindings.splitterBranches.get(normalizeIdentifier(element && element.id))
          : null;
        const branchSource = Array.isArray(routeBranchBinding && routeBranchBinding.branches) && routeBranchBinding.branches.length
          ? routeBranchBinding.branches
          : (Array.isArray(element && element.branches) ? element.branches : []);
        const branches = branchSource.map((branch, branchIndex) => {
          const component = branch && branch.component && typeof branch.component === 'object' ? { ...branch.component } : {};
          const payloadBranch = {
            id: cleanString(branch && branch.id) || `${cleanString(element && element.id) || 'splitter'}_branch_${branchIndex + 1}`,
            label: cleanString(branch && (branch.label || branch.name)) || `Branch ${branchIndex + 1}`,
            mode: cleanString(branch && branch.mode).toLowerCase() || (branchIndex === 0 ? 'transmitted' : 'reflected'),
            component,
            target_ids: normalizeTargetIds(branch && (branch.target_ids || branch.targets || branch.endpoint_id || branch.endpoint_ids || [])),
            sequence: Array.isArray(branch && branch.sequence) ? branch.sequence.map((item) => ({ ...item })) : [],
            __routes: normalizeRouteTags(branch && (branch.__routes || branch.routes || branch.path || branch.route)),
          };
          const branchRoutes = payloadBranch.__routes.length ? payloadBranch.__routes : routes;
          if (branchRoutes.length) {
            payloadBranch.routes = branchRoutes;
            payloadBranch.path = branchRoutes[0];
          }
          return payloadBranch;
        });
        const row = {
          id: cleanString(element && element.id) || `splitter_${index + 1}`,
          name: cleanString(element && (element.name || element.display_label)) || `Splitter ${index + 1}`,
          display_label: cleanString(element && (element.display_label || element.name)) || `Splitter ${index + 1}`,
          branches,
          selection_mode: cleanString(routeBranchBinding && routeBranchBinding.selection_mode).toLowerCase() || cleanString(element && element.selection_mode).toLowerCase() || (branches.length <= 1 ? 'fixed' : 'multiple'),
          branch_selection_required: (cleanString(routeBranchBinding && routeBranchBinding.selection_mode).toLowerCase() || cleanString(element && element.selection_mode).toLowerCase()) === 'exclusive' && branches.length > 1,
        };
        if (routes.length) {
          row.routes = routes;
          row.path = routes[0];
        }
        return row;
      });
  }

  function collectLegacyRouteCatalog(payload, runtimeProjection, allowApproximation) {
    const explicitRoutes = normalizeRouteCatalog(
      payload.available_routes
      || payload.route_options
      || (payload.simulation && payload.simulation.route_catalog)
      || runtimeProjection.available_routes
      || []
    );
    if (explicitRoutes.length) return explicitRoutes;
    if (!allowApproximation) return [];

    const normalizedPayload = {
      lightSources: normalizeMechanismList(runtimeProjection.light_sources || payload.light_sources),
      cube: normalizeMechanismList(((runtimeProjection.stages || payload.stages || {}).cube)),
      excitation: normalizeMechanismList(((runtimeProjection.stages || payload.stages || {}).excitation)),
      dichroic: normalizeMechanismList(((runtimeProjection.stages || payload.stages || {}).dichroic)),
      emission: normalizeMechanismList(((runtimeProjection.stages || payload.stages || {}).emission)),
      splitters: normalizeSplitters(runtimeProjection.runtime_splitters || runtimeProjection.splitters || payload.runtime_splitters || payload.splitters, { allowApproximation: true }),
      detectors: normalizeMechanismList(runtimeProjection.detectors || payload.detectors),
      terminals: normalizeTerminals(runtimeProjection.terminals || payload.terminals || payload.detection_endpoints || []),
    };
    return collectRouteCatalogFallback(normalizedPayload);
  }

  function adaptLegacyPayloadToCanonicalDto(rawPayload, options) {
    const payload = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
    const projections = payload.projections && typeof payload.projections === 'object' ? payload.projections : {};
    const runtimeProjection = projections.virtual_microscope && typeof projections.virtual_microscope === 'object'
      ? projections.virtual_microscope
      : {};
    const allowApproximation = Boolean(options && options.allowApproximation);

    const sources = [];
    normalizeMechanismList(runtimeProjection.light_sources || payload.light_sources).forEach((mechanism, mechanismIndex) => {
      positionValuesForRoute(mechanism, null).forEach((source, sourceIndex) => {
        sources.push({
          ...(source || {}),
          id: cleanString(source && source.id) || `${cleanString(mechanism && mechanism.id) || `legacy_source_${mechanismIndex + 1}`}_${sourceIndex + 1}`,
        });
      });
    });

    const opticalPathElements = [];
    ['cube', 'excitation', 'dichroic', 'emission'].forEach((stageRole) => {
      normalizeMechanismList(((runtimeProjection.stages || payload.stages || {})[stageRole])).forEach((mechanism, mechanismIndex) => {
        opticalPathElements.push({
          ...(mechanism || {}),
          id: cleanString(mechanism && mechanism.id) || `${stageRole}_${mechanismIndex + 1}`,
          stage_role: stageRole,
          element_type: cleanString(mechanism && (mechanism.element_type || mechanism.type)) || 'mechanism',
        });
      });
    });
    normalizeSplitters(runtimeProjection.runtime_splitters || runtimeProjection.splitters || payload.runtime_splitters || payload.splitters, { allowApproximation }).forEach((splitter, splitterIndex) => {
      opticalPathElements.push({
        ...(splitter || {}),
        id: cleanString(splitter && splitter.id) || `splitter_${splitterIndex + 1}`,
        stage_role: 'splitter',
        element_type: cleanString(splitter && splitter.element_type) || 'splitter',
      });
    });

    const endpoints = normalizeTerminals(runtimeProjection.terminals || payload.terminals || payload.detection_endpoints || []).map((endpoint, index) => ({
      ...(endpoint || {}),
      id: cleanString(endpoint && endpoint.id) || `endpoint_${index + 1}`,
    }));
    normalizeMechanismList(runtimeProjection.detectors || payload.detectors).forEach((mechanism, mechanismIndex) => {
      positionValuesForRoute(mechanism, null).forEach((detector, detectorIndex) => {
        endpoints.push({
          ...(detector || {}),
          id: cleanString(detector && detector.id) || `${cleanString(mechanism && mechanism.id) || `detector_${mechanismIndex + 1}`}_${detectorIndex + 1}`,
          endpoint_type: detector.endpoint_type || detector.kind || 'detector',
        });
      });
    });

    const routeCatalog = collectLegacyRouteCatalog(payload, runtimeProjection, allowApproximation);
    const lightPaths = routeCatalog.map((route) => ({ id: route.id, name: route.label, illumination_sequence: [], detection_sequence: [] }));
    const simulationMeta = payload.simulation && typeof payload.simulation === 'object' ? payload.simulation : {};

    return {
      metadata: payload.metadata || {},
      simulation: {
        ...simulationMeta,
        default_route: cleanString(payload.default_route || simulationMeta.default_route || runtimeProjection.default_route).toLowerCase() || null,
        route_catalog: routeCatalog,
      },
      sources,
      optical_path_elements: opticalPathElements,
      endpoints,
      light_paths: lightPaths,
      projections: {
        virtual_microscope: {
          valid_paths: Array.isArray(runtimeProjection.valid_paths || payload.valid_paths) ? (runtimeProjection.valid_paths || payload.valid_paths) : [],
        },
      },
    };
  }

  function terminalsAsDetectorMechanisms(terminals) {
    return (Array.isArray(terminals) ? terminals : []).map((terminal, index) => {
      const routes = terminal.__routes || routesFromObject(terminal);
      const slot = 1;
      const value = {
        ...terminal,
        slot,
        __routes: routes,
      };

      return {
        id: `terminal_mechanism_${cleanString(terminal.id || terminal.terminal_id || index + 1)}`,
        display_label: terminal.display_label || terminal.name || `Endpoint ${index + 1}`,
        name: terminal.name || terminal.display_label || `Endpoint ${index + 1}`,
        __routes: routes,
        positions: { [slot]: value },
        options: [{ slot, display_label: value.display_label || value.name || 'Endpoint', value }],
      };
    });
  }

  function deriveStageGroupAdapters(payload, topologyBindings, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    const normalizedTerminals = normalizeTerminals(canonicalEndpointPayload(payload, topologyBindings, { allowApproximation }));
    const stageSource = canonicalStagePayload(payload, topologyBindings, { allowApproximation });
    const splitterSource = canonicalSplitterPayload(payload, topologyBindings, { allowApproximation });
    // These are compatibility/UI adapters only. They are reconstructed from the
    // authoritative canonical payload so older stage/group-based consumers can
    // keep working, but routeTopology + hardwareInventory remain the topology truth.
    return {
      lightSources: normalizeMechanismList(canonicalSourceMechanisms(payload, topologyBindings, { allowApproximation })),
      stages: {
        cube: normalizeMechanismList(stageSource && stageSource.cube),
        excitation: normalizeMechanismList(stageSource && stageSource.excitation),
        dichroic: normalizeMechanismList(stageSource && stageSource.dichroic),
        emission: normalizeMechanismList(stageSource && stageSource.emission),
      },
      splitters: normalizeSplitters(splitterSource, { allowApproximation }),
      terminals: normalizedTerminals,
      detectors: terminalsAsDetectorMechanisms(normalizedTerminals),
    };
  }

  function normalizeInstrumentPayload(rawPayload, options) {
    const inputPayload = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
    const approximationMode = simulatorApproximationModeEnabled(inputPayload.metadata || {}, options);
    const payload = hasCanonicalDtoContract(inputPayload)
      ? inputPayload
      : adaptLegacyPayloadToCanonicalDto(inputPayload, { allowApproximation: approximationMode });
    const projections = payload.projections && typeof payload.projections === 'object' ? payload.projections : {};
    const runtimeProjection = projections.virtual_microscope && typeof projections.virtual_microscope === 'object'
      ? projections.virtual_microscope
      : {};
    const simulationMeta = payload.simulation && typeof payload.simulation === 'object' ? payload.simulation : {};
    const topologyBindings = canonicalTopologyBindings(payload);
    const routeTopology = canonicalRouteTopology(payload, topologyBindings);
    const derivedStageAdapters = deriveStageGroupAdapters(payload, topologyBindings, { allowApproximation: approximationMode });
    const normalized = {
      metadata: payload.metadata || {},
      lightPaths: Array.isArray(payload.light_paths) ? payload.light_paths : [],
      // Authoritative downstream DTO surfaces.
      routeTopology,
      hardwareInventory: Array.isArray(payload.hardware_inventory) ? payload.hardware_inventory : [],
      hardwareIndexMap: payload.hardware_index_map && typeof payload.hardware_index_map === 'object'
        ? payload.hardware_index_map
        : {},
      routeHardwareUsage: Array.isArray(payload.route_hardware_usage) ? payload.route_hardware_usage : [],
      normalizedEndpoints: Array.isArray(payload.normalized_endpoints || payload.endpoints) ? (payload.normalized_endpoints || payload.endpoints) : [],
      opticalPathElements: canonicalElements(payload.optical_path_elements),
      authoritativeTopologyContract: {
        routes: 'routeTopology.routes',
        hardwareInventory: 'hardwareInventory',
        hardwareIndexMap: 'hardwareIndexMap',
        routeHardwareUsage: 'routeHardwareUsage',
        normalizedEndpoints: 'normalizedEndpoints',
        graphFields: ['graphNodes', 'graphEdges'],
      },
      // Derived compatibility adapters reconstructed from the authoritative payload.
      stageAdapters: derivedStageAdapters,
      derivedStageAdapters,
      lightSources: derivedStageAdapters.lightSources,
      cube: derivedStageAdapters.stages.cube,
      excitation: derivedStageAdapters.stages.excitation,
      dichroic: derivedStageAdapters.stages.dichroic,
      emission: derivedStageAdapters.stages.emission,
      splitters: derivedStageAdapters.splitters,
      detectors: derivedStageAdapters.detectors,
      terminals: derivedStageAdapters.terminals,
      validPaths: Array.isArray(runtimeProjection.valid_paths || payload.valid_paths) ? (runtimeProjection.valid_paths || payload.valid_paths) : [],
      routeOptions: [],
      defaultRoute: cleanString(simulationMeta.default_route || payload.default_route || (topologyBindings.routeCatalog[0] && topologyBindings.routeCatalog[0].id)).toLowerCase() || null,
      strictHardwareTruth: !approximationMode,
      simulationMode: approximationMode ? 'approximate' : 'strict',
    };
    const explicitRouteOptions = normalizeRouteCatalog(
      simulationMeta.route_catalog
      || (Array.isArray(payload.light_paths) ? payload.light_paths.map((route) => ({ id: route.id, label: route.name })) : [])
    );
    normalized.routeOptions = explicitRouteOptions.length
      ? explicitRouteOptions
      : (approximationMode ? collectRouteCatalogFallback(normalized) : []);
    if (!normalized.defaultRoute || !normalized.routeOptions.some((entry) => entry.id === normalized.defaultRoute)) {
      if (!approximationMode) {
        normalized.defaultRoute = null;
      } else {
      normalized.defaultRoute = normalized.routeOptions[0] ? normalized.routeOptions[0].id : null;
      }
    }
    return normalized;
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

  function gaussianPointSeries(center, sigmaNm, minNm, maxNm, stepNm) {
    if (center === null || center === undefined) return [];
    const sigma = Math.max(8, numberOrNull(sigmaNm) ?? 35);
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
    const raw = [
      spectrum && spectrum.spectrum_type,
      spectrum && spectrum.type,
      spectrum && spectrum.subtype,
      spectrum && spectrum.category,
      spectrum && spectrum.name,
      spectrum && spectrum.label,
      spectrum && spectrum.kind,
    ].map((value) => cleanString(value)).filter(Boolean).join(' ').toLowerCase();
    const token = raw.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
    if (!token) return '';
    if (/\b(2p|two photon|two photons|two-photon|2 photon|twophoton|multiphoton)\b/.test(token)) return 'ex2p';
    if (/\b(em|emission|fluorescence|fluo)\b/.test(token)) return 'em';
    if (/\b(ex|excitation|absorption|absorbance|1p|one photon|one-photon)\b/.test(token)) return 'ex1p';
    return token;
  }

  function matchSpectrumType(token, aliases) {
    const normalizedToken = cleanString(token).toLowerCase();
    return aliases.some((alias) => {
      const normalizedAlias = cleanString(alias).toLowerCase();
      return normalizedToken === normalizedAlias || normalizedToken.includes(normalizedAlias);
    });
  }

  function pointsFromSpectrumRow(row) {
    if (Array.isArray(row)) return normalizePoints(row);
    return normalizePoints(
      row && (row.data || row.points || row.values || row.spectrum || row.curve || row.trace || row.measurements)
    );
  }

  function collectSpectraContainers(detail) {
    const containers = [];
    const visited = new Set();
    const queue = [detail];
    while (queue.length) {
      const current = queue.shift();
      if (!current || typeof current !== 'object' || visited.has(current)) continue;
      visited.add(current);
      [current.spectra, current.spectrum, current.spectral_data, current.data, current.rows].forEach((value) => {
        if (Array.isArray(value) && value.length) containers.push(value);
      });
      if (Array.isArray(current.states)) queue.push(...current.states);
      if (current.default_state && typeof current.default_state === 'object') queue.push(current.default_state);
      if (current.state && typeof current.state === 'object') queue.push(current.state);
      if (current.protein && typeof current.protein === 'object') queue.push(current.protein);
      if (current.fp && typeof current.fp === 'object') queue.push(current.fp);
      if (current.fluorophore && typeof current.fluorophore === 'object') queue.push(current.fluorophore);
      if (Array.isArray(current.results)) queue.push(...current.results);
      if (Array.isArray(current.proteins)) queue.push(...current.proteins);
    }
    return containers;
  }

  function collectTopLevelSpectra(detail) {
    return collectSpectraContainers(detail).flatMap((collection) => collection);
  }

  function extractSpectra(detail, aliases) {
    for (const collection of collectSpectraContainers(detail)) {
      for (const spectrum of collection) {
        const token = normalizeTypeToken(spectrum);
        if (!matchSpectrumType(token, aliases)) continue;
        const points = pointsFromSpectrumRow(spectrum);
        if (points.length) return points;
      }
    }
    return [];
  }

  function spectrumFromAliases(spectra, aliases) {
    return extractSpectra({ spectra: Array.isArray(spectra) ? spectra : [] }, aliases);
  }

  function summarizeSpectrumSources(spectrumSources) {
    const preferredOrder = ['api', 'detail', 'bundled_cache', 'synthetic'];
    const seen = [];
    preferredOrder.forEach((source) => {
      if (Object.values(spectrumSources || {}).includes(source) && !seen.includes(source)) {
        seen.push(source);
      }
    });
    Object.values(spectrumSources || {}).forEach((source) => {
      const cleaned = cleanString(source).toLowerCase();
      if (cleaned && !seen.includes(cleaned)) seen.push(cleaned);
    });
    return seen.join('+') || 'none';
  }

  function normalizedStateName(state, index) {
    const rawName = cleanString(state && (state.name || state.label));
    if (/^default$/i.test(rawName)) return 'Default state';
    return rawName || (index === 0 ? 'Default state' : `State ${index + 1}`);
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
      const points = pointsFromSpectrumRow(row);
      if (!points.length && Array.isArray(row.spectra)) {
        row.spectra.forEach(enqueue);
        return;
      }
      if (!points.length) return;
      const token = normalizeTypeToken(row);
      const type = matchSpectrumType(token, ['ex2p', '2p', 'two photon'])
        ? 'ex2p'
        : matchSpectrumType(token, ['em', 'emission', 'fluorescence'])
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
    const spectraOrigin = cleanString(fallbackSummary && fallbackSummary.sourceOrigin).toLowerCase() || 'detail';
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
    const ex1p = spectrumFromAliases(spectra, ['excitation', 'absorption', '1p', ' ex']);
    const ex2p = spectrumFromAliases(spectra, ['2p', 'two-photon', 'two photon']);
    const em = spectrumFromAliases(spectra, ['emission', ' em']);
    const spectrumSources = {
      ex1p: ex1p.length ? spectraOrigin : null,
      ex2p: ex2p.length ? spectraOrigin : null,
      em: em.length ? spectraOrigin : null,
    };
    return {
      key: cleanString(state && (state.uuid || state.slug || state.id || state.name)) || `state_${index + 1}`,
      slug: cleanString(state && state.slug),
      name: normalizedStateName(state, index),
      isDefault: Boolean(state && (state.is_default || state.default || index === 0)),
      ex1p,
      ex2p,
      em,
      exMax: maxima.exMax,
      emMax: maxima.emMax,
      ec,
      qy,
      brightness,
      spectrumSources,
      spectraSource: summarizeSpectrumSources(spectrumSources),
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
        spectrumSources: { ex1p: null, ex2p: null, em: null },
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

  function injectExternalSpectra(states, spectraSeed, sourceOrigin) {
    const rows = normalizeFPbaseSpectraResponse(spectraSeed);
    const spectraOrigin = cleanString(sourceOrigin || (spectraSeed && spectraSeed.sourceOrigin)).toLowerCase() || 'api';
    rows.forEach((row) => {
      const target = matchStateRecord(states, row);
      if (!target) return;
      if (row.type === 'ex2p' && row.points.length) {
        target.ex2p = row.points;
        target.spectrumSources.ex2p = spectraOrigin;
      }
      if (row.type === 'ex1p' && row.points.length) {
        target.ex1p = row.points;
        target.spectrumSources.ex1p = spectraOrigin;
      }
      if (row.type === 'em' && row.points.length) {
        target.em = row.points;
        target.spectrumSources.em = spectraOrigin;
      }
      target.spectraSource = summarizeSpectrumSources(target.spectrumSources);
    });
  }

  function ensureUsableStateSpectra(states) {
    (Array.isArray(states) ? states : []).forEach((state) => {
      if (!Array.isArray(state.ex1p) || !state.ex1p.length) {
        state.ex1p = synthesizeSpectrumFromMaxima('ex1p', state.exMax);
        if (state.ex1p.length) state.spectrumSources.ex1p = 'synthetic';
      }
      if (!Array.isArray(state.em) || !state.em.length) {
        state.em = synthesizeSpectrumFromMaxima('em', state.emMax);
        if (state.em.length) state.spectrumSources.em = 'synthetic';
      }
      state.spectraSource = summarizeSpectrumSources(state.spectrumSources);
    });
  }

  function normalizeFluorophoreDetail(detail, summarySeed, spectraSeed) {
    const summary = summarySeed && typeof summarySeed === 'object'
      ? summarySeed
      : (normalizeFPbaseSearchResults([detail])[0] || {});
    const states = ensureStateList(detail || {}, summary);
    if (spectraSeed) injectExternalSpectra(states, spectraSeed, summary && summary.sourceOrigin);
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
        detail: detail || {},
        detailId: cleanString(detail && (detail.id || detail.slug || detail.uuid || detail.name)),
      },
    };
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

  let bundledFallbackSearchCache = null;

  function bundledFallbackFluorophores() {
    if (bundledFallbackSearchCache) return bundledFallbackSearchCache.slice();
    bundledFallbackSearchCache = BUNDLED_FALLBACK_FLUOROPHORE_BUNDLES.map((bundle, index) => {
      const summarySeed = bundle && bundle.summary && typeof bundle.summary === 'object'
        ? { ...bundle.summary, sourceOrigin: 'bundled_cache' }
        : { key: `bundled_${index + 1}`, name: `Bundled ${index + 1}`, sourceOrigin: 'bundled_cache' };
      const detail = bundle && bundle.detail && typeof bundle.detail === 'object' ? bundle.detail : summarySeed;
      const spectra = bundle && bundle.spectra && typeof bundle.spectra === 'object'
        ? { ...bundle.spectra, sourceOrigin: 'bundled_cache' }
        : null;
      const fluor = normalizeFluorophoreDetail(detail, summarySeed, spectra);
      return { ...fluor, spectraSource: fluor.spectraSource || 'bundled_cache' };
    });
    return bundledFallbackSearchCache.slice();
  }

  function searchFallbackFluorophores(query) {
    const normalized = cleanString(query).toLowerCase();
    const library = bundledFallbackFluorophores();
    if (!normalized) return library;
    return library.filter((fluor) => {
      const haystack = [fluor.name, fluor.slug, fluor.uuid, fluor.key, fluor.canonicalKey, fluor.activeStateName]
        .map((value) => cleanString(value).toLowerCase())
        .filter(Boolean);
      return haystack.some((value) => value.includes(normalized));
    });
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
    const normalized = normalizePoints(points);
    if (!normalized.length) return 0;

    if (wavelength < normalized[0].x || wavelength > normalized[normalized.length - 1].x) {
      return 0;
    }
    if (wavelength === normalized[0].x) return normalized[0].y;
    if (wavelength === normalized[normalized.length - 1].x) return normalized[normalized.length - 1].y;

    for (let index = 0; index < normalized.length - 1; index += 1) {
      const left = normalized[index];
      const right = normalized[index + 1];
      if (wavelength < left.x || wavelength > right.x) continue;
      const range = right.x - left.x;
      if (range <= 0) return left.y;
      const ratio = (wavelength - left.x) / range;
      return left.y + ((right.y - left.y) * ratio);
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

  function arrayMax(values) {
    return Array.isArray(values) && values.length ? Math.max(...values) : 0;
  }

  function smoothStep(value, edge, width) {
    const safeWidth = Math.max(1, width || 1);
    if (value <= edge - safeWidth) return 0;
    if (value >= edge + safeWidth) return 1;
    return clamp((value - (edge - safeWidth)) / (2 * safeWidth), 0, 1);
  }


  function wavelengthToRGB(wavelength) {
    const wl = numberOrNull(wavelength);
    if (wl === null) return [0, 0, 0];
    if (wl < 380) return [90, 0, 150];
    if (wl > 780) return [120, 0, 0];
    let red = 0;
    let green = 0;
    let blue = 0;
    if (wl >= 380 && wl < 440) {
      red = -(wl - 440) / 60;
      blue = 1;
    } else if (wl < 490) {
      green = (wl - 440) / 50;
      blue = 1;
    } else if (wl < 510) {
      green = 1;
      blue = -(wl - 510) / 20;
    } else if (wl < 580) {
      red = (wl - 510) / 70;
      green = 1;
    } else if (wl < 645) {
      red = 1;
      green = -(wl - 645) / 65;
    } else {
      red = 1;
    }
    let factor = 1;
    if (wl < 420) factor = 0.3 + ((0.7 * (wl - 380)) / 40);
    else if (wl > 700) factor = 0.3 + ((0.7 * (780 - wl)) / 80);
    const gamma = 0.8;
    const channel = (value) => Math.round(255 * Math.pow(clamp(value * factor, 0, 1), gamma));
    return [channel(red), channel(green), channel(blue)];
  }

  function spectrumToCSSColor(spectrumArray, grid) {
    if (!Array.isArray(spectrumArray) || !Array.isArray(grid) || !spectrumArray.length || !grid.length) {
      return 'rgba(0,0,0,0)';
    }
    const count = Math.min(spectrumArray.length, grid.length);
    let total = 0;
    let peak = 0;
    let red = 0;
    let green = 0;
    let blue = 0;
    let visibleBins = 0;
    let visibleActive = 0;
    for (let index = 0; index < count; index += 1) {
      const intensity = Math.max(0, Number(spectrumArray[index] || 0));
      if (intensity <= 0) continue;
      const wavelength = grid[index];
      const [r, g, b] = wavelengthToRGB(wavelength);
      red += r * intensity;
      green += g * intensity;
      blue += b * intensity;
      total += intensity;
      peak = Math.max(peak, intensity);
      if (wavelength >= 390 && wavelength <= 700) visibleBins += 1;
    }
    if (total <= 1e-9) return 'rgba(0,0,0,0)';
    const threshold = peak * 0.18;
    for (let index = 0; index < count; index += 1) {
      const wavelength = grid[index];
      if (wavelength < 390 || wavelength > 700) continue;
      const intensity = Math.max(0, Number(spectrumArray[index] || 0));
      if (intensity >= threshold) visibleActive += 1;
    }
    const coverage = visibleBins ? (visibleActive / visibleBins) : 0;
    let outRed = red / total;
    let outGreen = green / total;
    let outBlue = blue / total;
    if (coverage >= 0.35) {
      const whiten = clamp((coverage - 0.35) / 0.45, 0, 1) * 0.88;
      outRed = ((1 - whiten) * outRed) + (whiten * 248);
      outGreen = ((1 - whiten) * outGreen) + (whiten * 248);
      outBlue = ((1 - whiten) * outBlue) + (whiten * 248);
    }
    return `rgb(${Math.round(outRed)}, ${Math.round(outGreen)}, ${Math.round(outBlue)})`;
  }

  function bandMask(grid, start, end, edgeWidth) {
    const low = Math.min(start, end);
    const high = Math.max(start, end);
    const shoulder = Math.max(0.5, numberOrNull(edgeWidth) ?? 2);
    return grid.map((wavelength) => {
      if (wavelength < low || wavelength > high) return 0;
      if (wavelength <= low + shoulder) return clamp((wavelength - low) / shoulder, 0, 1);
      if (wavelength >= high - shoulder) return clamp((high - wavelength) / shoulder, 0, 1);
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

  function sortedCutoffs(cutoffs) {
    return (Array.isArray(cutoffs) ? cutoffs : [])
      .map((cutoff) => numberOrNull(cutoff))
      .filter((cutoff) => cutoff !== null)
      .sort((left, right) => left - right);
  }

  function normalizedBandMasks(grid, bands) {
    const rows = Array.isArray(bands) ? bands : [];
    return rows
      .map((band) => {
        const center = numberOrNull(band && band.center_nm);
        const width = numberOrNull(band && band.width_nm);
        if (center === null || width === null || width <= 0) return null;
        return bandMask(grid, center - (width / 2), center + (width / 2), 2);
      })
      .filter(Boolean);
  }

  function legacyAlternatingCutoffTransmitMask(grid, cutoffs) {
    const ordered = sortedCutoffs(cutoffs);
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

  function simpleDichroicTransmitMask(grid, component) {
    const cutOn = numberOrNull(component && component.cut_on_nm);
    if (cutOn !== null) return grid.map((wavelength) => smoothStep(wavelength, cutOn, 2));

    const ordered = sortedCutoffs(component && component.cutoffs_nm);
    if (ordered.length === 1) {
      return grid.map((wavelength) => smoothStep(wavelength, ordered[0], 2));
    }
    return null;
  }

  function dichroicTransmitMask(grid, component) {
    const transmissionMasks = normalizedBandMasks(grid, component && component.transmission_bands);
    if (transmissionMasks.length) return sumMasks(transmissionMasks, grid);

    const reflectionMasks = normalizedBandMasks(grid, component && component.reflection_bands);
    if (reflectionMasks.length) {
      const reflected = sumMasks(reflectionMasks, grid);
      return reflected.map((value) => 1 - clamp(value, 0, 1));
    }

    // Generic bands array (used by multiband_dichroic YAML definitions that
    // store transmission windows in the common "bands" field).
    const genericBandMasks = normalizedBandMasks(grid, component && component.bands);
    if (genericBandMasks.length) return sumMasks(genericBandMasks, grid);

    const simpleMask = simpleDichroicTransmitMask(grid, component || {});
    if (simpleMask) return simpleMask;

    // Legacy/approximate fallback for cutoff-only multiband dichroics.
    return legacyAlternatingCutoffTransmitMask(grid, component && component.cutoffs_nm);
  }

  function componentMask(component, grid, context) {
    const type = cleanString(component && (component.component_type || component.type)).toLowerCase();
    if (!type || type === 'mirror' || type === 'empty' || type === 'passthrough' || type === 'neutral_density' || type === 'analyzer') {
      return grid.map(() => 1);
    }
    if (type === 'block' || type === 'blocker') {
      return grid.map(() => 0);
    }
    if (type === 'bandpass') {
      const center = numberOrNull(component.center_nm);
      const width = numberOrNull(component.width_nm);
      if (center === null || width === null) {
        // Fallback: bands array (YAML bandpass positions that list bands explicitly).
        const fallbackBands = normalizedBandMasks(grid, component.bands);
        if (fallbackBands.length) return sumMasks(fallbackBands, grid);
        return grid.map(() => 1);
      }
      return bandMask(grid, center - (width / 2), center + (width / 2), 2);
    }
    if (type === 'multiband_bandpass') {
      return sumMasks(normalizedBandMasks(grid, component.bands), grid);
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
      const transmit = dichroicTransmitMask(grid, component || {});
      const mode = cleanString(context && context.mode).toLowerCase();
      const branchMode = cleanString((context && context.branchMode) || component.branch_mode).toLowerCase();
      const wantsReflection = branchMode === 'reflected'
        ? true
        : branchMode === 'transmitted'
          ? false
          : mode === 'excitation';
      return wantsReflection ? transmit.map((value) => 1 - value) : transmit;
    }
    // filter_cube: treat as bandpass (single band) or multiband_bandpass (multiple bands).
    if (type === 'filter_cube') {
      const bands = normalizedBandMasks(grid, component.bands);
      if (bands.length) return sumMasks(bands, grid);
      const center = numberOrNull(component.center_nm);
      const width = numberOrNull(component.width_nm);
      if (center !== null && width !== null && width > 0) return bandMask(grid, center - (width / 2), center + (width / 2), 2);
      const cutOn = numberOrNull(component.cut_on_nm);
      if (cutOn !== null) return grid.map((wavelength) => smoothStep(wavelength, cutOn, 2));
      return grid.map(() => 1);
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

  function broadbandSpectrum(grid, source) {
    const minNm = firstDefinedNumber(source && source.broadband_min_nm, source && source.min_nm, 380) ?? 380;
    const maxNm = firstDefinedNumber(source && source.broadband_max_nm, source && source.max_nm, 760) ?? 760;
    const kind = cleanString(source && source.kind).toLowerCase();
    const mode = cleanString(source && source.spectral_mode).toLowerCase();
    const envelope = bandMask(grid, minNm, maxNm, 18);
    const warmBias = kind === 'halogen_lamp' ? 0.16 : 0.08;
    const amplitude = mode === 'broadband' ? ((kind === 'white_light_laser' || kind === 'supercontinuum') ? 0.22 : 0.12) : 0.1;
    return envelope.map((value, index) => {
      const wavelength = grid[index];
      const redTilt = clamp(1 + (((wavelength - 550) / 240) * warmBias), 0.65, 1.25);
      return clamp(value * amplitude * redTilt, 0, 1);
    });
  }

  function sourceSpectrum(source, grid) {
    const centers = sourceCenters(source);
    const center = centers.length ? centers[0] : null;
    const width = numberOrNull(source && source.width_nm);
    const tunableMin = numberOrNull(source && source.tunable_min_nm);
    const tunableMax = numberOrNull(source && source.tunable_max_nm);
    const mode = cleanString(source && source.spectral_mode).toLowerCase();
    const kind = cleanString(source && source.kind).toLowerCase();

    if (mode === 'broadband' || kind === 'halogen_lamp' || kind === 'arc_lamp' || kind === 'metal_halide') {
      return broadbandSpectrum(grid, source);
    }
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
      if (mode === 'tunable_band') {
        return bandMask(grid, chosen - ((width || 30) / 2), chosen + ((width || 30) / 2), 3);
      }
      return gaussianSpectrum(grid, chosen, width || 2);
    }
    if (center !== null) {
      return width && width > 2
        ? bandMask(grid, center - (width / 2), center + (width / 2), 3)
        : gaussianSpectrum(grid, center, 2);
    }
    if (kind === 'white_light_laser' || kind === 'supercontinuum') {
      return broadbandSpectrum(grid, source);
    }
    return grid.map((wavelength) => (wavelength >= 350 && wavelength <= 800 ? 0.08 : 0));
  }

  function sourceWeight(source) {
    const explicit = numberOrNull(source && source.user_weight);
    if (explicit !== null) return Math.max(0, explicit);

    const intrinsic = numberOrNull(source && source.power_weight);
    if (intrinsic !== null) return Math.max(0, intrinsic);

    return 1;
  }

  function fluorophoreBrightnessFactor(fluorophore) {
    const referenceBrightness = 55000 * 0.6;
    const explicitEc = numberOrNull(fluorophore && fluorophore.ec);
    const explicitQy = numberOrNull(fluorophore && fluorophore.qy);
    const explicitBrightness = numberOrNull(fluorophore && fluorophore.brightness);
    if (explicitEc !== null || explicitQy !== null) {
      const ec = explicitEc !== null ? explicitEc : 50000;
      const qy = explicitQy !== null ? explicitQy : 0.5;
      return clamp((ec * qy) / referenceBrightness, 0.05, 4);
    }
    if (explicitBrightness !== null) {
      return clamp(explicitBrightness / referenceBrightness, 0.05, 4);
    }
    return 1;
  }

  function sourceExcitationContribution(sourceSpectrumAtSample, excitationCurve, grid) {
    const overlapPower = integrateSpectrum(multiplyArrays(sourceSpectrumAtSample, excitationCurve), grid);
    const BASELINE_LASER_AREA = 2.12;
    const strength = overlapPower / BASELINE_LASER_AREA;
    return clamp(strength, 0, 1.5);
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
    const className = detectorClass(kind || (detector && detector.endpoint_type));
    let center = 550;
    let width = 260;
    let floor = 0.1;
    let peak = normalizePercent(detector && detector.qe_peak_pct, null);

    if (className === 'eyepiece') {
      const bounds = detectorCollectionBounds(detector);
      const eyeMin = bounds.min !== null ? bounds.min : 390;
      const eyeMax = bounds.max !== null ? bounds.max : 700;
      const visibleMask = bandMask(grid, eyeMin, eyeMax, 12);
      return visibleMask.map((value) => clamp((0.15 + (0.85 * value)) * 0.95, 0, 1));
    }
    if (className === 'camera_port') {
      return grid.map((wavelength) => (wavelength >= 350 && wavelength <= 900 ? 1 : 0));
    }
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

  function detectorCollectionBounds(detector) {
    const className = detector && detector.detector_class ? detector.detector_class : detectorClass(detector && (detector.kind || detector.endpoint_type));
    const explicitMin = firstDefinedNumber(
      detector && detector.collection_min_nm,
      detector && detector.min_nm,
    );
    const explicitMax = firstDefinedNumber(
      detector && detector.collection_max_nm,
      detector && detector.max_nm,
    );
    if (explicitMin !== null && explicitMax !== null) {
      const low = Math.min(explicitMin, explicitMax);
      const high = Math.max(explicitMin, explicitMax);
      return { min: low, max: high };
    }
    if (className === 'eyepiece') return { min: 390, max: 700 };
    if (className === 'camera' || className === 'camera_port') return { min: null, max: null };
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
    if (center === null || width === null) return { min: null, max: null };
    const halfWidth = Math.max(2, width / 2);
    return { min: center - halfWidth, max: center + halfWidth };
  }

  function detectorCollectionMask(detector, grid) {
    const className = detector && detector.detector_class ? detector.detector_class : detectorClass(detector && (detector.kind || detector.endpoint_type));
    if (className === 'camera' || className === 'camera_port') return grid.map(() => 1);
    if (detector && detector.collection_enabled === false) return grid.map(() => 1);
    const bounds = detectorCollectionBounds(detector);
    if (bounds.min === null || bounds.max === null) return grid.map(() => 1);
    if (className === 'eyepiece') {
      return bandMask(grid, bounds.min, bounds.max, 12);
    }
    return componentMask({
      component_type: 'bandpass',
      center_nm: (bounds.min + bounds.max) / 2,
      width_nm: Math.max(4, bounds.max - bounds.min),
    }, grid, { mode: 'emission' });
  }

  function leakageWarningLevel(leakageThroughput) {
    if (leakageThroughput >= 0.1) return 'high';
    if (leakageThroughput >= 0.03) return 'moderate';
    if (leakageThroughput >= 0.005) return 'low';
    return 'none';
  }

  function leakagePenalty(leakageThroughput) {
    const level = leakageWarningLevel(leakageThroughput);
    if (level === 'high') return 0.2;
    if (level === 'moderate') return 0.45;
    if (level === 'low') return 0.7;
    return 1;
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

  function branchTargetIds(branch, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    return normalizeTargetIds(branch && (allowApproximation
      ? (branch.target_ids || branch.targets || branch.terminal_ids || branch.endpoint_ids || branch.target || branch.endpoint)
      : branch.target_ids));
  }

  function selectedBranchIdsForSplitter(splitter, branchDefs, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    const selected = new Set(normalizeTargetIds(splitter && (splitter.selected_branch_ids || splitter.selectedBranchIds || splitter.active_branch_ids || splitter.activeBranchIds)));
    if (allowApproximation && !selected.size && splitter && splitter.branch_selection_required && Array.isArray(branchDefs) && branchDefs.length) {
      selected.add(normalizeIdentifier(branchDefs[0].id));
    }
    return selected;
  }

  function elementLookupById(normalizedInstrument) {
    const lookup = new Map();
    canonicalElements(normalizedInstrument && normalizedInstrument.opticalPathElements).forEach((element) => {
      const id = normalizeIdentifier(element && element.id);
      if (id) lookup.set(id, element);
    });
    return lookup;
  }

  function applyBranchSequenceSpectrum(inputSpectrum, branchDef, normalizedInstrument, grid) {
    const lookup = elementLookupById(normalizedInstrument);
    return applyComponentSeries(inputSpectrum, (Array.isArray(branchDef && branchDef.sequence) ? branchDef.sequence : []).map((step) => {
      if (!(step && typeof step === 'object')) return null;
      const elementId = normalizeIdentifier(step.optical_path_element_id);
      if (!elementId || !lookup.has(elementId)) return null;
      const element = lookup.get(elementId);
      if (element && element.component && typeof element.component === 'object') return element.component;
      if (element && element.dichroic && typeof element.dichroic === 'object') return element.dichroic;
      return element;
    }).filter(Boolean), grid, { mode: 'emission' });
  }

  function propagateSplitters(inputSpectrum, splitters, normalizedInstrument, grid, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    let branches = [{ id: 'main', label: 'Main Path', spectrum: inputSpectrum.slice(), targetIds: [] }];
    (Array.isArray(splitters) ? splitters : []).forEach((splitter, splitterIndex) => {
      const nextBranches = [];
      const splitterDichroic = splitter && splitter.dichroic && splitter.dichroic.positions
        ? splitter.dichroic.positions[1] || splitter.dichroic.positions['1']
        : (splitter && splitter.dichroic && typeof splitter.dichroic === 'object' ? splitter.dichroic : null);
      const branchDefs = Array.isArray(splitter && splitter.branches) && splitter.branches.length
        ? splitter.branches
        : (allowApproximation
          ? [{ id: `splitter_${splitterIndex}_main`, label: cleanString(splitter && splitter.label) || 'Primary Path', mode: 'transmitted', component: { component_type: 'passthrough' }, target_ids: [] }]
          : []);
      const explicitlySelectedBranchIds = selectedBranchIdsForSplitter(splitter, branchDefs, options);
      const requiresSelection = Boolean(splitter && splitter.branch_selection_required) && branchDefs.length > 1;

      branches.forEach((branch) => {
        branchDefs.forEach((branchDef, branchIndex) => {
          const normalizedBranchId = normalizeIdentifier(branchDef && branchDef.id) || `splitter_${splitterIndex}_branch_${branchIndex + 1}`;
          if ((requiresSelection || explicitlySelectedBranchIds.size) && !explicitlySelectedBranchIds.has(normalizedBranchId)) return;
          const mode = cleanString(branchDef && branchDef.mode).toLowerCase() || (branchIndex === 0 ? 'transmitted' : 'reflected');
          const baseSpectrum = splitterDichroic
            ? applyMask(branch.spectrum, componentMask(splitterDichroic, grid, { mode: 'emission', branchMode: mode }))
            : branch.spectrum.slice();
          const afterBranchComponent = applyMask(baseSpectrum, componentMask((branchDef && branchDef.component) || {}, grid, { mode: 'emission', branchMode: mode }));
          const branchSpectrum = applyBranchSequenceSpectrum(afterBranchComponent, branchDef, normalizedInstrument, grid);
          const localTargets = branchTargetIds(branchDef, options);
          const inheritedTargets = Array.isArray(branch.targetIds) ? branch.targetIds : [];
          const mergedTargets = inheritedTargets.length && localTargets.length
            ? inheritedTargets.filter((id) => localTargets.includes(id))
            : (inheritedTargets.length ? inheritedTargets.slice() : localTargets.slice());
          nextBranches.push({
            id: `${branch.id}/${cleanString(branchDef && branchDef.id) || `branch_${branchIndex + 1}`}`,
            label: `${branch.label} -> ${cleanString(branchDef && (branchDef.label || branchDef.name)) || `Branch ${branchIndex + 1}`}`,
            spectrum: branchSpectrum,
            targetIds: mergedTargets,
            splitterId: splitter && splitter.id ? splitter.id : `splitter_${splitterIndex}`,
            branchId: normalizedBranchId,
          });
        });
      });
      if (nextBranches.length) branches = nextBranches;
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

  function mechanismOptionsForRoute(mechanism, route) {
    if (!mechanism || typeof mechanism !== 'object') return [];
    const options = Array.isArray(mechanism.options) && mechanism.options.length
      ? mechanism.options
      : Object.values(mechanism.positions || {}).map((entry) => ({
          slot: entry.slot,
          display_label: entry.display_label || entry.label || `Slot ${entry.slot}`,
          value: entry,
        }));
    return options.filter((option) => routeMatches((option.value && option.value.__routes) || mechanism.__routes, route));
  }

  function expandCubeSelectionForOptimization(component) {
    const expanded = [];
    const excitation = component && (component.excitation_filter || component.excitation || component.ex);
    const dichroic = component && (component.dichroic_filter || component.dichroic || component.di);
    const emission = component && (component.emission_filter || component.emission || component.em);
    if (excitation) expanded.push({ stage: 'excitation', component: excitation });
    if (dichroic) expanded.push({ stage: 'dichroic', component: dichroic });
    if (emission) expanded.push({ stage: 'emission', component: emission });
    return expanded;
  }

  function routeMechanismsForOptimization(rows, route) {
    return (Array.isArray(rows) ? rows : []).filter((mechanism) => routeMatches(mechanism.__routes, route));
  }

  function positionValuesForRoute(mechanism, route) {
    return Object.values((mechanism && mechanism.positions) || {}).filter((entry) =>
      routeMatches((entry && entry.__routes) || (mechanism && mechanism.__routes), route)
    );
  }

  function pointMaskScore(component, wavelengths, mode) {
    if (!component || !Array.isArray(wavelengths) || !wavelengths.length) return 0;
    const min = Math.floor(Math.min(...wavelengths) - 20);
    const max = Math.ceil(Math.max(...wavelengths) + 20);
    const grid = wavelengthGrid({ min_nm: min, max_nm: max, step_nm: 2 });
    const mask = componentMask(component, grid, { mode });
    const sampleAt = (target) => {
      const idx = grid.reduce((best, wavelength, index) => Math.abs(wavelength - target) < Math.abs(grid[best] - target) ? index : best, 0);
      return mask[idx] || 0;
    };
    return wavelengths.reduce((sum, target) => sum + sampleAt(target), 0) / wavelengths.length;
  }

  function nearestSourceDistance(source, target) {
    const targetNm = numberOrNull(target);
    if (targetNm === null) return Infinity;
    const centers = sourceCenters(source);
    if (centers.length) return Math.min(...centers.map((center) => Math.abs(center - targetNm)));
    const min = numberOrNull(source && source.tunable_min_nm);
    const max = numberOrNull(source && source.tunable_max_nm);
    if (min !== null && max !== null) {
      if (targetNm >= min && targetNm <= max) return 0;
      return Math.min(Math.abs(targetNm - min), Math.abs(targetNm - max));
    }
    return Infinity;
  }

  function tunedSourceForTarget(source, target) {
    const clone = { ...(source || {}) };
    const targetNm = numberOrNull(target);
    const min = numberOrNull(source && source.tunable_min_nm);
    const max = numberOrNull(source && source.tunable_max_nm);
    if (targetNm !== null && min !== null && max !== null) {
      clone.selected_wavelength_nm = clamp(targetNm, Math.min(min, max), Math.max(min, max));
    } else if (targetNm !== null && numberOrNull(source && source.wavelength_nm) === null && sourceCenters(source).length) {
      const centers = sourceCenters(source);
      clone.selected_wavelength_nm = centers.reduce((best, center) => Math.abs(center - targetNm) < Math.abs(best - targetNm) ? center : best, centers[0]);
    }
    return clone;
  }

  function uniqueByKey(entries, keyFn) {
    const seen = new Set();
    return (Array.isArray(entries) ? entries : []).filter((entry) => {
      const key = keyFn(entry);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function sourceCandidateSetsForRoute(normalizedInstrument, fluorophores, route) {
    const candidates = [];
    const mechanisms = routeMechanismsForOptimization(normalizedInstrument.lightSources, route);
    const targets = (Array.isArray(fluorophores) ? fluorophores : []).map((fluor) => numberOrNull(fluor && fluor.exMax)).filter((value) => value !== null);
    mechanisms.forEach((mechanism) => {
      positionValuesForRoute(mechanism, route).forEach((source) => {
        const role = cleanString(source && source.role).toLowerCase();
        if (role === 'depletion' || role === 'transmitted_illumination') return;
        targets.forEach((target) => {
          const distance = nearestSourceDistance(source, target);
          if (!Number.isFinite(distance)) return;
          candidates.push({
            mechanismId: mechanism.id,
            slot: source.slot,
            score: Math.max(0, 160 - distance),
            source: tunedSourceForTarget(source, target),
          });
        });
      });
    });
    const narrowed = uniqueByKey(candidates.sort((a, b) => b.score - a.score).slice(0, 10), (entry) => `${entry.mechanismId}::${entry.slot}`);
    const sourceRefs = narrowed.slice(0, Math.min(4, Math.max(1, targets.length || 1)));
    const sets = [];
    const total = 2 ** sourceRefs.length;
    for (let mask = 1; mask < total; mask += 1) {
      const chosen = sourceRefs.filter((_, index) => mask & (1 << index));
      const coversAll = targets.every((target) => chosen.some((entry) => nearestSourceDistance(entry.source, target) <= 35));
      if (!coversAll) continue;
      sets.push(chosen);
    }
    if (!sets.length && sourceRefs.length) sets.push(sourceRefs);
    return sets.slice(0, 16);
  }

  function topMechanismOptions(mechanisms, route, scorer, limit = 3) {
    return routeMechanismsForOptimization(mechanisms, route).map((mechanism) => {
      const scored = mechanismOptionsForRoute(mechanism, route)
        .map((option) => ({ ...option, score: scorer(option.value, mechanism) }))
        .sort((a, b) => b.score - a.score)
        .slice(0, limit);
      return { mechanism, options: scored.length ? scored : mechanismOptionsForRoute(mechanism, route).slice(0, 1) };
    });
  }

  function combineMechanismSelections(groups) {
    const rows = Array.isArray(groups) ? groups : [];
    if (!rows.length) return [[]];
    const [head, ...tail] = rows;
    const tailCombos = combineMechanismSelections(tail);
    const out = [];
    (head.options || []).forEach((option) => {
      tailCombos.forEach((combo) => {
        out.push([{ mechanism: head.mechanism, option }, ...combo]);
      });
    });
    return out;
  }

  function detectorCandidatesForRoute(normalizedInstrument, fluorophores, route) {
    const emTargets = (Array.isArray(fluorophores) ? fluorophores : []).map((fluor) => numberOrNull(fluor && fluor.emMax)).filter((value) => value !== null);
    const scored = [];
    routeMechanismsForOptimization(normalizedInstrument.detectors, route).forEach((mechanism) => {
      positionValuesForRoute(mechanism, route).forEach((detector) => {
        const bounds = detectorCollectionBounds(detector);
        const coverage = emTargets.reduce((sum, emMax) => sum + ((bounds.min === null || bounds.max === null || (emMax >= bounds.min && emMax <= bounds.max)) ? 1 : 0), 0);
        const response = (bounds.min === null || bounds.max === null)
          ? 1
          : pointMaskScore({ component_type: 'bandpass', center_nm: (bounds.min + bounds.max) / 2, width_nm: Math.max(4, bounds.max - bounds.min) }, emTargets, 'emission');
        const qe = normalizePercent(detector && detector.qe_peak_pct, 0.5) ?? 0.5;
        const endpointBoost = detectorClass(detector && (detector.kind || detector.endpoint_type)) === 'eyepiece' ? 0.25 : 0;
        scored.push({ mechanismId: mechanism.id, slot: detector.slot, detector: { ...detector }, score: (coverage * 10) + response + (qe * 5) + endpointBoost });
      });
    });
    const narrowed = scored.sort((a, b) => b.score - a.score).slice(0, 3);
    if (!narrowed.length) return [[]];
    const sets = narrowed.map((entry) => [entry]);
    if (narrowed.length > 1) sets.push(narrowed.slice(0, 2));
    return sets;
  }

  function splitterSelectionsForRoute(normalizedInstrument, route) {
    const splitters = routeMechanismsForOptimization(normalizedInstrument.splitters, route);
    if (!splitters.length) return [[]];

    const perSplitter = splitters.map((splitter) => {
      const branches = (Array.isArray(splitter.branches) ? splitter.branches : []).filter((branch) =>
        routeMatches((branch && branch.__routes) || splitter.__routes, route)
      );
      const selectedBranchIds = branches
        .filter((branch) => !splitter.branch_selection_required || (Array.isArray(branch.target_ids) && branch.target_ids.length))
        .map((branch) => normalizeIdentifier(branch.id));

      if (splitter.branch_selection_required && !selectedBranchIds.length) return [];

      return [{
        ...splitter,
        branches: branches.map((branch) => ({ ...branch })),
        selected_branch_ids: selectedBranchIds,
      }];
    });

    if (perSplitter.some((group) => !group.length)) return [];
    return perSplitter.reduce(
      (combos, group) => combos.flatMap((combo) => group.map((entry) => [...combo, entry])),
      [[]]
    );
  }

  function evaluateConfigurationScore(simulation, fluorophores, tolerance) {
    if (!simulation || simulation.validSelection === false || !Array.isArray(simulation.results) || !simulation.results.length) {
      return null;
    }

    const leakFree = simulation.results.filter((row) =>
      (row.excitationLeakageWeightedIntensity || 0) <= tolerance
      && (row.excitationLeakageThroughput || 0) <= tolerance
    );

    const byFluor = new Map();
    leakFree.forEach((row) => {
      const current = byFluor.get(row.fluorophoreKey);
      const rowScore = row.detectorEfficiencyFraction || row.detectorWeightedIntensity || row.benchmarkFraction || 0;
      const currentScore = current
        ? (current.detectorEfficiencyFraction || current.detectorWeightedIntensity || current.benchmarkFraction || 0)
        : -Infinity;
      if (!current || rowScore > currentScore) {
        byFluor.set(row.fluorophoreKey, row);
      }
    });

    const fluorList = Array.isArray(fluorophores) ? fluorophores : [];
    const chosenRows = Array.from(byFluor.values());
    const strict = fluorList.every((fluor) => byFluor.has(fluor.key));
    const captureScore = chosenRows.reduce((sum, row) => sum + (row.detectorEfficiencyFraction || row.benchmarkFraction || 0), 0);

    const matrix = simulation.crosstalkMatrix || {};
    const pairwiseCrosstalkByTarget = chosenRows.map((targetRow) => chosenRows.reduce((sum, sourceRow) => {
      if (sourceRow.fluorophoreKey === targetRow.fluorophoreKey) return sum;
      return sum + ((((matrix[sourceRow.fluorophoreKey] || {})[targetRow.fluorophoreKey] || {}).percentOfTargetChannel) || 0);
    }, 0));

    const maxLeak = Math.max(...simulation.results.map((row) =>
      Math.max(row.excitationLeakageWeightedIntensity || 0, row.excitationLeakageThroughput || 0)
    ), 0);

    const maxCrosstalk = Math.max(0, ...pairwiseCrosstalkByTarget);
    const crosstalkPenalty = pairwiseCrosstalkByTarget.reduce(
      (product, pct) => product * clamp(1 - (pct / 100), 0.001, 1),
      1
    );

    return {
      strict,
      score: captureScore * crosstalkPenalty,
      maxLeak,
      maxCrosstalk,
    };
  }

  function computeCrosstalkMatrix(results) {
    const rows = Array.isArray(results) ? results : [];
    const bestChannelByFluor = new Map();

    rows.forEach((row) => {
      const current = bestChannelByFluor.get(row.fluorophoreKey);
      if (!current || (row.detectorWeightedIntensity || 0) > (current.detectorWeightedIntensity || 0)) {
        bestChannelByFluor.set(row.fluorophoreKey, row);
      }
    });

    const matrix = {};
    Array.from(bestChannelByFluor.values()).forEach((targetRow) => {
      const targetSignal = Math.max(targetRow.detectorWeightedIntensity || 0, 1e-12);
      const contributors = rows.filter((row) => row.pathKey === targetRow.pathKey);

      contributors.forEach((sourceRow) => {
        if (!matrix[sourceRow.fluorophoreKey]) matrix[sourceRow.fluorophoreKey] = {};
        matrix[sourceRow.fluorophoreKey][targetRow.fluorophoreKey] = {
          sourceFluorophoreKey: sourceRow.fluorophoreKey,
          targetFluorophoreKey: targetRow.fluorophoreKey,
          detectorKey: targetRow.detectorKey,
          pathKey: targetRow.pathKey,
          weightedIntensity: sourceRow.detectorWeightedIntensity || 0,
          percentOfTargetChannel: ((sourceRow.detectorWeightedIntensity || 0) / targetSignal) * 100,
        };
      });
    });

    return matrix;
  }

  function optimizeLightPath(fluorophores, instrument, options) {
    const normalizedInstrument = normalizeInstrumentPayload(instrument);
    const fluorList = Array.isArray(fluorophores) ? fluorophores.filter(Boolean) : [];
    if (!fluorList.length) return null;
    const exTargets = fluorList.map((fluor) => numberOrNull(fluor.exMax)).filter((value) => value !== null);
    const emTargets = fluorList.map((fluor) => numberOrNull(fluor.emMax)).filter((value) => value !== null);
    const requestedRoute = cleanString(options && options.currentRoute).toLowerCase();
    const routes = requestedRoute
      ? [requestedRoute]
      : Array.from(new Set([
          normalizedInstrument.defaultRoute,
          ...((normalizedInstrument.routeOptions || []).map((entry) => entry.id)),
        ].filter(Boolean)));
    const tolerance = numberOrNull(options && options.leakageTolerance) ?? 0.005;
    const EPS = 1e-9;
    let bestStrict = null;
    let bestFallback = null;

    routes.forEach((route) => {
      const sourceSets = sourceCandidateSetsForRoute(normalizedInstrument, fluorList, route);
      const cubeGroups = topMechanismOptions(normalizedInstrument.cube, route, (value) => {
        const expanded = expandCubeSelectionForOptimization(value);
        const ex = expanded.filter((entry) => entry.stage === 'excitation').map((entry) => entry.component);
        const di = expanded.filter((entry) => entry.stage === 'dichroic').map((entry) => entry.component);
        const em = expanded.filter((entry) => entry.stage === 'emission').map((entry) => entry.component);
        return (ex.reduce((sum, component) => sum + pointMaskScore(component, exTargets, 'excitation'), 0) * 3)
          + (di.reduce((sum, component) => sum + pointMaskScore(component, exTargets, 'excitation'), 0) * 2)
          + (di.reduce((sum, component) => sum + pointMaskScore(component, emTargets, 'emission'), 0) * 3)
          + (em.reduce((sum, component) => sum + pointMaskScore(component, emTargets, 'emission'), 0) * 4);
      }, 3);
      const excitationGroups = cubeGroups.length ? [] : topMechanismOptions(normalizedInstrument.excitation, route, (value) => pointMaskScore(value, exTargets, 'excitation') * 5, 3);
      const dichroicGroups = cubeGroups.length ? [] : topMechanismOptions(normalizedInstrument.dichroic, route, (value) => (pointMaskScore(value, exTargets, 'excitation') * 3) + (pointMaskScore(value, emTargets, 'emission') * 4), 3);
      const emissionGroups = topMechanismOptions(normalizedInstrument.emission, route, (value) => (pointMaskScore(value, emTargets, 'emission') * 5) + ((1 - pointMaskScore(value, exTargets, 'emission')) * 2), 3);
      const detectorSets = detectorCandidatesForRoute(normalizedInstrument, fluorList, route);

      const cubeCombos = combineMechanismSelections(cubeGroups);
      const excitationCombos = cubeGroups.length ? [[]] : combineMechanismSelections(excitationGroups);
      const dichroicCombos = cubeGroups.length ? [[]] : combineMechanismSelections(dichroicGroups);
      const emissionCombos = combineMechanismSelections(emissionGroups);
      const splitterCombos = splitterSelectionsForRoute(normalizedInstrument, route);

      sourceSets.forEach((sourceSet) => {
        cubeCombos.forEach((cubeCombo) => {
          excitationCombos.forEach((exCombo) => {
            dichroicCombos.forEach((diCombo) => {
              emissionCombos.forEach((emCombo) => {
                splitterCombos.forEach((splitterCombo) => {
                  detectorSets.forEach((detectorSet) => {
                    const selectionMap = {};
                    const selection = {
                      sources: sourceSet.map((entry) => ({ ...entry.source })),
                      excitation: [],
                      dichroic: [],
                      emission: [],
                      splitters: splitterCombo.map((entry) => ({ ...entry })),
                      detectors: detectorSet.map((entry) => ({ ...entry.detector })),
                      selectionMap,
                    };
                  cubeCombo.forEach(({ mechanism, option }) => {
                    selectionMap[mechanism.id] = Number(option.slot || (option.value && option.value.slot));
                    expandCubeSelectionForOptimization(option.value).forEach((entry) => {
                      if (entry.stage === 'excitation') selection.excitation.push({ ...entry.component });
                      if (entry.stage === 'dichroic') selection.dichroic.push({ ...entry.component });
                      if (entry.stage === 'emission') selection.emission.push({ ...entry.component });
                    });
                  });
                  exCombo.forEach(({ mechanism, option }) => {
                    selectionMap[mechanism.id] = Number(option.slot || (option.value && option.value.slot));
                    selection.excitation.push({ ...(option.value || {}) });
                  });
                  diCombo.forEach(({ mechanism, option }) => {
                    selectionMap[mechanism.id] = Number(option.slot || (option.value && option.value.slot));
                    selection.dichroic.push({ ...(option.value || {}) });
                  });
                  emCombo.forEach(({ mechanism, option }) => {
                    selectionMap[mechanism.id] = Number(option.slot || (option.value && option.value.slot));
                    selection.emission.push({ ...(option.value || {}) });
                  });
                  if (!selectionIsValid(normalizedInstrument.validPaths, selectionMap)) return;
                  const simulation = simulateInstrument(instrument, selection, fluorList, options || {});
                  const evaluated = evaluateConfigurationScore(simulation, fluorList, tolerance);
                  if (!evaluated) return;
                  const descriptor = {
                    route,
                    selectionMap,
                    sources: sourceSet.map((entry) => ({ mechanismId: entry.mechanismId, slot: entry.slot, selected_wavelength_nm: entry.source.selected_wavelength_nm || entry.source.wavelength_nm || null })),
                    detectors: detectorSet.map((entry) => {
                      const bounds = detectorCollectionBounds(entry.detector);
                      return { mechanismId: entry.mechanismId, slot: entry.slot, collection_min_nm: bounds.min, collection_max_nm: bounds.max };
                    }),
                    splitters: splitterCombo.map((entry) => ({ mechanismId: entry.id, selected_branch_ids: Array.isArray(entry.selected_branch_ids) ? entry.selected_branch_ids.slice() : [] })),
                    score: evaluated.score,
                    strictLeakageSatisfied: evaluated.strict,
                    maxLeakage: evaluated.maxLeak,
                    maxCrosstalk: evaluated.maxCrosstalk,
                  };
                    if (evaluated.strict) {
                      if (!bestStrict || descriptor.score > bestStrict.score) bestStrict = descriptor;
                    } else {
                      const isBetterFallback = !bestFallback
                        || descriptor.maxCrosstalk < (bestFallback.maxCrosstalk - EPS)
                        || (
                          Math.abs(descriptor.maxCrosstalk - bestFallback.maxCrosstalk) <= EPS
                          && descriptor.maxLeakage < (bestFallback.maxLeakage - EPS)
                        )
                        || (
                          Math.abs(descriptor.maxCrosstalk - bestFallback.maxCrosstalk) <= EPS
                          && Math.abs(descriptor.maxLeakage - bestFallback.maxLeakage) <= EPS
                          && descriptor.score > bestFallback.score
                        );
                      if (isBetterFallback) bestFallback = descriptor;
                    }
                  });
                });
              });
            });
          });
        });
      });
    });

    return bestStrict || bestFallback;
  }

  function selectionIsValid(validPaths, selectionMap) {
    if (!Array.isArray(validPaths) || !validPaths.length) return true;
    const requiredEntries = Object.entries(selectionMap || {}).filter(([, value]) => Number.isFinite(value));
    if (!requiredEntries.length) return true;
    return validPaths.some((path) => requiredEntries.every(([key, value]) => path[key] === undefined || path[key] === value));
  }


  function knownDetectorCatalog(normalizedInstrument) {
    const catalog = [];
    (Array.isArray(normalizedInstrument && normalizedInstrument.detectors) ? normalizedInstrument.detectors : []).forEach((mechanism) => {
      Object.values(mechanism.positions || {}).forEach((detector) => catalog.push({ ...detector }));
    });
    (Array.isArray(normalizedInstrument && normalizedInstrument.terminals) ? normalizedInstrument.terminals : []).forEach((terminal) => {
      catalog.push({
        ...terminal,
        id: terminal.id || terminal.terminal_id,
        terminal_id: terminal.terminal_id || terminal.id,
        display_label: terminal.display_label || terminal.name || 'Endpoint',
        name: terminal.name || terminal.display_label || 'Endpoint',
        kind: terminal.kind || terminal.endpoint_type || 'detector',
        detector_class: terminal.detector_class || detectorClass(terminal.kind || terminal.endpoint_type),
      });
    });
    const seen = new Set();
    return catalog.filter((entry) => {
      const key = Array.from(detectorIdentifiers(entry))[0] || `${seen.size}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function detectorIdentifiers(detector) {
    const ids = new Set();
    [
      detector && detector.id,
      detector && detector.terminal_id,
      detector && detector.display_label,
      detector && detector.name,
      detector && detector.channel_name,
      detector && detector.source_mechanism_id,
    ].forEach((value) => {
      const cleaned = normalizeIdentifier(value);
      if (cleaned) ids.add(cleaned);
    });
    return ids;
  }

  function hydrateDetectorSelection(detector, normalizedInstrument) {
    const catalog = knownDetectorCatalog(normalizedInstrument);
    const ids = detectorIdentifiers(detector);
    const match = catalog.find((entry) => Array.from(detectorIdentifiers(entry)).some((value) => ids.has(value)));
    if (match) {
      return {
        ...match,
        ...detector,
        id: detector && detector.id ? detector.id : (match.id || match.terminal_id),
        terminal_id: detector && detector.terminal_id ? detector.terminal_id : (match.terminal_id || match.id),
        display_label: detector && detector.display_label ? detector.display_label : (match.display_label || match.name),
        name: detector && detector.name ? detector.name : (match.name || match.display_label),
        kind: detector && detector.kind ? detector.kind : (match.kind || match.endpoint_type || 'detector'),
        detector_class: detector && detector.detector_class ? detector.detector_class : (match.detector_class || detectorClass(match.kind || match.endpoint_type)),
      };
    }
    const fallbackId = cleanString(detector && (detector.id || detector.terminal_id || detector.display_label || detector.name)) || 'detector';
    return {
      ...(detector || {}),
      id: fallbackId,
      terminal_id: detector && detector.terminal_id ? detector.terminal_id : fallbackId,
      display_label: cleanString(detector && (detector.display_label || detector.name)) || 'Detector',
      name: cleanString(detector && (detector.name || detector.display_label)) || 'Detector',
      kind: cleanString(detector && detector.kind) || cleanString(detector && detector.endpoint_type) || 'detector',
      detector_class: detector && detector.detector_class ? detector.detector_class : detectorClass(detector && (detector.kind || detector.endpoint_type)),
    };
  }

  function inferredDetectorTargets(normalizedInstrument, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    if (!allowApproximation) return [];
    const catalog = knownDetectorCatalog(normalizedInstrument);
    const explicitlyDefault = catalog.filter((entry) => entry.default_enabled === true);
    if (explicitlyDefault.length) return explicitlyDefault;
    const digital = catalog.filter((entry) => entry.endpoint_type !== 'eyepiece');
    if (digital.length) return digital;
    if (catalog.length) return catalog;
    return [{
      id: 'virtual_detector',
      terminal_id: 'virtual_detector',
      display_label: 'Virtual Detector',
      name: 'Virtual Detector',
      kind: 'detector',
      detector_class: 'detector',
    }];
  }

  function branchAcceptsDetector(branch, detector, options) {
    const allowApproximation = Boolean(options && options.allowApproximation);
    if (!branch || !branch.splitterId) return true;
    const targets = Array.isArray(branch && branch.targetIds) ? branch.targetIds : branchTargetIds(branch, options);
    if (!targets.length) return allowApproximation;
    const ids = detectorIdentifiers(detector);
    return targets.some((target) => ids.has(normalizeIdentifier(target)));
  }

  function simulateInstrument(instrument, selection, fluorophores, options) {
    const normalizedInstrument = normalizeInstrumentPayload(instrument, options);
    const allowApproximation = !normalizedInstrument.strictHardwareTruth;
    const activeRoute = cleanString(options && options.currentRoute).toLowerCase()
      || normalizedInstrument.defaultRoute
      || null;
    const grid = wavelengthGrid(normalizedInstrument.metadata && normalizedInstrument.metadata.wavelength_grid);
    const selected = selection && typeof selection === 'object' ? selection : {};
    const selectedSources = Array.isArray(selected.sources) ? selected.sources : [];
    const selectedSplitters = Array.isArray(selected.splitters) ? selected.splitters : [];
    const explicitDetectorSelections = Array.isArray(selected.detectors) ? selected.detectors : [];

    const routeViolations = [];
    selectedSources.forEach((source) => {
      if (!componentMatchesActiveRoute(source, activeRoute)) {
        routeViolations.push(`Source ${source.display_label || source.name || 'Source'} is not on route ${activeRoute}.`);
      }
    });
    explicitDetectorSelections.forEach((detector) => {
      if (!componentMatchesActiveRoute(detector, activeRoute)) {
        routeViolations.push(`Detector ${detector.display_label || detector.name || 'Detector'} is not on route ${activeRoute}.`);
      }
    });
    selectedSplitters.forEach((splitter) => {
      if (!componentMatchesActiveRoute(splitter, activeRoute)) {
        routeViolations.push(`Splitter ${splitter.display_label || splitter.name || splitter.id || 'Splitter'} is not on route ${activeRoute}.`);
      }
    });
    const excitationComponents = Array.isArray(selected.excitation) ? selected.excitation : [];
    const dichroicComponents = Array.isArray(selected.dichroic) ? selected.dichroic : [];
    const emissionComponents = Array.isArray(selected.emission) ? selected.emission : [];
    const illuminationOrdered = Array.isArray(selected.illuminationComponents) && selected.illuminationComponents.length ? selected.illuminationComponents : null;
    const detectionOrdered = Array.isArray(selected.detectionComponents) && selected.detectionComponents.length ? selected.detectionComponents : null;

    [
      ['Excitation component', excitationComponents],
      ['Dichroic', dichroicComponents],
      ['Emission component', emissionComponents],
    ].forEach(([label, components]) => {
      components.forEach((component) => {
        if (!componentMatchesActiveRoute(component, activeRoute)) {
          routeViolations.push(`${label} ${component.display_label || component.name || component.id || ''}`.trim() + ` is not on route ${activeRoute}.`);
        }
      });
    });

    if (routeViolations.length) {
      return {
        grid,
        excitationAtSample: grid.map(() => 0),
        emittedSpectra: [],
        pathSpectra: [],
        selectedSources: selectedSources.map((source) => source.display_label || source.name || 'Source'),
        selectedDetectors: explicitDetectorSelections.map((detector) => detector.display_label || detector.name || 'Detector'),
        validSelection: false,
        routeViolation: true,
        routeViolationDetails: routeViolations,
        results: [],
        crosstalkMatrix: {},
      };
    }

    const excitationSources = selectedSources.filter((source) => {
      const role = cleanString(source.role).toLowerCase();
      return role !== 'depletion' && role !== 'transmitted_illumination';
    });
    const depletionSources = selectedSources.filter((source) => cleanString(source.role).toLowerCase() === 'depletion');
    const resolvedDetectors = (explicitDetectorSelections.length ? explicitDetectorSelections : inferredDetectorTargets(normalizedInstrument, { allowApproximation }))
      .map((detector) => hydrateDetectorSelection(detector, normalizedInstrument));
    const fluorList = Array.isArray(fluorophores) ? fluorophores : [];

    const propagatedExcitationSources = excitationSources.map((source) => {
      const weightedSpectrum = scaleArray(sourceSpectrum(source, grid), sourceWeight(source));
      const atSample = illuminationOrdered
        ? applyComponentSeries(weightedSpectrum, illuminationOrdered.map((entry) => entry.component), grid, (component, index) => ({ mode: illuminationOrdered[index].mode }))
        : applyComponentSeries(
          applyComponentSeries(weightedSpectrum, excitationComponents, grid, { mode: 'excitation' }),
          dichroicComponents,
          grid,
          { mode: 'excitation' }
        );
      return { source, weightedSpectrum, atSample };
    });
    const combinedExcitation = propagatedExcitationSources.reduce(
      (sum, entry) => addArrays(sum, entry.atSample),
      grid.map(() => 0)
    );
    const excitationAtSample = combinedExcitation;
    const totalExcitationAtSampleArea = propagatedExcitationSources.reduce(
      (sum, entry) => sum + integrateSpectrum(entry.atSample, grid),
      0
    );
    const excitationLeakageBySource = propagatedExcitationSources.map((entry) => {
      const afterDetectionOptics = detectionOrdered
        ? applyComponentSeries(entry.atSample, detectionOrdered.map((e) => e.component), grid, (component, index) => ({ mode: detectionOrdered[index].mode }))
        : applyComponentSeries(applyComponentSeries(entry.atSample, dichroicComponents, grid, { mode: 'emission' }), emissionComponents, grid, { mode: 'emission' });
      const branches = selectedSplitters.length
        ? propagateSplitters(afterDetectionOptics, selectedSplitters, normalizedInstrument, grid, { allowApproximation })
        : [{ id: 'main', label: 'Main Path', spectrum: afterDetectionOptics, targetIds: [] }];
      return {
        sourceLabel: entry.source.display_label || entry.source.name || 'Source',
        sourceCenters: sourceCenters(entry.source),
        sourceArea: integrateSpectrum(entry.atSample, grid),
        branches: new Map(branches.map((branch) => [branch.id, branch])),
      };
    });

    const results = [];
    const emittedSpectra = [];
    const pathSpectra = [];
    fluorList.forEach((fluorophore) => {
      const { ex, em } = fluorophoreSpectra(fluorophore, { preferTwoPhoton: Boolean(options && options.preferTwoPhoton) });
      const excitationCurve = normalizeSpectrumForGrid(ex, grid);
      const emissionCurve = normalizeSpectrumForGrid(em, grid);
      const excitationOverlapPower = integrateSpectrum(multiplyArrays(excitationAtSample, excitationCurve), grid);
      const excitationStrength = clamp(
        propagatedExcitationSources.reduce(
          (sum, entry) => sum + sourceExcitationContribution(entry.atSample, excitationCurve, grid),
          0
        ),
        0,
        1.5
      );
      const sted = evaluateStedPair(fluorophore, excitationSources, depletionSources, grid);
      const brightnessFactor = fluorophoreBrightnessFactor(fluorophore);
      const generatedEmission = scaleArray(emissionCurve, excitationStrength * sted.suppressionFactor * brightnessFactor);
      const theoreticalBestEmission = scaleArray(emissionCurve, brightnessFactor);
      const afterEmissionFilters = detectionOrdered
        ? applyComponentSeries(generatedEmission, detectionOrdered.map((e) => e.component), grid, (component, index) => ({ mode: detectionOrdered[index].mode }))
        : applyComponentSeries(applyComponentSeries(generatedEmission, dichroicComponents, grid, { mode: 'emission' }), emissionComponents, grid, { mode: 'emission' });
      const branches = selectedSplitters.length
        ? propagateSplitters(afterEmissionFilters, selectedSplitters, normalizedInstrument, grid, { allowApproximation })
        : [{ id: 'main', label: 'Main Path', spectrum: afterEmissionFilters, targetIds: [] }];
      const emissionArea = integrateSpectrum(generatedEmission, grid);
      const theoreticalBestArea = integrateSpectrum(theoreticalBestEmission, grid);

      emittedSpectra.push({
        fluorophoreKey: fluorophore.key,
        fluorophoreName: fluorophore.name,
        absorptionSpectrum: excitationCurve,
        generatedSpectrum: generatedEmission,
        postOpticsSpectrum: afterEmissionFilters,
        excitationOverlapPower,
        excitationEfficiency: excitationStrength,
        depletionOverlap: sted.applied ? sted.emissionOverlap : 0,
        sted,
      });

      branches.forEach((branch) => {
        const candidateDetectors = resolvedDetectors.filter((detector) => branchAcceptsDetector(branch, detector, { allowApproximation }));
        if (!candidateDetectors.length) return;
        candidateDetectors.forEach((detector) => {
          const response = detectorResponse(detector, grid);
          const collectionMask = detectorCollectionMask(detector, grid);
          const gatingFactor = detectorGatingFactor(detector);
          const collectedSpectrum = applyMask(branch.spectrum, collectionMask);
          const emissionPathThroughput = safeRatio(integrateSpectrum(collectedSpectrum, grid), emissionArea);
          const detectorWeightedIntensity = integrateSpectrum(multiplyArrays(collectedSpectrum, response), grid) * gatingFactor;

          const leakageContributions = excitationLeakageBySource.map((entry) => {
            const branchLeakage = entry.branches.get(branch.id);
            const preDetectorSpectrum = branchLeakage && Array.isArray(branchLeakage.spectrum)
              ? branchLeakage.spectrum
              : grid.map(() => 0);
            const collectedLeakageSpectrum = applyMask(preDetectorSpectrum, collectionMask);
            return {
              sourceLabel: entry.sourceLabel,
              sourceCenters: entry.sourceCenters,
              spectrum: collectedLeakageSpectrum,
              weightedIntensity: integrateSpectrum(multiplyArrays(collectedLeakageSpectrum, response), grid) * gatingFactor,
              throughput: safeRatio(integrateSpectrum(collectedLeakageSpectrum, grid), entry.sourceArea),
            };
          });
          const excitationLeakageSpectrum = leakageContributions.reduce(
            (sum, entry) => addArrays(sum, entry.spectrum),
            grid.map(() => 0)
          );
          const excitationLeakageWeightedIntensity = leakageContributions.reduce(
            (sum, entry) => sum + entry.weightedIntensity,
            0
          );
          const excitationLeakageThroughput = safeRatio(
            integrateSpectrum(excitationLeakageSpectrum, grid),
            totalExcitationAtSampleArea
          );
          const excitationLeakageWarningLevel = leakageWarningLevel(excitationLeakageThroughput);
          const excitationLeakageSourceLabels = leakageContributions
            .filter((entry) => entry.throughput >= 0.005)
            .map((entry) => entry.sourceLabel);
          const collectedArea = integrateSpectrum(collectedSpectrum, grid);
          const detectorId = detector.id || detector.terminal_id || detector.display_label || detector.name || 'detector';
          const pathKey = `${branch.id}::${detectorId}`;
          const pathLabel = `${branch.label} -> ${detector.display_label || detector.name || 'Detector'}`;

          pathSpectra.push({
            fluorophoreKey: fluorophore.key,
            fluorophoreName: fluorophore.name,
            detectorKey: detectorId,
            detectorLabel: detector.display_label || detector.name || 'Detector',
            detectorClass: detector.detector_class || detectorClass(detector.kind || detector.endpoint_type),
            endpointType: detector.endpoint_type || 'detector',
            pathKey,
            pathLabel,
            spectrum: collectedSpectrum,
            preDetectorSpectrum: branch.spectrum.slice(),
            collectionMask,
            detectorResponse: response,
            collectionMinNm: detectorCollectionBounds(detector).min,
            collectionMaxNm: detectorCollectionBounds(detector).max,
            excitationLeakageSpectrum,
            excitationLeakageWeightedIntensity,
            excitationLeakageThroughput,
            excitationLeakageWarningLevel,
            excitationLeakageSourceLabels,
            targetIds: Array.isArray(branch.targetIds) ? branch.targetIds.slice() : [],
          });
          results.push({
            fluorophoreKey: fluorophore.key,
            fluorophoreName: fluorophore.name,
            fluorophoreState: fluorophore.activeStateName || 'Default state',
            detectorKey: detectorId,
            detectorLabel: detector.display_label || detector.name || 'Detector',
            detectorClass: detector.detector_class || detectorClass(detector.kind || detector.endpoint_type),
            endpointType: detector.endpoint_type || 'detector',
            pathKey,
            pathLabel,
            excitationStrength,
            emissionPathThroughput,
            detectorWeightedIntensity,
            detectorEfficiencyFraction: safeRatio(detectorWeightedIntensity, theoreticalBestArea),
            gatingFactor,
            sted,
            excitationLeakageWeightedIntensity,
            excitationLeakageThroughput,
            excitationLeakageWarningLevel,
            excitationLeakageSourceLabels,
            benchmarkGeneratedEmission: emissionArea,
            benchmarkCollectedEmission: collectedArea,
            theoreticalBestCase: theoreticalBestArea,
            benchmarkFraction: safeRatio(collectedArea, theoreticalBestArea),
          });
        });
      });
    });

    const crosstalkMatrix = computeCrosstalkMatrix(results);

    const bestChannelByFluor = new Map();
    results.forEach((result) => {
      const current = bestChannelByFluor.get(result.fluorophoreKey);
      if (!current || (result.detectorWeightedIntensity || 0) > (current.detectorWeightedIntensity || 0)) {
        bestChannelByFluor.set(result.fluorophoreKey, result);
      }
    });

    const pairwiseCrosstalkForTargetRow = (targetRow) => {
      const targetSignal = Math.max((targetRow && targetRow.detectorWeightedIntensity) || 0, 1e-12);
      return results.reduce((sum, sourceRow) => {
        if (!sourceRow || sourceRow.fluorophoreKey === targetRow.fluorophoreKey) return sum;
        if (sourceRow.pathKey !== targetRow.pathKey) return sum;
        return sum + (((sourceRow.detectorWeightedIntensity || 0) / targetSignal) * 100);
      }, 0);
    };

    results.forEach((result) => {
      const totalPairwise = pairwiseCrosstalkForTargetRow(result);
      result.pairwiseCrosstalkPct = totalPairwise;
      result.crosstalkPct = totalPairwise;
      result.bleedThrough = ((result.detectorWeightedIntensity || 0) * totalPairwise) / 100;
    });

    results.forEach((result) => {
      const crosstalkPenalty = clamp(1 - ((result.pairwiseCrosstalkPct || 0) / 100), 0.1, 1);
      const leakPenalty = leakagePenalty(result.excitationLeakageThroughput || 0);
      const benchmarkFraction = result.benchmarkFraction || 0;
      result.recordedIntensity = result.detectorWeightedIntensity;
      result.relativePlanningScore = benchmarkFraction;
      result.planningScore = clamp(100 * benchmarkFraction * crosstalkPenalty * leakPenalty, 0, 100);
      result.correctnessScore = clamp(100 * benchmarkFraction * crosstalkPenalty * leakPenalty, 0, 100);
      result.detectorEfficiencyPct = (result.detectorEfficiencyFraction || 0) * 100;
      result.benchmarkPct = benchmarkFraction * 100;
      result.theoreticalBenchmarkPct = result.detectorEfficiencyPct;
      if (result.detectorWeightedIntensity <= 1e-6 || result.excitationStrength <= 0.02) {
        result.qualityLabel = 'blocked';
      } else if (benchmarkFraction >= 0.55 && result.excitationLeakageWarningLevel !== 'high' && (result.crosstalkPct || 0) < 20) {
        result.qualityLabel = 'good';
      } else if (benchmarkFraction >= 0.25 && result.excitationLeakageWarningLevel !== 'high') {
        result.qualityLabel = 'usable';
      } else {
        result.qualityLabel = 'poor';
      }
      result.laserLeakageLikely = result.excitationLeakageWarningLevel !== 'none';
      const leakingSources = (result.excitationLeakageSourceLabels || []).join(', ');
      if (result.excitationLeakageWarningLevel === 'high') {
        result.laserLeakageNote = `Selected excitation light is poorly rejected by this detection path${leakingSources ? ` (${leakingSources})` : ''}.`;
      } else if (result.excitationLeakageWarningLevel === 'moderate') {
        result.laserLeakageNote = `Some selected excitation light can leak into this detection path${leakingSources ? ` (${leakingSources})` : ''}.`;
      } else if (result.excitationLeakageWarningLevel === 'low') {
        result.laserLeakageNote = `Minor excitation-path leakage is possible${leakingSources ? ` (${leakingSources})` : ''}.`;
      } else {
        result.laserLeakageNote = '';
      }
    });

    return {
      grid,
      excitationAtSample,
      emittedSpectra,
      pathSpectra,
      selectedSources: selectedSources.map((source) => source.display_label || source.name || 'Source'),
      selectedDetectors: resolvedDetectors.map((detector) => detector.display_label || detector.name || 'Detector'),
      validSelection: selectionIsValid(normalizedInstrument.validPaths, selected.selectionMap || {}),
      results,
      crosstalkMatrix,
    };
  }

  return {
    normalizeRouteTags,
    routeLabel,

    routesFromObject,
    routeMatches,
    detectorClass,
    normalizeMechanismList,
    normalizeSplitters,
    normalizeTerminals,
    normalizeInstrumentPayload,
    normalizeResultsShape,
    normalizeFPbaseSearchResults,
    normalizeTypeToken,
    collectSpectraContainers,
    extractSpectra,
    normalizeFPbaseSpectraResponse,
    normalizeFluorophoreDetail,
    setFluorophoreState,
    searchFallbackFluorophores,
    fluorophoreSpectra,
    normalizePoints,
    wavelengthGrid,
    wavelengthToRGB,
    spectrumToCSSColor,
    componentMask,
    sourceCenters,
    sourceSpectrum,
    detectorResponse,
    detectorCollectionBounds,
    detectorCollectionMask,
    selectionIsValid,
    simulateInstrument,
    optimizeLightPath,
    ROUTE_SORT_ORDER: Array.from(ROUTE_SORT_ORDER),
  };
});

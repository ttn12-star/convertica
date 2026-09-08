// static/js/workbench.js
/**
 * Workbench — a board of drop-target converter tiles.
 *
 * State lives in localStorage (convertica_workbench_v1); presets are shared
 * with workflow-presets.js (convertica_premium_workflows_v1). Conversions run
 * through window.submitAsyncConversion from utils.js with per-tile container ids.
 *
 * Self-test: open /workbench/?selftest=1 and read the console.
 */
(function () {
    'use strict';

    const STATE_KEY = 'convertica_workbench_v1';
    const PRESETS_KEY = 'convertica_premium_workflows_v1';
    const MAX_PRESETS = 40;
    const SIZES = ['s', 'm', 'l'];

    // ─── Data blocks ────────────────────────────────────────────────────
    function readJson(id, fallback) {
        try {
            const el = document.getElementById(id);
            return el ? JSON.parse(el.textContent) : fallback;
        } catch (_) {
            return fallback;
        }
    }

    // ─── Ids ────────────────────────────────────────────────────────────
    function uid(prefix) {
        return prefix + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    }

    // ─── Persistence ────────────────────────────────────────────────────
    function loadState() {
        try {
            const raw = JSON.parse(localStorage.getItem(STATE_KEY) || 'null');
            if (raw && Array.isArray(raw.boards)) return raw;
        } catch (_) { /* corrupt or blocked storage → fresh state */ }
        return { boards: [], activeBoardId: null };
    }

    function saveState(state) {
        try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch (_) { /* quota / private mode */ }
    }

    function loadPresets() {
        try {
            const list = JSON.parse(localStorage.getItem(PRESETS_KEY) || '[]');
            return Array.isArray(list) ? list : [];
        } catch (_) { return []; }
    }

    function savePresets(list) {
        try { localStorage.setItem(PRESETS_KEY, JSON.stringify(list.slice(0, MAX_PRESETS))); } catch (_) { /* ignore */ }
        if (typeof window.pushWorkflowPresets === 'function') window.pushWorkflowPresets();
    }

    // ─── Board ops (pure where possible) ────────────────────────────────
    function ensureBoard(state, name) {
        if (!state.boards.length) {
            state.boards.push({ id: uid('b'), name: name, isDefault: true, tiles: [], createdAt: Date.now() });
        }
        if (!state.boards.some(b => b.id === state.activeBoardId)) {
            state.activeBoardId = (state.boards.find(b => b.isDefault) || state.boards[0]).id;
        }
        return state;
    }

    function activeBoard(state) {
        return state.boards.find(b => b.id === state.activeBoardId) || state.boards[0] || null;
    }

    function canAddTile(board, limits) {
        return !!board && board.tiles.length < limits.tiles;
    }

    function addTile(board, tile, limits) {
        if (!canAddTile(board, limits)) return false;
        board.tiles.push({ id: tile.id || uid('t'), kind: tile.kind, presetId: tile.presetId, size: SIZES.includes(tile.size) ? tile.size : 'm' });
        return true;
    }

    function removeTile(board, tileId) {
        board.tiles = board.tiles.filter(t => t.id !== tileId);
    }

    /** Pure: returns a new array with item `from` moved to index `to`. */
    function reorder(list, from, to) {
        const next = list.slice();
        if (from < 0 || from >= next.length || to < 0 || to >= next.length) return next;
        const [item] = next.splice(from, 1);
        next.splice(to, 0, item);
        return next;
    }

    /**
     * Joins tiles with their preset + catalog tool. Tiles whose preset or tool
     * is gone are dropped (returned in `dropped` so the caller can persist).
     */
    function resolveTiles(board, presets, catalog) {
        const byId = Object.create(null);
        presets.forEach(p => { byId[p.id] = p; });
        const resolved = [];
        const dropped = [];
        board.tiles.forEach(tile => {
            if (tile.kind !== 'preset') { dropped.push(tile); return; } // phase 1: preset tiles only
            const preset = byId[tile.presetId];
            const tool = preset && catalog[preset.toolKey];
            if (!preset || !tool || !tool.droppable) { dropped.push(tile); return; }
            resolved.push({ tile, preset, tool });
        });
        return { resolved, dropped };
    }

    function presetFromTool(toolKey, tool) {
        return { id: uid('p'), name: tool.label, toolKey, toolUrl: tool.pageUrl, toolLabel: tool.label, notes: '', params: {}, createdAt: Date.now() };
    }

    /** Same encoding workflow-presets.js reads from `#wfp=` on tool pages. */
    function encodeParams(params) {
        try {
            return btoa(unescape(encodeURIComponent(JSON.stringify(params || {})))).replace(/\+/g, '-').replace(/\//g, '_');
        } catch (_) { return ''; }
    }

    /** `accept` is the <input accept> string from the tool config (".pdf,application/pdf"). */
    function acceptsFile(file, accept) {
        if (!accept) return true;
        const name = (file.name || '').toLowerCase();
        const type = (file.type || '').toLowerCase();
        return accept.split(',').map(s => s.trim().toLowerCase()).filter(Boolean).some(rule => {
            if (rule.startsWith('.')) return name.endsWith(rule);
            if (rule.endsWith('/*')) return type.startsWith(rule.slice(0, -1));
            return type === rule;
        });
    }

    // ─── Self-test (?selftest=1) ────────────────────────────────────────
    function selfTest() {
        const assert = (cond, msg) => { if (!cond) throw new Error('workbench selftest: ' + msg); };
        const limits = { tiles: 2 };
        const state = ensureBoard({ boards: [], activeBoardId: null }, 'B');
        const board = activeBoard(state);
        assert(board && state.activeBoardId === board.id, 'ensureBoard creates + activates');
        assert(addTile(board, { kind: 'preset', presetId: 'p1', size: 'xl' }, limits), 'first add ok');
        assert(board.tiles[0].size === 'm', 'bad size falls back to m');
        assert(addTile(board, { kind: 'preset', presetId: 'p2', size: 's' }, limits), 'second add ok');
        assert(!addTile(board, { kind: 'preset', presetId: 'p3' }, limits), 'third add blocked by limit');
        assert(reorder([1, 2, 3], 0, 2).join() === '2,3,1', 'reorder moves forward');
        assert(reorder([1, 2, 3], 2, 0).join() === '3,1,2', 'reorder moves back');
        assert(reorder([1, 2, 3], 5, 0).join() === '1,2,3', 'reorder ignores bad index');
        const catalog = { pdf_to_word: { droppable: true, label: 'PDF to Word', pageUrl: '/x/' }, sign_pdf: { droppable: false } };
        const presets = [{ id: 'p1', toolKey: 'pdf_to_word' }, { id: 'p2', toolKey: 'sign_pdf' }];
        const { resolved, dropped } = resolveTiles(board, presets, catalog);
        assert(resolved.length === 1 && resolved[0].preset.id === 'p1', 'resolves droppable preset tile');
        assert(dropped.length === 1 && dropped[0].presetId === 'p2', 'drops non-droppable tool tile');
        assert(acceptsFile({ name: 'a.PDF', type: '' }, '.pdf,application/pdf'), 'accept by extension');
        assert(acceptsFile({ name: 'a.bin', type: 'image/png' }, 'image/*'), 'accept by mime wildcard');
        assert(!acceptsFile({ name: 'a.docx', type: '' }, '.pdf'), 'reject wrong extension');
        assert(encodeParams({ a: 1 }) === btoa('{"a":1}'), 'encodeParams matches workflow-presets');
        console.info('workbench selftest: OK');
    }

    window.Workbench = {
        uid, readJson, loadState, saveState, loadPresets, savePresets, ensureBoard, activeBoard,
        canAddTile, addTile, removeTile, reorder, resolveTiles, presetFromTool, encodeParams, acceptsFile, selfTest,
    };

    if (new URLSearchParams(location.search).get('selftest') === '1') selfTest();
})();

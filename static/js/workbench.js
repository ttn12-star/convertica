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

    // ─── Run flow ───────────────────────────────────────────────────────
    const MAX_RESULT_ROWS = 3;
    const busy = new Set();

    function tileError(tileId, message) {
        if (typeof window.showError === 'function') window.showError(message, 'wb-error-' + tileId);
    }

    function addResultRow(tileId, blob, filename) {
        const list = $('wb-result-' + tileId);
        if (!list) return;
        const url = URL.createObjectURL(blob);
        const li = el('li', 'flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-sm');
        li.appendChild(el('span', 'text-emerald-700', '✓'));
        const name = el('span', 'min-w-0 flex-1 truncate', filename);
        name.title = filename;
        li.appendChild(name);
        li.appendChild(el('span', 'text-xs text-gray-500', typeof window.formatFileSize === 'function' ? window.formatFileSize(blob.size) : ''));
        const a = el('a', 'font-semibold text-emerald-800 underline', I18N.download || 'Download');
        a.href = url; a.download = filename;
        li.appendChild(a);
        const x = el('button', 'text-gray-400 hover:text-gray-700 px-1', '×');
        x.type = 'button'; x.setAttribute('aria-label', I18N.remove || 'Remove');
        x.addEventListener('click', () => { URL.revokeObjectURL(url); li.remove(); });
        li.appendChild(x);
        list.prepend(li);
        while (list.children.length > MAX_RESULT_ROWS) {
            const last = list.lastElementChild;
            const link = last.querySelector('a');
            if (link) URL.revokeObjectURL(link.href);
            last.remove();
        }
    }

    function submitOne(tileId, apiUrl, formData, originalFileName) {
        return window.submitAsyncConversion({
            apiUrl,
            formData,
            csrfToken: window.CSRF_TOKEN || (document.querySelector('meta[name="csrf-token"]') || {}).content || '',
            originalFileName,
            loadingContainerId: 'wb-loading-' + tileId,
            downloadContainerId: 'wb-result-' + tileId,
            errorContainerId: 'wb-error-' + tileId,
            onSuccess: (blob, filename) => addResultRow(tileId, blob, filename),
            onError: () => { /* utils.js already rendered the error into wb-error-<id> */ },
        });
    }

    async function runTile(tileId, fileList) {
        if (busy.has(tileId)) return;
        const board = activeBoard(state);
        const { resolved } = resolveTiles(board, presets, CATALOG);
        const item = resolved.find(r => r.tile.id === tileId);
        if (!item || typeof window.submitAsyncConversion !== 'function') return;
        const { preset, tool } = item;

        const files = Array.from(fileList);
        const accepted = files.filter(f => acceptsFile(f, tool.fileAccept));
        if (!accepted.length) {
            tileError(tileId, (I18N.wrongType || 'This tile accepts: %(accept)s').replace('%(accept)s', tool.fileAccept));
            return;
        }
        const params = Object.entries(preset.params || {});
        const appendParams = fd => params.forEach(([k, v]) => fd.append(k, v === true ? 'true' : String(v)));

        busy.add(tileId);
        try {
            if (accepted.length > 1 && tool.batchApiUrl && LIMITS.tier === 'premium') {
                const fd = new FormData();
                accepted.forEach(f => fd.append(tool.batchFieldName, f));
                appendParams(fd);
                await submitOne(tileId, tool.batchApiUrl, fd, accepted[0].name);
            } else {
                for (const file of accepted) {
                    const fd = new FormData();
                    fd.append(tool.fileInputName, file);
                    appendParams(fd);
                    await submitOne(tileId, tool.apiUrl, fd, file.name);
                }
            }
        } finally {
            busy.delete(tileId);
        }
    }

    // ─── Render ─────────────────────────────────────────────────────────
    const CATALOG = readJson('workbench-catalog', {});
    const LIMITS = readJson('workbench-limits', { tier: 'anonymous', boards: 1, tiles: 3 });
    const I18N = readJson('workbench-i18n', {});
    const state = ensureBoard(loadState(), I18N.boardName || 'My board');
    let presets = loadPresets();
    let onTileFiles = runTile;

    const $ = id => document.getElementById(id);
    const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
    const SIZE_CLASS = { s: '', m: 'md:col-span-2', l: 'md:col-span-2 md:row-span-2' };
    const GROUP_ICON = { convert: 'CV', edit: 'ED', organize: 'OR', security: 'SE', epub: 'EP', image: 'IM', archive: 'ZP' };

    function persist() { saveState(state); }

    function render() {
        const grid = $('wb-grid');
        const empty = $('wb-empty');
        const board = activeBoard(state);
        if (!grid || !board) return;
        $('wb-board-name').textContent = board.name;

        const { resolved, dropped } = resolveTiles(board, presets, CATALOG);
        if (dropped.length) { board.tiles = board.tiles.filter(t => !dropped.includes(t)); persist(); }

        grid.replaceChildren();
        empty.hidden = resolved.length > 0;
        resolved.forEach((item, index) => grid.appendChild(renderTile(item, index, resolved.length)));
        renderPickerList();
    }

    function renderTile({ tile, preset, tool }, index, count) {
        const node = $('wb-tile-template').content.firstElementChild.cloneNode(true);
        node.dataset.tileId = tile.id;
        node.className += ' ' + (SIZE_CLASS[tile.size] || '');
        node.querySelector('.wb-tile-icon').textContent = GROUP_ICON[tool.group] || 'CV';
        node.querySelector('.wb-tile-title').textContent = preset.name;
        node.querySelector('.wb-tile-subtitle').textContent = tool.label;
        node.querySelector('.wb-drop-text').textContent = I18N.dropHere || 'Drop files here';
        node.querySelector('.wb-loading').id = 'wb-loading-' + tile.id;
        node.querySelector('.wb-error').id = 'wb-error-' + tile.id;
        node.querySelector('.wb-results').id = 'wb-result-' + tile.id;

        const input = node.querySelector('.wb-file');
        input.accept = tool.fileAccept || '';
        input.multiple = true;
        input.addEventListener('change', () => { if (input.files.length) onTileFiles(tile.id, input.files); input.value = ''; });

        const drop = node.querySelector('.wb-drop');
        ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('border-amber-500', 'bg-amber-50'); }));
        ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, () => drop.classList.remove('border-amber-500', 'bg-amber-50')));
        drop.addEventListener('drop', e => { e.preventDefault(); if (e.dataTransfer.files.length) onTileFiles(tile.id, e.dataTransfer.files); });
        node.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target === node) input.click(); });

        buildMenu(node, tile, preset, tool, index, count);
        return node;
    }

    function buildMenu(node, tile, preset, tool, index, count) {
        const btn = node.querySelector('.wb-tile-menu-btn');
        const menu = node.querySelector('.wb-tile-menu');
        const item = (label, onClick, disabled) => {
            const b = el('button', 'w-full text-start px-3 py-2 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed', label);
            b.type = 'button'; b.role = 'menuitem'; b.disabled = !!disabled;
            b.addEventListener('click', () => { menu.classList.add('hidden'); onClick(); });
            return b;
        };
        const board = activeBoard(state);
        const sizeRow = el('div', 'flex items-center gap-1 px-3 py-2 text-xs text-gray-500');
        sizeRow.appendChild(el('span', 'me-auto', I18N.size || 'Size'));
        SIZES.forEach(s => {
            const b = el('button', 'px-2 py-0.5 rounded border ' + (tile.size === s ? 'border-amber-500 text-amber-700 font-bold' : 'border-gray-200'), s.toUpperCase());
            b.type = 'button';
            b.addEventListener('click', () => { tile.size = s; persist(); render(); });
            sizeRow.appendChild(b);
        });
        menu.replaceChildren(
            item(I18N.configure || 'Configure', () => { location.href = tool.pageUrl + '#wfp=' + encodeParams(preset.params); }),
            sizeRow,
            item(I18N.moveLeft || 'Move left', () => { board.tiles = reorder(board.tiles, index, index - 1); persist(); render(); }, index === 0),
            item(I18N.moveRight || 'Move right', () => { board.tiles = reorder(board.tiles, index, index + 1); persist(); render(); }, index === count - 1),
            item(I18N.remove || 'Remove', () => { removeTile(board, tile.id); persist(); render(); }),
        );
        menu.lastElementChild.classList.add('text-red-600');
        btn.addEventListener('click', e => {
            e.stopPropagation();
            document.querySelectorAll('.wb-tile-menu').forEach(m => {
                if (m !== menu) { m.classList.add('hidden'); const b = m.previousElementSibling; if (b) b.setAttribute('aria-expanded', 'false'); }
            });
            const open = menu.classList.toggle('hidden') === false;
            btn.setAttribute('aria-expanded', String(open));
            if (open) closePicker();
        });
    }

    // ─── Picker (dui SelectWidgets: search + toggle rows) ───────────────
    function pickerRows(query) {
        const board = activeBoard(state);
        const onBoard = new Set(board.tiles.map(t => t.presetId));
        const q = (query || '').trim().toLowerCase();
        const match = s => !q || s.toLowerCase().includes(q);
        const rows = [];
        presets.filter(p => p.params && Object.keys(p.params).length && CATALOG[p.toolKey] && CATALOG[p.toolKey].droppable && (match(p.name) || match(CATALOG[p.toolKey].label)))
            .forEach(p => rows.push({ group: I18N.myPresets || 'My presets', label: p.name, sub: CATALOG[p.toolKey].label, checked: onBoard.has(p.id), presetId: p.id, locked: CATALOG[p.toolKey].premiumOnly && LIMITS.tier !== 'premium' }));
        Object.entries(CATALOG).filter(([, t]) => t.droppable && match(t.label))
            .sort((a, b) => a[1].label.localeCompare(b[1].label))
            .forEach(([key, t]) => {
                const existing = presets.find(p => p.toolKey === key && (!p.params || !Object.keys(p.params).length));
                rows.push({ group: I18N.converters || 'Converters', label: t.label, sub: t.group, checked: !!existing && onBoard.has(existing.id), toolKey: key, presetId: existing && existing.id, locked: t.premiumOnly && LIMITS.tier !== 'premium' });
            });
        return rows;
    }

    function renderPickerList() {
        const list = $('wb-picker-list');
        if (!list) return;
        const board = activeBoard(state);
        const full = !canAddTile(board, LIMITS);
        const limitBox = $('wb-picker-limit');
        limitBox.hidden = !full;
        if (full) {
            limitBox.replaceChildren(el('span', '', (I18N.limitReached || 'Tile limit reached.') + ' '));
            const a = el('a', 'font-semibold underline', LIMITS.tier === 'anonymous' ? (I18N.signIn || 'Sign in') : (I18N.upgrade || 'Upgrade'));
            a.href = $('wb-root').dataset.upgradeUrl;
            limitBox.appendChild(a);
        }
        list.replaceChildren();
        let lastGroup = null;
        pickerRows($('wb-picker-search').value).forEach(row => {
            if (row.group !== lastGroup) { list.appendChild(el('li', 'px-3 pt-2 pb-1 text-[11px] font-bold uppercase tracking-wide text-gray-400', row.group)); lastGroup = row.group; }
            const li = el('li');
            const b = el('button', 'w-full flex items-center gap-3 px-3 py-2 text-sm text-start hover:bg-gray-50 disabled:opacity-40');
            b.type = 'button'; b.role = 'option'; b.setAttribute('aria-selected', String(row.checked));
            b.disabled = row.locked || (!row.checked && full);
            const box = el('span', 'w-4 h-4 rounded border flex items-center justify-center text-[10px] ' + (row.checked ? 'bg-amber-600 border-amber-600 text-white' : 'border-gray-300'), row.checked ? '✓' : '');
            const text = el('span', 'min-w-0 flex-1');
            text.appendChild(el('span', 'block truncate font-medium', row.label));
            text.appendChild(el('span', 'block truncate text-xs text-gray-500', row.sub));
            b.append(box, text);
            if (row.locked) b.appendChild(el('span', 'text-xs text-amber-700 font-bold', I18N.pro || 'PRO'));
            b.addEventListener('click', () => togglePickerRow(row));
            li.appendChild(b);
            list.appendChild(li);
        });
    }

    function togglePickerRow(row) {
        const board = activeBoard(state);
        if (row.checked) {
            board.tiles = board.tiles.filter(t => t.presetId !== row.presetId);
        } else {
            let presetId = row.presetId;
            if (!presetId) {
                const preset = presetFromTool(row.toolKey, CATALOG[row.toolKey]);
                presets = presets.concat([preset]);
                savePresets(presets);
                presetId = preset.id;
            }
            addTile(board, { kind: 'preset', presetId, size: 'm' }, LIMITS);
        }
        persist();
        render();
    }

    function openPicker() {
        $('wb-picker').hidden = false;
        $('wb-add-btn').setAttribute('aria-expanded', 'true');
        renderPickerList();
        $('wb-picker-search').focus();
    }

    function closePicker() {
        $('wb-picker').hidden = true;
        $('wb-add-btn').setAttribute('aria-expanded', 'false');
    }

    function bindChrome() {
        $('wb-add-btn').addEventListener('click', e => { e.stopPropagation(); $('wb-picker').hidden ? openPicker() : closePicker(); });
        document.querySelectorAll('[data-wb-open-picker]').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); openPicker(); }));
        $('wb-picker').addEventListener('click', e => e.stopPropagation());
        $('wb-picker-search').addEventListener('input', renderPickerList);
        document.addEventListener('click', () => {
            closePicker();
            document.querySelectorAll('.wb-tile-menu').forEach(m => m.classList.add('hidden'));
        });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') { closePicker(); document.querySelectorAll('.wb-tile-menu').forEach(m => m.classList.add('hidden')); } });
        window.addEventListener('convertica:workflows-synced', () => { presets = loadPresets(); render(); });
    }

    document.addEventListener('DOMContentLoaded', () => {
        if (!$('wb-grid')) return;
        bindChrome();
        render();
    });

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
        render, openPicker, closePicker,
    };

    if (new URLSearchParams(location.search).get('selftest') === '1') selfTest();
})();

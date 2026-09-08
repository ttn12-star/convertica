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

    /** `/en/pdf-to-word/` → `/pdf-to-word/`; a path without a locale is unchanged. */
    function stripLocale(path) {
        return String(path || '').replace(/^\/[a-z]{2}(?:-[a-z]{2})?(?=\/)/i, '');
    }

    /**
     * Which catalog tool a preset points at. Presets saved on a tool page carry
     * `toolKey` since v2.2; older ones only have `toolUrl` (possibly in another
     * locale), so fall back to matching page paths. '' when nothing matches.
     */
    function resolveToolKey(preset, catalog) {
        if (preset.toolKey && catalog[preset.toolKey]) return preset.toolKey;
        const want = stripLocale(preset.toolUrl);
        if (!want) return '';
        return Object.keys(catalog).find(key => stripLocale(catalog[key].pageUrl) === want) || '';
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
    // ponytail: one conversion at a time for the whole board. utils.js's
    // showLoading/updateProgress write to hard-coded #progressBar /
    // #progressPercentage ids and a global window._currentTaskId, so two
    // running tiles corrupt each other's progress and cancel button. Ceiling:
    // per-tile concurrency needs utils.js to take container-scoped ids.
    let runningTileId = null;
    const results = new Map(); // tileId -> [{url, filename, size}], newest first, max MAX_RESULT_ROWS

    function tileError(tileId, message) {
        if (typeof window.showError === 'function') window.showError(message, 'wb-error-' + tileId);
    }

    /** Rebuilds a tile's result list from `results` — survives `render()` rebuilding the tile DOM. */
    function renderResults(tileId, container) {
        const list = container || $('wb-result-' + tileId);
        if (!list) return;
        const entries = results.get(tileId) || [];
        list.replaceChildren(...entries.map(entry => {
            const li = el('li', 'flex items-center gap-2 rounded-lg bg-emerald-100 border border-emerald-200 px-3 py-1.5 text-sm');
            li.appendChild(el('span', 'text-emerald-700', '✓'));
            const name = el('span', 'min-w-0 flex-1 truncate', entry.filename);
            name.title = entry.filename;
            li.appendChild(name);
            li.appendChild(el('span', 'text-xs text-gray-500', typeof window.formatFileSize === 'function' ? window.formatFileSize(entry.size) : ''));
            const a = el('a', 'font-semibold text-emerald-800 underline', I18N.download || 'Download');
            a.href = entry.url; a.download = entry.filename;
            li.appendChild(a);
            const x = el('button', 'text-gray-400 hover:text-gray-700 px-1', '×');
            x.type = 'button'; x.setAttribute('aria-label', I18N.remove || 'Remove');
            x.addEventListener('click', () => {
                const current = results.get(tileId) || [];
                const i = current.indexOf(entry);
                if (i !== -1) { URL.revokeObjectURL(entry.url); current.splice(i, 1); }
                renderResults(tileId);
            });
            li.appendChild(x);
            return li;
        }));
    }

    function addResultRow(tileId, blob, filename) {
        const list = results.get(tileId) || [];
        list.unshift({ url: URL.createObjectURL(blob), filename, size: blob.size });
        while (list.length > MAX_RESULT_ROWS) URL.revokeObjectURL(list.pop().url);
        results.set(tileId, list);
        renderResults(tileId);
    }

    /** Revokes every result URL for a tile before it's removed from the board. */
    function clearResults(tileId) {
        (results.get(tileId) || []).forEach(entry => URL.revokeObjectURL(entry.url));
        results.delete(tileId);
    }

    /** Highlights the tile that currently owns the board's single conversion slot. */
    function markRunning(tileId, on) {
        const node = $('wb-grid') && $('wb-grid').querySelector('[data-tile-id="' + tileId + '"]');
        if (!node) return;
        node.classList.toggle('wb-tile-running', on);
        node.classList.toggle('ring-2', on);
        node.classList.toggle('ring-amber-400', on);
    }

    function submitOne(tileId, apiUrl, formData, originalFileName, useAsync) {
        // ponytail: submitAsyncConversion's promise settles before polling
        // finishes for async (>5MB) files (pollTaskStatus recurses via
        // setTimeout, not awaited) — resolve ourselves from its callbacks so
        // the sequential loop in runTile actually waits and releases `busy`
        // at the right time. Ceiling: a code path that fires none of
        // onSuccess/onError/onBackground leaves the tile busy until reload;
        // widen if that's ever observed.
        return new Promise(resolve => {
            const options = {
                apiUrl,
                formData,
                csrfToken: window.CSRF_TOKEN || (document.querySelector('meta[name="csrf-token"]') || {}).content || '',
                originalFileName,
                loadingContainerId: 'wb-loading-' + tileId,
                downloadContainerId: 'wb-result-' + tileId,
                errorContainerId: 'wb-error-' + tileId,
                onSuccess: (blob, filename) => { addResultRow(tileId, blob, filename); resolve(); },
                onError: () => resolve(), // utils.js already rendered the error into wb-error-<id>
                onBackground: () => resolve(),
            };
            // Only force async mode on the /async/ endpoints; the sync twins
            // answer 200-with-body and would never produce a task_id.
            if (useAsync) options.useAsync = true;
            window.submitAsyncConversion(options).catch(() => resolve());
        });
    }

    async function runTile(tileId, fileList) {
        if (runningTileId) {
            tileError(tileId, I18N.busy || 'Another tile is still converting. Please wait.');
            return;
        }
        if (typeof window.hideError === 'function') window.hideError('wb-error-' + tileId);
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

        runningTileId = tileId;
        markRunning(tileId, true);
        try {
            // Heavy tools and every batch go to the /async/ twin, like
            // converter.js does — the sync route races Cloudflare's 100s edge
            // timeout and pins a gunicorn worker for the whole conversion.
            if (accepted.length > 1 && tool.batchApiUrl && LIMITS.tier === 'premium') {
                const fd = new FormData();
                accepted.forEach(f => fd.append(tool.batchFieldName, f));
                appendParams(fd);
                await submitOne(tileId, tool.batchAsyncApiUrl || tool.batchApiUrl, fd, accepted[0].name, !!tool.batchAsyncApiUrl);
            } else {
                for (const file of accepted) {
                    const fd = new FormData();
                    fd.append(tool.fileInputName, file);
                    appendParams(fd);
                    await submitOne(tileId, tool.asyncApiUrl || tool.apiUrl, fd, file.name, !!tool.asyncApiUrl);
                }
            }
        } finally {
            markRunning(tileId, false);
            runningTileId = null;
        }
    }

    // ─── Render ─────────────────────────────────────────────────────────
    const CATALOG = readJson('workbench-catalog', {});
    const LIMITS = readJson('workbench-limits', { tier: 'anonymous', boards: 1, tiles: 3 });
    const I18N = readJson('workbench-i18n', {});
    const state = ensureBoard(loadState(), I18N.boardName || 'My board');
    let presets = loadPresets();
    let onTileFiles = runTile;

    /**
     * Presets saved before workflow-presets.js wrote `toolKey` only have a
     * `toolUrl` — resolve it once and persist, so they show up on the board.
     */
    function backfillToolKeys() {
        let changed = false;
        presets.forEach(preset => {
            if (preset.toolKey && CATALOG[preset.toolKey]) return;
            const key = resolveToolKey(preset, CATALOG);
            if (key && key !== preset.toolKey) { preset.toolKey = key; changed = true; }
        });
        if (changed) savePresets(presets);
    }

    backfillToolKeys();

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

        // Reuse tile nodes: a re-render (resize, reorder, add) must not wipe the
        // loader/result slots of a tile that is mid-conversion.
        const stale = new Map();
        Array.from(grid.children).forEach(node => stale.set(node.dataset.tileId, node));
        const nodes = resolved.map((item, index) => {
            const node = stale.get(item.tile.id);
            if (!node) return renderTile(item, index, resolved.length);
            stale.delete(item.tile.id);
            updateTile(node, item, index, resolved.length);
            return node;
        });
        stale.forEach((node, tileId) => { clearResults(tileId); node.remove(); });
        nodes.forEach(node => grid.appendChild(node)); // appending an attached node moves it
        empty.hidden = resolved.length > 0;
        renderPickerList();
    }

    /** Everything on a tile node that can change between renders. */
    function updateTile(node, { tile, preset, tool }, index, count) {
        node.classList.remove('md:col-span-2', 'md:row-span-2');
        const sizeClass = SIZE_CLASS[tile.size] || '';
        if (sizeClass) node.classList.add(...sizeClass.split(' '));
        node.querySelector('.wb-tile-icon').textContent = GROUP_ICON[tool.group] || 'CV';
        node.querySelector('.wb-tile-title').textContent = preset.name;
        // A quick-added preset is named after the tool — repeating the label as
        // the subtitle is noise, show the tool's group instead.
        const groups = I18N.groups || {};
        node.querySelector('.wb-tile-subtitle').textContent =
            preset.name === tool.label ? (groups[tool.group] || tool.group) : tool.label;
        buildMenu(node, tile, preset, tool, index, count);
    }

    function renderTile(item, index, count) {
        const { tile, tool } = item;
        const node = $('wb-tile-template').content.firstElementChild.cloneNode(true);
        node.dataset.tileId = tile.id;
        node.querySelector('.wb-drop-text').textContent = I18N.dropHere || 'Drop files here';
        node.querySelector('.wb-loading').id = 'wb-loading-' + tile.id;
        node.querySelector('.wb-error').id = 'wb-error-' + tile.id;
        const resultsEl = node.querySelector('.wb-results');
        resultsEl.id = 'wb-result-' + tile.id;
        renderResults(tile.id, resultsEl); // node isn't attached yet, pass it directly

        const input = node.querySelector('.wb-file');
        input.accept = tool.fileAccept || '';
        input.multiple = true;
        input.addEventListener('change', () => { if (input.files.length) onTileFiles(tile.id, input.files); input.value = ''; });

        const drop = node.querySelector('.wb-drop');
        const unhighlight = () => drop.classList.remove('border-amber-500', 'bg-amber-50');
        ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('border-amber-500', 'bg-amber-50'); }));
        // Moving over a child fires dragleave on the drop zone — only a real exit counts.
        drop.addEventListener('dragleave', e => { if (!drop.contains(e.relatedTarget)) unhighlight(); });
        drop.addEventListener('drop', e => { e.preventDefault(); unhighlight(); if (e.dataTransfer.files.length) onTileFiles(tile.id, e.dataTransfer.files); });
        node.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target === node) input.click(); });

        updateTile(node, item, index, count);
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
            item(I18N.configure || 'Configure', () => { location.href = tool.pageUrl + '#wfp=' + encodeParams(preset.params) + '&wfid=' + encodeURIComponent(preset.id); }),
            sizeRow,
            item(I18N.moveLeft || 'Move left', () => { board.tiles = reorder(board.tiles, index, index - 1); persist(); render(); }, index === 0),
            item(I18N.moveRight || 'Move right', () => { board.tiles = reorder(board.tiles, index, index + 1); persist(); render(); }, index === count - 1),
            item(I18N.remove || 'Remove', () => { clearResults(tile.id); removeTile(board, tile.id); persist(); render(); }),
        );
        menu.lastElementChild.classList.add('text-red-600');
        // Assigned, not addEventListener'd: buildMenu re-runs on every render.
        btn.onclick = e => {
            e.stopPropagation();
            document.querySelectorAll('.wb-tile-menu').forEach(m => {
                if (m !== menu) { m.classList.add('hidden'); const b = m.previousElementSibling; if (b) b.setAttribute('aria-expanded', 'false'); }
            });
            const open = menu.classList.toggle('hidden') === false;
            btn.setAttribute('aria-expanded', String(open));
            if (open) closePicker();
        };
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
                const checked = !!existing && onBoard.has(existing.id);
                // A blind quick-add would 400 on the first drop — send the user to
                // the tool page to configure it, unless they already have a
                // configured preset for it (that one gets its own row above).
                const needsSetup = !checked && t.requiresConfig
                    && !presets.some(p => p.toolKey === key && p.params && Object.keys(p.params).length);
                rows.push({ group: I18N.converters || 'Converters', label: t.label, sub: needsSetup ? (I18N.needsSetup || 'Set up on tool page') : t.group, checked, toolKey: key, presetId: existing && existing.id, pageUrl: t.pageUrl, needsSetup, locked: t.premiumOnly && LIMITS.tier !== 'premium' });
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
            const box = row.needsSetup
                ? el('span', 'w-4 h-4 flex items-center justify-center text-gray-400', '↗')
                : el('span', 'w-4 h-4 rounded border flex items-center justify-center text-[10px] ' + (row.checked ? 'bg-amber-600 border-amber-600 text-white' : 'border-gray-300'), row.checked ? '✓' : '');
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
        if (row.needsSetup) { location.href = row.pageUrl + '#wfsetup=1'; return; }
        const board = activeBoard(state);
        if (row.checked) {
            board.tiles.forEach(t => { if (t.presetId === row.presetId) clearResults(t.id); });
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
        window.addEventListener('convertica:workflows-synced', () => { presets = loadPresets(); backfillToolKeys(); render(); });
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
        assert(resolveToolKey({ toolKey: 'pdf_to_word' }, catalog) === 'pdf_to_word', 'resolveToolKey by key');
        assert(resolveToolKey({ toolUrl: '/de/x/' }, catalog) === 'pdf_to_word', 'resolveToolKey by localized url');
        assert(resolveToolKey({ toolKey: 'gone', toolUrl: '/nope/' }, catalog) === '', 'resolveToolKey gives up');
        console.info('workbench selftest: OK');
    }

    window.Workbench = {
        uid, readJson, loadState, saveState, loadPresets, savePresets, ensureBoard, activeBoard,
        canAddTile, addTile, removeTile, reorder, resolveTiles, presetFromTool, encodeParams, acceptsFile,
        resolveToolKey, selfTest,
        render, openPicker, closePicker,
    };

    if (new URLSearchParams(location.search).get('selftest') === '1') selfTest();
})();

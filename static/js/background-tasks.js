/**
 * Background Tasks Manager (Premium feature)
 *
 * Persists running Celery tasks in localStorage so premium users can
 * navigate between pages while conversions continue on the server.
 *
 * Loaded globally in base.html for premium users only.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'convertica_bg_tasks';
    const POLL_INTERVAL = 5000;   // poll every 5 s
    const MAX_AGE_MS = 50 * 60 * 1000; // auto-remove tasks older than 50 min (files live 1 h)
    const TOAST_DURATION = 15000; // auto-hide toast after 15 s

    let pollTimer = null;

    // ─── localStorage helpers ───────────────────────────────────────────

    function getTasks() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch (_) {
            return [];
        }
    }

    function saveTasks(tasks) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
    }

    function resolveTaskToken(taskId, explicitToken = null) {
        if (explicitToken) return explicitToken;
        if (window.getTaskToken) {
            const mappedToken = window.getTaskToken(taskId);
            if (mappedToken) return mappedToken;
        }
        const task = getTasks().find((t) => t.taskId === taskId);
        return task?.taskToken || null;
    }

    // ─── Public API (exposed on window) ─────────────────────────────────

    /**
     * Add a task to background tracking.
     * Called when premium user clicks "Continue in background".
     */
    function addBackgroundTask(taskId, conversionType, originalFilename, taskToken = null) {
        if (!taskId) return;
        const tasks = getTasks();
        // Avoid duplicates
        if (tasks.some(t => t.taskId === taskId)) return;

        tasks.push({
            taskId: taskId,
            conversionType: conversionType || '',
            originalFilename: originalFilename || '',
            outputFilename: '',
            taskToken: resolveTaskToken(taskId, taskToken) || '',
            startedAt: Date.now(),
            status: 'processing', // processing | success | error
            error: '',
            notified: false,
        });
        saveTasks(tasks);

        // Mark in task-cancellation so it won't be killed
        if (window.markTaskAsBackground) {
            window.markTaskAsBackground(taskId);
        }

        showToast(
            window.BG_TASK_SENT_TEXT || 'Task running in background',
            originalFilename,
            'info'
        );

        renderIndicator();
        ensurePolling();
    }

    /**
     * Remove a task (after download or manual dismiss).
     */
    function removeBackgroundTask(taskId) {
        const tasks = getTasks().filter(t => t.taskId !== taskId);
        saveTasks(tasks);
        renderIndicator();
        if (tasks.filter(t => t.status === 'processing').length === 0) {
            stopPolling();
        }
    }

    /**
     * Get all background tasks (for external consumers).
     */
    function getBackgroundTasks() {
        return getTasks();
    }

    // ─── Polling ────────────────────────────────────────────────────────

    function ensurePolling() {
        if (pollTimer) return;
        pollTimer = setInterval(pollAll, POLL_INTERVAL);
        // Also poll immediately
        pollAll();
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    async function pollAll() {
        let tasks = getTasks();
        let changed = false;

        // Remove stale tasks
        const now = Date.now();
        const before = tasks.length;
        tasks = tasks.filter(t => now - t.startedAt < MAX_AGE_MS || t.status === 'success');
        if (tasks.length !== before) changed = true;

        const processing = tasks.filter(t => t.status === 'processing');
        if (processing.length === 0) {
            if (changed) saveTasks(tasks);
            renderIndicator();
            stopPolling();
            return;
        }

        for (const task of processing) {
            try {
                const statusHeaders = {};
                const taskToken = resolveTaskToken(task.taskId, task.taskToken);
                if (taskToken) {
                    statusHeaders['X-Task-Token'] = taskToken;
                    if (task.taskToken !== taskToken) {
                        task.taskToken = taskToken;
                        changed = true;
                    }
                }
                const resp = await fetch(`/api/tasks/${task.taskId}/status/`, {
                    headers: statusHeaders,
                });
                if (!resp.ok) continue;
                const data = await resp.json();

                if (data.status === 'SUCCESS') {
                    task.status = 'success';
                    task.outputFilename = data.output_filename || task.originalFilename;
                    changed = true;

                    if (!task.notified) {
                        task.notified = true;
                        showToast(
                            window.BG_TASK_DONE_TEXT || 'File is ready!',
                            task.outputFilename,
                            'success',
                            task.taskId
                        );
                    }
                } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
                    task.status = 'error';
                    task.error = data.error || 'Conversion failed';
                    changed = true;

                    if (!task.notified) {
                        task.notified = true;
                        showToast(
                            window.BG_TASK_ERROR_TEXT || 'Conversion failed',
                            task.error,
                            'error'
                        );
                    }
                }
                // PENDING / PROGRESS / STARTED — keep polling
            } catch (_) {
                // Network error — retry next cycle
            }
        }

        if (changed) saveTasks(tasks);
        renderIndicator();
    }

    // ─── Toast Notifications ────────────────────────────────────────────

    function getOrCreateToastContainer() {
        let container = document.getElementById('bgTaskToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'bgTaskToastContainer';
            container.className = 'fixed top-20 right-4 z-[100] flex flex-col gap-3 max-w-sm';
            container.style.pointerEvents = 'none';
            document.body.appendChild(container);
        }
        return container;
    }

    function showToast(title, message, type, taskId) {
        const container = getOrCreateToastContainer();

        const colors = {
            success: 'bg-green-50 dark:bg-green-900/40 border-green-300 dark:border-green-700',
            error:   'bg-red-50 dark:bg-red-900/40 border-red-300 dark:border-red-700',
            info:    'bg-blue-50 dark:bg-blue-900/40 border-blue-300 dark:border-blue-700',
        };
        const iconColors = {
            success: 'text-green-600 dark:text-green-400',
            error:   'text-red-600 dark:text-red-400',
            info:    'text-blue-600 dark:text-blue-400',
        };
        const icons = {
            success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>',
            error:   '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>',
            info:    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
        };

        const downloadBtnHtml = (type === 'success' && taskId)
            ? `<button data-bg-download="${taskId}" class="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-green-700 dark:text-green-300 hover:underline" style="pointer-events:auto">
                 <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                 ${window.DOWNLOAD_BUTTON_TEXT || 'Download'}
               </button>`
            : '';

        const toast = document.createElement('div');
        toast.className = `${colors[type] || colors.info} border rounded-xl p-4 shadow-lg animate-fade-in`;
        toast.style.pointerEvents = 'auto';
        toast.innerHTML = `
            <div class="flex items-start gap-3">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5 ${iconColors[type] || iconColors.info}" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icons[type] || icons.info}</svg>
                <div class="flex-1 min-w-0">
                    <p class="font-semibold text-sm text-gray-900 dark:text-gray-100">${escapeForHtml(title)}</p>
                    <p class="text-xs text-gray-600 dark:text-gray-300 truncate">${escapeForHtml(message)}</p>
                    ${downloadBtnHtml}
                </div>
                <button class="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors" data-toast-close>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
        `;

        container.appendChild(toast);

        // Close button
        toast.querySelector('[data-toast-close]').addEventListener('click', () => toast.remove());

        // Download button
        const dlBtn = toast.querySelector('[data-bg-download]');
        if (dlBtn) {
            dlBtn.addEventListener('click', () => downloadBackgroundResult(dlBtn.dataset.bgDownload));
        }

        // Auto-hide
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }
        }, TOAST_DURATION);
    }

    function escapeForHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // ─── Header Indicator + Dropdown ────────────────────────────────────

    function renderIndicator() {
        const badge = document.getElementById('bgTasksBadge');
        const indicator = document.getElementById('bgTasksIndicator');
        const dropdown = document.getElementById('bgTasksDropdown');
        if (!indicator) return;

        const tasks = getTasks();
        const activeTasks = tasks.filter(t => t.status === 'processing');
        const completedTasks = tasks.filter(t => t.status === 'success');
        const errorTasks = tasks.filter(t => t.status === 'error');
        const total = tasks.length;

        if (total === 0) {
            indicator.classList.add('hidden');
            if (dropdown) dropdown.classList.add('hidden');
            return;
        }

        indicator.classList.remove('hidden');

        // Badge count
        if (badge) {
            if (activeTasks.length > 0) {
                badge.textContent = activeTasks.length;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }

        // Render dropdown content
        if (!dropdown) return;
        const listEl = dropdown.querySelector('#bgTasksList');
        if (!listEl) return;

        if (total === 0) {
            listEl.innerHTML = `<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">${window.BG_NO_TASKS_TEXT || 'No background tasks'}</p>`;
            return;
        }

        let html = '';
        for (const task of tasks) {
            const name = escapeForHtml(task.outputFilename || task.originalFilename || 'File');
            if (task.status === 'processing') {
                html += `
                    <div class="flex items-center gap-3 py-2 px-1">
                        <div class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
                        <span class="text-sm text-gray-700 dark:text-gray-300 truncate flex-1">${name}</span>
                    </div>`;
            } else if (task.status === 'success') {
                html += `
                    <div class="flex items-center gap-3 py-2 px-1">
                        <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                        <span class="text-sm text-gray-700 dark:text-gray-300 truncate flex-1">${name}</span>
                        <button data-bg-download="${task.taskId}" class="text-xs font-semibold text-green-600 dark:text-green-400 hover:underline flex-shrink-0">${window.DOWNLOAD_BUTTON_TEXT || 'Download'}</button>
                        <button data-bg-remove="${task.taskId}" class="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>`;
            } else if (task.status === 'error') {
                html += `
                    <div class="flex items-center gap-3 py-2 px-1">
                        <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        <span class="text-sm text-red-600 dark:text-red-400 truncate flex-1" title="${escapeForHtml(task.error)}">${name}</span>
                        <button data-bg-remove="${task.taskId}" class="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>`;
            }
        }

        listEl.innerHTML = html;

        // Wire up buttons
        listEl.querySelectorAll('[data-bg-download]').forEach(btn => {
            btn.addEventListener('click', () => downloadBackgroundResult(btn.dataset.bgDownload));
        });
        listEl.querySelectorAll('[data-bg-remove]').forEach(btn => {
            btn.addEventListener('click', () => {
                removeBackgroundTask(btn.dataset.bgRemove);
                // Also cleanup server files
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                    || document.querySelector('meta[name="csrf-token"]')?.content || '';
                const cleanupHeaders = { 'X-CSRFToken': csrfToken };
                const taskToken = resolveTaskToken(btn.dataset.bgRemove);
                if (taskToken) {
                    cleanupHeaders['X-Task-Token'] = taskToken;
                }
                fetch(`/api/tasks/${btn.dataset.bgRemove}/result/`, {
                    method: 'DELETE',
                    headers: cleanupHeaders,
                }).catch(() => {});
            });
        });
    }

    // ─── Download result for a background task ──────────────────────────

    async function downloadBackgroundResult(taskId) {
        if (!taskId) return;

        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || document.querySelector('meta[name="csrf-token"]')?.content || '';
            const taskToken = resolveTaskToken(taskId);
            const resultHeaders = { 'X-CSRFToken': csrfToken };
            if (taskToken) {
                resultHeaders['X-Task-Token'] = taskToken;
            }

            const resp = await fetch(`/api/tasks/${taskId}/result/`, {
                headers: resultHeaders,
            });

            if (!resp.ok) {
                showToast(window.BG_TASK_ERROR_TEXT || 'Download failed', 'File may have expired', 'error');
                removeBackgroundTask(taskId);
                return;
            }

            const blob = await resp.blob();
            const contentDisposition = resp.headers.get('content-disposition');
            let filename = 'convertica_file';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) filename = match[1].replace(/['"]/g, '');
            }

            // Trigger browser download
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 60000);

            // Cleanup
            removeBackgroundTask(taskId);
            const cleanupHeaders = { 'X-CSRFToken': csrfToken };
            if (taskToken) {
                cleanupHeaders['X-Task-Token'] = taskToken;
            }
            fetch(`/api/tasks/${taskId}/result/`, {
                method: 'DELETE',
                headers: cleanupHeaders,
            }).catch(() => {});

        } catch (err) {
            showToast(window.BG_TASK_ERROR_TEXT || 'Download failed', err.message || '', 'error');
        }
    }

    // ─── Dropdown toggle (header indicator) ─────────────────────────────

    function setupDropdownToggle() {
        const indicator = document.getElementById('bgTasksIndicator');
        const dropdown = document.getElementById('bgTasksDropdown');
        if (!indicator || !dropdown) return;

        indicator.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = dropdown.classList.contains('hidden');
            if (isHidden) {
                dropdown.classList.remove('hidden');
                renderIndicator(); // refresh content
            } else {
                dropdown.classList.add('hidden');
            }
        });

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && !indicator.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });
    }

    // ─── Init ───────────────────────────────────────────────────────────

    function init() {
        setupDropdownToggle();
        renderIndicator();

        // Start polling if there are active tasks
        const tasks = getTasks();
        if (tasks.some(t => t.status === 'processing')) {
            ensurePolling();
        }
    }

    // Run init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ─── Expose public API ──────────────────────────────────────────────
    window.addBackgroundTask = addBackgroundTask;
    window.removeBackgroundTask = removeBackgroundTask;
    window.getBackgroundTasks = getBackgroundTasks;

})();

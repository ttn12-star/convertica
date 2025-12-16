/**
 * Automatic task cancellation when user leaves the page
 *
 * Monitors page visibility and cancels running Celery tasks when user:
 * - Closes the page/tab
 * - Navigates away
 * - Switches to another tab for extended period
 *
 * This frees up the conversion queue for other users.
 */

(function() {
    'use strict';

    // Track active task IDs
    let activeTasks = new Set();
    let visibilityTimer = null;
    const VISIBILITY_TIMEOUT = 60000; // Cancel after 60 seconds of inactivity

    /**
     * Register a task for automatic cancellation
     * @param {string} taskId - Celery task ID
     */
    window.registerTaskForCancellation = function(taskId) {
        if (taskId) {
            activeTasks.add(taskId);
            console.log(`[Task Cancel] Registered task: ${taskId}`);
        }
    };

    /**
     * Unregister a task (completed or manually cancelled)
     * @param {string} taskId - Celery task ID
     */
    window.unregisterTaskForCancellation = function(taskId) {
        if (taskId) {
            activeTasks.delete(taskId);
            console.log(`[Task Cancel] Unregistered task: ${taskId}`);
        }
    };

    /**
     * Cancel a specific task via API
     * @param {string} taskId - Celery task ID
     * @returns {Promise}
     */
    async function cancelTask(taskId) {
        try {
            const response = await fetch('/api/cancel-task/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ task_id: taskId }),
            });

            const data = await response.json();

            if (response.ok) {
                console.log(`[Task Cancel] Cancelled task: ${taskId}`, data);
                return true;
            } else {
                console.warn(`[Task Cancel] Failed to cancel task: ${taskId}`, data);
                return false;
            }
        } catch (error) {
            console.error(`[Task Cancel] Error cancelling task: ${taskId}`, error);
            return false;
        }
    }

    /**
     * Cancel all active tasks
     */
    async function cancelAllTasks() {
        if (activeTasks.size === 0) return;

        console.log(`[Task Cancel] Cancelling ${activeTasks.size} active task(s)`);

        const promises = Array.from(activeTasks).map(taskId => cancelTask(taskId));
        await Promise.all(promises);

        activeTasks.clear();
    }

    /**
     * Handle page unload (user navigating away or closing tab)
     */
    function handleBeforeUnload() {
        // Use sendBeacon for reliable delivery even when page is closing
        if (activeTasks.size > 0 && navigator.sendBeacon) {
            const tasks = Array.from(activeTasks);
            tasks.forEach(taskId => {
                const blob = new Blob(
                    [JSON.stringify({ task_id: taskId })],
                    { type: 'application/json' }
                );
                navigator.sendBeacon('/api/cancel-task/', blob);
            });
            console.log(`[Task Cancel] Sent cancellation beacons for ${tasks.length} task(s)`);
        }
    }

    /**
     * Handle visibility change (tab hidden/shown)
     */
    function handleVisibilityChange() {
        if (document.hidden) {
            // Page hidden - start timer to cancel tasks if hidden too long
            visibilityTimer = setTimeout(() => {
                console.log('[Task Cancel] Page hidden for too long, cancelling tasks');
                cancelAllTasks();
            }, VISIBILITY_TIMEOUT);
        } else {
            // Page visible again - cancel the timer
            if (visibilityTimer) {
                clearTimeout(visibilityTimer);
                visibilityTimer = null;
            }
        }
    }

    /**
     * Handle page focus loss (for older browsers without visibilitychange)
     */
    function handleBlur() {
        if (!('hidden' in document)) {
            // Fallback for browsers without Page Visibility API
            visibilityTimer = setTimeout(() => {
                cancelAllTasks();
            }, VISIBILITY_TIMEOUT);
        }
    }

    function handleFocus() {
        if (visibilityTimer) {
            clearTimeout(visibilityTimer);
            visibilityTimer = null;
        }
    }

    // Register event listeners
    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('pagehide', handleBeforeUnload); // For mobile Safari
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);

    console.log('[Task Cancel] Task cancellation system initialized');

    // Cleanup on script unload
    window.addEventListener('unload', () => {
        if (visibilityTimer) {
            clearTimeout(visibilityTimer);
        }
    });
})();

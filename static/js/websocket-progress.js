/**
 * WebSocket Progress Client
 * Provides real-time progress updates for file conversions via WebSocket.
 */

class ConversionProgressClient {
    constructor(taskId, options = {}) {
        this.taskId = taskId;
        this.options = {
            onProgress: options.onProgress || this.defaultOnProgress,
            onCompleted: options.onCompleted || this.defaultOnCompleted,
            onError: options.onError || this.defaultOnError,
            onConnected: options.onConnected || this.defaultOnConnected,
            onDisconnected: options.onDisconnected || this.defaultOnDisconnected,
            reconnectAttempts: options.reconnectAttempts || 3,
            reconnectDelay: options.reconnectDelay || 2000,
            pingInterval: options.pingInterval || 30000, // 30 seconds
        };

        this.ws = null;
        this.reconnectCount = 0;
        this.pingTimer = null;
        this.isConnected = false;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/conversion/${this.taskId}/`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = (event) => this.handleOpen(event);
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (event) => this.handleError(event);
            this.ws.onclose = (event) => this.handleClose(event);

        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.options.onError({
                type: 'connection_error',
                message: 'Failed to establish WebSocket connection',
                error: error.message
            });
        }
    }

    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectCount = 0;

        // Start ping timer to keep connection alive
        this.startPingTimer();

        this.options.onConnected({
            taskId: this.taskId,
            timestamp: new Date().toISOString()
        });
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);

            switch (data.type) {
                case 'connected':
                    // Initial connection confirmation
                    break;

                case 'progress':
                    this.options.onProgress({
                        progress: data.progress,
                        message: data.message,
                        status: data.status,
                        taskId: data.task_id
                    });
                    break;

                case 'completed':
                    this.options.onCompleted({
                        downloadUrl: data.download_url,
                        filename: data.filename,
                        fileSize: data.file_size,
                        message: data.message,
                        taskId: data.task_id
                    });
                    this.disconnect();
                    break;

                case 'error':
                    this.options.onError({
                        type: 'conversion_error',
                        message: data.message,
                        error: data.error,
                        taskId: data.task_id
                    });
                    this.disconnect();
                    break;

                case 'pong':
                    // Pong response to ping
                    break;

                default:
                    console.warn('Unknown message type:', data.type);
            }

        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket error
     */
    handleError(event) {
        console.error('WebSocket error:', event);
        this.isConnected = false;

        this.options.onError({
            type: 'websocket_error',
            message: 'WebSocket connection error',
            event: event
        });
    }

    /**
     * Handle WebSocket close
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this.isConnected = false;
        this.stopPingTimer();

        this.options.onDisconnected({
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });

        // Attempt reconnection if not a clean close
        if (!event.wasClean && this.reconnectCount < this.options.reconnectAttempts) {
            this.reconnectCount++;
            console.log(`Reconnecting... Attempt ${this.reconnectCount}/${this.options.reconnectAttempts}`);

            setTimeout(() => {
                this.connect();
            }, this.options.reconnectDelay);
        }
    }

    /**
     * Start ping timer to keep connection alive
     */
    startPingTimer() {
        this.pingTimer = setInterval(() => {
            if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
                this.send({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, this.options.pingInterval);
    }

    /**
     * Stop ping timer
     */
    stopPingTimer() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    /**
     * Send message to WebSocket server
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket is not open. Cannot send message.');
        }
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        this.stopPingTimer();

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.isConnected = false;
    }

    /**
     * Default callbacks
     */
    defaultOnProgress(data) {
        console.log('Progress:', data.progress + '%', data.message);
    }

    defaultOnCompleted(data) {
        console.log('Completed:', data.filename);
    }

    defaultOnError(data) {
        console.error('Error:', data.message);
    }

    defaultOnConnected(data) {
        console.log('Connected:', data.taskId);
    }

    defaultOnDisconnected(data) {
        console.log('Disconnected:', data.code, data.reason);
    }
}


/**
 * Batch Conversion Progress Client
 */
class BatchConversionProgressClient {
    constructor(batchId, options = {}) {
        this.batchId = batchId;
        this.options = {
            onProgress: options.onProgress || this.defaultOnProgress,
            onFileCompleted: options.onFileCompleted || this.defaultOnFileCompleted,
            onCompleted: options.onCompleted || this.defaultOnCompleted,
            onError: options.onError || this.defaultOnError,
            onConnected: options.onConnected || this.defaultOnConnected,
            onDisconnected: options.onDisconnected || this.defaultOnDisconnected,
            reconnectAttempts: options.reconnectAttempts || 3,
            reconnectDelay: options.reconnectDelay || 2000,
            pingInterval: options.pingInterval || 30000,
        };

        this.ws = null;
        this.reconnectCount = 0;
        this.pingTimer = null;
        this.isConnected = false;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/batch/${this.batchId}/`;

        console.log(`Connecting to Batch WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = (event) => this.handleOpen(event);
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (event) => this.handleError(event);
            this.ws.onclose = (event) => this.handleClose(event);

        } catch (error) {
            console.error('Batch WebSocket connection error:', error);
            this.options.onError({
                type: 'connection_error',
                message: 'Failed to establish WebSocket connection',
                error: error.message
            });
        }
    }

    handleOpen(event) {
        console.log('Batch WebSocket connected');
        this.isConnected = true;
        this.reconnectCount = 0;
        this.startPingTimer();

        this.options.onConnected({
            batchId: this.batchId,
            timestamp: new Date().toISOString()
        });
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Batch WebSocket message:', data);

            switch (data.type) {
                case 'connected':
                    break;

                case 'batch_progress':
                    this.options.onProgress({
                        totalFiles: data.total_files,
                        completedFiles: data.completed_files,
                        currentFile: data.current_file,
                        progress: data.progress,
                        message: data.message,
                        status: data.status,
                        batchId: data.batch_id
                    });
                    break;

                case 'file_completed':
                    this.options.onFileCompleted({
                        filename: data.filename,
                        fileIndex: data.file_index,
                        message: data.message,
                        batchId: data.batch_id
                    });
                    break;

                case 'batch_completed':
                    this.options.onCompleted({
                        downloadUrl: data.download_url,
                        totalFiles: data.total_files,
                        successfulFiles: data.successful_files,
                        failedFiles: data.failed_files,
                        message: data.message,
                        batchId: data.batch_id
                    });
                    this.disconnect();
                    break;

                case 'batch_error':
                    this.options.onError({
                        type: 'batch_error',
                        message: data.message,
                        error: data.error,
                        batchId: data.batch_id
                    });
                    this.disconnect();
                    break;

                case 'pong':
                    break;

                default:
                    console.warn('Unknown batch message type:', data.type);
            }

        } catch (error) {
            console.error('Error parsing batch WebSocket message:', error);
        }
    }

    handleError(event) {
        console.error('Batch WebSocket error:', event);
        this.isConnected = false;

        this.options.onError({
            type: 'websocket_error',
            message: 'WebSocket connection error',
            event: event
        });
    }

    handleClose(event) {
        console.log('Batch WebSocket closed:', event.code, event.reason);
        this.isConnected = false;
        this.stopPingTimer();

        this.options.onDisconnected({
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });

        if (!event.wasClean && this.reconnectCount < this.options.reconnectAttempts) {
            this.reconnectCount++;
            console.log(`Reconnecting batch... Attempt ${this.reconnectCount}/${this.options.reconnectAttempts}`);

            setTimeout(() => {
                this.connect();
            }, this.options.reconnectDelay);
        }
    }

    startPingTimer() {
        this.pingTimer = setInterval(() => {
            if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
                this.send({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, this.options.pingInterval);
    }

    stopPingTimer() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    disconnect() {
        this.stopPingTimer();

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.isConnected = false;
    }

    defaultOnProgress(data) {
        console.log(`Batch Progress: ${data.completedFiles}/${data.totalFiles} (${data.progress}%)`, data.message);
    }

    defaultOnFileCompleted(data) {
        console.log('File completed:', data.filename);
    }

    defaultOnCompleted(data) {
        console.log(`Batch completed: ${data.successfulFiles}/${data.totalFiles} successful`);
    }

    defaultOnError(data) {
        console.error('Batch error:', data.message);
    }

    defaultOnConnected(data) {
        console.log('Batch connected:', data.batchId);
    }

    defaultOnDisconnected(data) {
        console.log('Batch disconnected:', data.code, data.reason);
    }
}


// Export for use in other modules
if (typeof window !== 'undefined') {
    window.ConversionProgressClient = ConversionProgressClient;
    window.BatchConversionProgressClient = BatchConversionProgressClient;
}

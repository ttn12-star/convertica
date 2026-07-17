/**
 * Cloud Import — "Google Drive" / "Dropbox" buttons in the upload area.
 *
 * Purely client-side: the picked file is downloaded in the browser and
 * injected into #fileInput, so the existing validation/submit path is
 * reused unchanged and no OAuth tokens ever reach our server.
 *
 * SDKs (Google GIS + Picker, Dropbox Chooser) are lazy-loaded on first
 * use (warmed up on pointerenter) to keep tool pages at zero extra weight.
 */
document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('cloudImport');
    const fileInput = document.getElementById('fileInput');
    if (!root || !fileInput) return;

    const cfg = root.dataset;
    const driveBtn = document.getElementById('googleDriveImport');
    const dropboxBtn = document.getElementById('dropboxImport');
    const allowMultiple = fileInput.hasAttribute('multiple');
    const MAX_FILES = 10; // matches batch backend limit in file-input-handler.js

    function fail(message) {
        if (typeof window.showError === 'function') {
            window.showError(message, 'converterResult');
        } else {
            alert(message);
        }
    }

    function setBusy(btn, busy) {
        btn.disabled = busy;
        btn.classList.toggle('opacity-60', busy);
        btn.classList.toggle('pointer-events-none', busy);
        btn.setAttribute('aria-busy', busy ? 'true' : 'false');
    }

    function injectFiles(files) {
        if (!files.length || typeof DataTransfer === 'undefined') return;
        const dt = new DataTransfer();
        files.slice(0, MAX_FILES).forEach((f) => dt.items.add(f));
        fileInput.files = dt.files;
        // The change handler in file-input-handler.js takes over from here
        // (merge, preview, fileSelected event, validation in converter.js).
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function loadScript(src, attrs) {
        return new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) {
                if (existing.dataset.loaded) return resolve();
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
                return;
            }
            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            Object.entries(attrs || {}).forEach(([k, v]) => script.setAttribute(k, v));
            script.addEventListener('load', () => {
                script.dataset.loaded = '1';
                resolve();
            }, { once: true });
            script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
            document.head.appendChild(script);
        });
    }

    // ---------------------------------------------------------------- Google

    const GOOGLE_NATIVE_PREFIX = 'application/vnd.google-apps';
    let pickerLoaded = false;
    let tokenClient = null;
    let accessToken = '';
    let tokenExpiresAt = 0;

    async function ensureGoogleSdks() {
        await loadScript('https://accounts.google.com/gsi/client');
        await loadScript('https://apis.google.com/js/api.js');
        if (!pickerLoaded) {
            await new Promise((resolve, reject) => {
                window.gapi.load('picker', { callback: resolve, onerror: reject });
            });
            pickerLoaded = true;
        }
    }

    function getAccessToken() {
        return new Promise((resolve, reject) => {
            if (accessToken && Date.now() < tokenExpiresAt - 60000) {
                return resolve(accessToken);
            }
            if (!tokenClient) {
                tokenClient = window.google.accounts.oauth2.initTokenClient({
                    client_id: cfg.googleClientId,
                    scope: 'https://www.googleapis.com/auth/drive.file',
                    callback: () => {},
                });
            }
            tokenClient.callback = (resp) => {
                if (resp.error) return reject(new Error(resp.error));
                accessToken = resp.access_token;
                tokenExpiresAt = Date.now() + (resp.expires_in || 3600) * 1000;
                resolve(accessToken);
            };
            tokenClient.error_callback = (err) => {
                reject(new Error((err && err.type) || 'popup_failed'));
            };
            tokenClient.requestAccessToken();
        });
    }

    function showDrivePicker(token) {
        return new Promise((resolve) => {
            const picker = window.google.picker;
            const view = new picker.DocsView(picker.ViewId.DOCS).setIncludeFolders(false);
            let builder = new picker.PickerBuilder()
                .setDeveloperKey(cfg.googleApiKey)
                .setAppId(cfg.googleAppId)
                .setOAuthToken(token)
                .setLocale(document.documentElement.lang || 'en')
                .addView(view)
                .setCallback((data) => {
                    const action = data[picker.Response.ACTION];
                    if (action === picker.Action.PICKED) {
                        resolve(data[picker.Response.DOCUMENTS] || []);
                    } else if (action === picker.Action.CANCEL) {
                        resolve([]);
                    }
                });
            if (allowMultiple) {
                builder = builder.enableFeature(picker.Feature.MULTISELECT_ENABLED);
            }
            builder.build().setVisible(true);
        });
    }

    async function downloadDriveFile(doc, token) {
        const url = `https://www.googleapis.com/drive/v3/files/${doc.id}?alt=media&supportsAllDrives=true`;
        const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
        if (!resp.ok) {
            if (resp.status === 401) accessToken = '';
            throw new Error(`drive download ${resp.status}`);
        }
        const blob = await resp.blob();
        return new File([blob], doc.name, { type: doc.mimeType || blob.type });
    }

    if (driveBtn) {
        driveBtn.addEventListener('pointerenter', () => {
            ensureGoogleSdks().catch(() => {});
        }, { once: true });

        driveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            setBusy(driveBtn, true);
            try {
                await ensureGoogleSdks();
                const token = await getAccessToken();
                const docs = await showDrivePicker(token);
                const native = docs.filter((d) => (d.mimeType || '').startsWith(GOOGLE_NATIVE_PREFIX));
                const regular = docs.filter((d) => !(d.mimeType || '').startsWith(GOOGLE_NATIVE_PREFIX));
                if (native.length) fail(cfg.errorGdoc);
                if (regular.length) {
                    const files = await Promise.all(
                        regular.slice(0, MAX_FILES).map((d) => downloadDriveFile(d, token))
                    );
                    injectFiles(files);
                }
            } catch (err) {
                // Closed popup / declined consent is not an error worth a toast.
                if (!/popup_closed|access_denied|user_cancel/i.test(String(err && err.message))) {
                    fail(/download/.test(String(err && err.message)) ? cfg.errorDownload : cfg.errorLoad);
                }
            } finally {
                setBusy(driveBtn, false);
            }
        });
    }

    // --------------------------------------------------------------- Dropbox

    function ensureDropboxSdk() {
        return loadScript('https://www.dropbox.com/static/api/2/dropins.js', {
            id: 'dropboxjs',
            'data-app-key': cfg.dropboxAppKey,
        });
    }

    function chooserExtensions() {
        // Dropbox `extensions` accepts ['.pdf', ...]; pass it only when the
        // accept attr is a plain extension list (it may also hold MIME types).
        const accept = (fileInput.getAttribute('accept') || '')
            .split(',').map((s) => s.trim()).filter(Boolean);
        return accept.length && accept.every((a) => a.startsWith('.')) ? accept : null;
    }

    if (dropboxBtn) {
        dropboxBtn.addEventListener('pointerenter', () => {
            ensureDropboxSdk().catch(() => {});
        }, { once: true });

        dropboxBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            setBusy(dropboxBtn, true);
            try {
                await ensureDropboxSdk();
                const picked = await new Promise((resolve) => {
                    const options = {
                        linkType: 'direct',
                        multiselect: allowMultiple,
                        success: resolve,
                        cancel: () => resolve([]),
                    };
                    const extensions = chooserExtensions();
                    if (extensions) options.extensions = extensions;
                    window.Dropbox.choose(options);
                });
                if (picked.length) {
                    const files = await Promise.all(
                        picked.slice(0, MAX_FILES).map(async (item) => {
                            const resp = await fetch(item.link);
                            if (!resp.ok) throw new Error(`dropbox download ${resp.status}`);
                            const blob = await resp.blob();
                            return new File([blob], item.name, { type: blob.type });
                        })
                    );
                    injectFiles(files);
                }
            } catch (err) {
                fail(/download/.test(String(err && err.message)) ? cfg.errorDownload : cfg.errorLoad);
            } finally {
                setBusy(dropboxBtn, false);
            }
        });
    }
});

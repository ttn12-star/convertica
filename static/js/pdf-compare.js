/**
 * Compare two PDFs:
 * 1) Send files to API (returns an archive with report + images)
 * 2) Parse the archive in browser via JSZip
 * 3) Render page-by-page visual report on screen
 * 4) Let user export the same report package on demand
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('compareForm');
    if (!form) return;

    const compareButton = document.getElementById('compareButton');
    const thresholdInput = document.getElementById('diffThreshold');
    const thresholdValue = document.getElementById('diffThresholdValue');
    const fileInput1 = document.getElementById('pdfFile1');
    const fileInput2 = document.getElementById('pdfFile2');

    const previewContainer = document.getElementById('comparisonPreview');
    const downloadButton = document.getElementById('compareDownloadButton');
    const prevPageButton = document.getElementById('comparePrevButton');
    const nextPageButton = document.getElementById('compareNextButton');
    const pageIndicator = document.getElementById('comparePageIndicator');
    const pageList = document.getElementById('comparePageList');

    const summaryGeneratedAt = document.getElementById('compareSummaryGeneratedAt');
    const summaryPages = document.getElementById('compareSummaryPages');
    const summaryChange = document.getElementById('compareSummaryChange');
    const summaryWordsAdded = document.getElementById('compareSummaryWordsAdded');
    const summaryWordsRemoved = document.getElementById('compareSummaryWordsRemoved');

    const mainImage = document.getElementById('compareMainImage');
    const mainEmpty = document.getElementById('compareMainEmpty');
    const mainLoading = document.getElementById('compareMainLoading');
    const mainViewport = document.getElementById('compareMainViewport');
    const baseImage = document.getElementById('compareBaseImage');
    const updatedImage = document.getElementById('compareUpdatedImage');
    const pageMeta = document.getElementById('comparePageMeta');

    const viewButtons = Array.from(document.querySelectorAll('.compare-view-btn'));

    const state = {
        archiveBlob: null,
        archiveFilename: null,
        zip: null,
        report: null,
        pages: [],
        currentPageIndex: 0,
        activeView: 'diff',
        assetUrlCache: new Map(),
        renderToken: 0,
    };

    function setFormDisabled(disabled) {
        if (compareButton) {
            compareButton.disabled = disabled;
            compareButton.classList.toggle('opacity-50', disabled);
            compareButton.classList.toggle('cursor-not-allowed', disabled);
        }
        if (fileInput1) fileInput1.disabled = disabled;
        if (fileInput2) fileInput2.disabled = disabled;
        if (thresholdInput) thresholdInput.disabled = disabled;
    }

    function getDownloadFilename(response, fallback) {
        const disposition = response.headers.get('content-disposition') || '';
        const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
            return match[1].replace(/['"]/g, '');
        }
        return fallback;
    }

    function formatUtcDate(value) {
        if (!value) return '';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return '';
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
            timeZone: 'UTC',
        }).format(parsed);
    }

    function formatNumber(value) {
        return new Intl.NumberFormat().format(Number(value) || 0);
    }

    function formatPercent(value) {
        const numeric = Number(value) || 0;
        return `${numeric.toFixed(2)}%`;
    }

    function getStatusLabel(status) {
        if (status === 'present_in_both') {
            return window.COMPARE_STATUS_PRESENT || 'Compared';
        }
        if (status === 'added_in_second_pdf') {
            return window.COMPARE_STATUS_ADDED || 'Added in updated PDF';
        }
        if (status === 'missing_in_second_pdf') {
            return window.COMPARE_STATUS_MISSING || 'Missing in updated PDF';
        }
        return window.COMPARE_STATUS_UNKNOWN || 'Status unknown';
    }

    function getStatusClasses(status) {
        if (status === 'present_in_both') {
            return {
                badge: 'bg-blue-100 text-blue-800',
                row: 'hover:bg-blue-50/60',
            };
        }
        if (status === 'added_in_second_pdf') {
            return {
                badge: 'bg-emerald-100 text-emerald-800',
                row: 'hover:bg-emerald-50/60',
            };
        }
        if (status === 'missing_in_second_pdf') {
            return {
                badge: 'bg-rose-100 text-rose-800',
                row: 'hover:bg-rose-50/60',
            };
        }
        return {
            badge: 'bg-gray-100 text-gray-700',
            row: 'hover:bg-gray-50',
        };
    }

    function revokeAssetUrls() {
        state.assetUrlCache.forEach((url) => {
            try {
                URL.revokeObjectURL(url);
            } catch (_) {
                // Ignore revoke errors
            }
        });
        state.assetUrlCache.clear();
    }

    function resetPreview() {
        state.archiveBlob = null;
        state.archiveFilename = null;
        state.zip = null;
        state.report = null;
        state.pages = [];
        state.currentPageIndex = 0;
        state.activeView = 'diff';
        state.renderToken += 1;
        revokeAssetUrls();

        if (previewContainer) previewContainer.classList.add('hidden');
        if (mainImage) {
            mainImage.classList.add('hidden');
            mainImage.removeAttribute('src');
        }
        if (mainEmpty) mainEmpty.classList.remove('hidden');
        if (pageList) pageList.innerHTML = '';
        if (pageMeta) pageMeta.textContent = '';
        if (baseImage) baseImage.removeAttribute('src');
        if (updatedImage) updatedImage.removeAttribute('src');
    }

    function isPreviewVisible() {
        return Boolean(
            previewContainer
            && !previewContainer.classList.contains('hidden')
            && state.pages.length > 0
        );
    }

    function isTypingContext(target) {
        if (!target) return false;
        const tag = (target.tagName || '').toLowerCase();
        return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable;
    }

    function setMainLoading(isLoading) {
        if (!mainLoading) return;
        if (isLoading) {
            mainLoading.classList.remove('hidden');
            mainLoading.classList.add('flex');
        } else {
            mainLoading.classList.add('hidden');
            mainLoading.classList.remove('flex');
        }
    }

    function updateViewButtons() {
        viewButtons.forEach((button) => {
            const isActive = button.dataset.view === state.activeView;
            button.classList.toggle('bg-white', isActive);
            button.classList.toggle('text-amber-700', isActive);
            button.classList.toggle('shadow-sm', isActive);
            button.classList.toggle('text-gray-700', !isActive);
        });
    }

    function updatePagerControls() {
        const total = state.pages.length;
        const pageNumber = total === 0 ? 0 : state.currentPageIndex + 1;
        if (pageIndicator) {
            pageIndicator.textContent = `${window.COMPARE_PAGE_TEXT || 'Page'} ${pageNumber} ${window.COMPARE_OF_TEXT || 'of'} ${total}`;
        }
        if (prevPageButton) prevPageButton.disabled = state.currentPageIndex <= 0;
        if (nextPageButton) nextPageButton.disabled = state.currentPageIndex >= total - 1;
    }

    function renderSummary() {
        const report = state.report || {};
        const pages = state.pages;
        const totalWordsAdded = pages.reduce((acc, page) => acc + (page.wordsAdded || 0), 0);
        const totalWordsRemoved = pages.reduce((acc, page) => acc + (page.wordsRemoved || 0), 0);

        if (summaryGeneratedAt) {
            const generated = formatUtcDate(report.generated_at_utc);
            summaryGeneratedAt.textContent = generated
                ? `UTC: ${generated}`
                : '';
        }
        if (summaryPages) {
            summaryPages.textContent = formatNumber(report.pages_analyzed || pages.length || 0);
        }
        if (summaryChange) {
            summaryChange.textContent = formatPercent(report.overall_visual_change_percent || 0);
        }
        if (summaryWordsAdded) {
            summaryWordsAdded.textContent = formatNumber(totalWordsAdded);
        }
        if (summaryWordsRemoved) {
            summaryWordsRemoved.textContent = formatNumber(totalWordsRemoved);
        }
    }

    function renderPageList() {
        if (!pageList) return;
        pageList.innerHTML = '';

        state.pages.forEach((page, index) => {
            const { badge, row } = getStatusClasses(page.status);
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.pageIndex = String(index);
            button.className = `w-full text-left px-3.5 py-3.5 transition-colors ${row}`;
            button.innerHTML = `
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="font-semibold text-gray-900">${window.COMPARE_PAGE_TEXT || 'Page'} ${page.pageNumber}</p>
                        <p class="text-xs text-gray-600 mt-1">${window.COMPARE_VISUAL_CHANGE_TEXT || 'Visual change'}: ${formatPercent(page.changePercent)}</p>
                    </div>
                    <span class="text-[11px] font-semibold px-2 py-1 rounded-full ${badge}">
                        ${getStatusLabel(page.status)}
                    </span>
                </div>
            `;
            button.addEventListener('click', () => {
                selectPage(index);
            });
            pageList.appendChild(button);
        });

        highlightActivePageButton();
    }

    function highlightActivePageButton() {
        if (!pageList) return;
        const buttons = pageList.querySelectorAll('button[data-page-index]');
        buttons.forEach((button) => {
            const index = Number(button.dataset.pageIndex);
            const isActive = index === state.currentPageIndex;
            button.classList.toggle('bg-amber-50', isActive);
            button.classList.toggle('ring-1', isActive);
            button.classList.toggle('ring-amber-300', isActive);
        });
    }

    async function getAssetUrl(assetPath) {
        if (!assetPath || !state.zip) return null;
        if (state.assetUrlCache.has(assetPath)) {
            return state.assetUrlCache.get(assetPath);
        }
        const file = state.zip.file(assetPath);
        if (!file) return null;
        const blob = await file.async('blob');
        const objectUrl = URL.createObjectURL(blob);
        state.assetUrlCache.set(assetPath, objectUrl);
        return objectUrl;
    }

    function buildPageMeta(page) {
        const labelChangedPixels = window.COMPARE_CHANGED_PIXELS_TEXT || 'Changed pixels';
        const labelTotalPixels = window.COMPARE_TOTAL_PIXELS_TEXT || 'Total pixels';
        const labelWordsAdded = window.COMPARE_WORDS_ADDED_TEXT || 'Words added';
        const labelWordsRemoved = window.COMPARE_WORDS_REMOVED_TEXT || 'Words removed';
        const labelTextSimilarity = window.COMPARE_TEXT_SIMILARITY_TEXT || 'Text similarity';

        return `
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
                <p><span class="font-semibold text-gray-900">${labelChangedPixels}:</span> ${formatNumber(page.changedPixels)}</p>
                <p><span class="font-semibold text-gray-900">${labelTotalPixels}:</span> ${formatNumber(page.totalPixels)}</p>
                <p><span class="font-semibold text-gray-900">${labelWordsAdded}:</span> ${formatNumber(page.wordsAdded)}</p>
                <p><span class="font-semibold text-gray-900">${labelWordsRemoved}:</span> ${formatNumber(page.wordsRemoved)}</p>
                <p><span class="font-semibold text-gray-900">${labelTextSimilarity}:</span> ${formatPercent(page.textSimilarityPercent)}</p>
            </div>
        `;
    }

    async function renderActivePage() {
        const page = state.pages[state.currentPageIndex];
        if (!page) return;

        const renderToken = ++state.renderToken;
        setMainLoading(true);
        if (mainEmpty) mainEmpty.classList.add('hidden');

        try {
            const [diffUrl, baseUrl, compareUrl] = await Promise.all([
                getAssetUrl(page.diffImagePath),
                getAssetUrl(page.baseImagePath),
                getAssetUrl(page.compareImagePath),
            ]);

            if (renderToken !== state.renderToken) return;

            const mainUrl = state.activeView === 'base'
                ? baseUrl
                : state.activeView === 'compare'
                    ? compareUrl
                    : diffUrl;

            if (mainImage && mainUrl) {
                mainImage.src = mainUrl;
                mainImage.classList.remove('hidden');
            }

            if (baseImage && baseUrl) {
                baseImage.src = baseUrl;
            }
            if (updatedImage && compareUrl) {
                updatedImage.src = compareUrl;
            }

            if (pageMeta) {
                pageMeta.innerHTML = buildPageMeta(page);
            }
        } finally {
            if (renderToken === state.renderToken) {
                setMainLoading(false);
                highlightActivePageButton();
                updatePagerControls();
            }
        }
    }

    async function selectPage(index) {
        if (index < 0 || index >= state.pages.length) return;
        state.currentPageIndex = index;
        await renderActivePage();
    }

    function getFallbackArchiveName(file1, file2) {
        const base = (file1?.name || 'base').replace(/\.pdf$/i, '');
        const compare = (file2?.name || 'compare').replace(/\.pdf$/i, '');
        return `${base}_vs_${compare}_convertica.zip`;
    }

    async function parseComparisonArchive(archiveBlob) {
        if (typeof window.JSZip === 'undefined') {
            throw new Error(window.COMPARE_ARCHIVE_ERROR_MESSAGE || 'Could not read comparison archive. Please try again.');
        }

        const zip = await window.JSZip.loadAsync(archiveBlob);
        const reportFile = zip.file('report.json');
        if (!reportFile) {
            throw new Error(window.COMPARE_REPORT_MISSING_MESSAGE || 'Comparison report is incomplete. Please run the comparison again.');
        }

        const reportText = await reportFile.async('text');
        let report;
        try {
            report = JSON.parse(reportText);
        } catch (_) {
            throw new Error(window.COMPARE_ARCHIVE_ERROR_MESSAGE || 'Could not read comparison archive. Please try again.');
        }

        const pageReports = Array.isArray(report.page_reports) ? report.page_reports : [];
        const pages = pageReports.map((pageReport, index) => ({
            pageNumber: Number(pageReport.page) || index + 1,
            status: pageReport.status || '',
            changePercent: Number(pageReport.change_percent) || 0,
            changedPixels: Number(pageReport.changed_pixels) || 0,
            totalPixels: Number(pageReport.total_pixels) || 0,
            wordsAdded: Number(pageReport.words_added) || 0,
            wordsRemoved: Number(pageReport.words_removed) || 0,
            textSimilarityPercent: Number(pageReport.text_similarity_percent) || 0,
            diffImagePath: pageReport.diff_image || '',
            baseImagePath: pageReport.base_image || '',
            compareImagePath: pageReport.compare_image || '',
        }));

        if (pages.length === 0) {
            throw new Error(window.COMPARE_NO_PAGES_MESSAGE || 'No pages found in comparison report.');
        }

        return { zip, report, pages };
    }

    async function showComparisonPreview(parsedData, archiveBlob, archiveFilename) {
        revokeAssetUrls();
        state.zip = parsedData.zip;
        state.report = parsedData.report;
        state.pages = parsedData.pages;
        state.archiveBlob = archiveBlob;
        state.archiveFilename = archiveFilename;
        state.currentPageIndex = 0;
        state.activeView = 'diff';

        updateViewButtons();
        renderSummary();
        renderPageList();
        updatePagerControls();

        if (downloadButton) {
            downloadButton.disabled = false;
            downloadButton.textContent = window.COMPARE_DOWNLOAD_REPORT_TEXT || 'Export Report';
        }

        if (previewContainer) {
            previewContainer.classList.remove('hidden');
            previewContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        await renderActivePage();
    }

    async function saveBlob(blob, filename) {
        if (window.showSaveFilePicker) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: filename,
                    types: [{
                        description: 'Comparison report archive',
                        accept: { 'application/zip': ['.zip'] },
                    }],
                });
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                return;
            } catch (error) {
                if (error && error.name === 'AbortError') {
                    return;
                }
            }
        }

        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        setTimeout(() => {
            URL.revokeObjectURL(objectUrl);
        }, 1000);
    }

    async function handleReportDownload() {
        if (!state.archiveBlob || !state.archiveFilename || !downloadButton) return;

        const originalText = window.COMPARE_DOWNLOAD_REPORT_TEXT || 'Export Report';
        downloadButton.disabled = true;
        downloadButton.textContent = window.COMPARE_DOWNLOAD_IN_PROGRESS_TEXT || 'Preparing report export...';

        try {
            await saveBlob(state.archiveBlob, state.archiveFilename);
        } catch (error) {
            window.showError(
                error.message || window.COMPARE_DOWNLOAD_FAILED_TEXT || 'Failed to export report.',
                'converterResult'
            );
        } finally {
            downloadButton.disabled = false;
            downloadButton.textContent = originalText;
        }
    }

    if (thresholdInput && thresholdValue) {
        thresholdInput.addEventListener('input', () => {
            thresholdValue.textContent = thresholdInput.value;
        });
    }

    viewButtons.forEach((button) => {
        button.addEventListener('click', async () => {
            const nextView = button.dataset.view;
            if (!nextView || nextView === state.activeView) return;
            state.activeView = nextView;
            updateViewButtons();
            await renderActivePage();
        });
    });

    if (prevPageButton) {
        prevPageButton.addEventListener('click', async () => {
            await selectPage(state.currentPageIndex - 1);
        });
    }

    if (nextPageButton) {
        nextPageButton.addEventListener('click', async () => {
            await selectPage(state.currentPageIndex + 1);
        });
    }

    if (downloadButton) {
        downloadButton.addEventListener('click', async () => {
            await handleReportDownload();
        });
    }

    document.addEventListener('keydown', async (event) => {
        if (!isPreviewVisible() || isTypingContext(event.target)) return;
        if (event.key === 'ArrowRight' || event.key === 'PageDown') {
            event.preventDefault();
            await selectPage(state.currentPageIndex + 1);
            return;
        }
        if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
            event.preventDefault();
            await selectPage(state.currentPageIndex - 1);
        }
    });

    if (mainViewport) {
        mainViewport.addEventListener('click', async (event) => {
            if (!isPreviewVisible()) return;
            const rect = mainViewport.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            if (clickX < rect.width / 2) {
                await selectPage(state.currentPageIndex - 1);
            } else {
                await selectPage(state.currentPageIndex + 1);
            }
        });
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const file1 = fileInput1?.files?.[0];
        const file2 = fileInput2?.files?.[0];
        if (!file1 || !file2) {
            window.showError(
                window.COMPARE_FILE_MESSAGE || 'Please select two PDF files.',
                'converterResult'
            );
            return;
        }

        resetPreview();
        window.hideError('converterResult');
        window.hideDownload('downloadContainer');
        window.showLoading('loadingContainer', { showProgress: true });
        setFormDisabled(true);

        const formData = new FormData();
        formData.append('pdf_file_1', file1);
        formData.append('pdf_file_2', file2);
        formData.append('diff_threshold', thresholdInput?.value || '32');

        try {
            const response = await fetch(window.COMPARE_API_URL, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN || '',
                },
                body: formData,
            });

            if (!response.ok) {
                let apiError = window.COMPARE_ERROR_MESSAGE || 'Comparison failed.';
                try {
                    const errorData = await response.json();
                    apiError = errorData.error || apiError;
                } catch (_) {
                    // Ignore non-JSON errors
                }
                throw new Error(apiError);
            }

            const archiveBlob = await response.blob();
            const archiveFilename = getDownloadFilename(
                response,
                getFallbackArchiveName(file1, file2)
            );

            const parsed = await parseComparisonArchive(archiveBlob);
            window.hideLoading('loadingContainer', true);
            await showComparisonPreview(parsed, archiveBlob, archiveFilename);
        } catch (error) {
            window.hideLoading('loadingContainer');
            window.showError(
                error.message || window.COMPARE_ERROR_MESSAGE || 'Comparison failed.',
                'converterResult'
            );
        } finally {
            setFormDisabled(false);
        }
    });
});

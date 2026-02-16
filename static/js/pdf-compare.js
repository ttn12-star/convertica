/**
 * Compare two PDFs and download visual diff report archive.
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('compareForm');
    if (!form) return;

    const compareButton = document.getElementById('compareButton');
    const thresholdInput = document.getElementById('diffThreshold');
    const thresholdValue = document.getElementById('diffThresholdValue');

    function setFormDisabled(disabled) {
        if (compareButton) {
            compareButton.disabled = disabled;
            compareButton.classList.toggle('opacity-50', disabled);
            compareButton.classList.toggle('cursor-not-allowed', disabled);
        }
        const file1 = document.getElementById('pdfFile1');
        const file2 = document.getElementById('pdfFile2');
        if (file1) file1.disabled = disabled;
        if (file2) file2.disabled = disabled;
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

    if (thresholdInput && thresholdValue) {
        thresholdInput.addEventListener('input', () => {
            thresholdValue.textContent = thresholdInput.value;
        });
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const fileInput1 = document.getElementById('pdfFile1');
        const fileInput2 = document.getElementById('pdfFile2');
        const file1 = fileInput1?.files?.[0];
        const file2 = fileInput2?.files?.[0];
        if (!file1 || !file2) {
            window.showError(
                window.COMPARE_FILE_MESSAGE || 'Please select two PDF files.',
                'converterResult'
            );
            return;
        }

        const formData = new FormData();
        formData.append('pdf_file_1', file1);
        formData.append('pdf_file_2', file2);
        formData.append('diff_threshold', thresholdInput?.value || '32');

        window.hideError('converterResult');
        window.hideDownload('downloadContainer');
        window.showLoading('loadingContainer', { showProgress: true });
        setFormDisabled(true);

        try {
            const response = await fetch(window.COMPARE_API_URL, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN || '',
                },
                body: formData,
            });

            if (!response.ok) {
                let errorMessage = window.COMPARE_ERROR_MESSAGE || 'Comparison failed.';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (_) {
                    // ignore JSON parse issues
                }
                throw new Error(errorMessage);
            }

            const blob = await response.blob();
            const fallbackName = `${file1.name.replace(/\.pdf$/i, '')}_vs_${file2.name.replace(/\.pdf$/i, '')}_convertica.zip`;
            const filename = getDownloadFilename(response, fallbackName);

            window.hideLoading('loadingContainer', true);
            window.showDownloadButton(blob, filename, 'downloadContainer');
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

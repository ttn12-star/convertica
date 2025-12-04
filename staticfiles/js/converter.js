// static/js/converter.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('fileInput');
        if (!fileInput?.files?.length) {
            alert(window.SELECT_FILE_MESSAGE || 'Please select a file');
            return;
        }

        const formData = new FormData();
        const fieldName = window.FILE_INPUT_NAME || 'file';
        formData.append(fieldName, fileInput.files[0]);

        const button = form.querySelector('button[type="submit"]');
        const originalText = button?.textContent || 'Convert';
        
        if (button) {
            button.disabled = true;
            button.textContent = 'Processing...';
        }

        try {
            const response = await fetch(window.API_URL, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN || ''
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || window.ERROR_MESSAGE || 'Conversion failed');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const originalName = fileInput.files[0].name;
            let downloadName = originalName;
            
            if (window.REPLACE_REGEX && window.REPLACE_TO) {
                try {
                    const regex = new RegExp(window.REPLACE_REGEX, 'i');
                    downloadName = originalName.replace(regex, window.REPLACE_TO);
                } catch (e) {
                    console.warn('Invalid regex pattern:', window.REPLACE_REGEX);
                }
            }
            
            a.download = downloadName;
            a.click();
            URL.revokeObjectURL(url);

        } catch (err) {
            console.error('Conversion error:', err);
            alert(err.message);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = originalText;
            }
        }
    });
});
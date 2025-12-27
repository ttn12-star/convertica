/**
 * Page Number Preview
 * Renders PDF preview with page numbers applied, matching backend logic.
 */

document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('fileInput');
  const fileInputDrop = document.getElementById('fileInputDrop');
  const canvas = document.getElementById('pageNumberCanvas');
  const pageSelector = document.getElementById('pageNumberPageSelector');
  const previewSection = document.getElementById('pageNumberPreviewSection');
  const settingsSection = document.getElementById('pageNumberSettingsSection');

  const positionSelect = document.getElementById('position');
  const fontSizeInput = document.getElementById('font_size');
  const startNumberInput = document.getElementById('start_number');
  const formatInput = document.getElementById('format_str');

  if (!canvas || !pageSelector || !previewSection || !settingsSection) return;

  let pdfDoc = null;
  let currentPage = 1;
  let scale = 1.2;

  // Initialize PDF.js worker when available
  function initPdfJsWorker() {
    if (typeof pdfjsLib !== 'undefined' && !pdfjsLib.GlobalWorkerOptions.workerSrc) {
      const localWorkerSrc = typeof window.PDFJS_LOCAL_WORKER === 'string' ? window.PDFJS_LOCAL_WORKER : null;
      pdfjsLib.GlobalWorkerOptions.workerSrc = localWorkerSrc || 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }
  }

  // Try to initialize immediately
  initPdfJsWorker();

  function calculateScale(viewport) {
    const container = canvas.parentElement;
    const containerWidth = container.clientWidth - 32; // padding
    const containerHeight = window.innerHeight > 768 ? 600 : 400; // responsive height

    const scaleX = containerWidth / viewport.width;
    const scaleY = containerHeight / viewport.height;

    return Math.min(scaleX, scaleY, 2); // max scale 2x
  }

  function getSelectedFile() {
    return fileInput?.files?.[0] || fileInputDrop?.files?.[0] || null;
  }

  function populatePageSelector(totalPages) {
    pageSelector.innerHTML = '';
    for (let i = 1; i <= totalPages; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}`;
      pageSelector.appendChild(opt);
    }
    currentPage = 1;
    pageSelector.value = '1';
  }

  function getFormatText(pageIndex, totalPages) {
    const startNum = parseInt(startNumberInput?.value || '1', 10) || 1;
    const formatStr = formatInput?.value?.trim() || '{page}';
    const pageNumber = startNum + (pageIndex - 1);
    try {
      return formatStr
        .replace('{page}', pageNumber)
        .replace('{total}', totalPages);
    } catch (e) {
      return `${pageNumber} / ${totalPages}`;
    }
  }

  function getPositionCoordinates(position, pageWidth, pageHeight, fontSizePx, textWidthPx) {
    // Match backend: margin = 0.5 inch = 36pt; convert using scale
    const baseMarginPt = 36;
    const margin = baseMarginPt * scale;

    // Canvas coordinates: Y=0 at top
    // For text positioning, we need to account for text baseline
    let y;
    if (position.includes('top')) {
      // Top: margin from top edge, text baseline at fontSizePx
      y = margin + fontSizePx;
    } else {
      // Bottom: margin from bottom edge, text sits on baseline
      y = pageHeight - margin;
    }

    let x;
    if (position.includes('left')) {
      // Left: margin from left edge
      x = margin;
    } else if (position.includes('right')) {
      // Right: margin from right edge, align right edge of text
      x = pageWidth - margin - textWidthPx;
    } else {
      // Center: exact center of text
      x = pageWidth / 2 - textWidthPx / 2;
    }
    return { x, y };
  }

  async function renderPage(pageNum) {
    if (!pdfDoc) return;
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: 1 }); // Get natural scale first

    // Calculate adaptive scale
    scale = calculateScale(viewport);
    const scaledViewport = page.getViewport({ scale });

    const ctx = canvas.getContext('2d');
    canvas.width = scaledViewport.width;
    canvas.height = scaledViewport.height;

    const renderContext = {
      canvasContext: ctx,
      viewport: scaledViewport,
    };

    await page.render(renderContext).promise;

    // Draw page number overlay
    const position = positionSelect?.value || 'bottom-center';
    const fontSize = parseInt(fontSizeInput?.value || '12', 10) || 12;
    const text = getFormatText(pageNum, pdfDoc.numPages);

    // Debug info
    console.log('Drawing page number:', { pageNum, text, position, fontSize, scale });

    ctx.save();
    ctx.fillStyle = '#1f2937'; // gray-800
    ctx.font = `${fontSize * scale}px Helvetica`;
    ctx.textBaseline = 'alphabetic'; // Match standard text rendering
    const textMetrics = ctx.measureText(text);
    const textWidth = textMetrics.width;

    const { x, y } = getPositionCoordinates(position, scaledViewport.width, scaledViewport.height, fontSize * scale, textWidth);

    console.log('Text position:', { x, y, textWidth, canvasWidth: canvas.width, canvasHeight: canvas.height });

    ctx.fillText(text, x, y);
    ctx.restore();
  }

  // Use showError from utils.js with additional logic
  function showError(message) {
    window.showError(message, 'editorResult');

    // Hide preview sections on error
    previewSection.classList.add('hidden');
    settingsSection.classList.add('hidden');
  }

function clearError() {
    const resultContainer = document.getElementById('editorResult');
    if (resultContainer) {
        resultContainer.classList.add('hidden');
        resultContainer.innerHTML = '';
    }
}

  async function loadPdf(file) {
    try {
      // Clear any previous errors when selecting a new file
      clearError();

      // Ensure PDF.js is loaded
      if (typeof pdfjsLib === 'undefined') {
        showError('Unable to load PDF preview. Please refresh the page or disable browser extensions that may block scripts, then try again.');
        return;
      }

      // Initialize worker if not already done
      initPdfJsWorker();

      // Validate page limit using common function
      if (typeof window.validatePdfPageLimit === 'function') {
        const isValid = await window.validatePdfPageLimit(file);
        if (!isValid) {
          // Error already shown by validatePdfPageLimit, hide preview
          previewSection.classList.add('hidden');
          settingsSection.classList.add('hidden');
          return;
        }
      }

      const arrayBuffer = await file.arrayBuffer();
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      pdfDoc = await loadingTask.promise;

      // Show preview and settings (common approach)
      previewSection.classList.remove('hidden');
      settingsSection.classList.remove('hidden');

      populatePageSelector(pdfDoc.numPages);
      await renderPage(currentPage);
    } catch (e) {
      console.error('Failed to render PDF preview', e);

      // Hide preview sections on error (common approach)
      previewSection.classList.add('hidden');
      settingsSection.classList.add('hidden');

      // Handle different types of errors
      let errorMessage = 'Failed to load PDF file. Please try again.';
      if (e && e.message) {
        if (e.message.includes('Invalid PDF')) {
          errorMessage = 'Invalid PDF file. Please select a valid PDF file.';
        } else if (e.message.includes('password')) {
          errorMessage = 'This PDF is password protected. Please unlock it first.';
        } else if (e.message.includes('network') || e.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your connection and try again.';
        } else if (e.message.includes('pages') && e.message.includes('maximum')) {
          errorMessage = e.message; // Use backend page limit error
        } else {
          errorMessage = `Error: ${e.message}`;
        }
      }

      showError(errorMessage);
    }
  }

  // Event bindings
  pageSelector.addEventListener('change', async (e) => {
    currentPage = parseInt(e.target.value, 10) || 1;
    await renderPage(currentPage);
  });

  [positionSelect, fontSizeInput, startNumberInput, formatInput].forEach((el) => {
    if (el) {
      el.addEventListener('input', () => renderPage(currentPage));
      el.addEventListener('change', () => renderPage(currentPage));
    }
  });

  // Listen to file selection
  const fileInputs = [fileInput, fileInputDrop];
  fileInputs.forEach((inp) => {
    if (inp) {
      inp.addEventListener('change', () => {
        const file = getSelectedFile();
        if (file && file.type === 'application/pdf') {
          loadPdf(file);
        } else {
          previewSection.classList.add('hidden');
          settingsSection.classList.add('hidden');
        }
      });
    }
  });

  // Format preset buttons
  const formatPresets = document.querySelectorAll('.format-preset');
  formatPresets.forEach((button) => {
    button.addEventListener('click', () => {
      const format = button.dataset.format;
      if (formatInput) {
        formatInput.value = format;

        // Visual feedback - highlight selected button
        formatPresets.forEach((btn) => {
          btn.classList.remove('bg-blue-500', 'text-white', 'border-blue-500');
          btn.classList.add('bg-gray-100', 'border-gray-300');
        });
        button.classList.remove('bg-gray-100', 'border-gray-300');
        button.classList.add('bg-blue-500', 'text-white', 'border-blue-500');

        // Trigger preview update if PDF is loaded
        if (pdfDoc) {
          renderPage(currentPage);
        }
      }
    });
  });

  // Real-time preview updates when settings change
  const settingsInputs = [positionSelect, fontSizeInput, startNumberInput, formatInput];
  settingsInputs.forEach((input) => {
    if (input) {
      input.addEventListener('input', () => {
        if (pdfDoc) {
          renderPage(currentPage);
        }
      });
      input.addEventListener('change', () => {
        if (pdfDoc) {
          renderPage(currentPage);
        }
      });
    }
  });

  // Page selector change
  if (pageSelector) {
    pageSelector.addEventListener('change', (e) => {
      currentPage = parseInt(e.target.value, 10);
      if (pdfDoc) {
        renderPage(currentPage);
      }
    });
  }
});

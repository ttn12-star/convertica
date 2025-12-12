/**
 * Page Number Preview
 * Renders PDF preview with page numbers applied, matching backend logic.
 */

document.addEventListener('DOMContentLoaded', () => {
  // pdf.js worker
  if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  } else {
    return;
  }

  const fileInput = document.getElementById('fileInput');
  const fileInputDrop = document.getElementById('fileInputDrop');
  const canvas = document.getElementById('pageNumberCanvas');
  const pageSelector = document.getElementById('pageNumberPageSelector');
  const previewSection = document.getElementById('pageNumberPreviewSection');

  const positionSelect = document.getElementById('position');
  const fontSizeInput = document.getElementById('font_size');
  const startNumberInput = document.getElementById('start_number');
  const formatInput = document.getElementById('format_str');

  if (!canvas || !pageSelector || !previewSection) return;

  let pdfDoc = null;
  let currentPage = 1;
  let scale = 1.2;

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

    let y = position.includes('top') ? pageHeight - margin - fontSizePx : margin + fontSizePx;

    let x;
    if (position.includes('left')) {
      x = margin;
    } else if (position.includes('right')) {
      x = pageWidth - margin - textWidthPx;
    } else {
      x = pageWidth / 2 - textWidthPx / 2;
    }
    return { x, y };
  }

  async function renderPage(pageNum) {
    if (!pdfDoc) return;
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const renderContext = {
      canvasContext: ctx,
      viewport,
    };

    await page.render(renderContext).promise;

    // Draw page number overlay
    const position = positionSelect?.value || 'bottom-center';
    const fontSize = parseInt(fontSizeInput?.value || '12', 10) || 12;
    const text = getFormatText(pageNum, pdfDoc.numPages);

    ctx.save();
    ctx.fillStyle = '#1f2937'; // gray-800
    ctx.font = `${fontSize * scale}px Helvetica`;
    const textMetrics = ctx.measureText(text);
    const textWidth = textMetrics.width;

    const { x, y } = getPositionCoordinates(position, viewport.width, viewport.height, fontSize * scale, textWidth);
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  async function loadPdf(file) {
    try {
      // Clear any previous errors when selecting a new file
      const errorElements = document.querySelectorAll('.error-message, .bg-red-50, .border-red-200');
      errorElements.forEach(el => el.remove());

      const arrayBuffer = await file.arrayBuffer();
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      pdfDoc = await loadingTask.promise;

      // Early page count validation - check before rendering
      const pageCount = pdfDoc.numPages;
      const maxPages = 50; // Same as backend

      if (pageCount > maxPages) {
        alert(`PDF has ${pageCount} pages, maximum allowed is ${maxPages}. Please split your PDF into smaller parts.`);
        previewSection.classList.add('hidden');
        pdfDoc = null;
        return;
      }

      previewSection.classList.remove('hidden');
      populatePageSelector(pageCount);
      await renderPage(currentPage);
    } catch (e) {
      console.error('Failed to render PDF preview', e);
      previewSection.classList.add('hidden');
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
        }
      });
    }
  });
});

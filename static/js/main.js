document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('uploadForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById('fileInput');
      if (!fileInput.files.length) return alert('Select a file');

      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

      document.getElementById('spinner').classList.remove('hidden');

      const apiUrl = window.location.pathname.includes('pdf-to-word') 
                     ? '/api/pdf-to-word/' 
                     : '/api/word-to-pdf/';

      try {
          const response = await fetch(apiUrl, {
              method: 'POST',
              body: formData
          });

          if (!response.ok) throw new Error('Conversion failed');

          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = fileInput.files[0].name.replace(/\.(pdf|docx?)$/i, apiUrl.includes('pdf-to-word') ? '.docx' : '.pdf');
          document.body.appendChild(a);
          a.click();
          a.remove();
      } catch (err) {
          alert(err.message);
      } finally {
          document.getElementById('spinner').classList.add('hidden');
      }
  });
});

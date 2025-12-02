document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("word-form");
  const result = document.getElementById("result");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("word-file");
    if (!fileInput.files.length) return alert("Please select a Word file.");

    const formData = new FormData();
    formData.append("docx_file", fileInput.files[0]);
    formData.append(
      "csrfmiddlewaretoken",
      document.querySelector('[name=csrfmiddlewaretoken]').value
    );

    result.innerHTML = "Processing...";

    try {
      const response = await fetch("/api/word-to-pdf/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        result.innerHTML = `Error: ${data.error || response.statusText}`;
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileInput.files[0].name.replace(/\.(docx?|doc)$/i, ".pdf");
      a.click();
      result.innerHTML = "Done! File downloaded.";
    } catch (err) {
      result.innerHTML = `Error: ${err.message}`;
    }
  });
});

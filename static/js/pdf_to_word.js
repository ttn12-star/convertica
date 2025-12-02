document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("pdf-form");
  const result = document.getElementById("result");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("pdf-file");
    if (!fileInput.files.length) return alert("Please select a PDF file.");

    const formData = new FormData();
    formData.append("pdf_file", fileInput.files[0]);

    result.innerHTML = "Processing...";

    try {
      const response = await fetch("/api/pdf-to-word/", {
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
      a.download = fileInput.files[0].name.replace(/\.pdf$/i, ".docx");
      a.click();
      result.innerHTML = "Done! File downloaded.";
    } catch (err) {
      result.innerHTML = `Error: ${err.message}`;
    }
  });
});

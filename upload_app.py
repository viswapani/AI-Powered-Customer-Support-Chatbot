from __future__ import annotations

import io
import os
from typing import Tuple

from flask import Flask, request, render_template_string, redirect, url_for, flash
from werkzeug.utils import secure_filename

from rag_pipeline import add_document

ALLOWED_EXTENSIONS = {"txt", "pdf"}

app = Flask(__name__)
# Simple secret key for flash messages; override via env in real deployments
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using PyPDF2.

    This is intentionally minimal; for complex PDFs you may want a richer extractor.
    """

    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            texts.append(page_text)
    return "\n".join(texts).strip()


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>MedEquip KB Uploader</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      .container { max-width: 600px; margin: 0 auto; }
      .messages { color: darkred; margin-bottom: 1rem; }
      .success { color: darkgreen; }
      label { display: block; margin-top: 1rem; }
      input[type="text"], input[type="file"] { width: 100%; }
      button { margin-top: 1rem; padding: 0.5rem 1rem; }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Upload Documents to Qdrant Knowledge Base</h1>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="messages">
            {% for category, message in messages %}
              <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <form method="post" enctype="multipart/form-data" action="{{ url_for('upload') }}">
        <label for="title">Title (optional, defaults to file name):</label>
        <input type="text" id="title" name="title" placeholder="Enter document title" />

        <label for="file">Select a .txt or .pdf file:</label>
        <input type="file" id="file" name="file" required />

        <button type="submit">Upload to Qdrant</button>
      </form>
    </div>
  </body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file part in request", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Unsupported file type. Please upload .txt or .pdf", "error")
        return redirect(url_for("index"))

    # Normalize filename: strip leading/trailing spaces and remove internal spaces
    raw_filename = file.filename.strip()
    filename = secure_filename(raw_filename.replace(" ", "_"))
    ext = filename.rsplit(".", 1)[1].lower()

    file_bytes = file.read()
    if not file_bytes:
        flash("Uploaded file is empty", "error")
        return redirect(url_for("index"))

    if ext == "txt":
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 as a best-effort
            content = file_bytes.decode("latin-1", errors="ignore")
    else:  # pdf
        content = extract_text_from_pdf(file_bytes)

    if not content.strip():
        flash("Could not extract any text from the document", "error")
        return redirect(url_for("index"))

    title = request.form.get("title") or os.path.splitext(filename)[0]

    try:
        add_document(title=title, content=content)
    except Exception as e:
        flash(f"Error adding document to Qdrant: {e}", "error")
        return redirect(url_for("index"))

    flash(f"Document '{title}' uploaded and indexed successfully.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # By default run on localhost:5000
    app.run(debug=True)

from flask import Flask, request, render_template_string
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime

app = Flask(__name__)

# Azure storage details
ACCOUNT_NAME = "alstorage001"
CONTAINER_NAME = "abc"
SAS_TOKEN = f"sp=racw&st=2025-08-21T18:33:38Z&se=2025-09-05T02:48:38Z&spr=https&sv=2024-11-04&sr=c&sig=1gPknht9pqZvmGFuIeU0eBgTb%2F9DI2KxKftEiC%2FRLtU%3D"

# HTML Template
HTML_FORM = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Excel Uploader</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .upload-card { max-width: 650px; margin: auto; margin-top: 50px; }
    </style>
</head>
<body>

<div class="card shadow upload-card">
    <div class="card-body">
        <h3 class="card-title text-center mb-4">📤 Upload Excel to Azure</h3>
        <form method="post" enctype="multipart/form-data">
            
            <div class="mb-3">
                <label class="form-label">Type of Excel</label>
                <select class="form-select" name="file_type" required onchange="toggleInputs(this.value)">
                    <option value="">-- Select --</option>
                    <option value="yearly">Yearly Excel</option>
                    <option value="monthly">Monthly Budget Excel</option>
                    <option value="bankstatement">Bank Statement Excel</option>
                </select>
            </div>

            <div class="mb-3">
                <label class="form-label">Outlet</label>
                <input type="text" class="form-control" name="outlet" placeholder="Outlet name" required>
            </div>

            <div class="mb-3" id="year_input" style="display:none;">
                <label class="form-label">Year</label>
                <input type="number" class="form-control" name="year" min="2000" max="2100">
            </div>

            <div class="mb-3" id="date_input" style="display:none;">
                <label class="form-label">Date</label>
                <input type="date" class="form-control" name="date">
            </div>

            <div class="mb-3" id="bank_input" style="display:none;">
                <label class="form-label">Bank Name</label>
                <select class="form-select" name="bank_name">
                    <option value="">-- Select Bank --</option>
                    <option value="bankAlraj">Bank Alraj</option>
                    <option value="bankRiyad">Bank Riyad</option>
                    <option value="bankSabb">Bank Sabb</option>
                </select>
            </div>

            <div class="mb-3">
                <label class="form-label">Upload File</label>
                <input type="file" class="form-control" name="file" accept=".xls,.xlsx" required>
            </div>

            <div class="d-grid">
                <button type="submit" class="btn btn-primary">Upload</button>
            </div>
        </form>
    </div>
</div>

<script>
function toggleInputs(fileType) {
    document.getElementById("year_input").style.display = fileType === "yearly" ? "block" : "none";
    document.getElementById("date_input").style.display = (fileType === "monthly" || fileType === "bankstatement") ? "block" : "none";
    document.getElementById("bank_input").style.display = fileType === "bankstatement" ? "block" : "none";
}
</script>

</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file_type = request.form['file_type']
        outlet = request.form['outlet'].replace(" ", "_")  # sanitize outlet
        year = request.form.get('year')
        date_str = request.form.get('date')
        uploaded_file = request.files['file']

        if not uploaded_file.filename.lower().endswith(('.xls', '.xlsx')):
            return "❌ Only .xls and .xlsx files are allowed."


        timestamp = datetime.now().strftime("%H%M%S")
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        # Decide folder + filename
        if file_type == "yearly":
            folder = "yearly"
            filename = f"yearly_{year}_{outlet}_{timestamp}{ext}"

        elif file_type == "monthly":
            folder = "monthly"
            yyyymmdd = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
            filename = f"monthly_{yyyymmdd}_{outlet}_{timestamp}{ext}"

        elif file_type == "bankstatement":
            bank_name = request.form.get('bank_name')
            if not bank_name:
                return "❌ Please select a bank."

            folder = f"bankstatements/{bank_name}"
            yyyymmdd = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
            filename = f"bankstatement_{yyyymmdd}_{outlet}_{timestamp}{ext}"

        else:
            return "❌ Invalid file type."

        # Upload to Azure Blob Storage
        blob_service_client = BlobServiceClient(
            f"https://{ACCOUNT_NAME}.blob.core.windows.net?{SAS_TOKEN}"
        )
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=f"{folder}/{filename}")
        blob_client.upload_blob(uploaded_file.read(), overwrite=True)

        return f"<h4 class='text-success text-center mt-5'>✅ File uploaded to '{folder}/{filename}' successfully.</h4>"

    return render_template_string(HTML_FORM)

if __name__ == '__main__':
    app.run(debug=True)

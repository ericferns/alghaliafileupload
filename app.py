from flask import Flask, request, render_template_string
from azure.storage.blob import BlobServiceClient
import os

app = Flask(__name__)

# 🔐 Your Azure Blob Storage credentials (use environment variables in production)
ACCOUNT_NAME = "alstorage001"
CONTAINER_NAME = "abc"
SAS_TOKEN = "sp=racw&st=2025-08-10T08:24:20Z&se=2025-08-11T16:39:20Z&spr=https&sv=2024-11-04&sr=c&sig=Y9QWImvApmTQ8mn5IWPc%2BPlfrI2Y%2FEsGjrHUnrvwh%2BA%3D"  # Container-level SAS token

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file:
            blob_name = uploaded_file.filename  # or add folder logic here
            blob_service_client = BlobServiceClient(
                f"https://{ACCOUNT_NAME}.blob.core.windows.net?{SAS_TOKEN}"
            )
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
            blob_client.upload_blob(uploaded_file.read(), overwrite=True)

            return f"✅ File '{blob_name}' uploaded successfully."

    # Simple HTML form
    return render_template_string('''
        <h2>Upload Excel File</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".xlsx">
            <input type="submit" value="Upload">
        </form>
    ''')

if __name__ == '__main__':
    app.run(debug=True)

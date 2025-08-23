from flask import Flask, request, render_template
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
import threading
import requests

app = Flask(__name__)

key_vault_url = "https://alghalia-kv.vault.azure.net/"
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

# Azure storage details
ACCOUNT_NAME = secret_client.get_secret("storage-account-name").value
SAS_TOKEN = secret_client.get_secret("storage-account-sas-key").value
CONTAINER_NAME = "abc"

# Databricks details (replace with real values)
DATABRICKS_HOST = secret_client.get_secret("databricks-workspace-host").value
DATABRICKS_TOKEN = secret_client.get_secret("databricks-workspace-token").value
DATABRICKS_JOB_ID = secret_client.get_secret("databricks-cashflow-job-id").value

# Global debounce timer
debounce_timer = None
DEBOUNCE_DELAY = 300  # 5 minutes in seconds

# HTML Template

def trigger_databricks_job():
    """Calls the Databricks job via REST API."""
    url = f"{DATABRICKS_HOST}/api/2.1/jobs/run-now"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
    payload = {"job_id": DATABRICKS_JOB_ID}

    try:
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            print("🚀 Databricks job triggered successfully.")
        else:
            print(f"⚠️ Failed to trigger job: {resp.text}")
    except Exception as e:
        print(f"❌ Error triggering Databricks job: {e}")


def schedule_databricks_job():
    """Debounces job execution with resettable timer."""
    global debounce_timer
    if debounce_timer and debounce_timer.is_alive():
        debounce_timer.cancel()  # reset countdown
    debounce_timer = threading.Timer(DEBOUNCE_DELAY, trigger_databricks_job)
    debounce_timer.start()
    print("⏳ Databricks job scheduled in 5 minutes (reset if another upload comes).")


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
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=f"{folder}/{filename}"
        )
        blob_client.upload_blob(uploaded_file.read(), overwrite=True)

        # Schedule Databricks job after debounce
        schedule_databricks_job()

        return f"<h4 class='text-success text-center mt-5'>✅ File uploaded to '{folder}/{filename}' successfully.<br>⏳ Databricks job will trigger in 5 min if no more uploads.</h4>"

    return render_template("upload.html")


if __name__ == '__main__':
    app.run(debug=True)

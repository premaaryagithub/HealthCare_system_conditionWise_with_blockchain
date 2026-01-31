# UI Dashboard (Windows)

This is a **Windows-only Streamlit dashboard** for the Trusted Authority (TA) API.

## Install

In your TA Python virtualenv (Windows):

```bash
pip install streamlit
```

## Run

Make sure Trusted Authority is running on `http://127.0.0.1:8000`.

Then run:

```bash
streamlit run ui_dashboard/app.py
```

### Optional

To point the UI at a different TA base URL:

```powershell
$env:TA_API_BASE_URL = "http://127.0.0.1:8000"
```

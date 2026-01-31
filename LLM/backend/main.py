from fastapi import FastAPI, UploadFile, File
from triage_agent import analyze_with_gemini
import tempfile
import os
import json

app = FastAPI(
    title="Gemini Medical Triage AI",
    description="Extracts and analyzes patient reports using Gemini",
    version="3.0.0"
)

@app.post("/bulk-analyze")
async def bulk_analyze(files: list[UploadFile] = File(...)):
    results = []

    for file in files:
        # Save the uploaded file temporarily
        temp_path = os.path.join(tempfile.gettempdir(), file.filename)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Analyze file with Gemini
        gemini_output = analyze_with_gemini(temp_path, file.filename)

        # Try to parse JSON, fallback to raw output
        try:
            parsed = json.loads(gemini_output)
        except json.JSONDecodeError:
            parsed = {"filename": file.filename, "raw_output": gemini_output}

        results.append(parsed)

        # Remove temp file after processing (optional)
        os.remove(temp_path)

    return {"total_documents": len(results), "results": results}

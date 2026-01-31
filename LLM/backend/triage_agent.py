import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def analyze_with_gemini(file_path: str, filename: str):
    prompt = f"""
    You are a medical triage assistant.
    The uploaded file may contain patient-related data (reports, prescriptions, or notes).

    1. Extract and summarize relevant medical information (symptoms, vitals, findings, test results, medications).
    2. Determine the seriousness of the condition using:
       - Critical (life-threatening emergency)
       - Urgent (needs prompt care)
       - Moderate (non-critical, monitor)
       - Normal (no concern)
    3. Respond ONLY in JSON format:
    {{
      "filename": "{filename}",
      "extracted_summary": "<brief extracted medical info>",
      "seriousness": "<Critical/Urgent/Moderate/Normal>",
      "score": "<0-3>",
      "reason": "<why this classification>"
    }}
    """

    # Gemini processes file + reasoning prompt together
    response = model.generate_content(
        [prompt, genai.upload_file(file_path)]
    )

    return response.text

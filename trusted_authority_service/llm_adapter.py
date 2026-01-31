import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class LlmTriageResult:
    raw: str
    parsed: dict
    priority: str


def _map_score_to_priority(score: int) -> str:
    if score >= 3:
        return "HIGH"
    if score == 2:
        return "MEDIUM"
    return "LOW"


def _load_triage_agent_module():
    repo_root = Path(__file__).resolve().parents[1]
    llm_backend_dir = repo_root / "LLM" / "backend"

    env_path = llm_backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # Make LLM/backend importable as top-level modules: triage_agent, config, etc.
    p = str(llm_backend_dir)
    if p not in sys.path:
        sys.path.insert(0, p)

    return importlib.import_module("triage_agent")


def classify_from_file(file_path: str, filename: str) -> LlmTriageResult:
    mock_priority = os.getenv("MOCK_LLM_PRIORITY")
    if mock_priority:
        p = mock_priority.upper()
        if p not in {"HIGH", "MEDIUM", "LOW"}:
            p = "MEDIUM"
        return LlmTriageResult(raw="MOCK", parsed={"mock": True, "filename": filename}, priority=p)

    triage_agent = _load_triage_agent_module()
    raw = triage_agent.analyze_with_gemini(file_path, filename)

    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        # Common Gemini format: ```json\n{...}\n```
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    parsed: dict
    try:
        parsed = json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except Exception:
                parsed = {"raw_output": raw}
        else:
            parsed = {"raw_output": raw}

    score = parsed.get("score")
    if score is None:
        seriousness = str(parsed.get("seriousness") or "").strip().lower()
        if seriousness == "critical":
            score_int = 3
        elif seriousness == "urgent":
            score_int = 2
        else:
            score_int = 1
    else:
        try:
            score_int = int(score)
        except Exception:
            score_int = 1

    priority = _map_score_to_priority(score_int)
    return LlmTriageResult(raw=raw, parsed=parsed, priority=priority)
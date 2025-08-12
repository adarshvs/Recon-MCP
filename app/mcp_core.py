import os
import re
import json
import requests
from typing import Any, Dict, Optional

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s or "")

def safe_json_parse(txt: str, default: Any = None) -> Any:
    """Try very hard to get a JSON object out of an LLM answer."""
    if not txt:
        return default
    txt = strip_ansi(txt).strip()

    # remove common fences
    txt = re.sub(r"^```(?:json)?", "", txt, flags=re.I).strip()
    txt = re.sub(r"```$", "", txt, flags=re.M).strip()

    # direct parse
    try:
        return json.loads(txt)
    except Exception:
        pass

    # crude last-brace chunk
    if "{" in txt and "}" in txt:
        blob = txt[txt.find("{"): txt.rfind("}") + 1]
        try:
            return json.loads(blob)
        except Exception:
            pass

    return default

def call_ollama(prompt: str,
                model: Optional[str] = None,
                json_mode: bool = False,
                options: Optional[Dict[str, Any]] = None) -> str:
    """
    One-shot call to Ollama (no streaming). Returns the raw 'response' text.
    """
    payload: Dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"
    if options:
        payload.update(options)

    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=180)
    # Happy path
    try:
        j = r.json()
        return j.get("response", r.text)
    except Exception:
        return strip_ansi(r.text)

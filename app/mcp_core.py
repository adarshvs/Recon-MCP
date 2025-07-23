# app/mcp_core.py
import json
import subprocess
from typing import Any, Dict

from app.config import LLM_MODEL

def call_ollama(prompt: str, model: str = LLM_MODEL) -> str:
    proc = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        capture_output=True
    )
    return proc.stdout.decode("utf-8", errors="ignore").strip()

def call_ollama_json(prompt: str, model: str = LLM_MODEL) -> Dict[str, Any]:
    txt = call_ollama(prompt, model=model)
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {}

def format_output_with_ollama(raw_output: str, context: str, model: str = LLM_MODEL) -> str:
    prompt = f"""
You are a cybersecurity recon assistant. The user asked: "{context}"

RAW tool output:
{raw_output}

Summarize key findings clearly (IPs, ports, tech stacks, WAF/CDN, interesting endpoints). 
Bullet points are fine. Keep it concise.
"""
    return call_ollama(prompt, model=model)

def run_mcp_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    request = {"jsonrpc": "2.0", "id": 1, "method": tool_name, "params": parameters}
    proc = subprocess.Popen(
        ["python3", "external-recon/main.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = proc.communicate(json.dumps(request) + "\n")
    try:
        resp = json.loads(stdout)
        return resp.get("result", stdout)
    except json.JSONDecodeError:
        return stdout or stderr

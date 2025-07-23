import subprocess
import json

def call_ollama(prompt: str, model: str = "mistral") -> str:
    """Call a local Ollama model and return plain text."""
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode(),
        capture_output=True
    )
    return result.stdout.decode().strip()

def run_mcp_tool(tool_name: str, parameters: dict) -> str:
    """Call the JSON-RPC tool server in external-recon/main.py."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": tool_name,
        "params": parameters
    }
    proc = subprocess.Popen(
        ["python3", "external-recon/main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(json.dumps(request) + "\n")
    try:
        resp = json.loads(stdout)
        return resp.get("result", stdout)
    except json.JSONDecodeError:
        return stdout or stderr

def format_output_with_ollama(raw_output: str, context: str, model: str = "mistral") -> str:
    """Summarize any tool output via local LLM."""
    prompt = f"""
You are a cybersecurity recon assistant. The user asked: "{context}"

Below is RAW output from a tool. Summarize key findings clearly and concisely.
RAW OUTPUT:
{raw_output}
"""
    return call_ollama(prompt, model=model)

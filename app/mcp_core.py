# app/mcp_core.py
import subprocess
import json
import re

def call_ollama(prompt):
    result = subprocess.run(
        ["ollama", "run", "mistral"],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def parse_tool_from_response(response):
    if "whois" in response.lower():
        match = re.search(r"(?:whois\s+)?([\w\.-]+\.\w+)", response)
        if match:
            return "whois", {"domain": match.group(1)}
    elif "dig" in response.lower() or "dns" in response.lower():
        match = re.search(r"(?:dig\s+)?([\w\.-]+\.\w+)", response)
        if match:
            return "dig", {"domain": match.group(1)}
    return None, None

def run_mcp_tool(tool_name, parameters):
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
        response = json.loads(stdout)
        return response.get("result", stdout)
    except json.JSONDecodeError:
        return stdout or stderr

def format_output_with_ollama(raw_output, original_prompt):
    """Send raw tool output and user prompt to LLM for clean formatting."""
    format_prompt = f"""
You are a cybersecurity assistant. A user asked: "{original_prompt}"

Below is the raw output from a recon or terminal tool. 
Format this output into a clear, human-readable summary focusing on the key insights (e.g. DNS records, registrar, subdomains, vulnerabilities, etc.)

Raw Output:
{raw_output}
"""
    result = subprocess.run(
        ["ollama", "run", "mistral"],
        input=format_prompt.strip(),
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

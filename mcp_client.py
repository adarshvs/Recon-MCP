import subprocess
import json
import re
import os

def call_ollama(prompt):
    result = subprocess.run(
        ["ollama", "run", "mistral"],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout

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

if __name__ == "__main__":
    prompt = input("💬 Ask something (e.g. whois google.com):\n> ")
    llm_response = call_ollama(prompt)
    print("🧠 LLM said:\n", llm_response)

    tool, params = parse_tool_from_response(llm_response)
    if tool:
        print(f"🔧 Running tool: {tool} with params {params}")
        output = run_mcp_tool(tool, params)
        print("📤 Output:\n", output)
    else:
        print("❌ Could not determine a valid tool to run.")

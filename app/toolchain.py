import platform
import subprocess
import json
import re

from app.mcp_core import call_ollama, run_mcp_tool, format_output_with_ollama

# -------- Config --------
SAFE_LOCAL_TOOLS = {
    "subfinder": {"timeout": 90},
    "nmap":      {"timeout": 120},
    "httpx":     {"timeout": 60},
    "wafw00f":   {"timeout": 40},
    "whatweb":   {"timeout": 60},
    "asnmap":    {"timeout": 30},
    "traceroute":{"timeout": 60},
    "tracert":   {"timeout": 60},
    "dig":       {"timeout": 20},   # but we run dig/whois via MCP
    "whois":     {"timeout": 20},   #   ^
}

# MCP-handled tools (JSON-RPC)
MCP_TOOLS = {"whois", "dig"}

# Quick keyword → intent/tool mapping
KEYWORD_INTENTS = [
    (r"\bsubdomains?\b",   ("subdomain_enum", "subfinder", "-d")),
    (r"\bwhois\b",         ("whois",          "whois",     "")),
    (r"\bdns\b|\bdig\b",   ("dns_recon",      "dig",       "")),
    (r"\btraceroute\b|\btrace route\b|\btracert\b", ("dns_recon", "traceroute", "")),
    (r"\bportscan\b|\bport scan\b|\bnmap\b",  ("port_scan","nmap",      "-sV -T4")),
    (r"\bwaf\b|\bwafw00f\b", ("cdn_detection","wafw00f",   "")),
    (r"\btech stack\b|\bwhatweb\b|\bwappalyzer\b", ("tech_fingerprint","whatweb","")),
    (r"\basn\b|\basnmap\b", ("asn_lookup","asnmap","")),
]


def _extract_domain(text: str) -> str:
    """Simple domain extractor."""
    m = re.search(r"([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})", text)
    return m.group(1) if m else text.strip()


def recognize_intent(query: str) -> dict:
    """
    1) Keyword-based overrides (deterministic).
    2) Regex for direct CLI commands (traceroute, whois, dig).
    3) LLM fallback returning JSON.
    """
    # 1) Keyword overrides
    for pattern, (intent, tool, flags) in KEYWORD_INTENTS:
        if re.search(pattern, query, re.IGNORECASE):
            domain = _extract_domain(query)
            # Special case for traceroute/tracert OS
            if tool in ("traceroute", "tracert"):
                tool = _os_trace_tool()
            return {
                "intent": intent,
                "tool":   tool,
                "target": domain,
                "flags":  flags
            }

    # 2) Direct CLI command override
    m = re.match(r'^\s*(traceroute|tracert|whois|dig)\s+(\S+)(?:\s+(.+))?$', query, re.IGNORECASE)
    if m:
        tool   = m.group(1).lower()
        target = m.group(2)
        flags  = m.group(3) or ""
        if tool in ("traceroute", "tracert"):
            tool = _os_trace_tool()
        intent_map = {
            "traceroute": "dns_recon",
            "tracert":    "dns_recon",
            "whois":      "whois",
            "dig":        "dns_recon",
        }
        return {
            "intent": intent_map.get(tool, "dns_recon"),
            "tool":   tool,
            "target": target,
            "flags":  flags.strip()
        }

    # 3) LLM fallback
    prompt = f"""
You are a pentesting recon assistant. Given the user's request, output valid JSON:
{{
  "intent": one of ["subdomain_enum","port_scan","dns_recon","whois","cdn_detection","tech_fingerprint","asn_lookup"],
  "tool":   the CLI tool to run (e.g. "subfinder","nmap","dig","whois","wafw00f","traceroute","asnmap","whatweb"),
  "target": the domain or IP string,
  "flags":  optional flags string
}}
Respond ONLY with JSON.
User request: "{query}"
"""
    llm_txt = call_ollama(prompt)
    try:
        return json.loads(llm_txt)
    except Exception:
        # final minimal fallback
        return {"intent": "whois", "tool": "whois", "target": _extract_domain(query), "flags": ""}


def _os_trace_tool() -> str:
    """Return traceroute variant for this OS."""
    os_name = platform.system().lower()
    return "tracert" if os_name == "windows" else "traceroute"


def _build_command(tool: str, target: str, flags: str) -> str:
    """Build the final shell command string."""
    tool = tool.strip()
    flags = flags.strip()
    target = target.strip()
    parts = [tool]
    if flags:
        parts.append(flags)
    if target:
        # special case subfinder: expects -d domain
        if tool == "subfinder" and "-d" not in flags:
            parts.extend(["-d", target])
        else:
            parts.append(target)
    return " ".join(parts)


def run_command(command: str) -> str:
    """Run a local command safely with timeout and return string output."""
    base = command.split()[0]
    timeout = SAFE_LOCAL_TOOLS.get(base, {}).get("timeout", 30)
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = res.stdout or res.stderr
    except subprocess.TimeoutExpired:
        output = f"Command timed out after {timeout} seconds"
    except Exception as e:
        output = str(e)
    if isinstance(output, (bytes, bytearray)):
        output = output.decode("utf-8", errors="ignore")
    return output


def process_query(query: str):
    # Step 1: decide what to do
    intent = recognize_intent(query)
    tool   = intent.get("tool", "whois")
    target = intent.get("target", query)
    flags  = intent.get("flags", "")

    # Step 2: dispatch
    if tool in MCP_TOOLS:
        output  = run_mcp_tool(tool, {"domain": target})
        command = f"{tool} {target}"
    elif tool in ("traceroute", "tracert"):
        # force OS-appropriate traceroute syntax
        tool = _os_trace_tool()
        # skip DNS lookups for speed
        flags = "-n" if tool == "traceroute" else "-d"
        command = _build_command(tool, target, flags)
        output  = run_command(command)
    else:
        command = _build_command(tool, target, flags)
        output  = run_command(command)

    # Step 3: summarize
    summary = ""
    low = output.lower() if isinstance(output, str) else ""
    if output and "timed out" not in low and "unknown command" not in low:
        summary = format_output_with_ollama(output, query)

    return {
        "llm_response": intent,   # show JSON so you can see what it decided
        "command": command,
        "output": output,
        "formatted_output": summary
    }

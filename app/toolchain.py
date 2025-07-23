# app/toolchain.py
import platform
import json
import re
from app.mcp_core import call_ollama
from app.config import TOOL_PATHS

DOMAIN_RE = re.compile(r"([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
IP_RE     = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

def extract_target(query: str) -> str:
    m = DOMAIN_RE.search(query)
    if m:
        return m.group(1)
    m2 = IP_RE.search(query.strip())
    if m2:
        return query.strip()
    return query.strip()

def os_trace_tool() -> str:
    return "tracert" if platform.system().lower() == "windows" else "traceroute"

def quick_intent(query: str) -> str:
    q = query.lower()
    if "subdomain" in q:
        return "subdomain_enum"
    if "port scan" in q or "nmap" in q:
        return "port_scan"
    if "everything" in q or "all details" in q or "full recon" in q:
        return "full_domain"
    if "waf" in q:
        return "cdn_detection"
    return ""  # unknown -> LLM

def llm_intent(query: str) -> dict:
    prompt = f"""
You are a pentesting recon assistant.
Return ONLY this JSON:
{{
  "intent": one of ["subdomain_enum","port_scan","dns_recon","whois","cdn_detection","tech_fingerprint","asn_lookup","content_discovery","wayback_scrape","full_domain","full_ip"],
  "target": "<domain or ip>"
}}
User: "{query}"
"""
    try:
        return json.loads(call_ollama(prompt))
    except Exception:
        return {"intent":"dns_recon","target":query}

def decide_intent_target(query: str) -> dict:
    base_intent = quick_intent(query)
    target = extract_target(query)

    if not base_intent:
        data = llm_intent(query)
        intent = data.get("intent", "dns_recon")
        tgt = data.get("target", target)
        return {"intent": intent, "target": tgt}
    else:
        # if ip and user asked "everything" -> full_ip
        if base_intent in ("full_domain",) and IP_RE.match(target):
            base_intent = "full_ip"
        return {"intent": base_intent, "target": target}

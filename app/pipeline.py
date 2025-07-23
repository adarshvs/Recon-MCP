# app/pipeline.py
import os
import re
import uuid
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

from app.config import TOOL_PATHS, SECLISTS_DIR, NUCLEI_TEMPLATES, NUCLEI_CONFIG_FILE, WORK_DIR

DOMAIN_RE = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
IP_RE     = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

@dataclass
class Step:
    name: str
    cmd: str
    outfile: Optional[str] = None

def is_domain(target: str) -> bool:
    return DOMAIN_RE.match(target) is not None

def is_ip(target: str) -> bool:
    return IP_RE.match(target) is not None

def ensure_job_dir(job_id: str) -> str:
    path = os.path.join(WORK_DIR, job_id)
    os.makedirs(path, exist_ok=True)
    return path

def domain_full_pipeline(domain: str, job_dir: str) -> List[Step]:
    subs_file      = os.path.join(job_dir, "subdomains.txt")
    resolved_file  = os.path.join(job_dir, "alive_dns.txt")
    httpx_file     = os.path.join(job_dir, "httpx.txt")
    waf_file       = os.path.join(job_dir, "wafw00f.txt")
    tech_file      = os.path.join(job_dir, "whatweb.txt")
    nuclei_file    = os.path.join(job_dir, "nuclei.txt")

    wordlist = os.path.join(SECLISTS_DIR, "Discovery/Web-Content/directory-list-2.3-medium.txt")
    # Build commands
    steps = [
        Step("Subdomain Enumeration (subfinder)",
             f"{TOOL_PATHS['subfinder']} -d {domain} -all -silent -o {subs_file}",
             subs_file),

        Step("Resolve & grab A records (dnsx)",
             f"{TOOL_PATHS['dnsx']} -l {subs_file} -a -resp -o {resolved_file}",
             resolved_file),

        Step("Probe HTTP(S) (httpx)",
             f"{TOOL_PATHS['httpx']} -l {resolved_file} -status-code -title -tech-detect -o {httpx_file}",
             httpx_file),

        Step("Detect WAF (wafw00f)",
             f"{TOOL_PATHS['wafw00f']} https://{domain} > {waf_file}",
             waf_file),

        Step("Tech Fingerprint (whatweb)",
             f"{TOOL_PATHS['whatweb']} -a 3 https://{domain} > {tech_file}",
             tech_file),

        Step("Vulnerability Scan (nuclei)",
             f"{TOOL_PATHS['nuclei']} -l {httpx_file} -c {NUCLEI_CONFIG_FILE} -t {NUCLEI_TEMPLATES} -o {nuclei_file}",
             nuclei_file),
    ]

    return steps

def ip_full_pipeline(ip: str, job_dir: str) -> List[Step]:
    nmap_file   = os.path.join(job_dir, "nmap.txt")
    nuclei_file = os.path.join(job_dir, "nuclei.txt")
    asn_file    = os.path.join(job_dir, "asn.txt")

    steps = [
        Step("Port Scan (nmap)", f"{TOOL_PATHS['nmap']} -sV -Pn -T4 {ip} -oN {nmap_file}", nmap_file),
        Step("ASN Lookup (asnmap)", f"{TOOL_PATHS['asnmap']} -ip {ip} > {asn_file}", asn_file),
        Step("Vulnerability Scan (nuclei)",
             f"{TOOL_PATHS['nuclei']} -u http://{ip} -c {NUCLEI_CONFIG_FILE} -t {NUCLEI_TEMPLATES} -o {nuclei_file}",
             nuclei_file),
    ]
    return steps

def make_pipeline(query: str, target: str, intent: str) -> Dict:
    """
    Build a list of Steps (plan) based on target & intent.
    If user said 'everything', we run full domain/IP pipeline.
    """
    job_id = str(uuid.uuid4())
    job_dir = ensure_job_dir(job_id)

    target_lower = target.lower()
    plan: List[Step] = []

    # Broad requests
    if "everything" in query or "all details" in query or intent in ("full_domain", "full_ip"):
        if is_domain(target_lower):
            plan = domain_full_pipeline(target_lower, job_dir)
        elif is_ip(target_lower):
            plan = ip_full_pipeline(target_lower, job_dir)
    else:
        # minimal single-intent (fallback)
        if intent == "subdomain_enum" and is_domain(target_lower):
            plan = [Step("Subdomain Enumeration",
                         f"{TOOL_PATHS['subfinder']} -d {target_lower} -all -silent -o {os.path.join(job_dir,'subdomains.txt')}",
                         os.path.join(job_dir, "subdomains.txt"))]
        elif intent == "port_scan" and is_ip(target_lower):
            plan = [Step("Port Scan (nmap)",
                         f"{TOOL_PATHS['nmap']} -sV -Pn -T4 {target_lower} -oN {os.path.join(job_dir,'nmap.txt')}",
                         os.path.join(job_dir, "nmap.txt"))]
        else:
            # fallback to domain_full or ip_full if we can't classify
            if is_domain(target_lower):
                plan = domain_full_pipeline(target_lower, job_dir)
            elif is_ip(target_lower):
                plan = ip_full_pipeline(target_lower, job_dir)

    return {
        "job_id": job_id,
        "job_dir": job_dir,
        "steps": [asdict(s) for s in plan]
    }

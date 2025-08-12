# agent/planner.py
import re
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional
from django.conf import settings

DOMAIN_RE = re.compile(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", re.I)
IPV4_RE   = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Toggle this to True once to debug PATH/tool resolution from Daphne
ADD_DIAG_STEP = False

def _q(s: str) -> str:
    """Shell-escape (best-effort) to avoid command injection in targets."""
    return shlex.quote(s)

def plan_for(query: str) -> Dict[str, Any]:
    """
    Offline planner (no LLM). Infers domain/ip and returns a task list.
    """
    q = (query or "").strip()
    domains = DOMAIN_RE.findall(q)
    ips     = IPV4_RE.findall(q)

    if domains and ips:
        target_type = "mixed"
        main_target = domains[0]
    elif domains:
        target_type = "domain"
        main_target = domains[0]
    elif ips:
        target_type = "ip"
        main_target = ips[0]
    else:
        target_type = "unknown"
        main_target = q

    tasks: List[str] = []
    if target_type in ("domain", "url", "mixed", "unknown"):
        tasks += [
            "subdomain_enum",
            "dns_resolve",
            "http_probe",
            "waf_detect",
            "tech_fingerprint",
            "nuclei_scan",
        ]
    if target_type in ("ip", "mixed"):
        tasks += ["nmap_basic", "cert_info"]

    # de-duplicate while preserving order
    tasks = list(dict.fromkeys(tasks))
    return {
        "main_target": main_target,
        "target_type": target_type,
        "tasks": tasks,
    }


def build_steps(job_dir: Path, plan: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """
    Build a list of shell steps from the plan. We *do not* check file existence
    here (they don't exist yet) — we guard inside the shell with [ -s file ].
    """
    ttype  = plan.get("target_type", "unknown")
    target = plan.get("main_target", "").strip()
    tasks  = plan.get("tasks", [])

    T = getattr(settings, "TOOLS", {})  # e.g. {"subfinder": "subfinder", ...}
    tgt = _q(target)

    steps: List[Dict[str, Optional[str]]] = []

    # common files
    subdomains_file = job_dir / "subdomains.txt"
    alive_dns_file  = job_dir / "alive_dns.txt"
    httpx_file      = job_dir / "httpx.txt"
    waf_file        = job_dir / "wafw00f.txt"
    whatweb_file    = job_dir / "whatweb.txt"
    nuclei_file     = job_dir / "nuclei.txt"
    nmap_file       = job_dir / "nmap.txt"
    cert_file       = job_dir / "cert.txt"

    def add(name: str, cmd: str, outfile: Optional[Path] = None):
        steps.append({
            "name": name,
            "cmd": cmd,
            "outfile": str(outfile) if outfile else None
        })

    # --- Optional diagnostic step to confirm PATH & which binaries Daphne sees ---
    if ADD_DIAG_STEP:
        add(
            "Diag PATH / which",
            "echo $PATH && which subfinder dnsx httpx wafw00f whatweb nuclei nmap || true"
        )

    if ttype in ("domain", "url", "mixed", "unknown"):
        if "subdomain_enum" in tasks and T.get("subfinder"):
            add(
                "Subdomain Enumeration (subfinder)",
                f"{T['subfinder']} -d {tgt} -all -silent -o {_q(str(subdomains_file))}",
                subdomains_file
            )

        if "dns_resolve" in tasks and T.get("dnsx"):
            # If subdomains.txt is non-empty => use -l; else resolve the single target with -d
            add(
                "Resolve & grab A records (dnsx)",
                "([ -s {subs} ] && {dnsx} -l {subs} -a -resp -o {alive}) || "
                "{dnsx} -d {tgt} -a -resp -o {alive}".format(
                    subs=_q(str(subdomains_file)),
                    dnsx=T["dnsx"],
                    alive=_q(str(alive_dns_file)),
                    tgt=tgt,
                ),
                alive_dns_file
            )

        if "http_probe" in tasks and T.get("httpx"):
            add(
                "Probe HTTP(S) (httpx)",
                "[ -s {alive} ] && {httpx} -l {alive} -status-code -title -tech-detect "
                "-no-color -o {httpx_out} || echo 'no alive hosts' > {httpx_out}".format(
                    alive=_q(str(alive_dns_file)),
                    httpx=T["httpx"],
                    httpx_out=_q(str(httpx_file))
                ),
                httpx_file
            )

        if "waf_detect" in tasks and T.get("wafw00f"):
            add(
                "Detect WAF (wafw00f)",
                f"{T['wafw00f']} https://{tgt} > {_q(str(waf_file))} 2>&1",
                waf_file
            )

        if "tech_fingerprint" in tasks and T.get("whatweb"):
            add(
                "Tech Fingerprint (whatweb)",
                f"{T['whatweb']} https://{tgt} > {_q(str(whatweb_file))} 2>&1",
                whatweb_file
            )

        if "nuclei_scan" in tasks and T.get("nuclei"):
            # Only scan if we actually have URLs
            add(
                "Vulnerability Scan (nuclei)",
                "[ -s {httpx_out} ] && {nuclei} -l {httpx_out} -no-color -o {nuclei_out} "
                "|| echo 'no urls to scan' > {nuclei_out}".format(
                    nuclei=T["nuclei"],
                    httpx_out=_q(str(httpx_file)),
                    nuclei_out=_q(str(nuclei_file)),
                ),
                nuclei_file
            )

    if ttype in ("ip", "mixed") or "nmap_basic" in tasks:
        if T.get("nmap"):
            add(
                "Port Scan (nmap)",
                f"{T['nmap']} -sV -T4 {tgt} -oN {_q(str(nmap_file))}",
                nmap_file
            )

    if ttype in ("ip", "mixed") or "cert_info" in tasks:
        if T.get("nmap"):
            add(
                "SSL Cert Info (nmap ssl-cert)",
                f"{T['nmap']} --script ssl-cert -p 443 {tgt} -oN {_q(str(cert_file))}",
                cert_file
            )

    return steps

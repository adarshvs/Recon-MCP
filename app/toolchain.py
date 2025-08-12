import asyncio
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from string import Template

from .config import (
    TOOLS, JOBS_DIR, DEFAULT_TIMEOUT,
    SECLISTS_DIR, NUCLEI_TEMPLATES, NUCLEI_CONFIG
)
from .mcp_core import call_ollama, safe_json_parse, strip_ansi

# ------------------ Data classes ------------------

@dataclass
class Step:
    name: str
    cmd: str
    outfile: Optional[str] = None
    status: str = "pending"         # pending|running|ok|fail|timeout
    exit_code: Optional[int] = None
    reason: Optional[str] = None

@dataclass
class JobMeta:
    job_id: str
    query: str
    plan: List[Step]
    started: Optional[str]
    finished: Optional[str] = None
    summary: Optional[str] = None


# ------------------ Helpers ------------------

def job_dir(job_id: str) -> Path:
    d = JOBS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def save_meta(meta: JobMeta):
    path = job_dir(meta.job_id) / "meta.json"
    data = asdict(meta)
    data["plan"] = [asdict(s) for s in meta.plan]
    path.write_text(json.dumps(data, indent=2))

def load_meta(job_id: str) -> JobMeta:
    data = json.loads((job_dir(job_id) / "meta.json").read_text())
    return JobMeta(
        job_id=data["job_id"],
        query=data["query"],
        plan=[Step(**s) for s in data["plan"]],
        started=data["started"],
        finished=data.get("finished"),
        summary=data.get("summary"),
    )

# ------------------ LLM Planning ------------------

PLANNER_PROMPT = Template("""You are a recon pipeline planner. Input: a freeform user query.
Infer:
1. target_type: one of ["domain","ip","asn","url","mixed","unknown"]
2. main_target: the core target string (domain/ip/asn/url)
3. tasks: array of high level actions to run (strings), choose from:
   ["subdomain_enum","dns_resolve","http_probe","waf_detect","tech_fingerprint",
    "nuclei_scan","nmap_basic","cert_info"]

Return ONLY JSON like:
{
  "target_type": "domain",
  "main_target": "example.com",
  "tasks": ["subdomain_enum","dns_resolve","http_probe","waf_detect","tech_fingerprint","nuclei_scan"]
}

User query: $q
""")

DOMAIN_RE = re.compile(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", re.I)
IPV4_RE   = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

def fallback_plan(q: str) -> Dict[str, Any]:
    domains = DOMAIN_RE.findall(q)
    ips     = IPV4_RE.findall(q)
    if domains and ips:
        tt = "mixed"; target = domains[0]
    elif domains:
        tt = "domain"; target = domains[0]
    elif ips:
        tt = "ip"; target = ips[0]
    else:
        tt = "unknown"; target = q.strip()

    tasks = []
    if tt in ("domain","url","mixed","unknown"):
        tasks += ["subdomain_enum","dns_resolve","http_probe","waf_detect","tech_fingerprint","nuclei_scan"]
    if tt in ("ip","mixed"):
        tasks += ["nmap_basic","cert_info"]

    return {"target_type": tt, "main_target": target, "tasks": list(dict.fromkeys(tasks))}

def classify_and_plan(q: str) -> Dict[str, Any]:
    raw = call_ollama(PLANNER_PROMPT.substitute(q=q), json_mode=True)
    data = safe_json_parse(raw, {})
    if not isinstance(data, dict) or "main_target" not in data:
        data = fallback_plan(q)
    return data

# ------------------ Step builder ------------------

def build_steps(jdir: Path, plan_info: Dict[str, Any]) -> List[Step]:
    ttype  = plan_info.get("target_type", "unknown")
    target = plan_info.get("main_target", "").strip()
    tasks  = plan_info.get("tasks", [])

    steps: List[Step] = []

    # common files
    subdomains_file = jdir / "subdomains.txt"
    alive_dns_file  = jdir / "alive_dns.txt"
    httpx_file      = jdir / "httpx.txt"
    waf_file        = jdir / "wafw00f.txt"
    whatweb_file    = jdir / "whatweb.txt"
    nuclei_file     = jdir / "nuclei.txt"
    nmap_file       = jdir / "nmap.txt"
    cert_file       = jdir / "cert.txt"

    def add(name, cmd, outfile=None):
        steps.append(Step(name=name, cmd=cmd, outfile=str(outfile) if outfile else None))

    if ttype in ("domain","url","mixed","unknown"):
        if "subdomain_enum" in tasks:
            add("Subdomain Enumeration (subfinder)",
                f"{TOOLS['subfinder']} -d {target} -all -silent -o {subdomains_file}",
                subdomains_file)

            wordlist = next(SECLISTS_DIR.glob("**/dns/subdomains-top1million-5000.txt"), None)
            if wordlist:
                add("Subdomain Brute (amass)",
                    f"{TOOLS['amass']} enum -d {target} -brute -w {wordlist} -o {jdir/'amass.txt'}",
                    jdir/'amass.txt')

        if "dns_resolve" in tasks:
            add("Resolve & grab A records (dnsx)",
                f"{TOOLS['dnsx']} -l {subdomains_file} -a -resp -o {alive_dns_file}",
                alive_dns_file)

        if "http_probe" in tasks:
            add("Probe HTTP(S) (httpx)",
                f"{TOOLS['httpx']} -l {alive_dns_file} -status-code -title -tech-detect -no-color -o {httpx_file}",
                httpx_file)

        if "waf_detect" in tasks:
            add("Detect WAF (wafw00f)",
                f"{TOOLS['wafw00f']} https://{target} > {waf_file}",
                waf_file)

        if "tech_fingerprint" in tasks:
            add("Tech Fingerprint (whatweb)",
                f"{TOOLS['whatweb']} -a 3 https://{target} > {whatweb_file}",
                whatweb_file)

        if "nuclei_scan" in tasks:
            add("Vulnerability Scan (nuclei)",
                f"{TOOLS['nuclei']} -l {httpx_file} -config {NUCLEI_CONFIG} "
                f"-t {NUCLEI_TEMPLATES} -no-color -o {nuclei_file}",
                nuclei_file)

    if ttype in ("ip","mixed") or "nmap_basic" in tasks:
        add("Port Scan (nmap)",
            f"{TOOLS['nmap']} -sV -T4 {target} -oN {nmap_file}",
            nmap_file)

    if ttype in ("ip","mixed") or "cert_info" in tasks:
        add("SSL Cert Info (nmap ssl-cert)",
            f"{TOOLS['nmap']} --script ssl-cert -p 443 {target} -oN {cert_file}",
            cert_file)

    return steps


# ------------------ Runner ------------------

async def stream_subprocess(cmd: str, timeout: int, ws, job_id: str, step_name: str):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def streamer(stream, label):
        collected = []
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(errors="ignore")
            collected.append(text)
            if ws:
                await ws.send_text(json.dumps({
                    "job": job_id, "step": step_name, "stream": label, "data": text
                }))
        return "".join(collected)

    try:
        out_task = asyncio.create_task(streamer(proc.stdout, "stdout"))
        err_task = asyncio.create_task(streamer(proc.stderr, "stderr"))

        await asyncio.wait_for(proc.wait(), timeout=timeout)
        stdout = await out_task
        stderr = await err_task
        return proc.returncode, stdout + stderr
    except asyncio.TimeoutError:
        proc.kill()
        return -1, f"Command '{cmd}' timed out after {timeout} seconds"


async def run_job(meta: JobMeta, ws=None):
    meta.started = datetime.utcnow().isoformat()
    save_meta(meta)

    for step in meta.plan:
        step.status = "running"
        save_meta(meta)
        if ws:
            await ws.send_text(json.dumps({"event": "step_start", "step": step.name}))

        code, output = await stream_subprocess(step.cmd, DEFAULT_TIMEOUT, ws, meta.job_id, step.name)

        step.exit_code = code
        if code == 0:
            step.status = "ok"
        elif code == -1 and "timed out" in output:
            step.status = "timeout"
            step.reason = "timeout"
        else:
            step.status = "fail"
            step.reason = f"exit {code}"

        # store outputs
        raw_path = job_dir(meta.job_id) / f"{slug(step.name)}.raw.txt"
        raw_path.write_text(strip_ansi(output))

        if step.outfile and not Path(step.outfile).exists():
            Path(step.outfile).write_text(output)

        save_meta(meta)

        if ws:
            await ws.send_text(json.dumps({
                "event": "step_end",
                "step": step.name,
                "status": step.status,
                "exit": code
            }))

    # Summary
    meta.finished = datetime.utcnow().isoformat()
    meta.summary = make_summary(meta)
    save_meta(meta)

    if ws:
        await ws.send_text(json.dumps({"event": "job_done"}))


# ------------------ Public API for main.py ------------------

def create_job(query: str, plan_info: Dict[str, Any], job_id: str) -> JobMeta:
    jd = job_dir(job_id)
    steps = build_steps(jd, plan_info)
    meta = JobMeta(job_id=job_id, query=query, plan=steps, started=None)
    save_meta(meta)
    return meta

def get_job_report(job_id: str):
    meta = load_meta(job_id)
    report = {
        "summary": meta.summary or "",
        "steps": [asdict(s) for s in meta.plan]
    }
    return meta, report

# ------------------ Summary ------------------

SUMMARY_PROMPT = """Summarize these recon steps & outputs:
- IPs/ports, tech stacks, interesting endpoints
- CDN/WAF usage
- Potential issues
- Count successes vs failures and reasons

JSON input:
"""

def make_summary(meta: JobMeta) -> str:
    data = {
        "query": meta.query,
        "steps": [asdict(s) for s in meta.plan]
    }
    raw = call_ollama(SUMMARY_PROMPT + json.dumps(data)[:8000])
    return raw.strip()

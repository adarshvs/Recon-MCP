# agent/utils.py
import asyncio
import re
from pathlib import Path
from django.conf import settings

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s or "")

def job_dir_for(job_id) -> Path:
    p = settings.JOBS_DIR / str(job_id)
    p.mkdir(parents=True, exist_ok=True)
    return p

async def run_cmd(cmd: str, timeout: int):
    """
    Runs a shell command asynchronously and returns (exit_code, stdout, stderr).
    On timeout, returns (-1, "", f'timed out ...').
    """
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode,
            stdout.decode(errors="ignore"),
            stderr.decode(errors="ignore"),
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return -1, "", f"Command '{cmd}' timed out after {timeout} seconds"

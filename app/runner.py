# app/runner.py
import asyncio
import subprocess
from typing import AsyncGenerator, Dict, List
from datetime import datetime

# In-memory store for job results
JOBS: Dict[str, Dict] = {}

async def stream_command(cmd: str) -> AsyncGenerator[str, None]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    assert proc.stdout
    async for line in proc.stdout:
        yield line.decode("utf-8", errors="ignore")
    await proc.wait()

async def run_job(job_id: str, steps: List[Dict], websocket_send):
    """
    Run each command, stream output to websocket, record success/failure.
    websocket_send: callable to send dict as JSON-string
    """
    JOBS[job_id] = {
        "started": datetime.utcnow().isoformat(),
        "finished": None,
        "steps": [],
    }

    for idx, step in enumerate(steps, start=1):
        name = step["name"]
        cmd  = step["cmd"]
        outfile = step.get("outfile")

        step_rec = {
            "name": name,
            "cmd": cmd,
            "outfile": outfile,
            "success": False,
            "error": "",
            "raw_output": ""
        }

        await websocket_send({"event":"step_start","idx":idx,"name":name,"cmd":cmd})

        buf = []
        try:
            async for line in stream_command(cmd):
                buf.append(line)
                await websocket_send({"event":"stdout","idx":idx,"line":line})
            full_out = "".join(buf)
            step_rec["raw_output"] = full_out
            step_rec["success"] = True
        except Exception as e:
            step_rec["error"] = str(e)
            await websocket_send({"event":"error","idx":idx,"error":str(e)})

        JOBS[job_id]["steps"].append(step_rec)
        await websocket_send({"event":"step_done","idx":idx,"success":step_rec["success"]})

    JOBS[job_id]["finished"] = datetime.utcnow().isoformat()
    await websocket_send({"event":"job_done"})

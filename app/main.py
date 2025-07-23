# app/main.py
import json
import os
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.toolchain import decide_intent_target
from app.pipeline import make_pipeline
from app.runner import run_job, JOBS
from app.mcp_core import format_output_with_ollama
from app.config import WORK_DIR

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start", response_class=HTMLResponse)
async def start(request: Request, query: str = Form(...)):
    parsed = decide_intent_target(query)
    plan = make_pipeline(query, parsed["target"], parsed["intent"])
    # Render dashboard page with job info, will open WS
    return templates.TemplateResponse("job.html", {
        "request": request,
        "query": query,
        "job_id": plan["job_id"],
        "plan": json.dumps(plan["steps"], indent=2)
    })

@app.websocket("/ws/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    await websocket.accept()

    async def send_json(payload):
        await websocket.send_text(json.dumps(payload))

    try:
        # First message from client should contain 'steps'
        data = await websocket.receive_text()
        payload = json.loads(data)
        steps = payload["steps"]
        # run and stream
        await run_job(job_id, steps, send_json)
    except WebSocketDisconnect:
        pass

@app.get("/report/{job_id}", response_class=HTMLResponse)
async def report(request: Request, job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return HTMLResponse("No such job", status_code=404)

    # Build a human-readable report (could be improved with templates)
    successes = []
    fails = []
    for s in job["steps"]:
        if s["success"]:
            successes.append(s)
        else:
            fails.append(s)

    # Combine raw outputs & ask LLM for global summary
    raw_all = "\n\n".join([f"== {st['name']} ==\n{st['raw_output']}" for st in successes])
    context = f"User requested a full recon job {job_id}"
    global_summary = format_output_with_ollama(raw_all, context) if raw_all else ""

    return templates.TemplateResponse("report.html", {
        "request": request,
        "job": job,
        "job_id": job_id,
        "successes": successes,
        "fails": fails,
        "global_summary": global_summary
    })

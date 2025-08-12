import uuid
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .toolchain import (
    classify_and_plan, create_job, run_job,
    get_job_report
)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start", response_class=HTMLResponse)
async def start_job(request: Request):
    form = await request.form()
    query = form.get("query", "").strip()
    jid = str(uuid.uuid4())

    plan_info = classify_and_plan(query)
    meta = create_job(query, plan_info, jid)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "job_id": jid,
        "query": query,
        "plan_json": plan_info
    })

@app.websocket("/ws/{job_id}")
async def ws_job(ws: WebSocket, job_id: str):
    await ws.accept()
    try:
        # load meta and run
        from .toolchain import load_meta   # lazy import to avoid cycles
        meta = load_meta(job_id)
        await run_job(meta, ws)
    except WebSocketDisconnect:
        # client closed, just stop streaming
        return
    except Exception as e:
        await ws.send_text(f'{{"event":"error","msg":"{str(e)}"}}')
    finally:
        await ws.close()

@app.get("/report/{job_id}", response_class=HTMLResponse)
async def report(job_id: str, request: Request):
    meta, report = get_job_report(job_id)
    return templates.TemplateResponse("report.html", {
        "request": request,
        "job_id": job_id,
        "meta": meta,
        "report": report
    })

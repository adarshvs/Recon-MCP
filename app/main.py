from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.toolchain import process_query

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def form_post(request: Request, query: str = Form(...)):
    result = process_query(query)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": query,
        "llm_response": result["llm_response"],
        "command": result["command"],
        "output": result["output"],
        "formatted_output": result["formatted_output"]
    })

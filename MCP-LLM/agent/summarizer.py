# agent/summarizer.py
from asgiref.sync import sync_to_async
from .models import Job

async def summarize_job(job_id: str) -> str:
    # TODO: plug in your local LLM later
    return "Summary not implemented yet."

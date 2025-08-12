import asyncio
import os
import re
from pathlib import Path
from typing import Tuple

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from .models import Job, Step, Status, JobStatus
from .utils import job_dir_for, strip_ansi  # you already have these two


ANSI_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


async def run_job(job_id: str, channel_layer, group_name: str):
    """
    Executes all steps for a Job in order, streaming output to a channels group
    so every connected browser tab can see the live console.

    We wrap **all ORM access in sync_to_async** to avoid blocking the event loop.
    """
    try:
        job = await _get_job(job_id)

        steps = await _get_steps(job)

        for step in steps:
            await _step_mark_running(step, job, channel_layer, group_name)

            code, combined = await _stream_subprocess(
                step.cmd,
                timeout=getattr(settings, "DEFAULT_TIMEOUT", 180),
                channel_layer=channel_layer,
                group_name=group_name,
                step_name=step.name,
            )

            await _step_finalize(step, code, combined)

            # Inform UI
            await channel_layer.group_send(
                group_name,
                {
                    "type": "job.event",
                    "payload": {
                        "event": "step_end",
                        "step": step.name,
                        "status": step.status,
                        "exit": step.exit_code,
                    },
                },
            )

        # Mark job finished
        await _finish_job(job_id, JobStatus.DONE)

        await channel_layer.group_send(
            group_name,
            {
                "type": "job.event",
                "payload": {"event": "job_done", "status": JobStatus.DONE},
            },
        )

    except Exception as e:
        # In case the runner itself explodes, mark job failed
        await _finish_job(job_id, JobStatus.FAIL)
        await channel_layer.group_send(
            group_name,
            {
                "type": "job.event",
                "payload": {"event": "job_done", "status": JobStatus.FAIL, "error": str(e)},
            },
        )


# ----------------- Step lifecycle helpers ----------------- #

async def _get_job(job_id: str) -> Job:
    return await sync_to_async(Job.objects.get)(id=job_id)


async def _get_steps(job: Job):
    return await sync_to_async(list)(job.steps.all())


async def _step_mark_running(step: Step, job: Job, channel_layer, group_name: str):
    step.status = Status.RUNNING
    step.started_at = timezone.now()
    await sync_to_async(step.save)(update_fields=["status", "started_at"])

    # Emit step_start
    await channel_layer.group_send(
        group_name,
        {
            "type": "job.event",
            "payload": {"event": "step_start", "step": step.name},
        },
    )


async def _step_finalize(step: Step, exit_code: int, output: str):
    if exit_code == 0:
        step.status = Status.OK
    elif exit_code == -1:
        step.status = Status.TIMEOUT
        step.reason = "timeout"
    else:
        step.status = Status.FAIL
        step.reason = f"exit {exit_code}"

    step.exit_code = exit_code
    step.finished_at = timezone.now()

    # Save raw output to files
    jd = job_dir_for(step.job_id)
    safe_name = _slug(step.name)
    raw_path = Path(jd) / f"{safe_name}.raw.txt"
    raw_path.write_text(output, encoding="utf-8", errors="ignore")

    clean_path = Path(jd) / f"{safe_name}.txt"
    clean_path.write_text(strip_ansi(output), encoding="utf-8", errors="ignore")

    step.stdout_path = str(clean_path)
    # You could split stdout/stderr if you want. For now both go to same file.

    await sync_to_async(step.save)(
        update_fields=[
            "status",
            "exit_code",
            "reason",
            "finished_at",
            "stdout_path",
        ]
    )


async def _finish_job(job_id: str, status: str):
    job = await _get_job(job_id)
    job.status = status
    job.finished_at = timezone.now()
    await sync_to_async(job.save)(update_fields=["status", "finished_at"])


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ----------------- Process runner ----------------- #

async def _stream_subprocess(
    cmd: str,
    timeout: int,
    channel_layer,
    group_name: str,
    step_name: str,
) -> Tuple[int, str]:
    """
    Runs `cmd` and streams both stdout & stderr lines to WS group.
    Returns (exit_code, combined_output).
    """
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy(),
    )

    combined = []

    async def reader(stream, label):
        async for raw_bytes in stream:
            text = raw_bytes.decode(errors="ignore")
            combined.append(text)
            await channel_layer.group_send(
                group_name,
                {
                    "type": "job.event",
                    "payload": {
                        "event": "stream",
                        "step": step_name,
                        "stream": label,
                        "data": text,
                    },
                },
            )

    try:
        out_task = asyncio.create_task(reader(proc.stdout, "stdout"))
        err_task = asyncio.create_task(reader(proc.stderr, "stderr"))

        await asyncio.wait_for(proc.wait(), timeout=timeout)
        await out_task
        await err_task
        return proc.returncode, "".join(combined)

    except asyncio.TimeoutError:
        proc.kill()
        return -1, f"Command '{cmd}' timed out after {timeout} seconds"

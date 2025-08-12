import asyncio
import json
import uuid

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

from .models import Job, JobStatus
from .jobrunner import run_job


class JobConsumer(AsyncWebsocketConsumer):
    """
    WebSocket per job. When the browser connects, if the job is still pending
    we mark it RUNNING and spawn the async runner that executes all steps and
    streams output back over this socket (via a channel layer group).
    """

    async def connect(self):
        try:
            job_id_raw = self.scope["url_route"]["kwargs"]["job_id"]
            self.job_id = str(job_id_raw)
            # group where the runner will publish messages
            self.group_name = f"job_{self.job_id}"

            # Join group
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
            await self.send_json({"event": "connected"})

            # Start if needed
            await self._start_if_pending()
        except Exception as e:
            await self.accept()
            await self.send_json({"event": "error", "detail": str(e)})
            await self.close()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # (MVP) We don't accept client->server commands yet.
        # Reserve for cancel/pause/etc.
        pass

    # ---------------- internal helpers ----------------

    async def _start_if_pending(self):
        job = await sync_to_async(Job.objects.select_related)(None)  # no-op to get ORM loaded
        job = await sync_to_async(Job.objects.get)(id=uuid.UUID(self.job_id))

        if job.status == JobStatus.PENDING:
            # Mark running
            job.status = JobStatus.RUNNING
            job.started_at = timezone.now()
            await sync_to_async(job.save)(update_fields=["status", "started_at"])

            # Fire-and-forget runner
            asyncio.create_task(
                run_job(
                    job_id=self.job_id,
                    channel_layer=self.channel_layer,
                    group_name=self.group_name,
                )
            )

    # --------------- messages FROM the runner ---------------

    async def job_event(self, event):
        """
        Generic handler – the runner sends all events with type='job.event'
        and a JSON-able 'payload'. We just forward to the browser.
        """
        await self.send_json(event["payload"])

    # --------------- utility ----------------

    async def send_json(self, data: dict):
        await super().send(text_data=json.dumps(data))

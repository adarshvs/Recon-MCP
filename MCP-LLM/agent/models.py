import uuid
from django.db import models

class TargetType(models.TextChoices):
    DOMAIN = "domain"
    IP = "ip"
    ASN = "asn"
    URL = "url"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class Status(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAIL = "fail"
    TIMEOUT = "timeout"

class JobStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAIL = "fail"

class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(max_length=512)
    target = models.CharField(max_length=255, blank=True)
    target_type = models.CharField(max_length=16, choices=TargetType.choices, default=TargetType.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.PENDING)
    summary = models.TextField(blank=True)

    def __str__(self):
        return f"{self.id} - {self.query}"

class Step(models.Model):
    job = models.ForeignKey(Job, related_name="steps", on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    cmd = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    exit_code = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    stdout_path = models.TextField(blank=True)
    stderr_path = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.name}"

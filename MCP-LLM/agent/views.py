from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from pathlib import Path
from .models import Job, Step, JobStatus, Status
from .forms import NewJobForm
from .planner import plan_for, build_steps
from .utils import job_dir_for


def console(request):
    return render(request, "agent/console.html")

def jobs_list(request):
    jobs = Job.objects.order_by("-created_at")[:50]
    return render(request, "agent/jobs_list.html", {"jobs": jobs})

def new_job(request):
    if request.method == "POST":
        form = NewJobForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data["query"]
            plan = plan_for(query)

            job = Job.objects.create(
                query=query,
                target=plan["main_target"],
                target_type=plan["target_type"],
                status=JobStatus.PENDING,
            )

            jd = job_dir_for(job.id)
            steps = build_steps(jd, plan)
            for i, s in enumerate(steps, 1):
                Step.objects.create(
                    job=job,
                    order=i,
                    name=s["name"],
                    cmd=s["cmd"]
                )

            return redirect(reverse("job_detail", args=[str(job.id)]))
    else:
        form = NewJobForm()
    return render(request, "agent/new_job.html", {"form": form})

def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, "agent/job_detail.html", {"job": job})

def job_report(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, "agent/report.html", {"job": job})
from django.urls import path
from .views import console, jobs_list, new_job, job_detail, job_report

urlpatterns = [
    path("", console, name="console"),
    path("", jobs_list, name="jobs_list"),
    path("new/", new_job, name="new_job"),
    path("jobs/<uuid:job_id>/", job_detail, name="job_detail"),
    path("jobs/<uuid:job_id>/report/", job_report, name="job_report"),
    path("console/", console, name="console"),  # keep MVP console   
]

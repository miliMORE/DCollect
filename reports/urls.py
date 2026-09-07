from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.centre, name="centre"),
    path("county/<int:pk>/pack/", views.county_pack, name="county_pack"),
    path("county/<int:pk>/complete/", views.county_complete, name="county_complete"),
    path("county/<int:pk>/individuals/", views.county_individuals, name="county_individuals"),
    path("progress/", views.progress_report, name="progress"),
    path("questionnaire-extract/", views.questionnaire_extract, name="questionnaire_extract"),
    path("market-position/", views.analysis_workbook, name="analysis_workbook"),
    path("individual-responses/", views.individuals_extract, name="individuals_extract"),
    path("job-groups/", views.job_group_extract, name="job_groups"),
    path("benefits/", views.benefits_extract, name="benefits"),
    path("documents/", views.documents_register, name="documents"),
]

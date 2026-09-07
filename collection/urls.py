from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "collection"

urlpatterns = [
    path("", login_required(views.dashboard), name="dashboard"),
    path("help/", login_required(views.help_centre), name="help"),
    path("s/<str:token>/", views.public_survey, name="public_survey"),
    path("s/<str:token>/thanks/", views.public_survey_thanks, name="survey_thanks"),
    path("staff-survey/", views.staff_survey_links, name="staff_links"),
    path("cases/", views.case_list, name="cases"),
    path("questionnaires/", views.questionnaire_list, name="questionnaires"),
    path("cases/open-period/", views.open_period_cases, name="open_period"),
    path("cases/<int:pk>/", views.case_hub, name="case_hub"),
    path("cases/<int:pk>/individuals/", views.individual_responses, name="individuals"),
    path("cases/<int:pk>/questionnaire/", views.questionnaire, name="questionnaire"),
    path("cases/<int:pk>/jobs/", views.jobs, name="jobs"),
    path("cases/<int:pk>/benefits/", views.benefits, name="benefits"),
    path("cases/<int:pk>/documents/", views.documents, name="documents"),
    path("cases/<int:pk>/documents/zip/", views.download_case_files, name="documents_zip"),
    path("cases/<int:pk>/documents/<int:doc_id>/download/", views.download_document, name="document_download"),
    path(
        "cases/<int:pk>/documents/<int:doc_id>/files/<int:file_id>/download/",
        views.download_document_file,
        name="document_file_download",
    ),
    path(
        "cases/<int:pk>/documents/<int:doc_id>/files/<int:file_id>/delete/",
        views.delete_document_file,
        name="document_file_delete",
    ),
    path("cases/<int:pk>/validation/", views.validation, name="validation"),
    path("cases/<int:pk>/certify/", views.certify, name="certify"),
    path("cases/<int:pk>/submit/", views.submit_case, name="submit"),
    path("cases/<int:pk>/reopen/", views.reopen_case, name="reopen"),
    path("cases/<int:pk>/validate/", views.validate_case, name="validate"),
    path("cases/<int:pk>/clarifications/", views.clarifications, name="clarifications"),
    path("cases/<int:pk>/clarifications/resolve/", views.resolve_clarification, name="resolve"),
    path("comparators/", views.comparator_list, name="comparators"),
    path("comparators/<int:org_id>/edit/", views.comparator_edit, name="comparator_edit"),
    path("comparators/<int:org_id>/delete/", views.comparator_delete, name="comparator_delete"),
    path("comparators/<int:org_id>/pay/", views.comparator_pay, name="comparator_pay"),
    path("comparators/<int:org_id>/benefits/", views.comparator_benefits, name="comparator_benefits"),
    path("analysis/", views.analysis, name="analysis"),
]

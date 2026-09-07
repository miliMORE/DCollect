from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.settings_home, name="settings"),
    path("periods/", views.period_list, name="periods"),
    path("periods/new/", views.period_edit, name="period_new"),
    path("periods/<int:pk>/", views.period_edit, name="period_edit"),
    path("periods/<int:pk>/activate/", views.period_activate, name="period_activate"),
    path("lists/", views.option_list, name="options"),
    path("lists/new/", views.option_edit, name="option_new"),
    path("lists/<int:pk>/", views.option_edit, name="option_edit"),
    path("forms/", views.forms_home, name="forms"),
    path("questions/", views.question_list, name="questions"),
    path("questions/new/", views.question_edit, name="question_new"),
    path("questions/<int:pk>/", views.question_edit, name="question_edit"),
    path("questions/<int:pk>/delete/", views.question_delete, name="question_delete"),
    path("<slug:key>/", views.catalog_list, name="catalog_list"),
    path("<slug:key>/new/", views.catalog_edit, name="catalog_new"),
    path("<slug:key>/<int:pk>/", views.catalog_edit, name="catalog_edit"),
]

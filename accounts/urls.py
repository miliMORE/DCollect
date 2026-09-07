from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.PlatformLoginView.as_view(), name="login"),
    path("logout/", views.PlatformLogoutView.as_view(), name="logout"),
    path("password/", views.password_change, name="password_change"),
    path("users/", views.user_list, name="users"),
    path("users/new/", views.user_edit, name="user_new"),
    path("users/create-county-logins/", views.create_missing_county_users, name="create_county_users"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle_active, name="user_toggle"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path("manual/", views.user_manual, name="user_manual"),
    path("audit/", views.audit_trail, name="audit"),
    path("audit/export/", views.audit_export, name="audit_export"),
    path("data/", views.data_admin, name="data"),
    path("data/purge-county/", views.purge_county, name="purge_county"),
    path("data/purge-user/", views.purge_user_data, name="purge_user_data"),
    path("data/reset/", views.reset_data, name="reset_data"),
]

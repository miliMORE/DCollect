from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "DCollect administration"
admin.site.site_title = "DCollect admin"
admin.site.index_title = "Catalogues, users and survey setup"


def health(_request):
    return JsonResponse({"status": "ok", "service": "dcollect"})


@login_required
def protected_media(request, path):
    """County uploads are confidential. Counties download via the file page."""
    if getattr(request.user, "is_county_role", False) and not request.user.is_superuser:
        return HttpResponseForbidden("Download files from the county file Documents page.")
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("accounts/", include("accounts.urls")),
    path("reports/", include("reports.urls")),
    path("setup/", include("catalog.urls")),
    path("", include("collection.urls")),
    re_path(r"^media/(?P<path>.*)$", protected_media),
]

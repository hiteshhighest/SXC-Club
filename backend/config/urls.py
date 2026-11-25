import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path
from django.views.decorators.http import require_safe
from clubs.views import csrf_token

@require_safe
def serve_media(request, media_path):
    try:
        media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
        file_path = (media_root / media_path).resolve(strict=True)
        file_path.relative_to(media_root)
    except (OSError, ValueError):
        raise Http404
    if not file_path.is_file():
        raise Http404
    content_type, _ = mimetypes.guess_type(file_path.name)
    response = FileResponse(file_path.open("rb"), content_type=content_type or "application/octet-stream")
    response["X-Content-Type-Options"] = "nosniff"
    return response

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/csrf/", csrf_token),
    path("api/", include("clubs.urls")),
    path("media/<path:media_path>", serve_media),
]

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

# We only import the webhook here because it must bypass i18n
from core.views import telegram_webhook

urlpatterns = [
    # Static & Webhook Endpoints
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("img/favicon.ico")),
    ),
    path("reload/", include("django_browser_reload.urls")),  # Hot-reloading in dev
    path("telegram-webhook/", telegram_webhook, name="telegram_webhook"),
]

urlpatterns += i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    # 🌍 All Distributed Application Routes
    path("", include("core.urls")),  # Contains Home Page ("")
    path("", include("accounts.urls")),  # Contains Auth & Onboarding (/login, /join)
    path("", include("workspace.urls")),  # Contains /workspace, /teams, /challenges
    path("", include("profiles.urls")),  # Contains /p/..., /company/..., /dashboard/...
    path("ops/", include("operations.urls")),  # Contains Operations God-Mode (/ops/...)
    path("nexus/", include("network.urls")),  # Your already clean Network App
    path(
        "opportunities/", include("opportunities.urls")
    ),  # Your already clean Opportunities App
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

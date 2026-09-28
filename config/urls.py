from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1 = [
    path("auth/", include("apps.users.urls")),
    path("", include("apps.users.admin_urls")),
    path("", include("apps.movies.urls")),
    path("", include("apps.showtimes.urls")),
    path("", include("apps.reservations.urls")),
    path("", include("apps.payments.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

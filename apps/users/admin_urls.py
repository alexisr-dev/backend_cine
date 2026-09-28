from django.urls import path

from .views import AdminUsuarioDetailView, AdminUsuarioListView

urlpatterns = [
    path("admin/users", AdminUsuarioListView.as_view(), name="admin-usuario-list"),
    path(
        "admin/users/<int:pk>",
        AdminUsuarioDetailView.as_view(),
        name="admin-usuario-detail",
    ),
]

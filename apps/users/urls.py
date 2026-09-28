from django.urls import path

from .views import CambiarPasswordView, LoginView, PerfilView, RefreshView, RegistroView

urlpatterns = [
    path("register", RegistroView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("me", PerfilView.as_view(), name="auth-me"),
    path("password", CambiarPasswordView.as_view(), name="auth-password"),
]

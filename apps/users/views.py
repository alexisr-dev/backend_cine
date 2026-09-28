from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.exceptions import OperacionInvalida

from .permissions import IsAdmin
from .serializers import (
    CambiarPasswordSerializer,
    LoginSerializer,
    RegistroSerializer,
    UsuarioAdminCreateSerializer,
    UsuarioAdminSerializer,
    UsuarioAdminUpdateSerializer,
    UsuarioSerializer,
)

Usuario = get_user_model()


class SesionSerializer(serializers.Serializer):
    usuario = UsuarioSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()


@extend_schema(request=RegistroSerializer, responses={201: SesionSerializer})
class RegistroView(generics.CreateAPIView):
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]
    queryset = Usuario.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        tokens = LoginSerializer.get_token(usuario)
        return Response(
            {
                "usuario": UsuarioSerializer(usuario).data,
                "access": str(tokens.access_token),
                "refresh": str(tokens),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class PerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class MensajeSerializer(serializers.Serializer):
    mensaje = serializers.CharField()


@extend_schema(
    request=CambiarPasswordSerializer,
    responses={200: OpenApiResponse(response=MensajeSerializer)},
)
class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CambiarPasswordSerializer

    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"mensaje": "Contrasena actualizada"}, status=status.HTTP_200_OK)


class AdminUsuarioListView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    queryset = Usuario.objects.all().order_by("-created_at")
    search_fields = ("email", "nombre", "apellido")

    def get_serializer_class(self):
        return UsuarioAdminCreateSerializer if self.request.method == "POST" else UsuarioAdminSerializer

    def create(self, request, *args, **kwargs):
        entrada = UsuarioAdminCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = entrada.save()
        return Response(UsuarioAdminSerializer(usuario).data, status=status.HTTP_201_CREATED)


class AdminUsuarioDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsAdmin]
    queryset = Usuario.objects.all()

    def update(self, request, *args, **kwargs):
        instancia = self.get_object()
        if instancia.id == request.user.id:
            raise OperacionInvalida("No puedes cambiar tu propio rol o estado")
        parcial = kwargs.pop("partial", False)
        entrada = UsuarioAdminUpdateSerializer(instancia, data=request.data, partial=parcial)
        entrada.is_valid(raise_exception=True)
        usuario = entrada.save()
        return Response(UsuarioAdminSerializer(usuario).data)

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "rol",
            "email_verificado",
            "created_at",
        )
        read_only_fields = ("id", "rol", "email_verificado", "created_at")


class UsuarioAdminSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "rol",
            "is_active",
            "email_verificado",
            "created_at",
        )
        read_only_fields = (
            "id",
            "email",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "email_verificado",
            "created_at",
        )


class UsuarioAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("rol", "is_active")


class UsuarioAdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = ("email", "nombre", "apellido", "telefono", "rol", "password")

    def validate_email(self, value):
        email = value.lower().strip()
        if Usuario.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este email")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = ("email", "nombre", "apellido", "telefono", "password", "password_confirm")

    def validate_email(self, value):
        email = value.lower().strip()
        if Usuario.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este email")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Las contrasenas no coinciden"})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    username_field = Usuario.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["rol"] = user.rol
        token["nombre"] = user.nombre
        return token

    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, "").lower().strip()
        data = super().validate(attrs)
        data["usuario"] = UsuarioSerializer(self.user).data
        return data


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True, min_length=8)

    def validate_password_actual(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contrasena actual no es correcta")
        return value

    def validate_password_nueva(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["password_nueva"])
        usuario.save(update_fields=["password", "updated_at"])
        return usuario

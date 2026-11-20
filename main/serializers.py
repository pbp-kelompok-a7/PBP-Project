from django.contrib.auth.models import User
from rest_framework import serializers

from .decorators import is_merchant
from .models import ConsumerProfile, UserProfile, MerchantLocationIntegrator


def get_user_role(user):
    """Mengembalikan peran pengguna: admin, merchant, consumer, atau guest."""
    if not user or not user.is_authenticated:
        return "guest"
    if user.is_superuser or user.is_staff:
        return "admin"
    if is_merchant(user):
        return "merchant"
    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.role:
        return profile.role.lower()
    return "consumer"


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_staff",
            "is_superuser",
        ]

    def get_role(self, obj):
        return get_user_role(obj)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=""
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username sudah terdaftar. Silakan pilih username lain.")
        return value

    def validate(self, data):
        pwd = data.get("password")
        pwd_confirm = data.get("password_confirm")
        if pwd_confirm and pwd != pwd_confirm:
            raise serializers.ValidationError({"password_confirm": "Konfirmasi password tidak cocok."})
        return data

    def create(self, validated_data):
        username = validated_data["username"]
        password = validated_data["password"]
        email = validated_data.get("email", "")
        user = User.objects.create_user(username=username, password=password, email=email)
        UserProfile.objects.get_or_create(user=user, defaults={"role": UserProfile.Role.CONSUMER})
        ConsumerProfile.objects.get_or_create(user=user)
        return user
    
class MerchantLocationSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    class Meta:
        model = MerchantLocationIntegrator
        fields = [
            "id_merchant",
            "name_merchant",
            "address",
            "latitude",
            "longitude",
        ]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

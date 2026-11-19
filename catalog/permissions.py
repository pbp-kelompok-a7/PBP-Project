from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, SAFE_METHODS


# dipakai di endpoint review: lihat boleh siapa aja, tapi nulis review harus login
class IsLoggedInOrReadOnly(BasePermission):
    message = "Kamu harus login dulu untuk menulis review."

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_authenticated


# login di flutter (pbp_django_auth) pakai cookie session tapi gak ngirim csrf token,
# jadi khusus api catalog pengecekan csrf-nya dimatiin biar request dari flutter gak ditolak
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

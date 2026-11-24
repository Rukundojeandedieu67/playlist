from rest_framework.permissions import BasePermission


class IsPlaylistUser(BasePermission):
    message = "A signed-in user account is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "user"
        )

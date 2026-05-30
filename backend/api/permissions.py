from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsStaffOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user and request.user.is_staff
            or request.method in SAFE_METHODS
        )


class IsAuthorStaffOrReadOnlyObject(BasePermission):

    def has_object_permission(self, request, view, obj):
        return (
            request.method in SAFE_METHODS
            or obj.author == request.user
            or request.user.is_staff
        )

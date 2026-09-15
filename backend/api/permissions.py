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


class CanPublishRecipesOrReadOnly(BasePermission):
    message = (
        'У вас нет права на публикацию рецептов. Обратитесь к '
        'администратору сайта, чтобы получить доступ.'
    )
    publish_actions = ('create', 'update', 'partial_update', 'destroy')

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS
            or view.action not in self.publish_actions
            or bool(
                request.user
                and request.user.is_authenticated
                and (request.user.is_staff
                     or request.user.can_publish_recipes)
            )
        )

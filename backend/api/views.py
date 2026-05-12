from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)
from common.constants import SHORT_CODE_MAX_LENGTH
from common.permissions import IsAuthorStaffOrReadOnly, IsStaffOrReadOnly
from common.utils import generate_short_code
from recipes.models import Ingredient, Recipe, RecipeShortLink, Tag

User = get_user_model()


class UserViewSet(DjoserUserViewSet):

    def get_permissions(self):
        if self.action in ('retrieve', 'list', 'create'):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    @action(detail=False, methods=('put', 'delete'), url_path='me/avatar')
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data)

        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = PageNumberPagination
    permission_classes = (IsAuthorStaffOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        max_attempts = 100
        for attempt in range(max_attempts):
            try:
                short_link, created = RecipeShortLink.objects.get_or_create(
                    recipe=recipe,
                    defaults={'code': generate_short_code(SHORT_CODE_MAX_LENGTH)}
                )
                break
            except IntegrityError as e:
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise e

        short_url = f'{settings.SITE_URL}/s/{short_link.code}'

        return Response({'short-link': short_url})


class TagViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (IsStaffOrReadOnly,)


class IngredientViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (IsStaffOrReadOnly,)


def short_link_redirect(request, code):
    print("HIT SHORT LINK:", code)
    short_link = get_object_or_404(RecipeShortLink, code=code)

    return HttpResponseRedirect(
        f'/recipes/{short_link.recipe.id}'
    )

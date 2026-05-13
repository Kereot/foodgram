from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.serializers import (
    CustomUserCreateSerializer,
    CustomUserSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    UserFollowSerializer,
)
from common.constants import SHORT_CODE_MAX_LENGTH
from common.permissions import IsAuthorStaffOrReadOnly, IsStaffOrReadOnly
from common.utils import generate_short_code
from recipes.models import Ingredient, Recipe, RecipeShortLink, Tag
from users.models import Follow

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'subscriptions':
            return UserFollowSerializer
        return CustomUserSerializer

    def get_permissions(self):
        if self.action in ('retrieve', 'list', 'create'):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)

        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow, created = Follow.objects.get_or_create(
            user=request.user,
            author=author
        )

        if not created:
            return Response(
                {'errors': 'Вы уже подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(author)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)

        deleted, _ = Follow.objects.filter(
            user=request.user,
            author=author
        ).delete()

        if not deleted:
            return Response(
                {'errors': 'Вы не были подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        recipes_limit = request.query_params.get('recipes_limit')
        recipes_qs = Recipe.objects.only(
            'id',
            'name',
            'image',
            'cooking_time',
            'author_id'
        ).order_by('-id')

        users = User.objects.filter(
            following__user=request.user
        ).distinct().prefetch_related(
            Prefetch('recipes', queryset=recipes_qs)
        ).order_by('id')

        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
                context={
                    'request': request,
                    'recipes_limit': recipes_limit
                }
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            users,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return Response(serializer.data)

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

    def get_queryset(self):
        queryset = super().get_queryset()
        author_id = self.request.query_params.get('author')

        if author_id:
            queryset = queryset.filter(author_id=author_id)

        return queryset

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

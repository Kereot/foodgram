from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Prefetch, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from djoser import serializers
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.paginators import LimitOnlyPagination
from api.serializers import (AvatarSerializer, CustomUserCreateSerializer,
                             CustomUserSerializer, IngredientSerializer,
                             RecipeBasicReadSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, TagSerializer,
                             UserFollowSerializer)
from common.constants import SHORT_CODE_MAX_LENGTH
from common.permissions import IsAuthorStaffOrReadOnly
from common.utils import build_pdf, build_txt, generate_short_code
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            RecipeShortLink, ShoppingList, Tag)
from users.models import Follow

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'set_password':
            return serializers.SetPasswordSerializer
        if self.action == 'avatar':
            return AvatarSerializer
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

        serializer = UserFollowSerializer(
            author,
            context={'request': request}
        )
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
    pagination_class = LimitOnlyPagination
    permission_classes = (IsAuthorStaffOrReadOnly,)
    filterset_class = RecipeFilter
    ordering_fields = ('id', 'name')
    ordering = ('-id',)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        author_id = self.request.query_params.get('author')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')

        if author_id:
            queryset = queryset.filter(author_id=author_id)
        if is_favorited == '1' and user.is_authenticated:
            queryset = queryset.filter(favorites__user=self.request.user)
        if is_in_shopping_cart == '1' and user.is_authenticated:
            queryset = queryset.filter(shoppinglists__user=self.request.user)

        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def _handle_recipe_relation(
        self,
        request,
        recipe_id,
        model
    ):
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if request.method == 'POST':
            obj, created = model.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )

            if not created:
                return Response(
                    {'errors': 'Рецепт уже добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeBasicReadSerializer(
                recipe,
                context={'request': request}
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            deleted_count, _ = model.objects.filter(
                user=request.user,
                recipe=recipe
            ).delete()

            if not deleted_count:
                return Response(
                    {'errors': 'Рецепт не найден в списке'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link'
    )
    def get_short_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        max_attempts = 100
        for attempt in range(max_attempts):
            try:
                short_link, created = RecipeShortLink.objects.get_or_create(
                    recipe=recipe,
                    defaults={
                        'code': generate_short_code(SHORT_CODE_MAX_LENGTH)
                    }
                )
                break
            except IntegrityError as e:
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise e

        short_url = f'{settings.SITE_URL}/s/{short_link.code}'

        return Response({'short-link': short_url})

    @action(
        detail=True,
        methods=('post', 'delete')
    )
    def favorite(self, request, pk=None):
        return self._handle_recipe_relation(
            request=request,
            recipe_id=pk,
            model=Favorite
        )

    @action(
        detail=True,
        methods=('post', 'delete')
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_recipe_relation(
            request=request,
            recipe_id=pk,
            model=ShoppingList
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        file_format = request.query_params.get('format', 'pdf')
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shoppinglists__user=request.user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        if file_format == 'txt':
            content_with_bom = '\ufeff' + build_txt(ingredients)

            return HttpResponse(
                content_with_bom.encode('utf-8'),
                content_type='text/plain',
                headers={
                    'Content-Disposition':
                        'attachment; filename="shopping_list.txt"'
                }
            )

        if file_format == 'pdf':
            buffer = build_pdf(ingredients)

            return HttpResponse(
                buffer,
                content_type='application/pdf',
                headers={
                    'Content-Disposition':
                        'attachment; filename="shopping_list.pdf"'
                }
            )

        return Response(
            {'errors': 'Unsupported format (txt, pdf)'},
            status=400
        )


class TagViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class IngredientViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('name',)
    pagination_class = None
    permission_classes = (AllowAny,)


def short_link_redirect(request, code):
    short_link = get_object_or_404(RecipeShortLink, code=code)

    return HttpResponseRedirect(
        f'/recipes/{short_link.recipe.id}'
    )

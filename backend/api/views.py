from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Prefetch, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.paginators import LimitOnlyPagination
from api.permissions import IsAuthorStaffOrReadOnlyObject
from api.serializers import (AvatarSerializer, IngredientSerializer,
                             RecipeBasicReadSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, TagSerializer,
                             UserFollowSerializer)
from common.constants import (MAX_COLLISION_ATTEMPTS, RECIPE_FRONTEND_PATH,
                              SHORT_CODE_MAX_LENGTH)
from common.utils import build_shopping_list_response, generate_short_code
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            RecipeShortLink, ShoppingList, Tag)
from users.models import Follow

User = get_user_model()


class UserViewSet(DjoserUserViewSet):

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

    @action(
        detail=False,
        methods=['get'],
        serializer_class=UserFollowSerializer
    )
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
        serializer = self.get_serializer(
            page,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit
            }
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        serializer_class=AvatarSerializer
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = self.get_serializer(
                user,
                data=request.data
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
    permission_classes = (
        IsAuthenticatedOrReadOnly, IsAuthorStaffOrReadOnlyObject
    )
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = RecipeFilter
    ordering_fields = ('id',)

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

        for attempt in range(MAX_COLLISION_ATTEMPTS):
            try:
                short_link, created = RecipeShortLink.objects.get_or_create(
                    recipe=recipe,
                    defaults={
                        'code': generate_short_code(SHORT_CODE_MAX_LENGTH)
                    }
                )
                break
            except IntegrityError as e:
                if attempt < MAX_COLLISION_ATTEMPTS - 1:
                    continue
                else:
                    raise e

        short_url = request.build_absolute_uri(
            reverse('short-link', kwargs={'code': short_link.code})
        )

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

        return build_shopping_list_response(ingredients)


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
    search_fields = ('^name',)  # Мне кажется, ограничивать началом неудобно.
    pagination_class = None
    permission_classes = (AllowAny,)


def short_link_redirect(request, code):
    try:
        short_link = RecipeShortLink.objects.get(code=code)
        return HttpResponseRedirect(
            RECIPE_FRONTEND_PATH.format(id=short_link.recipe.id)
        )

    except RecipeShortLink.DoesNotExist:
        return HttpResponseRedirect('/not-existing-page')

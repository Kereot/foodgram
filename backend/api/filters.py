from django_filters import AllValuesMultipleFilter, NumberFilter
from django_filters.rest_framework import FilterSet
from rest_framework.filters import SearchFilter

from recipes.models import Recipe


class IngredientSearchFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(FilterSet):
    tags = AllValuesMultipleFilter(
        field_name='tags__slug',

    )
    author = NumberFilter(
        field_name='author_id',
    )
    is_favorited = NumberFilter(
        method='filter_is_favorited',
    )
    is_in_shopping_cart = NumberFilter(
        method='filter_is_in_shopping_cart',
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def _relation_manager(self, qs, value, related_name):
        user = self.request.user

        return qs.filter(
            **{f'{related_name}__user': user}
        ) if value == 1 and user.is_authenticated else qs

    def filter_is_favorited(
        self,
        queryset,
        name,
        value
    ):
        return self._relation_manager(
            queryset,
            value,
            'favorites'
        )

    def filter_is_in_shopping_cart(
        self,
        queryset,
        name,
        value
    ):
        return self._relation_manager(
            queryset,
            value,
            'shoppinglists'
        )

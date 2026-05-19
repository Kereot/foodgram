from django_filters.rest_framework import (
    FilterSet,
    ModelMultipleChoiceFilter,
)
from rest_framework.filters import SearchFilter

from recipes.models import Recipe, Tag


class IngredientSearchFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(FilterSet):
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False,
    )

    class Meta:
        model = Recipe
        fields = ('tags',)

from django.contrib import admin
from django.db.models import Count

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            RecipeShortLink, ShoppingList, Tag)


class EmptyDisplayAdmin(admin.ModelAdmin):
    empty_value_display = '-пусто-'


@admin.register(Ingredient)
class IngredientAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(EmptyDisplayAdmin):
    inlines = (RecipeIngredientInline,)
    list_display = ('pk', 'name', 'author', 'get_ingredients', 'get_tags',
                    'text', 'cooking_time', 'favorites_count')
    search_fields = ('name', 'author__username', 'text')
    list_filter = ('tags', 'cooking_time')
    readonly_fields = ('favorites_count',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_favorites_count=Count('favorites'))

    @admin.display(description=Tag._meta.verbose_name_plural)
    def get_tags(self, obj):
        return ', '.join([t.name for t in obj.tags.all()])

    @admin.display(description=Ingredient._meta.verbose_name_plural)
    def get_ingredients(self, obj):
        return ', '.join([i.name for i in obj.ingredients.all()])

    @admin.display(description='Число добавлений в избранное')
    def favorites_count(self, obj):
        return obj._favorites_count


@admin.register(Tag)
class TagAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'name', 'slug')
    search_fields = ('name', 'slug')
    list_filter = ('name',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'recipe', 'ingredient', 'amount')


@admin.register(RecipeShortLink)
class RecipeShortLinkAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'recipe', 'code')
    search_fields = ('recipe__name',)


class AbstractUserRecipeAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Favorite)
class FavoriteAdmin(AbstractUserRecipeAdmin):
    pass


@admin.register(ShoppingList)
class ShoppingListAdmin(AbstractUserRecipeAdmin):
    pass

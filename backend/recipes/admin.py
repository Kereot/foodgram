from django.contrib import admin

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag


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
    list_display = ('pk', 'get_ingredients', 'get_tags', 'name', 'text',
                    'cooking_time')
    search_fields = ('name', 'text')
    list_filter = ('name', 'tags', 'cooking_time')

    @admin.display(description=Tag._meta.verbose_name_plural)
    def get_tags(self, obj):
        return ', '.join([t.name for t in obj.tags.all()])

    @admin.display(description=Ingredient._meta.verbose_name_plural)
    def get_ingredients(self, obj):
        return ', '.join([i.name for i in obj.ingredients.all()])


@admin.register(Tag)
class TagAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'name', 'slug')
    search_fields = ('name', 'slug')
    list_filter = ('name',)

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')

from django.db import models
from django.db.models import ForeignKey

from common.constants import (
    DEFAULT_MAX_LENGTH,
    INGREDIENT_NAME_MAX_LENGTH,
    INGREDIENT_MEASUREMENT_MAX_LENGTH,
    RECIPE_NAME_MAX_LENGTH,
    SHORT_CODE_MAX_LENGTH,
    TAG_NAME_SLUG_FIELD_MAX_LENGTH,
    VISUAL_NAME_LIMIT
)
from common.validators import slug_validator
from users.models import User


class StrNameModel(models.Model):
    name = models.CharField(max_length=DEFAULT_MAX_LENGTH)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name[:VISUAL_NAME_LIMIT]


class Tag(StrNameModel):
    name = models.CharField(
        max_length=TAG_NAME_SLUG_FIELD_MAX_LENGTH,
        unique=True,
        verbose_name='Уникальное название'
    )
    slug = models.CharField(
        max_length=TAG_NAME_SLUG_FIELD_MAX_LENGTH,
        null=True,
        unique=True,
        validators=(slug_validator,),
        verbose_name='Уникальный слаг'
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'


class Ingredient(StrNameModel):
    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LENGTH,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=INGREDIENT_MEASUREMENT_MAX_LENGTH,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Recipe(StrNameModel):
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Список ингредиентов'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Список id тегов'
    )
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True, #ToDo: убрать!
        default=None,
        verbose_name='Картинка, закодированная в Base64'
    )
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LENGTH,
        verbose_name='Название'
    )
    text = models.TextField(
        verbose_name='Описание',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (в минутах)'
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество ингредиентов'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            )
        ]
        verbose_name = 'ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'


class RecipeShortLink(models.Model):
    code = models.SlugField(
        max_length=SHORT_CODE_MAX_LENGTH,
        unique=True,
        editable=False,
        verbose_name='Уникальный код'
    )
    recipe = models.OneToOneField(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='short_link',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'короткая ссылка на рецепт'
        verbose_name_plural = 'Короткие ссылки на рецепт'

    def __str__(self):
        return str(self.code)


class AbstractUserRecipe(models.Model):
    user = ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name = '%(class)s_unique_user_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.recipe}'


class Favorite(AbstractUserRecipe):

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'


class ShoppingList(AbstractUserRecipe):

    class Meta:
        verbose_name = 'список ингредиентов'
        verbose_name_plural = 'Списки ингредиентов'

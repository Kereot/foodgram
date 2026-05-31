from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import ForeignKey

from common.constants import (DEFAULT_MAX_LENGTH,
                              INGREDIENT_MEASUREMENT_MAX_LENGTH,
                              INGREDIENT_NAME_MAX_LENGTH,
                              MIN_POSITIVE_INTEGER_FIELD,
                              RECIPE_NAME_MAX_LENGTH, SHORT_CODE_MAX_LENGTH,
                              TAG_NAME_SLUG_FIELD_MAX_LENGTH,
                              VISUAL_NAME_LIMIT)
from users.models import User


class StrNameModel(models.Model):
    name = models.CharField(
        max_length=DEFAULT_MAX_LENGTH,
        verbose_name='Название'
    )

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return self.name[:VISUAL_NAME_LIMIT]


class Tag(StrNameModel):
    name = models.CharField(
        max_length=TAG_NAME_SLUG_FIELD_MAX_LENGTH,
        unique=True,
        verbose_name='Уникальное название'
    )
    slug = models.SlugField(
        max_length=TAG_NAME_SLUG_FIELD_MAX_LENGTH,
        unique=True,
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
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_name_with_unit'
            )
        ]
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
        blank=False,
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
        validators=(MinValueValidator(MIN_POSITIVE_INTEGER_FIELD),),
        verbose_name='Время приготовления (в минутах)'
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        validators=(MinValueValidator(MIN_POSITIVE_INTEGER_FIELD),),
        verbose_name='Количество ингредиентов'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            )
        ]
        default_related_name = 'recipe_ingredients'
        verbose_name = 'ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        return f'{self.recipe}: {self.ingredient} - {self.amount}'


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
                name='%(class)s_unique_user_recipe'
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

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from rest_framework import serializers

from api.fields import NoBlankBase64ImageField
from common.constants import (MAX_SMALL_POSITIVE_INTEGER_FIELD,
                              MIN_POSITIVE_INTEGER_FIELD)
from common.validators import validate_required_field, validate_unique_field
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = NoBlankBase64ImageField(required=True, allow_null=False)

    class Meta:
        model = User
        fields = ('avatar',)


class ExtendedUserSerializer(UserSerializer):
    avatar = NoBlankBase64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + (
            'avatar',
            # 'is_staff',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        # Разве это лучше читается варианта с if?
        return bool(
            request
            and request.user.is_authenticated
            and request.user.following.filter(author=obj).exists()
        )


class UserFollowSerializer(ExtendedUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(ExtendedUserSerializer.Meta):
        fields = ExtendedUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        qs = Recipe.objects.filter(author=obj).order_by('-id')

        if limit:
            try:
                qs = qs[:int(limit)]
            except ValueError:
                pass

        serializer = RecipeBasicReadSerializer(
            qs,
            many=True,
            context=self.context,
        )

        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        fields = 'id', 'name', 'slug'
        model = Tag


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        fields = 'id', 'name', 'measurement_unit'
        model = Ingredient


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        fields = ('id', 'name', 'measurement_unit', 'amount')
        model = RecipeIngredient


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_POSITIVE_INTEGER_FIELD,
        max_value=MAX_SMALL_POSITIVE_INTEGER_FIELD
    )

    class Meta:
        fields = ('id', 'amount')
        model = RecipeIngredient


class RecipeBasicReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    image = NoBlankBase64ImageField(allow_null=True)

    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        model = Recipe


class RecipeReadSerializer(RecipeBasicReadSerializer):
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    tags = TagSerializer(many=True)
    author = ExtendedUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta(RecipeBasicReadSerializer.Meta):
        fields = RecipeBasicReadSerializer.Meta.fields + (
            'tags',
            'author',
            'ingredients',
            'text',
            'is_favorited',
            'is_in_shopping_cart',
        )
        read_only_fields = ('author',)

    def _relation_manager(self, obj, related_name):
        user = self.context['request'].user
        return (
                user.is_authenticated
                and getattr(obj, related_name).filter(user=user).exists()
                )

    def get_is_favorited(self, obj):
        return self._relation_manager(obj, 'favorites')

    def get_is_in_shopping_cart(self, obj):
        return self._relation_manager(obj, 'shoppinglists')


class RecipeWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    ingredients = RecipeIngredientWriteSerializer(
        source='recipe_ingredients',
        many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = NoBlankBase64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        min_value=MIN_POSITIVE_INTEGER_FIELD,
        max_value=MAX_SMALL_POSITIVE_INTEGER_FIELD,
        error_messages={
            'min_value': (
                f'Время приготовления должно быть '
                f'не меньше {MIN_POSITIVE_INTEGER_FIELD}.'
            )
        }
    )

    class Meta:
        fields = ('id', 'tags', 'author', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')
        model = Recipe
        read_only_fields = ('author',)

    def validate(self, attrs):
        validate_required_field('tags', attrs)
        validate_required_field('recipe_ingredients', attrs)
        validate_unique_field('tags', attrs)
        validate_unique_field('recipe_ingredients', attrs, True)
        return attrs
    # Я так понимаю, уже не нужна проверка image, она есть в кастомном
    # NoBlankBase64ImageField. Я её туда вставил, т.к. в модели оставил
    # null=True, чтобы можно было напрямую в БД заносить без картинок. Из-за
    # этого параметра в модели, drf_extra_fields иначе упорно пропускает None.

    def _ingredients_bulk_create(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        self._ingredients_bulk_create(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance.tags.set(tags_data)

        instance.ingredients.clear()
        self._ingredients_bulk_create(instance, ingredients_data)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data

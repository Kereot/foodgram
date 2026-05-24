import base64
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from common.constants import (MAX_SMALL_POSITIVE_INTEGER_FIELD,
                              MIN_POSITIVE_INTEGER_FIELD,
                              USER_CHAR_FIELD_MAX_LENGTH)
from common.validators import validate_required_field, validate_unique_field
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import Follow

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'{uuid.uuid4()}.{ext}'
            data = ContentFile(base64.b64decode(imgstr), name=filename)

        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):
    first_name = serializers.CharField(
        max_length=USER_CHAR_FIELD_MAX_LENGTH,
        required=True
    )
    last_name = serializers.CharField(
        max_length=USER_CHAR_FIELD_MAX_LENGTH,
        required=True
    )

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class CustomUserSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(AvatarSerializer.Meta):
        model = User
        fields = AvatarSerializer.Meta.fields + (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            # Поле ниже позволяет редактировать чужие рецепты админу из
            # обычного интерфейса сайта, соответствующие изменения внесены на
            # фронт, но постман-тесты требуют отсутствия лишних полей.
            # 'is_staff',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False


class UserFollowSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
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

        return [
            {
                'id': recipe.pk,
                'name': recipe.name,
                'image': (f'{settings.SITE_URL}{recipe.image.url}'
                          if recipe.image else None),
                'cooking_time': recipe.cooking_time,
            }
            for recipe in qs
        ]

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
    image = Base64ImageField(allow_null=True)

    class Meta:
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        model = Recipe
        read_only_fields = ('author',)


class RecipeReadSerializer(RecipeBasicReadSerializer):
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
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

    def get_is_favorited(self, obj):
        user = self.context['request'].user

        if user.is_anonymous:
            return False

        return obj.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user

        if user.is_anonymous:
            return False

        return obj.shoppinglists.filter(user=user).exists()


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
    image = Base64ImageField(required=True)

    class Meta:
        fields = ('id', 'tags', 'author', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')
        model = Recipe
        read_only_fields = ('author',)

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError('Время приготовления должно '
                                              'быть больше 1')
        return value

    def validate(self, attrs):
        validate_required_field('tags', attrs)
        validate_required_field('recipe_ingredients', attrs)
        validate_unique_field('tags', attrs)
        validate_unique_field('recipe_ingredients', attrs, True)
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.ingredients.clear()
            for item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=item['id'],
                    amount=item['amount']
                )

        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data

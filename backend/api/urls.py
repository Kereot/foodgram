from django.urls import include, path
from rest_framework import routers

from api.views import UserViewSet, TagViewSet, IngredientViewSet, RecipeViewSet

router_v1 = routers.DefaultRouter()

router_v1.register('users', UserViewSet, basename='users')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register(
    'ingredients',
    IngredientViewSet,
    basename='ingredients')
router_v1.register('recipes', RecipeViewSet, basename='recipes')

v1_patterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]

urlpatterns = [
    path('', include(v1_patterns)),
]

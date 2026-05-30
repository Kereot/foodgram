from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework import routers

from api.views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet

router_v1 = routers.DefaultRouter()

router_v1.register('users', UserViewSet, basename='users')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register(
    'ingredients',
    IngredientViewSet,
    basename='ingredients'
)
router_v1.register('recipes', RecipeViewSet, basename='recipes')

v1_patterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]

urlpatterns = [
    path(
        'docs/',
        TemplateView.as_view(
            template_name='docs/redoc.html',
            extra_context={'is_local': settings.DEBUG}
        ),
        name='redoc'
    ),
    path('', include(v1_patterns)),
]

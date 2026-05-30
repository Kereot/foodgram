from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from users.models import Follow, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    empty_value_display = '-пусто-'
    list_display = ('pk', 'email', 'username', 'first_name', 'last_name',
                    'avatar')
    search_fields = ('email', 'username')
    list_filter = ('is_staff', 'is_active')

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('avatar',)}),
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    empty_value_display = '-пусто-'
    list_display = ('pk', 'user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')


admin.site.unregister(Group)

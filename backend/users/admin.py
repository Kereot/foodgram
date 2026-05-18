from django.contrib import admin

from users.models import Follow, User


class EmptyDisplayAdmin(admin.ModelAdmin):
    empty_value_display = '-пусто-'


@admin.register(User)
class UserAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'email', 'username', 'first_name', 'last_name',
                    'avatar')
    search_fields = ('email', 'username')
    list_filter = ('email', 'username')

@admin.register(Follow)
class FollowAdmin(EmptyDisplayAdmin):
    list_display = ('pk', 'user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms import BooleanField, forms
from django.shortcuts import render
from django.template import Template, Context

from . import models
from .models import User
from .utils import for_admin
from base.settings import LDAP_ADMIN_DATA


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserAdmin(UserAdmin):
    model = MyUserChangeForm

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "is_teacher")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "uni_group",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "first_name", "last_name", "is_teacher", "uni_group", "password1", "password2"),
            },
        ),
    )

    list_display = ("username", "first_name", "last_name", "is_teacher")


# @login_required
# @for_admin()
# def admin_sync(request):
#     from .logic.users_syncronisation import synchronise
#     synchronise(LDAP_ADMIN_DATA["USER"],
#                 LDAP_ADMIN_DATA["PASSWORD"])
#     return render(request, 'index.html')


admin.site.register(User, MyUserAdmin)
admin.site.register(models.Task)
admin.site.register(models.Variable)
admin.site.register(models.File)
admin.site.register(models.Formula)
admin.site.register(models.Mapping)
admin.site.register(models.Course)
admin.site.register(models.UniGroup)

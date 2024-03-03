from django.contrib import admin
from . import models


admin.site.register(models.Task)
admin.site.register(models.Variable)
admin.site.register(models.File)
admin.site.register(models.Formula)
admin.site.register(models.Mapping)

"""
URL configuration for base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

import web_page.views
from web_page.logic import cource_editor, task_editor

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', web_page.views.index, name='main'),
    path('course/editor', cource_editor.course_editor, kwargs={"course_id": None},  name='create_course'),
    path('course/<int:course_id>/editor', cource_editor.course_editor, name='edit_course'),
    path('course/<int:course_id>/task/editor', task_editor.task_editor, kwargs={"task_id": None}, name='create_task'),
    path('course/<int:course_id>/task/<int:task_id>/editor', task_editor.task_editor, name='edit_task'),
    path('courses/', web_page.views.course_list, name='courses')
]

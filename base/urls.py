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
from django.urls import path, include, re_path

import web_page.views
import web_page.admin
from web_page.logic import cource_editor, task_editor, file_uploader, user_login_contoroller

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', web_page.views.index, name='main'),
    path('login', user_login_contoroller.login, name='login'),
    path('logout', user_login_contoroller.logout, name='logout'),
    path('groups', web_page.views.groups_list, name='groups_list'),
    path('group/editor', web_page.views.group_page, kwargs={'group_id': None}, name='group_create'),
    path('group/<int:group_id>/editor', web_page.views.group_page, name='group_page'),
    path('group/<int:group_id>/delete', web_page.views.delete_group, name='group_delete'),
    path('course/editor', cource_editor.course_editor, kwargs={"course_id": None},  name='create_course'),
    path('course/<int:course_id>/editor', cource_editor.course_editor, name='edit_course'),
    path('course/<int:course_id>/task/editor', task_editor.task_editor, kwargs={"task_id": None}, name='create_task'),
    path('course/<int:course_id>/task/<int:task_id>/editor', task_editor.task_editor, name='edit_task'),
    path('courses/', web_page.views.course_list, name='courses'),
    path('courses/created', web_page.views.created_course_list, name='created_courses'),
    path('course/<int:course_id>', web_page.views.course_page, name='course'),
    path('course/<int:course_id>/tasks', web_page.views.task_list, name='course-tasks'),
    path('task/<int:task_id>', web_page.views.task_page, name='task'),
    path('task/<int:task_id>/practice/', web_page.views.task_practice, name='task_practice'),
    path('task/<int:task_id>/practice/get_report', web_page.views.task_get_report, name='task_get_report'),
    path('task/<int:task_id>/editor/formulas', web_page.views.task_formulas, name='task_formulas'),
    path('task/<int:task_id>/editor/formulas/<int:formula_id>/extract', web_page.views.formula_extract_variables, name='task_formula_extract'),
    path('task/<int:task_id>/editor/formulas/create', web_page.views.task_create_formula, name='task_create_formula'),
    path('task/<int:task_id>/editor/formulas/mapping', web_page.views.task_formulas_mapping, name='task_formulas_mapping'),
    path('task/<int:task_id>/editor/formulas/<int:formula_id>/delete', web_page.views.task_delete_formula, name='task_delete_formula'),
    path('fp/', web_page.logic.file_uploader.load_attachment, name='load_attachment'),
    path('fp/revert/', web_page.logic.file_uploader.remove_attachment, name="remove_attachment"),
    path('fp/process/', web_page.logic.file_uploader.upload_attachment, name="upload_attachment"),
    path('fp/image/', web_page.logic.file_uploader.upload_image, name="upload_image"),
    path('fp/image/<str:name>', web_page.logic.file_uploader.get_image, name="get_image"),
    path('fp/file/<int:file_id>', web_page.logic.file_uploader.get_file, name="get_file"),
    path("sync", web_page.admin.admin_sync, name="sync")
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


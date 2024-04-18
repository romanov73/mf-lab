import os
import uuid
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from web_page.models import Course, File, Group
from web_page.utils import for_teacher

BASE_DIR = Path(__file__).resolve().parent.parent


@login_required
@for_teacher()
def course_editor(request, course_id: int | None):
    if request.method == "GET":
        if course_id is None:
            return create_course_view(request)
        else:
            return edit_course_view(request, course_id)
    elif request.method == "POST":
        if course_id is None:
            return add_course_action(request)

        else:
            return update_course_action(request, course_id)


def create_course_view(request):
    return render(request, 'create.html',
                  context={
                      "creating_title": "Создание курса",
                      "button_text": "Создать курс",
                      "creating_url": reverse('create_course'),
                      "groups": list(Group.objects.all().values("id", "name"))
                  })


def edit_course_view(request, id: int):
    course: Course = get_object_or_404(Course, id=id)
    return render(request, 'create.html',
                  context={
                      "creating_title": "Редактирование курса",
                      "button_text": "Изменить курс",
                      "creating_url": reverse('edit_course', kwargs={"course_id": id}),
                      "course_id": course.id,
                      "object_name": course.name,
                      "object_summary": course.summary,
                      "object_description": course.description,
                      "files": [i.id for i in File.objects.filter(course=course)],
                      "groups": list(Group.objects.all().values("id", "name")),
                      "my_groups": list(i["id"] for i in course.groups.values("id"))
                  })


def add_course_action(request):
    groups = []
    try:
        groups = list(map(int, request.POST.get("groups").split("|")))
    except:
        pass#Что-то тут надо другое

    course: Course = Course(
        name=request.POST.get("name"),
        summary=request.POST.get("summary"),
        description=request.POST.get("text"),
        user=request.user
    )
    course.save()
    course.groups.set(Group.objects.filter(id__in=groups).all())


    if request.POST["attachments[]"]:
        for fid in request.POST["attachments[]"].split("|"):
            file: File = File.objects.get(id=fid)
            if file is not None:
                file.course = course
                file.task = None
                file.save()

    return redirect("edit_course", course.id)


def update_course_action(request, id):
    groups = []
    try:
        groups = list(map(int, request.POST.get("groups").split("|")))
    except:
        pass#Что-то тут надо другое

    course: Course = get_object_or_404(Course, id=id)
    course.name = request.POST.get("name")
    course.summary = request.POST.get("summary")
    course.description = request.POST.get("text")
    course.groups.set(Group.objects.filter(id__in=groups).all())
    course.save()

    if request.POST["attachments[]"]:

        for fid in request.POST["attachments[]"].split("|"):
            file: File = File.objects.get(id=fid)
            if file is not None:
                if file.course != course:
                    file.course = course
                    file.task = None
                    file.save()

    return redirect("edit_course", id)

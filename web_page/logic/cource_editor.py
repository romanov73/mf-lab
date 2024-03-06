from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from web_page.models import Course


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
                      "creating_url": reverse('create_course')
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
                      "object_description": course.description
                  })


def add_course_action(request):
    course: Course = Course(name=request.POST.get("name"), description=request.POST.get("text"))
    course.save()
    return redirect("edit_course", course.id)


def update_course_action(request, id):
    course: Course = get_object_or_404(Course, id=id)
    course.name = request.POST.get("name")
    course.description = request.POST.get("text")
    course.save()
    return redirect("edit_course", id)

import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from web_page.models import Course, Task, File
from web_page.utils import for_teacher


@login_required
@for_teacher()
def task_editor(request, course_id: int, task_id: int | None):
    if request.method == "GET":
        if task_id is None:
            return create_task_view(request, course_id)
        else:
            return edit_course_view(request, course_id, task_id)
    elif request.method == "POST":
        if task_id is None:
            return add_task_action(request, course_id)
        else:
            return update_task_action(request, course_id, task_id)


def create_task_view(request, course_id: int):
    return render(request, 'create.html',
                  context={
                      "creating_title": "Создание задачи",
                      "button_text": "Создать задачу",
                      "creating_url": reverse('create_task', kwargs={"course_id": course_id})
                  })


def edit_course_view(request, course_id: int, task_id: int):
    task: Task = get_object_or_404(Task, id=task_id)
    return render(request, 'create.html',
                  context={
                      "creating_title": "Редактирование задачи",
                      "button_text": "Изменить задачу",
                      "creating_url": reverse('edit_task', kwargs={
                          "course_id": course_id,
                          "task_id": task_id
                      }),
                      "task_id": task.id,
                      "object_name": task.name,
                      "object_summary": task.summary,
                      "object_description": task.description,
                      "files": [i.id for i in File.objects.filter(task=task)]
                  })


def add_task_action(request, course_id: int):
    task: Task = Task(
        name=request.POST.get("name"),
        summary=request.POST.get("summary"),
        description=request.POST.get("text"),
        created_at=datetime.datetime.now()
    )
    task.course = get_object_or_404(Course, id=course_id)
    task.save()

    if request.POST["attachments[]"]:
        for fid in request.POST["attachments[]"].split("|"):
            file: File = File.objects.get(id=fid)
            if file is not None:
                file.course = None
                file.task = task
                file.save()

    return redirect("course-tasks", course_id)


def update_task_action(request, course_id: int, task_id: int):
    task: Task = get_object_or_404(Task, id=task_id)
    task.name = request.POST.get("name")
    task.summary = request.POST.get("summary"),
    task.description = request.POST.get("text")
    task.save()

    if request.POST["attachments[]"]:

        for fid in request.POST["attachments[]"].split("|"):
            file: File = File.objects.get(id=fid)
            if file is not None:
                if file.task != task:
                    file.course = None
                    file.task = task
                    file.save()

    return redirect("edit_task", course_id, task_id)


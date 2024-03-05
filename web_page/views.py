from django.shortcuts import render, redirect


courses: list = []


def index(request):
    return render(request, 'index.html')


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
                      "creating_url": "/CourseEditor"
                  })


def edit_course_view(request, id: int):
    if len(courses) > id:
        return render(request, 'create.html',
                      context={
                          "creating_title": "Редактирования курса",
                          "button_text": "Изменить курс",
                          "creating_url": f"/CourseEditor/{id}",
                          "object_name": courses[id]["name"],
                          "object_description": courses[id]["text"]
                      })
    return redirect("/")


def add_course_action(request):
    courses.append({
        "name": request.POST.get("name"),
        "text": request.POST.get("text")
    })
    return redirect(f"/CourseEditor/{len(courses) - 1}")


def update_course_action(request, id):
    courses[id] = {
        "name": request.POST.get("name"),
        "text": request.POST.get("text")
    }
    return redirect(f"/CourseEditor/{id}")


def course_list(request):
    return render(request, 'course_list.html')

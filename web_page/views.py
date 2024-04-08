from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from json import loads

from frc import DocxReport
from web_page.models import Course, Formula, Variable, Task, Mapping, File
from expression_parser import Formula as Expression  # Да простит меня Бог


def index(request):
    return render(request, 'index.html')


def course_list(request):
    name = request.GET.get('name')
    if name:
        courses = Course.objects.filter(name__icontains=name)
    else:
        courses = Course.objects.all()

    courses_per_page = 5
    paginator = Paginator(courses, courses_per_page)

    page = request.GET.get('page')
    try:
        courses_page = paginator.page(page)
    except PageNotAnInteger:
        courses_page = paginator.page(1)
    except EmptyPage:
        courses_page = paginator.page(paginator.num_pages)

    return render(request, 'course_list.html', {'courses': courses_page})


def course_page(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    tasks = Task.objects.filter(course_id=course_id)
    files = File.objects.filter(course_id=course_id)

    tasks_per_page = 5
    paginator = Paginator(tasks, tasks_per_page)

    page = request.GET.get('page')
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)

    return render(request, 'course.html', {'course': course, 'tasks': tasks_page, 'files': files})


def task_list(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    tasks = Task.objects.filter(course_id=course_id)

    tasks_per_page = 5
    paginator = Paginator(tasks, tasks_per_page)

    page = request.GET.get('page')
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)

    return render(request, 'task_list.html', {'course': course, 'tasks': tasks_page})


def task_page(request, task_id: int, **kwargs):
    task = get_object_or_404(Task, id=task_id)
    files = File.objects.filter(task_id=task_id)

    return render(request, 'task.html', {'task': task, 'files': files})


def formula_extract_variables(request, formula_id: int, **kwargs):
    if request.method == 'POST':
        formula = get_object_or_404(Formula, id=formula_id)
        expression = Expression(request.POST.get('expression'))  # Это Formula из пакета с парсером, но имя Expression

        if expression is None:
            return redirect(request.POST.get('next'))

        formula.expression = expression.expression
        variables = set(expression.variables)

        Variable.objects.filter(formula_id=formula_id).exclude(name__in=list(variables)).delete()
        stored = set(map(lambda v: v.name, Variable.objects.filter(formula_id=formula_id).all()))

        for variable in variables - stored:
            Variable(name=variable, formula_id=formula_id).save()

        formula.save()

        return redirect(request.POST.get('next'))


def task_create_formula(request, task_id: int):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        Formula(expression='', task_id=task_id).save()

        return redirect(request.POST.get('next'))


def task_delete_formula(request, formula_id: int, **kwargs):
    if request.method == 'POST':
        get_object_or_404(Formula, id=formula_id).delete()

        return redirect(request.POST.get('next'))


def task_formulas_mapping(request, task_id: int, **kwargs):
    if request.method == 'POST':
        variables = loads(request.body.decode('utf-8'))
        Mapping.objects.filter(variable__formula__task_id=task_id).delete()
        for variable in variables:
            Mapping.objects.bulk_create(
                (Mapping(key=mapping['key'], value=mapping['value'], variable_id=variable['id'])
                 for mapping in variable['mapping'])
            )

        return HttpResponse('Изменения прошли успешно')


def task_formulas(request, task_id: int):
    task = get_object_or_404(Task, id=task_id)

    return render(request,
                  'task_formulas.html',
                  {
                      'formulas': task.formula_set.all(),
                      'task_id': task.id
                   }
                  )


def task_practice(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    formulas = task.formula_set.all()
    context = {
        'task': task,
        'formulas': formulas,
    }
    return render(request, 'task_practice.html', context)


def task_get_report(request, task_id: int):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        formulas = []
        data = {'data': formulas}

        for formula in task.formula_set.all():
            expression = Expression(formula.expression)
            variables = {
                variable.name: float(request.POST.get(str(variable.id)))
                for variable in formula.variable_set.all()
            }
            expression.set_variables(variables)
            formulas.append({
                'variables': [{
                    'name': name,
                    'value': value
                } for name, value in variables.items()],
                'formula': formula.expression,
                'result': expression.calculate_result()
            })

        report = DocxReport()
        report.render(data)
        return HttpResponse(report.get_bytes_array())

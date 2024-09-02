import json

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from json import loads
from frc import DocxReport
from web_page.models import Course, Formula, Variable, Task, Mapping, File, UniGroup, User
from expression_parser.FormulaPackage import FormulaPackage
from web_page.utils import for_student, for_teacher


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
def course_list(request):
    name = request.GET.get('name')

    if name:
        courses = Course.objects.filter(uni_groups__name=request.user.uni_group).filter(name__icontains=name).all()
    else:
        courses = Course.objects.filter(uni_groups__name=request.user.uni_group).all()

    courses_per_page = 5
    paginator = Paginator(courses, courses_per_page)

    page = request.GET.get('page')
    try:
        courses_page = paginator.page(page)
    except PageNotAnInteger:
        courses_page = paginator.page(1)
    except EmptyPage:
        courses_page = paginator.page(paginator.num_pages)

    return render(request, 'course_list.html', {'courses': courses_page, 'user': request.user})


@login_required
@for_teacher()
def created_course_list(request):
    name = request.GET.get('name')

    if name:
        courses = Course.objects.filter(name__icontains=name).filter(user=request.user).all()
    else:
        courses = Course.objects.filter(user=request.user).all()

    courses_per_page = 5
    paginator = Paginator(courses, courses_per_page)

    page = request.GET.get('page')
    try:
        courses_page = paginator.page(page)
    except PageNotAnInteger:
        courses_page = paginator.page(1)
    except EmptyPage:
        courses_page = paginator.page(paginator.num_pages)

    return render(request, 'created_course_list.html', {'courses': courses_page, 'user': request.user})



@login_required
@for_teacher()
def groups_list(request):
    groups = UniGroup.objects.all()

    groups_per_page = 10
    paginator = Paginator(groups, groups_per_page)

    page = request.GET.get('page')

    try:
        groups_page = paginator.page(page)
    except PageNotAnInteger:
        groups_page = paginator.page(1)
    except EmptyPage:
        groups_page = paginator.page(paginator.num_pages)

    return render(request, 'groups_list.html', {'groups': groups_page})


@login_required
@for_teacher()
def group_page(request, group_id=None, **kwargs):
    if request.method == 'GET':
        if group_id is None:
            return render(request, 'group.html', {'students': User.objects.filter(is_teacher=False, uni_group=None).all()})

        group = get_object_or_404(UniGroup, id=group_id)

        return render(request, 'group.html', {'group': group, 'students': User.objects.filter(is_teacher=False, uni_group=None).all()})

    if group_id is None:
        group = UniGroup(name=request.POST.get('name'))
        group.save()
        group_id = group.id
    else:
        group = get_object_or_404(UniGroup, id=group_id)
        for student in group.user_set.all():
            student.uni_group = None
            student.save()

    if request.POST.get('students'):
        for student in [User.objects.get(id=int(student_id)) for student_id in request.POST.get('students').split('|')]:
            student.uni_group = group
            student.save()


    return redirect('group_page', group_id=group_id)


@login_required
@for_teacher()
def delete_group(request, group_id, **kwargs):
    if request.method == 'POST':
        group = get_object_or_404(UniGroup, id=group_id)

        group.delete()

        return redirect('groups_list')


@login_required
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


@login_required
@for_teacher()
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


@login_required
@for_student()
def task_page(request, task_id: int, **kwargs):
    task = get_object_or_404(Task, id=task_id)
    files = File.objects.filter(task_id=task_id)

    return render(request, 'task.html', {'task': task, 'files': files})


@login_required
@for_teacher()
def formula_extract_variables(request, task_id: int, **kwargs):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        if not request.POST.get('next'):
            formulas = FormulaPackage(json.loads(request.body)['formulas'])
        else:
            formulas = FormulaPackage(list(map(lambda x: x.expression, Formula.objects.all())))

        if formulas.error_text is not None:
            return redirect(json.loads(request.body)['next'])

        for formula, expression in zip(task.formula_set.all(), formulas.formulas):
            if expression.res_variables is not None:
                formula.expression = expression.res_variables + '=' + expression.expression
            formula.save()

        variables = set(formulas.variables)

        Variable.objects.filter(task_id=task_id).exclude(name__in=list(variables)).delete()
        stored = set(map(lambda v: v.name, Variable.objects.filter(task_id=task_id).all()))

        for variable in variables - stored:
            Variable(name=variable, task_id=task_id).save()

        task.save()

        if next_page := request.POST.get('next'):
            return redirect(next_page)
        else:
            return redirect(json.loads(request.body)['next'])


@login_required
@for_teacher()
def task_create_formula(request, task_id: int):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        Formula(expression='', task_id=task_id).save()

        return redirect(request.POST.get('next'))


@login_required
@for_teacher()
def task_delete_formula(request, formula_id: int, **kwargs):
    if request.method == 'POST':
        formula = get_object_or_404(Formula, id=formula_id)
        formula.delete()
        return formula_extract_variables(request, int(formula.task_id))


@login_required
@for_teacher()
def task_formulas_mapping(request, task_id: int, **kwargs):
    if request.method == 'POST':
        variables = loads(request.body.decode('utf-8'))
        Mapping.objects.filter(variable__task_id=task_id).delete()
        for variable in variables:
            Mapping.objects.bulk_create(
                (Mapping(key=mapping['key'], value=mapping['value'], variable_id=variable['id'])
                 for mapping in variable['mapping'])
            )

        return HttpResponse('Изменения прошли успешно')


@login_required
@for_teacher()
def task_formulas(request, task_id: int):
    task = get_object_or_404(Task, id=task_id)

    return render(request,
                  'task_formulas.html',
                  {
                      'formulas': task.formula_set.all(),
                      'variables': task.variable_set.all(),
                      'has_empty': '' in map(lambda x: x.expression, task.formula_set.all()),
                      'task_id': task.id
                  }
                  )


@login_required
@for_student()
def task_practice(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    formulas = task.formula_set.all()
    variables = task.variable_set.all()
    context = {
        'task': task,
        'formulas': formulas,
        'variables': variables
    }
    return render(request, 'task_practice.html', context)


@login_required
@for_student()
def task_get_report(request, task_id: int):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        formulas = []
        variables = []
        data = {'data': {'formulas': formulas, 'variables': variables}}

        package = FormulaPackage(list(map(lambda x: x.expression, task.formula_set.all())))

        variables.extend(
            {
                "name": variable.name,
                "value": float(request.POST.get(str(variable.id)))
            }
            for variable in task.variable_set.all()
        )

        package.set_variables(
            {
                variable['name']: variable['value']
                for variable in variables
            }
        )

        formulas_results = package.calculate()

        formulas.extend([
            {
                'expression': formula.expression,
                'result': formulas_results[formula.expression.split('=')[0].strip()]
            }
            for formula in task.formula_set.all()
        ])

        report = DocxReport()
        report.render(data)

        return HttpResponse(report.get_bytes_array())

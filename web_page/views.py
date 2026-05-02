import json

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from json import loads
from frc import DocxReport
from web_page.logic.file_uploader import PDF_PREFIX
from web_page.models import Course, Formula, Variable, Task, Mapping, File, UniGroup, User
from expression_parser.FormulaPackage import FormulaPackage
from web_page.utils import for_student, for_teacher


LAB1_A_COEFFS = {
    "TiAlMe2N": {
        "Fe": {"A0": 0.4230, "A1": -0.0016, "A2": 2.30e-4},
        "Cr": {"A0": 0.4230, "A1": -4.91e-4, "A2": 3.60e-5},
        "Zr": {"A0": 0.4230, "A1": 1.86e-4, "A2": -5.0e-6},
    },
    "TiZrMe2N": {
        "Fe": {"A0": 0.4293, "A1": -5.8e-4, "A2": 1.90e-4},
        "Cr": {"A0": 0.4293, "A1": -2.63e-4, "A2": 1.28e-5},
        "Al": {"A0": 0.4293, "A1": -2.5e-6, "A2": 1.49e-4},
    },
    "TiSiMe2N": {
        "Cr": {"A0": 0.4243, "A1": 3.7e-5, "A2": 2.0e-6},
        "Zr": {"A0": 0.4243, "A1": 1.42e-4, "A2": -2.6e-6},
        "Al": {"A0": 0.4243, "A1": -3.31e-4, "A2": 1.56e-5},
    },
}

LAB1_BETA_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": {"A0": 0.57, "A1": 0.235, "A2": -0.130},
            "Cr": {"A0": 0.57, "A1": -0.002, "A2": 0.0315},
            "Zr": {"A0": 0.57, "A1": 0.020, "A2": -0.0006},
        },
        "Р6М5К5": {
            "Fe": {"A0": 0.53, "A1": 0.215, "A2": -0.116},
            "Cr": {"A0": 0.53, "A1": 0.032, "A2": -0.0024},
            "Zr": {"A0": 0.53, "A1": 0.015, "A2": -0.0004},
        },
    },
    "TiZrMe2N": {
        "МК8": {
            "Fe": {"A0": 0.55, "A1": 0.177, "A2": -0.079},
            "Cr": {"A0": 0.55, "A1": 0.020, "A2": -0.0012},
            "Al": {"A0": 0.55, "A1": 0.027, "A2": -0.0015},
        },
        "Р6М5К5": {
            "Fe": {"A0": 0.51, "A1": 0.147, "A2": -0.069},
            "Cr": {"A0": 0.51, "A1": -0.002, "A2": 0.0278},
            "Al": {"A0": 0.51, "A1": -0.002, "A2": 0.0318},
        },
    },
    "TiSiMe2N": {
        "МК8": {
            "Cr": {"A0": 0.56, "A1": 0.014, "A2": -0.0007},
            "Zr": {"A0": 0.56, "A1": 0.012, "A2": -0.0003},
            "Al": {"A0": 0.56, "A1": 0.026, "A2": -0.0015},
        },
        "Р6М5К5": {
            "Cr": {"A0": 0.51, "A1": 0.017, "A2": -0.0008},
            "Zr": {"A0": 0.51, "A1": 0.013, "A2": -0.0004},
            "Al": {"A0": 0.51, "A1": 0.026, "A2": -0.0015},
        },
    },
}

LAB1_SIGMA_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": {"A0": 903, "A1": -217, "A2": 114.4},
            "Cr": {"A0": 903, "A1": 203.1, "A2": -13.86},
            "Zr": {"A0": 903, "A1": 98.0, "A2": -3.00},
        },
        "Р6М5К5": {
            "Fe": {"A0": 2443, "A1": -1244, "A2": 693.9},
            "Cr": {"A0": 2443, "A1": 245.2, "A2": -15.25},
            "Zr": {"A0": 2443, "A1": 81.7, "A2": -2.61},
        },
    },
    "TiZrMe2N": {
        "МК8": {
            "Fe": {"A0": 1256, "A1": -144, "A2": 38.3},
            "Cr": {"A0": 1256, "A1": 38.7, "A2": -2.18},
            "Al": {"A0": 1256, "A1": 31.8, "A2": -1.60},
        },
        "Р6М5К5": {
            "Fe": {"A0": 2619, "A1": -731, "A2": 288.5},
            "Cr": {"A0": 2619, "A1": 82.8, "A2": -5.26},
            "Al": {"A0": 2619, "A1": 76.8, "A2": -3.83},
        },
    },
    "TiSiMe2N": {
        "МК8": {
            "Cr": {"A0": 1020, "A1": 78.2, "A2": -3.08},
            "Zr": {"A0": 1020, "A1": 52.2, "A2": -1.53},
            "Al": {"A0": 1020, "A1": 127.1, "A2": -7.45},
        },
        "Р6М5К5": {
            "Cr": {"A0": 2541, "A1": 53.6, "A2": -2.21},
            "Zr": {"A0": 2541, "A1": 74.4, "A2": -2.61},
            "Al": {"A0": 2541, "A1": 90.9, "A2": -4.90},
        },
    },
}


def _quadratic_model(c_value: float, coeffs: dict) -> float:
    return coeffs['A0'] + coeffs['A1'] * c_value + coeffs['A2'] * (c_value ** 2)


def _build_result_items(lab: dict, calculated_results: dict | None = None) -> list:
    calculated_results = calculated_results or {}
    return [
        {
            'label': label,
            'value': calculated_results.get(label, '-'),
        }
        for label in lab.get('result_fields', [])
    ]


def _build_form_fields_with_values(lab: dict, form_values: dict) -> list:
    fields = []
    selected_coating = form_values.get('coating', '')
    for field in lab.get('form_fields', []):
        prepared = field.copy()

        if lab.get('id') == 1 and field.get('name') == 'alloying_element':
            allowed_elements = lab.get('alloying_by_coating', {}).get(selected_coating, field.get('options', []))
            prepared['options'] = allowed_elements

        prepared['current_value'] = form_values.get(field['name'], '')

        if prepared.get('options') and prepared['current_value'] not in prepared['options']:
            prepared['current_value'] = prepared['options'][0]

        fields.append(prepared)
    return fields


def _build_lab1_graph_data(coating: str, tool_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count < 2:
        points_count = 2

    step = (max_c - min_c) / (points_count - 1)
    c_values = [min_c + i * step for i in range(points_count)]

    a_coeffs = LAB1_A_COEFFS[coating][alloying_element]
    beta_coeffs = LAB1_BETA_COEFFS[coating][tool_material][alloying_element]
    sigma_coeffs = LAB1_SIGMA_COEFFS[coating][tool_material][alloying_element]

    return {
        'c_values': [round(value, 4) for value in c_values],
        'a_values': [round(_quadratic_model(value, a_coeffs), 8) for value in c_values],
        'beta_values': [round(_quadratic_model(value, beta_coeffs), 8) for value in c_values],
        'sigma_values': [round(_quadratic_model(value, sigma_coeffs), 8) for value in c_values],
    }


LABS_DATA = [
    {
        'id': 1,
        'title': 'Исследование структурных параметров покрытий',
        'algorithm': [
            'выбирается покрытие: TiAlMe2N или TiZrMe2N или TiSiMe2N',
            'выбирается инструментальный материал: МК8 или Р6М5К5',
            'выбирается содержание легирующего элемента в покрытии: для покрытия TiAlMe2N - Fe (0,43-1,22 %), Cr (1,35-11,12 %), Zr (4,61-23,39 %); для покрытия TiZrMe2N - Fe (0,49-0,94 %), Cr (1,44-11,28 %), Al (6,36-9,25 %); для покрытия TiSiMe2N - Cr (6,12-11,37 %), Zr (7,81-24,74 %), Al (6,45-9,16 %)',
            'определяются: период кристаллической решетки (a, нм), полуширина рентгеновской линии (β111, град), остаточные напряжения (σ0, МПа)',
            'строятся графики зависимостей a, β111 и σ0 от содержания легирующего элемента в покрытии',
        ],
        'form_fields': [
            {
                'name': 'coating',
                'label': 'износостойкое покрытие',
                'type': 'select',
                'options': ['TiAlMe2N', 'TiZrMe2N', 'TiSiMe2N'],
            },
            {
                'name': 'tool_material',
                'label': 'инструментальный материал',
                'type': 'select',
                'options': ['МК8', 'Р6М5К5'],
            },
            {
                'name': 'alloying_element',
                'label': 'легирующий элемент',
                'type': 'select',
                'options': ['Fe', 'Cr', 'Zr', 'Al'],
            },
            {
                'name': 'alloying_content',
                'label': 'содержание легирующего элемента',
                'type': 'text',
                'placeholder': 'Введите значение, %',
            },
        ],
        'alloying_by_coating': {
            'TiAlMe2N': ['Fe', 'Cr', 'Zr'],
            'TiZrMe2N': ['Fe', 'Cr', 'Al'],
            'TiSiMe2N': ['Cr', 'Zr', 'Al'],
        },
        'content_ranges': {
            'TiAlMe2N': {
                'Fe': (0.43, 1.22),
                'Cr': (1.35, 11.12),
                'Zr': (4.61, 23.39),
            },
            'TiZrMe2N': {
                'Fe': (0.49, 0.94),
                'Cr': (1.44, 11.28),
                'Al': (6.36, 9.25),
            },
            'TiSiMe2N': {
                'Cr': (6.12, 11.37),
                'Zr': (7.81, 24.74),
                'Al': (6.45, 9.16),
            },
        },
        'notes': [
            'TiAlMe2N: Fe (0,43-1,22 %), Cr (1,35-11,12 %), Zr (4,61-23,39 %)',
            'TiZrMe2N: Fe (0,49-0,94 %), Cr (1,44-11,28 %), Al (6,36-9,25 %)',
            'TiSiMe2N: Cr (6,12-11,37 %), Zr (7,81-24,74 %), Al (6,45-9,16 %)',
        ],
        'result_fields': ['a, нм', 'β111, град', 'σ0, МПа'],
    },
    {
        'id': 2,
        'title': 'Исследование механических свойств покрытий',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
    {
        'id': 3,
        'title': 'Исследование циклической трещиностойкости и интенсивности изнашивания режущего инструмента',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
    {
        'id': 4,
        'title': 'Исследование контактных характеристик процесса резания',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
    {
        'id': 5,
        'title': 'Исследование теплового состояния режущего клина инструмента',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
    {
        'id': 6,
        'title': 'Исследование напряженного состояния режущего клина инструмента',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
    {
        'id': 7,
        'title': 'Исследование работоспособности режущего инструмента с покрытиями',
        'algorithm': ['Данные из ТЗ для этой лабораторной пока не переданы.'],
        'form_fields': [],
        'result_fields': [],
    },
]


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
def labs_list(request):
    labs = [{'id': lab['id'], 'title': lab['title']} for lab in LABS_DATA]
    return render(request, 'labs_list.html', {'labs': labs})


@login_required
def lab_page(request, lab_id: int):
    lab = next((item for item in LABS_DATA if item['id'] == lab_id), None)
    if lab is None:
        raise Http404()

    form_values = {
        'coating': '',
        'tool_material': '',
        'alloying_element': '',
        'alloying_content': '',
    }
    error_message = None
    calculated_results = {}
    graph_data = None

    if request.method == 'GET' and lab_id == 1:
        coating_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'coating'), [])
        tool_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'tool_material'), [])

        if coating_options:
            form_values['coating'] = coating_options[0]
        if tool_options:
            form_values['tool_material'] = tool_options[0]

        allowed_elements = lab.get('alloying_by_coating', {}).get(form_values['coating'], [])
        if allowed_elements:
            form_values['alloying_element'] = allowed_elements[0]

    if request.method == 'POST' and lab_id == 1:
        form_values['coating'] = request.POST.get('coating', '').strip()
        form_values['tool_material'] = request.POST.get('tool_material', '').strip()
        form_values['alloying_element'] = request.POST.get('alloying_element', '').strip()
        form_values['alloying_content'] = request.POST.get('alloying_content', '').strip()

        coating = form_values['coating']
        tool_material = form_values['tool_material']
        alloying_element = form_values['alloying_element']
        content_raw = form_values['alloying_content']

        if not coating:
            error_message = 'Выберите износостойкое покрытие.'
        elif not tool_material:
            error_message = 'Выберите инструментальный материал.'
        elif not alloying_element:
            error_message = 'Выберите легирующий элемент.'
        else:
            allowed_elements = lab.get('alloying_by_coating', {}).get(coating, [])
            if alloying_element not in allowed_elements:
                error_message = 'Выбранный легирующий элемент недоступен для указанного покрытия.'

        content_value = None
        if error_message is None:
            try:
                content_value = float(content_raw.replace(',', '.'))
            except ValueError:
                error_message = 'Содержание легирующего элемента должно быть числом.'

        if error_message is None:
            content_range = lab.get('content_ranges', {}).get(coating, {}).get(alloying_element)
            if content_range is None:
                error_message = 'Для выбранной пары покрытие + легирующий элемент диапазон не задан.'
            else:
                min_value, max_value = content_range
                if not (min_value <= content_value <= max_value):
                    error_message = (
                        f'Содержание легирующего элемента должно быть в диапазоне '
                        f'{min_value:.2f}-{max_value:.2f} %.'
                    )

        if error_message is None:
            try:
                a_value = _quadratic_model(content_value, LAB1_A_COEFFS[coating][alloying_element])
                beta_value = _quadratic_model(content_value, LAB1_BETA_COEFFS[coating][tool_material][alloying_element])
                sigma_value = _quadratic_model(content_value, LAB1_SIGMA_COEFFS[coating][tool_material][alloying_element])

                calculated_results = {
                    'a, нм': f'{a_value:.6f}',
                    'β111, град': f'{beta_value:.6f}',
                    'σ0, МПа': f'{sigma_value:.3f}',
                }

                graph_data = _build_lab1_graph_data(
                    coating=coating,
                    tool_material=tool_material,
                    alloying_element=alloying_element,
                    content_range=lab['content_ranges'][coating][alloying_element],
                )
            except KeyError:
                error_message = 'Для выбранной комбинации отсутствуют коэффициенты расчета.'

    result_items = _build_result_items(lab, calculated_results)
    form_fields = _build_form_fields_with_values(lab, form_values)

    return render(
        request,
        'lab_page.html',
        {
            'lab': lab,
            'form_values': form_values,
            'form_fields': form_fields,
            'error_message': error_message,
            'result_items': result_items,
            'graph_data': graph_data,
        }
    )


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
    name = request.GET.get('name')

    if name:
        groups = UniGroup.objects.filter(name__icontains=name)
    else:
        groups = UniGroup.objects.all()

    groups = groups.order_by('name')

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
            return render(request, 'group.html',
                          {'students': User.objects.filter(is_teacher=False, uni_group=None).all()})

        group = get_object_or_404(UniGroup, id=group_id)

        return render(request, 'group.html',
                      {'group': group, 'students': User.objects.filter(is_teacher=False, uni_group=None).all()})

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
def task_page(request, task_id: int, **kwargs):
    task = get_object_or_404(Task, id=task_id)
    files = File.objects.filter(task_id=task_id).exclude(file_name__startswith=PDF_PREFIX)
    main_pdf = File.objects.filter(task_id=task_id, file_name__startswith=PDF_PREFIX).first()

    return render(request, 'task.html', {'task': task, 'files': files, 'main_pdf': main_pdf})


@login_required
@for_teacher()
def formula_extract_variables(request, task_id: int, **kwargs):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        if not request.POST.get('next'):
            formulas = FormulaPackage(json.loads(request.body)['formulas'])
        else:
            formulas = FormulaPackage(list(map(lambda x: x.expression, task.formula_set.all())))

        if formulas.error_text is not None:
            return redirect(json.loads(request.body)['next'])

        for formula, expression in zip(task.formula_set.all(), formulas.formulas):
            if expression.res_variables is not None:
                formula.expression = expression.res_variables + '=' + expression.expression
            formula.save()

        variables = set(formulas.variables)

        Variable.objects.filter(task_id=task_id).exclude(name__in=list(variables)).filter(mapping__isnull=True).delete()
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
        task_id = int(formula.task_id)
        formula.delete()
        return formula_extract_variables(request, task_id)


@login_required
@for_teacher()
def task_formulas_mapping_by_id(request, task_id: int, **kwargs):
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
def task_formulas_mapping_by_name(request, task_id: int, **kwargs):
    if request.method == 'POST':
        variables_json = loads(request.body.decode('utf-8'))
        # variables_json = [{"name": "a",
        #                    "mapping": [
        #                        {
        #                            "key": "ad",
        #                            "value": "23.0"
        #                        },
        #                        {
        #                            "key": "fa",
        #                            "value": "56.0"
        #                        }
        #                    ]
        #                    },
        #                   {
        #                       "name": "d",
        #                       "mapping": [
        #                           {
        #                               "key": "4",
        #                               "value": "1.0"
        #                           },
        #                           {
        #                               "key": "45",
        #                               "value": "5.0"
        #                           }
        #                       ]
        #                   }
        # ]
        variables_json = {i["name"]: i["mapping"] for i in variables_json}
        variables_local = Variable.objects.filter(task_id=task_id).all()
        task = get_object_or_404(Task, id=task_id)
        formulas = FormulaPackage(list(map(lambda x: x.expression, task.formula_set.all())))

        formulas_variables = formulas.variables

        for variable in variables_local:
            if variable.name in variables_json.keys():
                variable.mapping_set.all().delete()
                Mapping.objects.bulk_create(
                    (Mapping(key=mapping['key'], value=mapping['value'], variable_id=variable.id)
                     for mapping in variables_json[variable.name])
                )
                variables_json.pop(variable.name)
            elif variable.name in formulas_variables:
                variable.mapping_set.all().delete()
            else:
                variable.delete()

        for variable in variables_json.keys():
            new_var = Variable.objects.create(name=variable, task_id=task_id)
            Mapping.objects.bulk_create(
                (Mapping(key=mapping['key'], value=mapping['value'], variable_id=new_var.id)
                 for mapping in variables_json[variable])
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
def task_get_report(request, task_id: int):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        formulas = []
        variables = []
        global_tables = {}
        data = {'variables': variables, 'formulas': formulas, "global_tables": global_tables}

        package = FormulaPackage(list(map(lambda x: x.expression, task.formula_set.all())))

        variables.extend(
            {
                "name": variable.name,
                "value": float(request.POST.get(str(variable.id)))
            }
            for variable in task.variable_set.all()
        )

        dct = {}
        for variable in task.variable_set.all():
            mappings = variable.mapping_set.all()
            for mapping in mappings:
                if mapping.key not in dct:
                    dct[mapping.key] = {}
                dct[mapping.key][variable.name] = mapping.value

        for key, item in dct.items():
            str_var = "".join(sorted(item.keys()))
            if str_var not in global_tables:
                global_tables[str_var] = {}
            global_tables[str_var][key] = item

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

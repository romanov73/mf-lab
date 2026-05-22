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


def _cubic_model(c_value: float, coeffs: dict | list | tuple) -> float:
    if isinstance(coeffs, (list, tuple)):
        a0, a1, a2, a3 = (list(coeffs) + [0, 0, 0, 0])[:4]
        return (
            (a0 or 0)
            + (a1 or 0) * c_value
            + (a2 or 0) * (c_value ** 2)
            + (a3 or 0) * (c_value ** 3)
        )

    return (
        coeffs['A0']
        + coeffs['A1'] * c_value
        + coeffs['A2'] * (c_value ** 2)
        + coeffs.get('A3', 0) * (c_value ** 3)
    )


def _build_result_items(lab: dict, calculated_results: dict | None = None) -> list:
    calculated_results = calculated_results or {}
    result_fields = lab.get('result_fields', [])

    if isinstance(result_fields, dict):
        result_fields = result_fields.get(calculated_results.get('_mode'), [])

    return [
        {
            'label': label,
            'value': calculated_results.get(label, '-'),
        }
        for label in result_fields
        if not str(label).startswith('_')
    ]


def _build_form_fields_with_values(lab: dict, form_values: dict) -> list:
    fields = []
    selected_coating = form_values.get('coating', '')
    for field in lab.get('form_fields', []):
        prepared = field.copy()

        if lab.get('id') in (1, 2, 4, 5) and field.get('name') == 'alloying_element':
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


LAB2_HMU_COEFFS = {
    "TiAlMe2N": {
        "Fe": {"A0": 38.39, "A1": 12.68, "A2": -9.32, "A3": 2.04},
        "Cr": {"A0": 38.39, "A1": 2.347, "A2": -0.1820, "A3": 0.00264},
        "Zr": {"A0": 38.39, "A1": 1.109, "A2": -0.0405, "A3": 0.00028},
    },
    "TiZrMe2N": {
        "Fe": {"A0": 38.65, "A1": 4.47, "A2": 0.33, "A3": -1.21},
        "Cr": {"A0": 38.65, "A1": 1.216, "A2": -0.0164, "A3": -0.00350},
        "Al": {"A0": 38.65, "A1": 1.716, "A2": -0.0950, "A3": 0},
    },
    "TiSiMe2N": {
        "Cr": {"A0": 34.67, "A1": 1.219, "A2": -0.0624, "A3": 0},
        "Zr": {"A0": 34.67, "A1": 0.880, "A2": -0.0246, "A3": 0},
        "Al": {"A0": 34.67, "A1": 2.077, "A2": -0.1257, "A3": 0},
    },
}

LAB2_K0_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": {"A0": 0.907, "A1": -0.177, "A2": 0.070, "A3": 0},
            "Cr": {"A0": 0.907, "A1": 0.0698, "A2": -0.00344, "A3": 0},
            "Zr": {"A0": 0.907, "A1": 0.0398, "A2": -0.00087, "A3": 0},
        },
        "Р6М5К5": {
            "Fe": {"A0": 0.295, "A1": -0.088, "A2": 0.029, "A3": 0},
            "Cr": {"A0": 0.295, "A1": 0.0228, "A2": -0.00102, "A3": 0},
            "Zr": {"A0": 0.295, "A1": 0.0096, "A2": -0.00021, "A3": 0},
        },
    },
    "TiZrMe2N": {
        "МК8": {
            "Fe": {"A0": 1.316, "A1": -0.515, "A2": 0.206, "A3": -0.008},
            "Cr": {"A0": 1.316, "A1": 0.0780, "A2": -0.00840, "A3": 0.000312},
            "Al": {"A0": 1.316, "A1": -0.0980, "A2": 0.00552, "A3": 0},
        },
        "Р6М5К5": {
            "Fe": {"A0": 0.478, "A1": -0.187, "A2": 0.079, "A3": 0},
            "Cr": {"A0": 0.478, "A1": 0.0349, "A2": -0.00169, "A3": 0},
            "Al": {"A0": 0.478, "A1": -0.0276, "A2": 0.00144, "A3": 0},
        },
    },
    "TiSiMe2N": {
        "МК8": {
            "Cr": {"A0": 1.493, "A1": 0.0684, "A2": -0.00268, "A3": 0},
            "Zr": {"A0": 1.493, "A1": 0.0172, "A2": -0.00031, "A3": 0},
            "Al": {"A0": 1.493, "A1": -0.0652, "A2": 0.00334, "A3": 0},
        },
        "Р6М5К5": {
            "Cr": {"A0": 0.531, "A1": 0.0260, "A2": -0.00124, "A3": 0},
            "Zr": {"A0": 0.531, "A1": 0.0083, "A2": -0.00020, "A3": 0},
            "Al": {"A0": 0.531, "A1": -0.0294, "A2": 0.00156, "A3": 0},
        },
    },
}

LAB2_E_COEFFS = {
    "TiAlMe2N": {
        "Fe": {"A0": 369, "A1": 39.2, "A2": -22.7, "A3": 4.9},
        "Cr": {"A0": 369, "A1": 7.09, "A2": -0.325, "A3": -0.0034},
        "Zr": {"A0": 369, "A1": 7.30, "A2": -0.335, "A3": 0.0049},
    },
    "TiZrMe2N": {
        "Fe": {"A0": 379, "A1": 7.2, "A2": 10.5, "A3": -8.5},
        "Cr": {"A0": 379, "A1": 5.96, "A2": -0.283, "A3": -0.0037},
        "Al": {"A0": 379, "A1": 11.49, "A2": -0.669, "A3": 0},
    },
    "TiSiMe2N": {
        "Cr": {"A0": 350, "A1": 7.78, "A2": -0.391, "A3": 0},
        "Zr": {"A0": 350, "A1": 6.87, "A2": -0.191, "A3": 0},
        "Al": {"A0": 350, "A1": 15.35, "A2": -0.865, "A3": 0},
    },
}

LAB2_KICP_COEFFS = {
    "TiAlMe2N": {
        "Fe": {"A0": 14.77, "A1": -1.67, "A2": 1.61, "A3": -0.33},
        "Cr": {"A0": 14.77, "A1": -0.194, "A2": 0.0125, "A3": 0.00028},
        "Zr": {"A0": 14.77, "A1": 0.095, "A2": -0.0023, "A3": 0},
    },
    "TiZrMe2N": {
        "Fe": {"A0": 14.44, "A1": -0.92, "A2": 0.37, "A3": 0},
        "Cr": {"A0": 14.44, "A1": -0.015, "A2": 0.0007, "A3": 0},
        "Al": {"A0": 14.44, "A1": 0.424, "A2": -0.0256, "A3": 0},
    },
    "TiSiMe2N": {
        "Cr": {"A0": 14.46, "A1": 0.097, "A2": -0.0046, "A3": 0},
        "Zr": {"A0": 14.46, "A1": 0.091, "A2": -0.0015, "A3": 0},
        "Al": {"A0": 14.46, "A1": 0.352, "A2": -0.0163, "A3": 0},
    },
}

LAB2_COMPOSITION_RESULTS = {
    "TiN": {"hmu": 31.5, "e": 307, "kicp": 12.3, "k0": 1.1},
    "TiZrN": {"hmu": 36.6, "e": 379, "kicp": 14.4, "k0": 1.32},
    "TiZrAlN": {"hmu": 42.0, "e": 428, "kicp": 16.1, "k0": 1.57},
    "TiSiN": {"hmu": 33.2, "e": 350, "kicp": 14.4, "k0": 1.5},
    "TiSiZrN": {"hmu": 39.7, "e": 403, "kicp": 15.5, "k0": 1.72},
}


def _build_lab2_mode1_graph_data(coating: str, tool_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count < 2:
        points_count = 2

    step = (max_c - min_c) / (points_count - 1)
    c_values = [min_c + i * step for i in range(points_count)]

    hmu_coeffs = LAB2_HMU_COEFFS[coating][alloying_element]
    e_coeffs = LAB2_E_COEFFS[coating][alloying_element]
    kicp_coeffs = LAB2_KICP_COEFFS[coating][alloying_element]
    k0_coeffs = LAB2_K0_COEFFS[coating][tool_material][alloying_element]

    return {
        'mode': 'mode1',
        'c_values': [round(value, 4) for value in c_values],
        'hmu_values': [round(_cubic_model(value, hmu_coeffs), 8) for value in c_values],
        'e_values': [round(_cubic_model(value, e_coeffs), 8) for value in c_values],
        'kicp_values': [round(_cubic_model(value, kicp_coeffs), 8) for value in c_values],
        'k0_values': [round(_cubic_model(value, k0_coeffs), 8) for value in c_values],
    }


def _build_lab2_mode2_chart_data() -> dict:
    coatings = list(LAB2_COMPOSITION_RESULTS.keys())
    return {
        'mode': 'mode2',
        'coatings': coatings,
        'hmu_values': [LAB2_COMPOSITION_RESULTS[item]['hmu'] for item in coatings],
        'e_values': [LAB2_COMPOSITION_RESULTS[item]['e'] for item in coatings],
        'kicp_values': [LAB2_COMPOSITION_RESULTS[item]['kicp'] for item in coatings],
        'k0_values': [LAB2_COMPOSITION_RESULTS[item]['k0'] for item in coatings],
    }


LAB3_TC_COEFFS = {
        "TiAlMe2N": {
            "МК8": {
                "Fe": {"A0": 16.48, "A1": 10.83, "A2": -2.39, "A3": -1.92},
                "Cr": {"A0": 16.48, "A1": 3.306, "A2": -0.1777, "A3": -0.00153},
                "Zr": {"A0": 16.48, "A1": 2.226, "A2": -0.0071, "A3": -0.00250},
            },
            "Р6М5К5": {
                "Fe": {"A0": 8.03, "A1": 1.57, "A2": -0.65, "A3": -0.13},
                "Cr": {"A0": 8.03, "A1": 2.828, "A2": -0.2263, "A3": 0.00536},
                "Zr": {"A0": 8.03, "A1": 2.732, "A2": -0.0788, "A3": -0.00043},
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": {"A0": 13.80, "A1": 4.33, "A2": 5.68, "A3": -4.33},
                "Cr": {"A0": 13.80, "A1": 2.191, "A2": 0.1435, "A3": -0.01998},
                "Al": {"A0": 13.80, "A1": 7.170, "A2": -0.4277, "A3": 0},
            },
            "Р6М5К5": {
                "Fe": {"A0": 6.79, "A1": 4.75, "A2": -1.84, "A3": -0.10},
                "Cr": {"A0": 6.79, "A1": 2.011, "A2": -0.0678, "A3": -0.00357},
                "Al": {"A0": 6.79, "A1": 5.543, "A2": -0.3137, "A3": 0},
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": {"A0": 24.18, "A1": 2.481, "A2": -0.1356, "A3": 0},
                "Zr": {"A0": 24.18, "A1": 2.570, "A2": -0.0790, "A3": 0},
                "Al": {"A0": 24.18, "A1": 5.240, "A2": -0.3071, "A3": 0},
            },
            "Р6М5К5": {
                "Cr": {"A0": 11.29, "A1": 1.518, "A2": -0.0790, "A3": 0},
                "Zr": {"A0": 11.29, "A1": 2.078, "A2": -0.06260, "A3": 0},
                "Al": {"A0": 11.29, "A1": 3.948, "A2": -0.2225, "A3": 0},
            },
        },
    }


LAB3_J_COEFFS = {
        '30XGSA': {
            "TiAlMe2N": {
                "МК8": {
                    "Fe": {"A0": 0.249, "A1": -0.0166, "A2": -0.1008, "A3": 0.07},
                    "Cr": {"A0": 0.249, "A1": -0.0135, "A2": 0.000666, "A3": 0.00000755},
                    "Zr": {"A0": 0.249, "A1": -0.0070, "A2": 0.000013, "A3": 0.00000818},
                },
                "Р6М5К5": {
                    "Fe": {"A0": 1.027, "A1": -0.0586, "A2": -0.7099, "A3": 0.5196},
                    "Cr": {"A0": 1.027, "A1": -0.06834, "A2": 0.00523, "A3": -0.000000121},
                    "Zr": {"A0": 1.027, "A1": -0.0213, "A2": -0.000838, "A3": 0.0000495},
                },
            },
            "TiZrMe2N": {
                "МК8": {
                    "Fe": {"A0": 0.226, "A1": -0.0266, "A2": -0.0621, "A3": 0.0395},
                    "Cr": {"A0": 0.226, "A1": -0.0026, "A2": -0.00174, "A3": 0.000135},
                    "Al": {"A0": 0.226, "A1": -0.0239, "A2": 0.00149, "A3": 0},
                },
                "Р6М5К5": {
                    "Fe": {"A0": 1.076, "A1": -0.1678, "A2": -0.3472, "A3": 0.2458},
                    "Cr": {"A0": 1.076, "A1": -0.0725, "A2": 0.00413, "A3": 0.000011},
                    "Al": {"A0": 1.076, "A1": -0.0881, "A2": 0.00475, "A3": 0},
                },
            },
            "TiSiMe2N": {
                "МК8": {
                    "Cr": {"A0": 0.197, "A1": -0.0120, "A2": 0.00062, "A3": 0},
                    "Zr": {"A0": 0.197, "A1": -0.0077, "A2": 0.00023, "A3": 0},
                    "Al": {"A0": 0.197, "A1": -0.0164, "A2": 0.00096, "A3": 0},
                },
                "Р6М5К5": {
                    "Cr": {"A0": 1.124, "A1": -0.0637, "A2": 0.00325, "A3": 0},
                    "Zr": {"A0": 1.124, "A1": -0.0517, "A2": 0.00150, "A3": 0},
                    "Al": {"A0": 1.124, "A1": -0.1087, "A2": 0.00637, "A3": 0},
                },
            },
        },
        '12X18N10T': {
            "TiAlMe2N": {
                "МК8": {
                    "Fe": {"A0": 0.834, "A1": -0.4379, "A2": 0.4098, "A3": -0.1122},
                    "Cr": {"A0": 0.834, "A1": -0.0497, "A2": 0.002743, "A3": 0.0001017},
                    "Zr": {"A0": 0.834, "A1": -0.0442, "A2": 0.0022, "A3": -0.0000308},
                },
                "Р6М5К5": {
                    "Fe": {"A0": 3.278, "A1": -0.7682, "A2": -0.5234, "A3": 0.6478},
                    "Cr": {"A0": 3.278, "A1": -0.229, "A2": 0.01401, "A3": 0.000238},
                    "Zr": {"A0": 3.278, "A1": -0.1526, "A2": 0.006213, "A3": -0.000056},
                },
            },
            "TiZrMe2N": {
                "МК8": {
                    "Fe": {"A0": 0.826, "A1": -0.0324, "A2": -0.3617, "A3": 0.2261},
                    "Cr": {"A0": 0.826, "A1": -0.0525, "A2": 0.00378, "A3": -0.000037},
                    "Al": {"A0": 0.826, "A1": -0.0807, "A2": 0.00492, "A3": 0},
                },
                "Р6М5К5": {
                    "Cr": {"A0": 3.094, "A1": -0.0848, "A2": -0.01032, "A3": 0.001268},
                    "Al": {"A0": 3.094, "A1": -0.2220, "A2": 0.01313, "A3": 0},
                },
            },
            "TiSiMe2N": {
                "МК8": {
                    "Cr": {"A0": 0.724, "A1": -0.0428, "A2": 0.00250, "A3": 0},
                    "Zr": {"A0": 0.724, "A1": -0.0257, "A2": 0.00082, "A3": 0},
                    "Al": {"A0": 0.724, "A1": -0.0500, "A2": 0.00280, "A3": 0},
                },
                "Р6М5К5": {
                    "Cr": {"A0": 3.221, "A1": -0.1949, "A2": 0.01131, "A3": 0},
                    "Zr": {"A0": 3.221, "A1": -0.1251, "A2": 0.0043, "A3": 0},
                    "Al": {"A0": 3.221, "A1": -0.2024, "A2": 0.01164, "A3": 0},
                },
            },
        }
}


def _build_lab3_graph_data(coating: str, tool_material: str, processed_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count < 2:
        points_count = 2

    step = (max_c - min_c) / (points_count - 1)
    c_values = [min_c + i * step for i in range(points_count)]

    tc_coeffs = LAB3_TC_COEFFS[coating][tool_material][alloying_element]
    # map processed_material to keys used in LAB3_J_COEFFS: '30XGSA' and '12X18N10T'
    proc_key = '30XGSA' if processed_material == '30ХГСА' else '12X18N10T'
    j_coeffs = LAB3_J_COEFFS[proc_key][coating][tool_material][alloying_element]

    return {
        'c_values': [round(value, 4) for value in c_values],
        'tc_values': [round(_cubic_model(value, tc_coeffs), 8) for value in c_values],
        'j_values': [round(_cubic_model(value, j_coeffs), 8) for value in c_values],
    }


LAB4_CGAMMA_COEFFS = {
    'TiAlMe2N': {
        'МК8': {
            'Fe': {'A0': 0.501, 'A1': 0.1210, 'A2': -0.05135, 'A3': 0},
            'Cr': {'A0': 0.501, 'A1': 0.0166, 'A2': -0.00087, 'A3': 0},
            'Zr': {'A0': 0.501, 'A1': 0.0073, 'A2': -0.00027, 'A3': 2.382e-06},
        },
        'Р6М5К5': {
            'Fe': {'A0': 0.483, 'A1': 0.1802, 'A2': -0.13825, 'A3': 3.166e-02},
            'Cr': {'A0': 0.483, 'A1': 0.0145, 'A2': -0.00068, 'A3': 4.35e-06},
            'Zr': {'A0': 0.483, 'A1': 0.0074, 'A2': -0.00031, 'A3': 3.92e-06},
        },
    },
    'TiZrMe2N': {
        'МК8': {
            'Fe': {'A0': 0.508, 'A1': 0.0834, 'A2': -0.02986, 'A3': 0},
            'Cr': {'A0': 0.508, 'A1': 0.0136, 'A2': -0.00073, 'A3': 0},
            'Al': {'A0': 0.508, 'A1': 0.0110, 'A2': -0.00057, 'A3': 0},
        },
        'Р6М5К5': {
            'Fe': {'A0': 0.497, 'A1': 0.1411, 'A2': -0.09028, 'A3': 1.586e-02},
            'Cr': {'A0': 0.497, 'A1': 0.0212, 'A2': -0.00177, 'A3': 3.75e-05},
            'Al': {'A0': 0.497, 'A1': 0.0118, 'A2': -0.00069, 'A3': 0},
        },
    },
    'TiSiMe2N': {
        'МК8': {
            'Cr': {'A0': 0.492, 'A1': 0.0167, 'A2': -0.00086, 'A3': 0},
            'Zr': {'A0': 0.492, 'A1': 0.0072, 'A2': -0.00019, 'A3': 0},
            'Al': {'A0': 0.492, 'A1': 0.0124, 'A2': -0.00070, 'A3': 0},
        },
        'Р6М5К5': {
            'Cr': {'A0': 0.476, 'A1': 0.0092, 'A2': -0.00046, 'A3': 0},
            'Zr': {'A0': 0.476, 'A1': 0.0040, 'A2': -0.00011, 'A3': 0},
            'Al': {'A0': 0.476, 'A1': 0.0069, 'A2': -0.00039, 'A3': 0},
        },
    },
}

LAB4_KL_COEFFS = {
    'TiAlMe2N': {
        'МК8': {
            'Fe': {'A0': 1.91, 'A1': 0.264, 'A2': -0.1163, 'A3': 0},
            'Cr': {'A0': 1.91, 'A1': 0.035, 'A2': -0.0018, 'A3': 0},
            'Zr': {'A0': 1.91, 'A1': 0.018, 'A2': -0.0005, 'A3': -4.27e-06},
        },
        'Р6М5К5': {
            'Fe': {'A0': 1.79, 'A1': 0.271, 'A2': -0.1123, 'A3': -5.31e-03},
            'Cr': {'A0': 1.79, 'A1': 0.043, 'A2': -0.0030, 'A3': 4.63e-05},
            'Zr': {'A0': 1.79, 'A1': 0.015, 'A2': -0.0007, 'A3': 9.5e-06},
        },
    },
    'TiZrMe2N': {
        'МК8': {
            'Fe': {'A0': 1.96, 'A1': 0.239, 'A2': -0.0883, 'A3': 0},
            'Cr': {'A0': 1.96, 'A1': 0.035, 'A2': -0.0017, 'A3': 0},
            'Al': {'A0': 1.96, 'A1': 0.019, 'A2': -0.0011, 'A3': 0},
        },
        'Р6М5К5': {
            'Fe': {'A0': 1.82, 'A1': 0.356, 'A2': -0.2526, 'A3': 5.58e-02},
            'Cr': {'A0': 1.82, 'A1': 0.055, 'A2': -0.0053, 'A3': 1.59e-04},
            'Al': {'A0': 1.82, 'A1': 0.024, 'A2': -0.0014, 'A3': 0},
        },
    },
    'TiSiMe2N': {
        'МК8': {
            'Cr': {'A0': 1.90, 'A1': 0.026, 'A2': -0.0012, 'A3': 0},
            'Zr': {'A0': 1.90, 'A1': 0.008, 'A2': -0.0002, 'A3': 0},
            'Al': {'A0': 1.90, 'A1': 0.010, 'A2': -0.0005, 'A3': 0},
        },
        'Р6М5К5': {
            'Cr': {'A0': 1.75, 'A1': 0.032, 'A2': -0.0017, 'A3': 0},
            'Zr': {'A0': 1.75, 'A1': 0.009, 'A2': -0.00025, 'A3': 0},
            'Al': {'A0': 1.75, 'A1': 0.015, 'A2': -0.0008, 'A3': 0},
        },
    },
}

LAB4_PX_COEFFS = {
    'TiAlMe2N': {
        'МК8': {
            'Fe': {'A0': 83, 'A1': 15.8, 'A2': -6.64, 'A3': 0},
            'Cr': {'A0': 83, 'A1': 2.47, 'A2': -0.133, 'A3': 0},
            'Zr': {'A0': 83, 'A1': 0.96, 'A2': -0.048, 'A3': 7.5e-04},
        },
        'Р6М5К5': {
            'Fe': {'A0': 110, 'A1': 29.9, 'A2': -22.61, 'A3': 4.81},
            'Cr': {'A0': 110, 'A1': 2.28, 'A2': -0.042, 'A3': -5.2e-03},
            'Zr': {'A0': 110, 'A1': 0.79, 'A2': -0.032, 'A3': 3.7e-04},
        },
    },
    'TiZrMe2N': {
        'МК8': {
            'Fe': {'A0': 86, 'A1': 10.7, 'A2': -4.1, 'A3': 0},
            'Cr': {'A0': 86, 'A1': 1.72, 'A2': -0.09, 'A3': 0},
            'Al': {'A0': 86, 'A1': 0.78, 'A2': -0.04, 'A3': 0},
        },
        'Р6М5К5': {
            'Fe': {'A0': 111, 'A1': 26.4, 'A2': -18.1, 'A3': 3.75},
            'Cr': {'A0': 111, 'A1': 4.0, 'A2': -0.36, 'A3': 9.9e-03},
            'Al': {'A0': 111, 'A1': 1.4, 'A2': -0.07, 'A3': 0},
        },
    },
    'TiSiMe2N': {
        'МК8': {
            'Cr': {'A0': 81, 'A1': 2.5, 'A2': -0.12, 'A3': 0},
            'Zr': {'A0': 81, 'A1': 0.9, 'A2': -0.02, 'A3': 0},
            'Al': {'A0': 81, 'A1': 0.8, 'A2': -0.04, 'A3': 0},
        },
        'Р6М5К5': {
            'Cr': {'A0': 108, 'A1': 1.66, 'A2': -0.08, 'A3': 0},
            'Zr': {'A0': 108, 'A1': 0.50, 'A2': -0.014, 'A3': 0},
            'Al': {'A0': 108, 'A1': 0.42, 'A2': -0.022, 'A3': 0},
        },
    },
}

LAB4_PY_COEFFS = {
    'TiAlMe2N': {
        'МК8': {
            'Fe': {'A0': 130, 'A1': 23.04, 'A2': -10.34, 'A3': 0.594},
            'Cr': {'A0': 130, 'A1': 3.71, 'A2': -0.201, 'A3': 0},
            'Zr': {'A0': 130, 'A1': 1.115, 'A2': -0.047, 'A3': 6.2e-04},
        },
        'Р6М5К5': {
            'Fe': {'A0': 189, 'A1': 59.5, 'A2': -48.57, 'A3': 12.24},
            'Cr': {'A0': 189, 'A1': 4.73, 'A2': -0.22, 'A3': -1.7e-03},
            'Zr': {'A0': 189, 'A1': 1.59, 'A2': -0.06, 'A3': 7.4e-04},
        },
    },
    'TiZrMe2N': {
        'МК8': {
            'Fe': {'A0': 133, 'A1': 19.6, 'A2': -7.2, 'A3': 0},
            'Cr': {'A0': 133, 'A1': 2.8, 'A2': -0.141, 'A3': 0},
            'Al': {'A0': 133, 'A1': 1.50, 'A2': -0.081, 'A3': 0},
        },
        'Р6М5К5': {
            'Fe': {'A0': 193, 'A1': 46.0, 'A2': -29.3, 'A3': 5.0},
            'Cr': {'A0': 193, 'A1': 7.27, 'A2': -0.75, 'A3': 0.025},
            'Al': {'A0': 193, 'A1': 2.51, 'A2': -0.14, 'A3': 0},
        },
    },
    'TiSiMe2N': {
        'МК8': {
            'Cr': {'A0': 127, 'A1': 3.7, 'A2': -0.17, 'A3': 0},
            'Zr': {'A0': 127, 'A1': 1.1, 'A2': -0.03, 'A3': 0},
            'Al': {'A0': 127, 'A1': 0.9, 'A2': -0.05, 'A3': 0},
        },
        'Р6М5К5': {
            'Cr': {'A0': 184, 'A1': 2.56, 'A2': -0.125, 'A3': 0},
            'Zr': {'A0': 184, 'A1': 0.99, 'A2': -0.029, 'A3': 0},
            'Al': {'A0': 184, 'A1': 0.90, 'A2': -0.051, 'A3': 0},
        },
    },
}

LAB4_PZ_COEFFS = {
    'TiAlMe2N': {
        'МК8': {
            'Fe': {'A0': 209, 'A1': 32.6, 'A2': -13.4, 'A3': 0},
            'Cr': {'A0': 209, 'A1': 5.46, 'A2': -0.297, 'A3': 0},
            'Zr': {'A0': 209, 'A1': 1.89, 'A2': -0.096, 'A3': 1.5e-03},
        },
        'Р6М5К5': {
            'Fe': {'A0': 424, 'A1': 113.2, 'A2': -94.6, 'A3': 24.65},
            'Cr': {'A0': 424, 'A1': 10.53, 'A2': -0.71, 'A3': 0.011},
            'Zr': {'A0': 424, 'A1': 2.58, 'A2': -0.09, 'A3': 7.2e-04},
        },
    },
    'TiZrMe2N': {
        'МК8': {
            'Fe': {'A0': 216, 'A1': 31.6, 'A2': -15.0, 'A3': 1.9},
            'Cr': {'A0': 216, 'A1': 4.2, 'A2': -0.21, 'A3': 0},
            'Al': {'A0': 216, 'A1': 2.2, 'A2': -0.12, 'A3': 0},
        },
        'Р6М5К5': {
            'Fe': {'A0': 433, 'A1': 94.9, 'A2': -66.23, 'A3': 13.65},
            'Cr': {'A0': 433, 'A1': 10.41, 'A2': -0.59, 'A3': 0},
            'Al': {'A0': 433, 'A1': 3.75, 'A2': -0.21, 'A3': 0},
        },
    },
    'TiSiMe2N': {
        'МК8': {
            'Cr': {'A0': 205, 'A1': 5.4, 'A2': -0.27, 'A3': 0},
            'Zr': {'A0': 205, 'A1': 1.6, 'A2': -0.05, 'A3': 0},
            'Al': {'A0': 205, 'A1': 1.6, 'A2': -0.09, 'A3': 0},
        },
        'Р6М5К5': {
            'Cr': {'A0': 415, 'A1': 5.12, 'A2': -0.25, 'A3': 0},
            'Zr': {'A0': 415, 'A1': 1.83, 'A2': -0.055, 'A3': 0},
            'Al': {'A0': 415, 'A1': 1.16, 'A2': -0.067, 'A3': 0},
        },
    },
}

LAB4_COMPOSITION_RESULTS = {
    'без покрытия': {'cgamma': 0.71, 'kl': 2.21, 'pz': 228, 'ngamma': 272, 'fgamma': 135, 'qn': 578, 'qf': 430, 'sigma_n': 1720, 'tau_f': 510},
    'TiN': {'cgamma': 0.45, 'kl': 1.77, 'pz': 197, 'ngamma': 198, 'fgamma': 120, 'qn': 624, 'qf': 379, 'sigma_n': 1908, 'tau_f': 559},
    'TiZrN': {'cgamma': 0.51, 'kl': 1.96, 'pz': 216, 'ngamma': 218, 'fgamma': 130, 'qn': 608, 'qf': 362, 'sigma_n': 1839, 'tau_f': 544},
    'TiZrAlN': {'cgamma': 0.56, 'kl': 2.05, 'pz': 226, 'ngamma': 228, 'fgamma': 136, 'qn': 577, 'qf': 345, 'sigma_n': 1773, 'tau_f': 530},
    'TiSiN': {'cgamma': 0.50, 'kl': 1.90, 'pz': 205, 'ngamma': 207, 'fgamma': 123, 'qn': 594, 'qf': 354, 'sigma_n': 1808, 'tau_f': 533},
    'TiSiZrN': {'cgamma': 0.55, 'kl': 1.97, 'pz': 217, 'ngamma': 220, 'fgamma': 133, 'qn': 565, 'qf': 341, 'sigma_n': 1644, 'tau_f': 510},
}


def _build_lab4_mode1_graph_data(coating: str, tool_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count < 2:
        points_count = 2

    step = (max_c - min_c) / (points_count - 1)
    c_values = [min_c + i * step for i in range(points_count)]

    cgamma_coeffs = LAB4_CGAMMA_COEFFS[coating][tool_material][alloying_element]
    kl_coeffs = LAB4_KL_COEFFS[coating][tool_material][alloying_element]
    px_coeffs = LAB4_PX_COEFFS[coating][tool_material][alloying_element]
    py_coeffs = LAB4_PY_COEFFS[coating][tool_material][alloying_element]
    pz_coeffs = LAB4_PZ_COEFFS[coating][tool_material][alloying_element]

    return {
        'mode': 'mode1',
        'c_values': [round(value, 4) for value in c_values],
        'cgamma_values': [round(_cubic_model(value, cgamma_coeffs), 8) for value in c_values],
        'kl_values': [round(_cubic_model(value, kl_coeffs), 8) for value in c_values],
        'px_values': [round(_cubic_model(value, px_coeffs), 8) for value in c_values],
        'py_values': [round(_cubic_model(value, py_coeffs), 8) for value in c_values],
        'pz_values': [round(_cubic_model(value, pz_coeffs), 8) for value in c_values],
    }


def _build_lab4_mode2_chart_data() -> dict:
    coatings = list(LAB4_COMPOSITION_RESULTS.keys())
    return {
        'mode': 'mode2',
        'coatings': coatings,
        'cgamma_values': [LAB4_COMPOSITION_RESULTS[item]['cgamma'] for item in coatings],
        'kl_values': [LAB4_COMPOSITION_RESULTS[item]['kl'] for item in coatings],
        'pz_values': [LAB4_COMPOSITION_RESULTS[item]['pz'] for item in coatings],
        'ngamma_values': [LAB4_COMPOSITION_RESULTS[item]['ngamma'] for item in coatings],
        'fgamma_values': [LAB4_COMPOSITION_RESULTS[item]['fgamma'] for item in coatings],
        'qn_values': [LAB4_COMPOSITION_RESULTS[item]['qn'] for item in coatings],
        'qf_values': [LAB4_COMPOSITION_RESULTS[item]['qf'] for item in coatings],
        'sigma_n_values': [LAB4_COMPOSITION_RESULTS[item]['sigma_n'] for item in coatings],
        'tau_f_values': [LAB4_COMPOSITION_RESULTS[item]['tau_f'] for item in coatings],
    }


LAB5_THERMAL_STATE_RESULTS = {
    'Отрезка': {
        'Без покрытия': {'Qп': 85.1, 'Qз': -1.2, 'qп': 21.3, 'qз': -24.1, 'Тп.ср.': 849, 'Тз.ср.': 440},
        'TiN': {'Qп': 74.6, 'Qз': -1.1, 'qп': 22.0, 'qз': -25.4, 'Тп.ср.': 804, 'Тз.ср.': 380},
        'TiAlN': {'Qп': 77.9, 'Qз': -1.1, 'qп': 21.4, 'qз': -24.6, 'Тп.ср.': 810, 'Тз.ср.': 396},
        'TiAlCrN': {'Qп': 78.2, 'Qз': -1.1, 'qп': 20.4, 'qз': -23.4, 'Тп.ср.': 805, 'Тз.ср.': 389},
    },
    'Нарезание резьбы': {
        'Без покрытия': {'Qп': 45.0, 'Qз': -1.05, 'qп': 6.48, 'qз': -8.32, 'Тп.ср.': 656, 'Тз.ср.': 359},
        'TiN': {'Qп': 34.75, 'Qз': -0.7, 'qп': 6.41, 'qз': -7.87, 'Тп.ср.': 636, 'Тз.ср.': 340},
        'TiCrN': {'Qп': 36.57, 'Qз': -0.73, 'qп': 5.53, 'qз': -5.81, 'Тп.ср.': 648, 'Тз.ср.': 341},
        'TiCrZrN': {'Qп': 41.21, 'Qз': -0.76, 'qп': 3.5, 'qз': -4.14, 'Тп.ср.': 653, 'Тз.ср.': 355},
    },
}


LAB5_HEAT_BALANCE_RESULTS = {
    'Нарезание резьбы': {
        'Без покрытия': {'стружка': 65, 'инструмент': 27, 'заготовка': 8},
        'TiN': {'стружка': 73, 'инструмент': 18, 'заготовка': 9},
        'TiCrN': {'стружка': 74, 'инструмент': 16, 'заготовка': 10},
        'TiCrZrN': {'стружка': 76, 'инструмент': 14, 'заготовка': 10},
    },
    'Торцовое фрезерование': {
        'Без покрытия': {'стружка': 69.1, 'инструмент': 13.4, 'заготовка': 17.5},
        'TiN': {'стружка': 75.4, 'инструмент': 8.8, 'заготовка': 15.8},
        'TiZrN': {'стружка': 76.6, 'инструмент': 10.2, 'заготовка': 16.2},
        'TiZrCN': {'стружка': 73.4, 'инструмент': 10.6, 'заготовка': 15.9},
    },
}


LAB5_MODE1_COEFFS = {
    "qp": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [47.7, 4.7, -1.54, -0.292],
                "Cr": [47.7, 0.84, -0.08, 0.0025],
                "Zr": [47.7, 0.15, -0.0034, -0.000043],
            },
            "Р6М5К5": {
                "Fe": [14.4, 4.8, -3.80, 0.80],
                "Cr": [14.4, 0.409, -0.0366, 0.001],
                "Zr": [14.4, 0.09, -0.0032, 0.000017],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [50.9, 10.2, -8.21, 2.10],
                "Cr": [50.9, 0.82, -0.052, 0.000146],
                "Al": [50.9, 0.36, -0.019, None],
            },
            "Р6М5К5": {
                "Fe": [16.3, 4.7, -2.70, 0.33],
                "Cr": [16.3, 0.36, -0.023, 0.00011],
                "Al": [16.3, 0.08, -0.004, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [49.9, 0.78, -0.045, None],
                "Zr": [49.9, 0.11, -0.003, None],
                "Al": [49.9, 0.11, -0.007, None],
            },
            "Р6М5К5": {
                "Cr": [16.1, 0.211, -0.0132, None],
                "Zr": [16.1, 0.077, -0.0024, None],
                "Al": [16.1, 0.056, -0.0031, None],
            },
        },
    },

    "qz_power": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [-8.53, -0.49, 0.191, None],
                "Cr": [-8.53, -0.096, 0.0053, 0.000017],
                "Zr": [-8.53, -0.008, 0.0002, None],
            },
            "Р6М5К5": {
                "Fe": [-2.43, 0.14, -0.055, None],
                "Cr": [-2.43, -0.024, -0.0010, -0.000017],
                "Zr": [-2.43, 0.026, -0.00075, None],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [-9.02, -0.384, -0.782, 0.616],
                "Cr": [-9.02, 0.175, -0.0164, 0.000497],
                "Al": [-9.02, 0.1560, -0.00821, None],
            },
            "Р6М5К5": {
                "Fe": [-2.79, 0.254, -0.211, 0.058],
                "Cr": [-2.79, 0.036, -0.00081, -0.000086],
                "Al": [-2.79, 0.081, -0.0043, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [-9.02, -0.061, 0.0031, None],
                "Zr": [-9.02, 0.029, -0.0005, None],
                "Al": [-9.02, 0.146, -0.0074, None],
            },
            "Р6М5К5": {
                "Cr": [-2.91, 0.064, -0.0032, None],
                "Zr": [-2.91, 0.035, -0.0009, None],
                "Al": [-2.91, 0.082, -0.0034, None],
            },
        },
    },

    "qpi": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [68, -5.35, -0.55, 3.44],
                "Cr": [68, -0.59, 0.054, -0.0015],
                "Zr": [68, -0.39, 0.011, None],
            },
            "Р6М5К5": {
                "Fe": [21.1, -0.55, -0.05, 0.212],
                "Cr": [21.1, -0.225, 0.0135, -0.000096],
                "Zr": [21.1, -0.199, 0.00524, None],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [71, -1.3, -1.24, 0.95],
                "Cr": [71, -1.07, 0.070, -0.0013],
                "Al": [71, -0.97, 0.051, None],
            },
            "Р6М5К5": {
                "Fe": [23.3, -0.88, 0.60, -0.125],
                "Cr": [23.3, -0.395, 0.0348, -0.00082],
                "Al": [23.3, -0.777, 0.0431, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [72, -1.01, 0.054, None],
                "Zr": [72, -0.77, 0.023, None],
                "Al": [72, -2.01, 0.117, None],
            },
            "Р6М5К5": {
                "Cr": [24.0, -0.61, 0.034, None],
                "Zr": [24.0, -0.35, 0.009, None],
                "Al": [24.0, -0.86, 0.049, None],
            },
        },
    },

    "qzi": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [-121, -10.6, 8.23, -2.15],
                "Cr": [-121, -1.18, -0.006, 0.0056],
                "Zr": [-121, -0.16, 0.0068, -0.000094],
            },
            "Р6М5К5": {
                "Fe": [-37.5, 2.7, -1.79, 0.44],
                "Cr": [-37.5, 0.60, -0.048, 0.0011],
                "Zr": [-37.5, 0.51, -0.014, -0.000014],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [-128, -5.5, -11.09, 8.74],
                "Cr": [-128, 2.49, -0.233, 0.00706],
                "Al": [-128, 2.21, -0.117, None],
            },
            "Р6М5К5": {
                "Fe": [-39.6, 2.2, -0.65, -0.04],
                "Cr": [-39.6, 0.84, -0.064, 0.0011],
                "Al": [-39.6, 1.27, -0.066, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [-128, -1.01, 0.050, None],
                "Zr": [-128, 0.24, -0.004, None],
                "Al": [-128, 1.72, -0.091, None],
            },
            "Р6М5К5": {
                "Cr": [-41.3, 0.93, -0.049, None],
                "Zr": [-41.3, 0.51, -0.013, None],
                "Al": [-41.3, 1.19, -0.050, None],
            },
        },
    },

    "tp_avg": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [899, 90.7, -40.64, None],
                "Cr": [899, 12.21, -0.67, None],
                "Zr": [899, 3.43, -0.14, 0.00168],
            },
            "Р6М5К5": {
                "Fe": [416, 39.5, -29.0, 5.5],
                "Cr": [416, 3.50, -0.19, None],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [911, 66.3, -12.04, -11.64],
                "Cr": [911, 8.02, -0.251, -0.016],
                "Al": [911, 3.21, -0.183, None],
            },
            "Р6М5К5": {
                "Fe": [418, 31.4, -19.55, 3.36],
                "Cr": [418, 2.91, -0.085, -0.0069],
                "Al": [418, -0.27, 0.017, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [879, 9.54, -0.491, None],
                "Zr": [879, 3.65, -0.107, None],
                "Al": [879, 4.77, -0.258, None],
            },
            "Р6М5К5": {
                "Cr": [410, 1.01, -0.058, None],
                "Zr": [410, 0.34, -0.010, None],
                "Al": [410, -0.26, 0.017, None],
            },
        },
    },

    "tz_avg": {
        "TiAlMe2N": {
            "МК8": {
                "Fe": [428, 65.4, -26.0, None],
                "Cr": [428, 9.9, -0.532, None],
                "Zr": [428, 3.24, -0.147, 0.00184],
            },
            "Р6М5К5": {
                "Fe": [227, 46.4, -30.09, 5.10],
                "Cr": [227, 4.89, -0.261, None],
                "Zr": [227, 1.68, -0.089, 0.0015],
            },
        },
        "TiZrMe2N": {
            "МК8": {
                "Fe": [447, 64.4, -23.1, None],
                "Cr": [447, 10.9, -0.859, 0.0197],
                "Al": [447, 4.28, -0.241, None],
            },
            "Р6М5К5": {
                "Fe": [234, 51.8, -39.13, 9.50],
                "Cr": [234, 7.18, -0.679, 0.0198],
                "Al": [234, 2.00, -0.117, None],
            },
        },
        "TiSiMe2N": {
            "МК8": {
                "Cr": [428, 8.94, -0.446, None],
                "Zr": [428, 2.96, -0.084, None],
                "Al": [428, 2.51, -0.149, None],
            },
            "Р6М5К5": {
                "Cr": [225, 3.12, -0.162, None],
                "Zr": [225, 1.01, -0.031, None],
                "Al": [225, 0.74, -0.042, None],
            },
        },
    },
}


# --- Lab 6 coefficients: напряженное состояние режущего клина ---
LAB6_QN_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": [596, -42.3, 20, 0],
            "Cr": [596, -2.96, 0.134, 0],
            "Zr": [596, -3.04, 0.069, 0.00046],
        },
        "Р6М5К5": {
            "Fe": [532, -47.3, 31.8, -5.14],
            "Cr": [532, 1.88, -0.28, 0.024],
            "Zr": [532, -3.55, 0.10, 0],
        }
    },

    "TiZrMe2N": {
        "МК8": {
            "Fe": [608, -11.5, 3.2, 0],
            "Cr": [608, -4.0, 0.41, -0.011],
            "Al": [608, -6.2, 0.31, 0],
        },
        "Р6М5К5": {
            "Fe": [529, 28.6, 12.0, 0.28],
            "Cr": [529, -5.2, 0.22, 0.011],
            "Al": [529, -7.19, 0.44, 0],
        }
    },

    "TiSiMe2N": {
        "МК8": {
            "Cr": [594, -3.1, 0.2, 0],
            "Zr": [594, -3.3, 0.1, 0],
            "Al": [594, -9.1, 0.5, 0],
        },
        "Р6М5К5": {
            "Cr": [528, -3.13, 0.167, 0],
            "Zr": [528, -1.83, 0.051, 0],
            "Al": [528, -5.74, 0.328, 0],
        }
    }
}

LAB6_QF_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": [357, -13.7, 4.48, 1.4],
            "Cr": [357, -0.54, 0.02, 0],
            "Zr": [357, -1.45, 0.04, 0.0002],
        },
        "Р6М5К5": {
            "Fe": [390, -20.8, 14.8, -2.80],
            "Cr": [390, -1.47, -0.013, 0.0058],
            "Zr": [390, -2.13, 0.06, 0],
        }
    },

    "TiZrMe2N": {
        "МК8": {
            "Fe": [362, -4, 1.1, 0],
            "Cr": [362, -1.6, 0.15, -0.003],
            "Al": [362, -3.5, 0.18, 0],
        },
        "Р6М5К5": {
            "Fe": [387, -9.9, 0.76, 3.00],
            "Cr": [387, -2.22, 0.09, 0.0053],
            "Al": [387, -3.74, 0.22, 0],
        }
    },

    "TiSiMe2N": {
        "МК8": {
            "Cr": [354, -0.6, 0.04, 0],
            "Zr": [354, -1.5, 0.04, 0],
            "Al": [354, -5.3, 0.32, 0],
        },
        "Р6М5К5": {
            "Cr": [385, -1.44, 0.08, 0],
            "Zr": [385, -1.01, 0.029, 0],
            "Al": [385, -3.52, 0.204, 0],
        }
    }
}

LAB6_SIGMA_N_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": [1804, -211.9, 98.9, 0],
            "Cr": [1804, -20.85, 1.056, 0],
            "Zr": [1804, -15.49, 0.504, -0.0028],
        },
        "Р6М5К5": {
            "Fe": [1927, -366.3, 302.2, -73.2],
            "Cr": [1927, -21.66, 0.107, 0.0630],
            "Zr": [1927, -24.14, 1.181, -0.0184],
        }
    },

    "TiZrMe2N": {
        "МК8": {
            "Fe": [1839, -111.3, 45.02, 0],
            "Cr": [1839, -19.90, 1.316, -0.0071],
            "Al": [1839, -28.23, 1.497, 0],
        },
        "Р6М5К5": {
            "Fe": [1898, -226.3, 148.9, -28.8],
            "Cr": [1898, -35.20, 2.306, -0.000407],
            "Al": [1898, -35.20, 2.099, 0],
        }
    },

    "TiSiMe2N": {
        "МК8": {
            "Cr": [1808, -22.26, 1.208, 0],
            "Zr": [1808, -15.47, 0.357, 0],
            "Al": [1808, -39.41, 2.312, 0],
        },
        "Р6М5К5": {
            "Cr": [1911, -17.08, 0.867, 0],
            "Zr": [1911, -10.19, 0.271, 0],
            "Al": [1911, -28.04, 1.654, 0],
        }
    }
}

LAB6_TAU_F_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": [537, -29.6, 14.2, 0],
            "Cr": [537, -2.47, 0.133, 0],
            "Zr": [537, -2.82, 0.096, -0.0005],
        },
        "Р6М5К5": {
            "Fe": [611, -42.3, 23.3, 0],
            "Cr": [611, -4.33, 0.218, 0],
            "Zr": [611, -4.61, 0.215, -0.0032],
        }
    },

    "TiZrMe2N": {
        "МК8": {
            "Fe": [544, -12.6, 4.34, 0],
            "Cr": [544, -3.20, 0.305, -0.0082],
            "Al": [544, -5.92, 0.312, 0],
        },
        "Р6М5К5": {
            "Fe": [605, -30.3, 22.57, -5.38],
            "Cr": [605, 3.41, -0.071, 0.0240],
            "Al": [605, -6.92, 0.421, 0],
        }
    },

    "TiSiMe2N": {
        "МК8": {
            "Cr": [533, -1.76, 0.101, 0],
            "Zr": [533, -2.57, 0.066, 0],
            "Al": [533, -8.73, 0.512, 0],
        },
        "Р6М5К5": {
            "Cr": [604, -2.91, 0.156, 0],
            "Zr": [604, -1.87, 0.043, 0],
            "Al": [604, -6.35, 0.383, 0],
        }
    }
}

LAB6_SIGMA_MAX_COEFFS = {
    "TiAlMe2N": {
        "МК8": {
            "Fe": [846, -105.51, 53.11, 0],
            "Cr": [846, -10.01, 0.265, 0.0294],
            "Zr": [846, -10.42, 0.505, -0.0073],
        },
        "Р6М5К5": {
            "Fe": [1101, -135.0, 76.46, -3.80],
            "Cr": [1101, -16.04, 0.575, 0.0240],
            "Zr": [1101, -12.63, 0.416, -0.0018],
        }
    },

    "TiZrMe2N": {
        "МК8": {
            "Fe": [857, -82.0, 25.52, 6.58],
            "Cr": [857, -16.30, 1.241, -0.0209],
            "Al": [857, -20.19, 1.271, 0],
        },
        "Р6М5К5": {
            "Fe": [1060, -34.3, -69.30, 47.86],
            "Cr": [1060, -18.24, 1.344, -0.0187],
            "Al": [1060, -21.45, 1.170, 0],
        }
    },

    "TiSiMe2N": {
        "МК8": {
            "Cr": [856, -14.14, 0.841, 0],
            "Zr": [856, -8.56, 0.259, 0],
            "Al": [856, -18.52, 1.068, 0],
        },
        "Р6М5К5": {
            "Cr": [1084, -18.93, 1.111, 0],
            "Zr": [1084, -13.15, 0.402, 0],
            "Al": [1084, -25.94, 1.490, 0],
        }
    }
}

LAB6_COMPOSITION_DATA = {
    "МК8": {
        "TiN":      {"sigma1": 546,  "sigma_ost": -775,  "sigma_t": -1827, "sigma_sum": -2056},
        "TiAlN":    {"sigma1": 589,  "sigma_ost": -903,  "sigma_t": -1890, "sigma_sum": -2204},
        "TiAlSiN":  {"sigma1": 642,  "sigma_ost": -1609, "sigma_t": -2278, "sigma_sum": -3245},
        "TiZrN":    {"sigma1": 613,  "sigma_ost": -1256, "sigma_t": -1906, "sigma_sum": -2549},
        "TiZrCrN":  {"sigma1": -1422,"sigma_ost": -2145, "sigma_t": -2955, "sigma_sum": -1422},
        "TiSiN":    {"sigma1": 565,  "sigma_ost": -1069, "sigma_t": -1857, "sigma_sum": -2361},
        "TiSiAlN":  {"sigma1": 628,  "sigma_ost": -1560, "sigma_t": -2156, "sigma_sum": -3088},
    },
    "Р6М5К5": {
        "TiN":      {"sigma1": 1427, "sigma_ost": -1501, "sigma_t": 468, "sigma_sum": 394},
        "TiAlN":    {"sigma1": 1625, "sigma_ost": -2443, "sigma_t": 483, "sigma_sum": -335},
        "TiAlSiN":  {"sigma1": 1743, "sigma_ost": -2894, "sigma_t": 569, "sigma_sum": -582},
        "TiZrN":    {"sigma1": 1607, "sigma_ost": -2619, "sigma_t": 484, "sigma_sum": -528},
        "TiZrCrN":  {"sigma1": 1617, "sigma_ost": -2865, "sigma_t": 542, "sigma_sum": -706},
        "TiSiN":    {"sigma1": 1518, "sigma_ost": -2541, "sigma_t": 480, "sigma_sum": -543},
        "TiSiAlN":  {"sigma1": 1624, "sigma_ost": -2963, "sigma_t": 540, "sigma_sum": -799},
    }
}

# --- Lab 7 coating factors ---
LAB7_COATING_FACTORS = {
    "TiN":     {"wear": 1.00, "temp": 1.00, "strength": 1.00},
    "TiAlN":   {"wear": 0.92, "temp": 0.88, "strength": 1.08},
    "TiZrN":   {"wear": 0.89, "temp": 0.91, "strength": 1.10},
    "TiSiN":   {"wear": 0.85, "temp": 0.86, "strength": 1.12},
    "TiAlSiN": {"wear": 0.80, "temp": 0.82, "strength": 1.18},
    "TiZrCrN": {"wear": 0.78, "temp": 0.79, "strength": 1.22},
}

def _build_lab7_graph_data(coating: str, feed: float, tool_life: float) -> dict:
    # speed values from 160 to 220 step 5
    speed_values = list(range(160, 221, 5))
    factors = LAB7_COATING_FACTORS.get(coating, {"wear": 1.0, "temp": 1.0, "strength": 1.0})
    k_values = []
    i_values = []
    r_values = []
    tcoef_values = []

    for V in speed_values:
        S = feed
        T = tool_life
        I = (V * S * factors["wear"]) / T if T != 0 else 0
        K = (factors["strength"] * T) / (V * S) if (V * S) != 0 else 0
        R = (T * factors["strength"]) / factors["wear"] if factors["wear"] != 0 else 0
        Tcoef = (V * factors["temp"]) / 100

        k_values.append(round(K, 6))
        i_values.append(round(I, 6))
        r_values.append(round(R, 6))
        tcoef_values.append(round(Tcoef, 6))

    return {
        'speed_values': speed_values,
        'k_values': k_values,
        'i_values': i_values,
        'r_values': r_values,
        'tcoef_values': tcoef_values,
    }

def _build_lab6_mode1_graph_data(coating: str, tool_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count <= 1:
        c_values = [min_c]
    else:
        step = (max_c - min_c) / (points_count - 1)
        c_values = [round(min_c + i * step, 4) for i in range(points_count)]

    def safe_coeffs(store, coating, tool, element):
        try:
            return store[coating][tool][element]
        except Exception:
            return [0, 0, 0, 0]

    qn_coeffs = safe_coeffs(LAB6_QN_COEFFS, coating, tool_material, alloying_element)
    qf_coeffs = safe_coeffs(LAB6_QF_COEFFS, coating, tool_material, alloying_element)
    sigma_n_coeffs = safe_coeffs(LAB6_SIGMA_N_COEFFS, coating, tool_material, alloying_element)
    tau_f_coeffs = safe_coeffs(LAB6_TAU_F_COEFFS, coating, tool_material, alloying_element)
    sigma_max_coeffs = safe_coeffs(LAB6_SIGMA_MAX_COEFFS, coating, tool_material, alloying_element)

    qn_values = [_cubic_model(c, qn_coeffs) for c in c_values]
    qf_values = [_cubic_model(c, qf_coeffs) for c in c_values]
    sigma_n_values = [_cubic_model(c, sigma_n_coeffs) for c in c_values]
    tau_f_values = [_cubic_model(c, tau_f_coeffs) for c in c_values]
    sigma_max_values = [_cubic_model(c, sigma_max_coeffs) for c in c_values]

    return {
        'mode': 'mode1',
        'c_values': c_values,
        'qn_values': qn_values,
        'qf_values': qf_values,
        'sigma_n_values': sigma_n_values,
        'tau_f_values': tau_f_values,
        'sigma_max_values': sigma_max_values,
    }


def _build_lab5_mode1_graph_data(coating: str, tool_material: str, alloying_element: str, content_range: tuple, points_count: int = 41) -> dict:
    min_c, max_c = content_range
    if points_count < 2:
        points_count = 2

    step = (max_c - min_c) / (points_count - 1)
    c_values = [min_c + i * step for i in range(points_count)]

    qp_coeffs = LAB5_MODE1_COEFFS["qp"][coating][tool_material][alloying_element]
    qz_coeffs = LAB5_MODE1_COEFFS["qz_power"][coating][tool_material][alloying_element]
    qpi_coeffs = LAB5_MODE1_COEFFS["qpi"][coating][tool_material][alloying_element]
    qzi_coeffs = LAB5_MODE1_COEFFS["qzi"][coating][tool_material][alloying_element]
    tp_avg_coeffs = LAB5_MODE1_COEFFS["tp_avg"][coating][tool_material][alloying_element]
    tz_avg_coeffs = LAB5_MODE1_COEFFS["tz_avg"][coating][tool_material][alloying_element]

    return {
        'mode': 'mode1',
        'c_values': [round(value, 4) for value in c_values],
        'qp_values': [round(_cubic_model(value, qp_coeffs), 8) for value in c_values],
        'qz_values': [round(_cubic_model(value, qz_coeffs), 8) for value in c_values],
        'qpi_values': [round(_cubic_model(value, qpi_coeffs), 8) for value in c_values],
        'qzi_values': [round(_cubic_model(value, qzi_coeffs), 8) for value in c_values],
        'tp_avg_values': [round(_cubic_model(value, tp_avg_coeffs), 8) for value in c_values],
        'tz_avg_values': [round(_cubic_model(value, tz_avg_coeffs), 8) for value in c_values],
    }


def _build_lab5_mode2_chart_data(operation_type: str) -> dict:
    coatings = list(LAB5_THERMAL_STATE_RESULTS[operation_type].keys())
    return {
        'mode': 'mode2',
        'operation_type': operation_type,
        'coatings': coatings,
        'qp_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['Qп'] for item in coatings],
        'qz_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['Qз'] for item in coatings],
        'qpi_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['qп'] for item in coatings],
        'qzi_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['qз'] for item in coatings],
        'tp_avg_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['Тп.ср.'] for item in coatings],
        'tz_avg_values': [LAB5_THERMAL_STATE_RESULTS[operation_type][item]['Тз.ср.'] for item in coatings],
    }


def _build_lab5_mode3_chart_data(operation_type: str) -> dict:
    coatings = list(LAB5_HEAT_BALANCE_RESULTS[operation_type].keys())
    return {
        'mode': 'mode3',
        'operation_type': operation_type,
        'coatings': coatings,
        'chip_values': [LAB5_HEAT_BALANCE_RESULTS[operation_type][item]['стружка'] for item in coatings],
        'tool_values': [LAB5_HEAT_BALANCE_RESULTS[operation_type][item]['инструмент'] for item in coatings],
        'workpiece_values': [LAB5_HEAT_BALANCE_RESULTS[operation_type][item]['заготовка'] for item in coatings],
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
        'algorithm': [
            'выбирается режим исследования: влияние содержания легирующего элемента или влияние состава покрытия',
            'для режима влияния содержания выбираются: износостойкое покрытие (TiAlMe2N, TiZrMe2N, TiSiMe2N), инструментальный материал (МК8, Р6М5К5), легирующий элемент и его содержание C, % в допустимом диапазоне',
            'для режима влияния состава выбирается покрытие: TiN, TiZrN, TiZrAlN, TiSiN, TiSiZrN',
            'определяются механические характеристики: микротвердость Hµ, модуль упругости E, трещиностойкость KICП, коэффициент отслоения K0',
            'строятся графики Hµ(C), E(C), KICП(C), K0(C) или диаграммы по всем покрытиям для выбранного режима',
        ],
        'form_fields': [
            {
                'name': 'research_mode',
                'label': 'режим исследования',
                'type': 'select',
                'options': [
                    'Влияние содержания легирующего элемента',
                    'Влияние состава покрытия',
                ],
            },
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
                'label': 'содержание легирующего элемента, %',
                'type': 'text',
                'placeholder': 'Введите значение, %',
            },
            {
                'name': 'composition_coating',
                'label': 'покрытие',
                'type': 'select',
                'options': ['TiN', 'TiZrN', 'TiZrAlN', 'TiSiN', 'TiSiZrN'],
            },
        ],
        'research_modes': {
            'mode1': 'Влияние содержания легирующего элемента',
            'mode2': 'Влияние состава покрытия',
        },
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
        'result_fields': [
            'микротвердость Hµ, ГПа',
            'модуль упругости E, ГПа',
            'трещиностойкость KICП, МПа·м^1/2',
            'коэффициент отслоения K0',
        ],
    },
    {
        'id': 3,
        'title': 'Исследование циклической трещиностойкости и интенсивности изнашивания режущего инструмента',
        'algorithm': [
            'выбирается покрытие: TiAlMe2N, TiZrMe2N, TiSiMe2N',
            'выбирается инструментальный материал: МК8 или Р6М5К5',
            'выбирается обрабатываемый материал: 30ХГСА или 12Х18Н10Т',
            'выбирается легирующий элемент и его содержание C в допустимом диапазоне',
            'определяются: циклическая трещиностойкость tц (мин) и интенсивность изнашивания J·10^4 (мм/м)',
            'строятся графики tц(C) и J(C) по допустимому диапазону',
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
                'name': 'processed_material',
                'label': 'обрабатываемый материал',
                'type': 'select',
                'options': ['30ХГСА', '12Х18Н10Т'],
            },
            {
                'name': 'alloying_element',
                'label': 'легирующий элемент',
                'type': 'select',
                'options': ['Fe', 'Cr', 'Zr', 'Al'],
            },
            {
                'name': 'alloying_content',
                'label': 'содержание легирующего элемента, %',
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
        'result_fields': ['tц, мин', 'J·10^4, мм/м'],
    },
    {
        'id': 4,
        'title': 'Исследование контактных характеристик процесса резания',
        'algorithm': [
            'выбирается режим исследования: влияние содержания легирующего элемента в покрытии или влияние состава покрытия',
            'для режима влияния содержания выбираются покрытие, инструментальный материал, обрабатываемый материал, легирующий элемент и его содержание C, % в допустимом диапазоне',
            'для режима влияния состава выбирается покрытие из таблицы 6',
            'определяются контактные характеристики процесса резания',
            'строятся 5 графиков зависимости от содержания легирующего элемента или диаграммы сравнения по покрытиям',
        ],
        'form_fields': [
            {
                'name': 'research_mode',
                'label': 'режим исследования',
                'type': 'select',
                'options': [
                    'Влияние содержания легирующего элемента',
                    'Влияние состава покрытия',
                ],
            },
            {
                'name': 'coating',
                'label': 'износостойкое покрытие',
                'type': 'select',
                'options': ['TiAlMe2N', 'TiZrMe2N', 'TiSiMe2N', 'без покрытия', 'TiN', 'TiZrN', 'TiZrAlN', 'TiSiN', 'TiSiZrN'],
            },
            {
                'name': 'tool_material',
                'label': 'инструментальный материал',
                'type': 'select',
                'options': ['МК8', 'Р6М5К5'],
            },
            {
                'name': 'processed_material',
                'label': 'обрабатываемый материал',
                'type': 'select',
                'options': ['30ХГСА', '12Х18Н10Т'],
            },
            {
                'name': 'alloying_element',
                'label': 'легирующий элемент',
                'type': 'select',
                'options': ['Fe', 'Cr', 'Zr', 'Al'],
            },
            {
                'name': 'alloying_content',
                'label': 'содержание легирующего элемента, %',
                'type': 'text',
                'placeholder': 'Введите значение, %',
            },
        ],
        'research_modes': {
            'mode1': 'Влияние содержания легирующего элемента',
            'mode2': 'Влияние состава покрытия',
        },
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
        'result_fields': {
            'mode1': ['Cγ, мм', 'KL', 'Px, Н', 'Py, Н', 'Pz, Н'],
            'mode2': ['Cγ', 'KL', 'Pz, Н', 'Nγ, Н', 'Fγ, Н', 'qN, МПа', 'qF, МПа', 'σN, МПа', 'τF, МПа'],
        },
    },
    {
        'id': 5,
        'title': 'Исследование теплового состояния режущего клина инструмента',
        'algorithm': [
            'выбирается режим исследования: влияние содержания легирующего элемента, влияние состава покрытия на показатели теплового состояния или влияние состава покрытия на тепловой баланс',
            'для режима влияния содержания выбираются покрытие, инструментальный материал, обрабатываемый материал, легирующий элемент и его содержание C',
            'для режима влияния состава покрытия выбирается тип операции и покрытие',
            'определяются тепловые характеристики согласно таблицам ТЗ',
            'строятся линейные графики или столбчатые диаграммы в зависимости от режима',
        ],
        'form_fields': [
            {
                'name': 'research_mode',
                'label': 'режим исследования',
                'type': 'select',
                'options': [
                    'Влияние содержания легирующего элемента',
                    'Влияние состава покрытия на показатели теплового состояния',
                    'Влияние состава покрытия на тепловой баланс',
                ],
            },
            {
                'name': 'coating',
                'label': 'износостойкое покрытие',
                'type': 'select',
                'options': ['TiAlMe2N', 'TiZrMe2N', 'TiSiMe2N', 'Без покрытия', 'TiN', 'TiAlN', 'TiAlCrN', 'TiCrN', 'TiCrZrN', 'TiZrN', 'TiZrCN'],
            },
            {
                'name': 'tool_material',
                'label': 'инструментальный материал',
                'type': 'select',
                'options': ['МК8', 'Р6М5К5'],
            },
            {
                'name': 'processed_material',
                'label': 'обрабатываемый материал',
                'type': 'select',
                'options': ['30ХГСА', '12Х18Н10Т'],
            },
            {
                'name': 'alloying_element',
                'label': 'легирующий элемент',
                'type': 'select',
                'options': ['Fe', 'Cr', 'Zr', 'Al'],
            },
            {
                'name': 'alloying_content',
                'label': 'содержание легирующего элемента, %',
                'type': 'text',
                'placeholder': 'Введите значение, %',
            },
            {
                'name': 'operation_type',
                'label': 'тип операции',
                'type': 'select',
                'options': ['Отрезка', 'Нарезание резьбы'],
            },
            {
                'name': 'composition_coating',
                'label': 'покрытие',
                'type': 'select',
                'options': ['Без покрытия', 'TiN', 'TiAlN', 'TiAlCrN', 'TiCrN', 'TiCrZrN'],
            },
            {
                'name': 'balance_operation_type',
                'label': 'тип операции',
                'type': 'select',
                'options': ['Нарезание резьбы', 'Торцовое фрезерование'],
            },
            {
                'name': 'balance_coating',
                'label': 'покрытие',
                'type': 'select',
                'options': ['Без покрытия', 'TiN', 'TiCrN', 'TiCrZrN', 'TiZrN', 'TiZrCN'],
            },
        ],
        'research_modes': {
            'mode1': 'Влияние содержания легирующего элемента',
            'mode2': 'Влияние состава покрытия на показатели теплового состояния',
            'mode3': 'Влияние состава покрытия на тепловой баланс',
        },
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
        'operation_type_coatings': {
            'Отрезка': ['Без покрытия', 'TiN', 'TiAlN', 'TiAlCrN'],
            'Нарезание резьбы': ['Без покрытия', 'TiN', 'TiCrN', 'TiCrZrN'],
        },
        'balance_operation_type_coatings': {
            'Нарезание резьбы': ['Без покрытия', 'TiN', 'TiCrN', 'TiCrZrN'],
            'Торцовое фрезерование': ['Без покрытия', 'TiN', 'TiZrN', 'TiZrCN'],
        },
        'result_fields': {
            'mode1': [],
            'mode2': ['Qп', 'Qз', 'qп', 'qз', 'Тп.ср.', 'Тз.ср.'],
            'mode3': ['стружка', 'инструмент', 'заготовка'],
        },
    },
    {
        'id': 6,
        'title': 'Исследование напряженного состояния режущего клина инструмента',
        'algorithm': [
            'выбирается режим исследования: влияние содержания легирующего элемента или влияние состава покрытия',
            'для режима влияния содержания выбираются: покрытие (TiAlMe2N, TiZrMe2N, TiSiMe2N), инструментальный материал (МК8, Р6М5К5), обрабатываемый материал (30ХГСА), легирующий элемент и его содержание C',
            'определяются qN, qF, σN, τF, σmax по регрессионным моделям из ТЗ',
            'строятся линейные графики зависимостей параметров от содержания легирующего элемента или столбчатые диаграммы по составам покрытий',
        ],
        'form_fields': [
            {
                'name': 'research_mode',
                'label': 'режим исследования',
                'type': 'select',
                'options': [
                    'Влияние содержания легирующего элемента',
                    'Влияние состава покрытия',
                ],
            },
            {
                'name': 'coating',
                'label': 'износостойкое покрытие',
                'type': 'select',
                'options': ['TiAlMe2N', 'TiZrMe2N', 'TiSiMe2N', 'TiN', 'TiAlN', 'TiAlSiN', 'TiZrN', 'TiZrCrN', 'TiSiN', 'TiSiAlN'],
            },
            {
                'name': 'tool_material',
                'label': 'инструментальный материал',
                'type': 'select',
                'options': ['МК8', 'Р6М5К5'],
            },
            {
                'name': 'processed_material',
                'label': 'обрабатываемый материал',
                'type': 'select',
                'options': ['30ХГСА'],
            },
            {
                'name': 'alloying_element',
                'label': 'легирующий элемент',
                'type': 'select',
                'options': ['Fe', 'Cr', 'Zr', 'Al'],
            },
            {
                'name': 'alloying_content',
                'label': 'содержание легирующего элемента, %',
                'type': 'text',
                'placeholder': 'Введите значение, %',
            },
            {
                'name': 'stress_coating',
                'label': 'покрытие',
                'type': 'select',
                'options': ['TiN', 'TiAlN', 'TiAlSiN', 'TiZrN', 'TiZrCrN', 'TiSiN', 'TiSiAlN'],
            },
        ],
        'research_modes': {
            'mode1': 'Влияние содержания легирующего элемента',
            'mode2': 'Влияние состава покрытия',
        },
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
        'result_fields': {
            'mode1': ['qN', 'qF', 'sigmaN', 'tauF', 'sigmaMax'],
            'mode2': ['sigma1', 'sigma_ost', 'sigma_t', 'sigma_sum'],
        },
    },
    {
        'id': 7,
        'title': 'Работоспособность режущего инструмента',
        'algorithm': [
            'выбирается покрытие',
            'выбирается инструментальный материал',
            'выбирается обрабатываемый материал (30ХГСА)',
            'задаются скорость резания V (м/мин), подача S (мм/об), период стойкости T (мин)',
            'рассчитываются I, K, R, Tcoef по формулам и строятся графики зависимостей от V'
        ],
        'form_fields': [
            {
                'name': 'coating',
                'label': 'покрытие',
                'type': 'select',
                'options': ['TiN', 'TiAlN', 'TiZrN', 'TiSiN', 'TiAlSiN', 'TiZrCrN'],
            },
            {
                'name': 'tool_material',
                'label': 'инструментальный материал',
                'type': 'select',
                'options': ['МК8', 'Р6М5К5'],
            },
            {
                'name': 'processed_material',
                'label': 'обрабатываемый материал',
                'type': 'select',
                'options': ['30ХГСА'],
            },
            {
                'name': 'cutting_speed',
                'label': 'скорость резания V, м/мин',
                'type': 'text',
                'placeholder': '160-220',
            },
            {
                'name': 'feed',
                'label': 'подача S, мм/об',
                'type': 'text',
                'placeholder': '0.1-0.3',
            },
            {
                'name': 'tool_life',
                'label': 'период стойкости T, мин',
                'type': 'text',
                'placeholder': '10-90',
            },
        ],
        'notes': [
            'Диапазон скоростей V: 160–220 м/мин',
            'Подача S: 0.1–0.3 мм/об',
            'Период стойкости T: 10–90 мин',
        ],
        'result_fields': ['K', 'I', 'R', 'Tcoef'],
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

    form_values = {field.get('name'): '' for field in lab.get('form_fields', [])}
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

    if request.method == 'GET' and lab_id == 2:
        mode_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'research_mode'), [])
        coating_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'coating'), [])
        tool_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'tool_material'), [])
        composition_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'composition_coating'), [])

        if mode_options:
            form_values['research_mode'] = mode_options[0]
        if coating_options:
            form_values['coating'] = coating_options[0]
        if tool_options:
            form_values['tool_material'] = tool_options[0]
        if composition_options:
            form_values['composition_coating'] = composition_options[0]

        allowed_elements = lab.get('alloying_by_coating', {}).get(form_values['coating'], [])
        if allowed_elements:
            form_values['alloying_element'] = allowed_elements[0]

    if request.method == 'GET' and lab_id == 3:
        coating_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'coating'), [])
        tool_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'tool_material'), [])
        proc_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'processed_material'), [])

        if coating_options:
            form_values['coating'] = coating_options[0]
        if tool_options:
            form_values['tool_material'] = tool_options[0]
        if proc_options:
            form_values['processed_material'] = proc_options[0]

        allowed_elements = lab.get('alloying_by_coating', {}).get(form_values['coating'], [])
        if allowed_elements:
            form_values['alloying_element'] = allowed_elements[0]

    if request.method == 'GET' and lab_id == 4:
        mode_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'research_mode'), [])
        coating_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'coating'), [])
        tool_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'tool_material'), [])
        proc_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'processed_material'), [])

        if mode_options:
            form_values['research_mode'] = mode_options[0]
        if coating_options:
            form_values['coating'] = coating_options[0]
        if tool_options:
            form_values['tool_material'] = tool_options[0]
        if proc_options:
            form_values['processed_material'] = proc_options[0]

        allowed_elements = lab.get('alloying_by_coating', {}).get(form_values['coating'], [])
        if allowed_elements:
            form_values['alloying_element'] = allowed_elements[0]

    if request.method == 'GET' and lab_id == 5:
        mode_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'research_mode'), [])
        coating_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'coating'), [])
        tool_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'tool_material'), [])
        proc_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'processed_material'), [])
        op_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'operation_type'), [])
        comp_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'composition_coating'), [])
        balance_op_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'balance_operation_type'), [])
        balance_comp_options = next((f['options'] for f in lab.get('form_fields', []) if f.get('name') == 'balance_coating'), [])

        if mode_options:
            form_values['research_mode'] = mode_options[0]
        if coating_options:
            form_values['coating'] = coating_options[0]
        if tool_options:
            form_values['tool_material'] = tool_options[0]
        if proc_options:
            form_values['processed_material'] = proc_options[0]
        if op_options:
            form_values['operation_type'] = op_options[0]
        if balance_op_options:
            form_values['balance_operation_type'] = balance_op_options[0]

        allowed_elements = lab.get('alloying_by_coating', {}).get(form_values['coating'], [])
        if allowed_elements:
            form_values['alloying_element'] = allowed_elements[0]

        operation_coatings = lab.get('operation_type_coatings', {}).get(form_values.get('operation_type', ''), [])
        if operation_coatings and comp_options:
            form_values['composition_coating'] = operation_coatings[0]

        balance_operation_coatings = lab.get('balance_operation_type_coatings', {}).get(form_values.get('balance_operation_type', ''), [])
        if balance_operation_coatings and balance_comp_options:
            form_values['balance_coating'] = balance_operation_coatings[0]

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

    if request.method == 'POST' and lab_id == 2:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        mode1_name = lab.get('research_modes', {}).get('mode1')
        mode2_name = lab.get('research_modes', {}).get('mode2')
        selected_mode = form_values.get('research_mode', '')

        if selected_mode not in (mode1_name, mode2_name):
            error_message = 'Выберите корректный режим исследования.'

        if error_message is None and selected_mode == mode1_name:
            coating = form_values.get('coating', '')
            tool_material = form_values.get('tool_material', '')
            alloying_element = form_values.get('alloying_element', '')
            content_raw = form_values.get('alloying_content', '')

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
                    hmu_value = _cubic_model(content_value, LAB2_HMU_COEFFS[coating][alloying_element])
                    e_value = _cubic_model(content_value, LAB2_E_COEFFS[coating][alloying_element])
                    kicp_value = _cubic_model(content_value, LAB2_KICP_COEFFS[coating][alloying_element])
                    k0_value = _cubic_model(content_value, LAB2_K0_COEFFS[coating][tool_material][alloying_element])

                    calculated_results = {
                        'микротвердость Hµ, ГПа': f'{hmu_value:.3f}',
                        'модуль упругости E, ГПа': f'{e_value:.3f}',
                        'трещиностойкость KICП, МПа·м^1/2': f'{kicp_value:.3f}',
                        'коэффициент отслоения K0': f'{k0_value:.3f}',
                    }

                    graph_data = _build_lab2_mode1_graph_data(
                        coating=coating,
                        tool_material=tool_material,
                        alloying_element=alloying_element,
                        content_range=lab['content_ranges'][coating][alloying_element],
                    )
                except KeyError:
                    error_message = 'Для выбранной комбинации отсутствуют коэффициенты расчета.'

    if request.method == 'POST' and lab_id == 3:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        coating = form_values.get('coating', '')
        tool_material = form_values.get('tool_material', '')
        processed_material = form_values.get('processed_material', '')
        alloying_element = form_values.get('alloying_element', '')
        content_raw = form_values.get('alloying_content', '')

        if not coating:
            error_message = 'Выберите износостойкое покрытие.'
        elif not tool_material:
            error_message = 'Выберите инструментальный материал.'
        elif not processed_material:
            error_message = 'Выберите обрабатываемый материал.'
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
                tc_coeffs = LAB3_TC_COEFFS[coating][tool_material][alloying_element]
                tc_value = _cubic_model(content_value, tc_coeffs)

                proc_key = '30XGSA' if processed_material == '30ХГСА' else '12X18N10T'
                j_coeffs = LAB3_J_COEFFS[proc_key][coating][tool_material][alloying_element]
                j_value = _cubic_model(content_value, j_coeffs)

                calculated_results = {
                    'tц, мин': f'{tc_value:.3f}',
                    'J·10^4, мм/м': f'{j_value:.3f}',
                }

                graph_data = _build_lab3_graph_data(
                    coating=coating,
                    tool_material=tool_material,
                    processed_material=processed_material,
                    alloying_element=alloying_element,
                    content_range=lab['content_ranges'][coating][alloying_element],
                )
            except KeyError:
                error_message = 'Для выбранной комбинации отсутствуют коэффициенты расчета.'

    if request.method == 'POST' and lab_id == 4:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        mode1_name = lab.get('research_modes', {}).get('mode1')
        mode2_name = lab.get('research_modes', {}).get('mode2')
        selected_mode = form_values.get('research_mode', '')

        if selected_mode not in (mode1_name, mode2_name):
            error_message = 'Выберите корректный режим исследования.'

        if error_message is None and selected_mode == mode1_name:
            coating = form_values.get('coating', '')
            tool_material = form_values.get('tool_material', '')
            processed_material = form_values.get('processed_material', '')
            alloying_element = form_values.get('alloying_element', '')
            content_raw = form_values.get('alloying_content', '')

            if not coating:
                error_message = 'Выберите износостойкое покрытие.'
            elif not tool_material:
                error_message = 'Выберите инструментальный материал.'
            elif not processed_material:
                error_message = 'Выберите обрабатываемый материал.'
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
                    cgamma_value = _cubic_model(content_value, LAB4_CGAMMA_COEFFS[coating][tool_material][alloying_element])
                    kl_value = _cubic_model(content_value, LAB4_KL_COEFFS[coating][tool_material][alloying_element])
                    px_value = _cubic_model(content_value, LAB4_PX_COEFFS[coating][tool_material][alloying_element])
                    py_value = _cubic_model(content_value, LAB4_PY_COEFFS[coating][tool_material][alloying_element])
                    pz_value = _cubic_model(content_value, LAB4_PZ_COEFFS[coating][tool_material][alloying_element])

                    calculated_results = {
                        '_mode': 'mode1',
                        'Cγ, мм': f'{cgamma_value:.3f}',
                        'KL': f'{kl_value:.3f}',
                        'Px, Н': f'{px_value:.3f}',
                        'Py, Н': f'{py_value:.3f}',
                        'Pz, Н': f'{pz_value:.3f}',
                    }

                    graph_data = _build_lab4_mode1_graph_data(
                        coating=coating,
                        tool_material=tool_material,
                        alloying_element=alloying_element,
                        content_range=lab['content_ranges'][coating][alloying_element],
                    )
                except KeyError:
                    error_message = 'Для выбранной комбинации отсутствуют коэффициенты расчета.'

        if error_message is None and selected_mode == mode2_name:
            coating = form_values.get('coating', '')

            if not coating:
                error_message = 'Выберите покрытие.'
            else:
                composition = LAB4_COMPOSITION_RESULTS.get(coating)
                if composition is None:
                    error_message = 'Для выбранного покрытия отсутствуют данные таблицы 6.'

            if error_message is None:
                calculated_results = {
                    '_mode': 'mode2',
                    'Cγ': f'{composition["cgamma"]:g}',
                    'KL': f'{composition["kl"]:g}',
                    'Pz, Н': f'{composition["pz"]:g}',
                    'Nγ, Н': f'{composition["ngamma"]:g}',
                    'Fγ, Н': f'{composition["fgamma"]:g}',
                    'qN, МПа': f'{composition["qn"]:g}',
                    'qF, МПа': f'{composition["qf"]:g}',
                    'σN, МПа': f'{composition["sigma_n"]:g}',
                    'τF, МПа': f'{composition["tau_f"]:g}',
                }

                graph_data = _build_lab4_mode2_chart_data()

    if request.method == 'POST' and lab_id == 5:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        mode1_name = lab.get('research_modes', {}).get('mode1')
        mode2_name = lab.get('research_modes', {}).get('mode2')
        mode3_name = lab.get('research_modes', {}).get('mode3')
        selected_mode = form_values.get('research_mode', '')

        if selected_mode not in (mode1_name, mode2_name, mode3_name):
            error_message = 'Выберите корректный режим исследования.'

        if error_message is None and selected_mode == mode1_name:
            coating = form_values.get('coating', '')
            tool_material = form_values.get('tool_material', '')
            alloying_element = form_values.get('alloying_element', '')
            content_raw = form_values.get('alloying_content', '')

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
                    qp_coeffs = LAB5_MODE1_COEFFS["qp"][coating][tool_material][alloying_element]
                    qz_coeffs = LAB5_MODE1_COEFFS["qz_power"][coating][tool_material][alloying_element]
                    qpi_coeffs = LAB5_MODE1_COEFFS["qpi"][coating][tool_material][alloying_element]
                    qzi_coeffs = LAB5_MODE1_COEFFS["qzi"][coating][tool_material][alloying_element]
                    tp_avg_coeffs = LAB5_MODE1_COEFFS["tp_avg"][coating][tool_material][alloying_element]
                    tz_avg_coeffs = LAB5_MODE1_COEFFS["tz_avg"][coating][tool_material][alloying_element]

                    qp_value = _cubic_model(content_value, qp_coeffs)
                    qz_value = _cubic_model(content_value, qz_coeffs)
                    qpi_value = _cubic_model(content_value, qpi_coeffs)
                    qzi_value = _cubic_model(content_value, qzi_coeffs)
                    tp_avg_value = _cubic_model(content_value, tp_avg_coeffs)
                    tz_avg_value = _cubic_model(content_value, tz_avg_coeffs)

                    calculated_results = {
                        '_mode': 'mode1',
                        'Qп': f'{qp_value:.3f}',
                        'Qз': f'{qz_value:.3f}',
                        'qп': f'{qpi_value:.3f}',
                        'qз': f'{qzi_value:.3f}',
                        'Тп.ср.': f'{tp_avg_value:.3f}',
                        'Тз.ср.': f'{tz_avg_value:.3f}',
                    }

                    graph_data = _build_lab5_mode1_graph_data(
                        coating=coating,
                        tool_material=tool_material,
                        alloying_element=alloying_element,
                        content_range=lab['content_ranges'][coating][alloying_element],
                    )
                except KeyError:
                    error_message = 'Для выбранной комбинации нет полного набора коэффициентов в ТЗ'

        if error_message is None and selected_mode == mode2_name:
            operation_type = form_values.get('operation_type', '')
            coating = form_values.get('composition_coating', '')

            if not operation_type:
                error_message = 'Выберите тип операции.'
            elif not coating:
                error_message = 'Выберите покрытие.'
            else:
                allowed_coatings = lab.get('operation_type_coatings', {}).get(operation_type, [])
                if coating not in allowed_coatings:
                    error_message = 'Выбранное покрытие недоступно для указанного типа операции.'

            if error_message is None:
                operation_results = LAB5_THERMAL_STATE_RESULTS.get(operation_type, {})
                coating_results = operation_results.get(coating)

                if coating_results is None:
                    error_message = 'Для выбранной комбинации отсутствуют данные таблицы 7.'
                else:
                    calculated_results = {
                        '_mode': 'mode2',
                        'Qп': f'{coating_results["Qп"]:g}',
                        'Qз': f'{coating_results["Qз"]:g}',
                        'qп': f'{coating_results["qп"]:g}',
                        'qз': f'{coating_results["qз"]:g}',
                        'Тп.ср.': f'{coating_results["Тп.ср."]:g}',
                        'Тз.ср.': f'{coating_results["Тз.ср."]:g}',
                    }

                    graph_data = _build_lab5_mode2_chart_data(operation_type)

        if error_message is None and selected_mode == mode3_name:
            operation_type = form_values.get('balance_operation_type', '')
            coating = form_values.get('balance_coating', '')

            if not operation_type:
                error_message = 'Выберите тип операции.'
            elif not coating:
                error_message = 'Выберите покрытие.'
            else:
                allowed_coatings = lab.get('balance_operation_type_coatings', {}).get(operation_type, [])
                if coating not in allowed_coatings:
                    error_message = 'Выбранное покрытие недоступно для указанного типа операции.'

            if error_message is None:
                operation_results = LAB5_HEAT_BALANCE_RESULTS.get(operation_type, {})
                coating_results = operation_results.get(coating)

                if coating_results is None:
                    error_message = 'Для выбранной комбинации отсутствуют данные таблицы 8.'
                else:
                    calculated_results = {
                        '_mode': 'mode3',
                        'стружка': f'{coating_results["стружка"]:g}',
                        'инструмент': f'{coating_results["инструмент"]:g}',
                        'заготовка': f'{coating_results["заготовка"]:g}',
                    }

                    graph_data = _build_lab5_mode3_chart_data(operation_type)

    

    # POST handler for lab 6
    if request.method == 'POST' and lab_id == 6:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        mode1_name = lab.get('research_modes', {}).get('mode1')
        mode2_name = lab.get('research_modes', {}).get('mode2')
        selected_mode = form_values.get('research_mode', '')

        if selected_mode not in (mode1_name, mode2_name):
            error_message = 'Выберите корректный режим исследования.'

        # Mode 1: влияние содержания легирующего элемента
        if error_message is None and selected_mode == mode1_name:
            coating = form_values.get('coating', '')
            tool_material = form_values.get('tool_material', '')
            processed = form_values.get('processed_material', '')
            alloying_element = form_values.get('alloying_element', '')
            content_raw = form_values.get('alloying_content', '')

            if not coating or coating not in ('TiAlMe2N', 'TiZrMe2N', 'TiSiMe2N'):
                error_message = 'Выберите корректное износостойкое покрытие.'
            elif not tool_material:
                error_message = 'Выберите инструментальный материал.'
            elif processed != '30ХГСА':
                error_message = 'Выберите обрабатываемый материал 30ХГСА.'
            elif not alloying_element:
                error_message = 'Выберите легирующий элемент.'

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
                        error_message = f'Содержание легирующего элемента должно быть в диапазоне {min_value:.2f}-{max_value:.2f} %.'

            if error_message is None:
                # retrieve coefficients safely (missing -> zeros)
                def sc(store, coating, tool, elem):
                    try:
                        return store[coating][tool][elem]
                    except Exception:
                        return [0, 0, 0, 0]

                qn_c = sc(LAB6_QN_COEFFS, coating, tool_material, alloying_element)
                qf_c = sc(LAB6_QF_COEFFS, coating, tool_material, alloying_element)
                sigma_n_c = sc(LAB6_SIGMA_N_COEFFS, coating, tool_material, alloying_element)
                tau_f_c = sc(LAB6_TAU_F_COEFFS, coating, tool_material, alloying_element)
                sigma_max_c = sc(LAB6_SIGMA_MAX_COEFFS, coating, tool_material, alloying_element)

                qn_value = _cubic_model(content_value, qn_c)
                qf_value = _cubic_model(content_value, qf_c)
                sigma_n_value = _cubic_model(content_value, sigma_n_c)
                tau_f_value = _cubic_model(content_value, tau_f_c)
                sigma_max_value = _cubic_model(content_value, sigma_max_c)

                calculated_results = {
                    '_mode': 'mode1',
                    'qN': f'{qn_value:.3f}',
                    'qF': f'{qf_value:.3f}',
                    'sigmaN': f'{sigma_n_value:.3f}',
                    'tauF': f'{tau_f_value:.3f}',
                    'sigmaMax': f'{sigma_max_value:.3f}',
                }

                graph_data = _build_lab6_mode1_graph_data(
                    coating=coating,
                    tool_material=tool_material,
                    alloying_element=alloying_element,
                    content_range=lab['content_ranges'][coating][alloying_element],
                )

        # Mode 2: влияние состава покрытия (сравнение покрытий для выбранного материала инструмента)
        if error_message is None and selected_mode == mode2_name:
            tool_material = form_values.get('tool_material', '')
            processed = form_values.get('processed_material', '')
            stress_coating = form_values.get('stress_coating', '')

            if processed != '30ХГСА':
                error_message = 'Выберите обрабатываемый материал 30ХГСА.'
            elif not tool_material:
                error_message = 'Выберите инструментальный материал.'
            elif not stress_coating:
                error_message = 'Выберите покрытие для сравнения.'

            if error_message is None:
                comp_data = LAB6_COMPOSITION_DATA.get(tool_material, {})
                if not comp_data:
                    error_message = 'Нет данных по составам для выбранного материала инструмента.'
                else:
                    labels = list(comp_data.keys())
                    sigma1_values = [comp_data[k]['sigma1'] for k in labels]
                    sigma_ost_values = [comp_data[k]['sigma_ost'] for k in labels]
                    sigma_t_values = [comp_data[k]['sigma_t'] for k in labels]
                    sigma_sum_values = [comp_data[k]['sigma_sum'] for k in labels]

                    calculated_results = {
                        '_mode': 'mode2',
                        'sigma1': f'{comp_data.get(stress_coating, {}).get("sigma1", 0):g}',
                        'sigma_ost': f'{comp_data.get(stress_coating, {}).get("sigma_ost", 0):g}',
                        'sigma_t': f'{comp_data.get(stress_coating, {}).get("sigma_t", 0):g}',
                        'sigma_sum': f'{comp_data.get(stress_coating, {}).get("sigma_sum", 0):g}',
                    }

                    graph_data = {
                        'mode': 'mode2',
                        'labels': labels,
                        'sigma1_values': sigma1_values,
                        'sigma_ost_values': sigma_ost_values,
                        'sigma_t_values': sigma_t_values,
                        'sigma_sum_values': sigma_sum_values,
                    }

    # POST handler for lab 7
    if request.method == 'POST' and lab_id == 7:
        for field in lab.get('form_fields', []):
            name = field.get('name')
            form_values[name] = request.POST.get(name, '').strip()

        coating = form_values.get('coating', '')
        tool_material = form_values.get('tool_material', '')
        processed = form_values.get('processed_material', '')
        cutting_speed_raw = form_values.get('cutting_speed', '')
        feed_raw = form_values.get('feed', '')
        tool_life_raw = form_values.get('tool_life', '')

        # Basic validations
        if not coating or coating not in ('TiN', 'TiAlN', 'TiZrN', 'TiSiN', 'TiAlSiN', 'TiZrCrN'):
            error_message = 'Выберите покрытие.'
        elif not tool_material or tool_material not in ('МК8', 'Р6М5К5'):
            error_message = 'Выберите инструментальный материал.'
        elif processed != '30ХГСА':
            error_message = 'Выберите обрабатываемый материал 30ХГСА.'

        try:
            V = float(cutting_speed_raw.replace(',', '.'))
        except Exception:
            V = None
        try:
            S = float(feed_raw.replace(',', '.'))
        except Exception:
            S = None
        try:
            T = float(tool_life_raw.replace(',', '.'))
        except Exception:
            T = None

        if error_message is None:
            if V is None or not (160 <= V <= 220):
                error_message = 'Скорость резания должна быть в диапазоне 160–220.'
            elif S is None or not (0.1 <= S <= 0.3):
                error_message = 'Подача должна быть в диапазоне 0.1–0.3.'
            elif T is None or not (10 <= T <= 90):
                error_message = 'Период стойкости должен быть в диапазоне 10–90.'

        if error_message is None:
            factors = LAB7_COATING_FACTORS.get(coating, {"wear": 1.0, "temp": 1.0, "strength": 1.0})
            I = (V * S * factors["wear"]) / T if T != 0 else 0
            K = (factors["strength"] * T) / (V * S) if (V * S) != 0 else 0
            R = (T * factors["strength"]) / factors["wear"] if factors["wear"] != 0 else 0
            Tcoef = (V * factors["temp"]) / 100

            calculated_results = {
                '_mode': 'lab7',
                'K': f'{round(K, 3)}',
                'I': f'{round(I, 3)}',
                'R': f'{round(R, 3)}',
                'Tcoef': f'{round(Tcoef, 3)}',
            }

            graph_data = _build_lab7_graph_data(coating=coating, feed=S, tool_life=T)

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

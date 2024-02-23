from pathlib import Path
from docxtpl import DocxTemplate
from typing import Dict, Any, Optional
from jinja2.environment import Environment
from schema import Schema, Or, SchemaError


TEMPLATE_PATH = Path(__file__).parent / "report_templates" / "Template.docx"

"""Требуемый формат данных для построения отчетов"""
CONTEXT_SCHEMA = Schema({
    'variables': [
        {
            "name": str,
            "value": Or(int, float)
        }
    ],
    "formula": str,
    "result": Or(str, int, float)
})


class DocxReport(DocxTemplate):
    """Класс для создания отчетов в формате docx"""
    def __init__(self):
        super().__init__(TEMPLATE_PATH)

    def render(
        self,
        context: Dict[str, Any],
        jinja_env: Optional[Environment] = None,
        autoescape: bool = False
    ) -> None:

        if not CONTEXT_SCHEMA.is_valid(context):
            raise SchemaError("Неправильный формат данных")

        super().render(context, jinja_env, autoescape)

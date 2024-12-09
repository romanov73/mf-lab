import io
from pathlib import Path
from docxtpl import DocxTemplate
from typing import Dict, Any, Optional, List
from jinja2.environment import Environment
from schema import Schema, Or, SchemaError


TEMPLATE_PATH = Path(__file__).parent / "report_templates" / "Template.docx"

CONTEXT_SCHEMA = Schema({
    'variables': [
        {
            "name": str,
            "value": Or(int, float)
        }
    ],
    "formulas": [
        {
            "expression": str,
            "result": Or(str, int, float)
        }
    ],
    "global_tables": dict,
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

    def get_bytes_array(self):
        file_stream = io.BytesIO()
        self.save(file_stream)
        file_stream.seek(0)
        return file_stream

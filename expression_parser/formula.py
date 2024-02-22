import ast
import regex
import numexpr as ne


class Formula:
    def __init__(self, expression: str):
        """
        Формула, которую можно вычислить. Для этого необходимо передать значения всех переменных.

        Поля класса:
            expression (str): текстовое представление формулы после предобработки (в случае ошибки валидации - None)

            variables (dict[float]): словарь, где ключ - переменная, а значение - её значение(изначально - None)

            error_text (str): текст ошибки, если таковая имеется

            error_position (int): позиция ошибки в формуле

        Args:
            expression (str): Текст формулы, которую пытаемся вычислить.
        """
        expression = self._preprocess_formula(expression)
        error_position: int = self._formula_validation(expression)

        if error_position is None:
            self.expression: str = expression
            self.variables: dict[float] = self._extract_all_variable()
            if self.variables is None:
                self.expression = None
        else:
            self.expression = None
            self.variables = {}
            self.error_text = "Ошибка валидации формулы"
            self.error_position = error_position

    def _formula_validation(self, formula: str) -> int | None:
        """
        Проверка текстовой версии формула на синтаксическую корректность. Работает через ast.

        Args:
            formula (str): Текст формулы, которую валидируем

        Returns:
            int: Начальная позиция ошибки. В случае, если валидация успешная - возвращаем None

        """
        try:
            ast.parse(formula)
            return None
        except SyntaxError as se:
            return se.end_offset
        except Exception:
            raise

    def _preprocess_formula(self, formula_str: str) -> str:
        """
        Метод для предобработки текста формулы. Пока тут только перевод стандартного изображения степени(^) в
        варианта python (**)

        Args:
            formula_str (str): текст формулы, который нужно обработать

        Returns:
            str: Текст формулы после обработки
        """
        return formula_str.replace("^", "**")

    def _extract_all_variable(self) -> dict[float] | None:
        """
        Получение списка всех переменных, значение которых необходимо задать, для вычисления значения по формуле.
        В случае ошибок, они будут записаны в поле error_text

        Returns:
            dict[float]: Словарь, где ключ - название переменной, а значение - None

        """
        try:
            return {i[0]: None for i in regex.findall(
                r'(\b[a-z]\w*\b(?!\s*[\(\"])(\[(?:[^\[\]]|(?2))*\])?)',
                self.expression,
                overlapped=True)}
        except Exception as ex:
            self.error_text = str(ex)
            return None

    def calculate_result(self) -> float | None:
        """
        Вычисляет значение по формуле для указанных в поле класса variables значений переменных.
        В случае невозможности вычисления значения(по арифметическим или иным причинам) ошибка в
         текстовом виде будет помещена в error_text, а функция вернёт None

        Returns:
            float: Результат вычисления.
        """
        if self.expression is None or self.variables is None:
            return None

        if any([i is None for i in self.variables.values()]):
            self.error_text = "Не все переменные заполнены, что недопустимо"
            return None

        try:
            self.error_text = None
            return ne.evaluate(self.expression, local_dict=self.variables).item()
        except ArithmeticError as ae:
            self.error_text = f"Арифметическая ошибка:{str(ae)}"
        except Exception as ex:
            self.error_text = str(ex)

        return None

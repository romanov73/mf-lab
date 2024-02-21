import regex
import numexpr as ne


class Formula:
    def __init__(self, expression: str):
        """
        Формула, которую можно вычислить. Для этого необходимо передать значения всех переменных

        Args:
            expression (str): Текст формулы, которую пытаемся вычислить.
        """
        self.expression = expression.replace("^", "**")

    def extract_all_variable(self) -> list[str]:
        """
        Получение списка всех переменных, значение которых необходимо задать, для вычисления значения по формуле.
        Обработка ошибок на данном уровне отсутствует.

        Returns:
            list[str]: Список переменных

        """
        return [i[0] for i in regex.findall(
            r'(\b[a-z]\w*\b(?!\s*[\(\"])(\[(?:[^\[\]]|(?2))*\])?)',
            self.expression,
            overlapped=True)]

    def calculate_result(self, variables: dict[float]) -> float:
        """
        Вычисляет значение по формуле для указанных переменных.
        Обработка ошибок на данном уровне отсутствует.

        Args:
            variables (dict[float]): Словарь, где ключ - название переменной, а значение - её значение.

        Returns:
            float: Результат вычисления.
        """
        return ne.evaluate(self.expression, local_dict=variables).item()
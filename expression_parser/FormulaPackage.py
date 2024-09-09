from expression_parser import Formula


class FormulaPackage:
    def __init__(self, expressions: list[str]):
        """
        Поля экземпляра:
            variables (list[str]): Список невычисляемых переменных для данного пакета. Если при парснге ошибка - None

            formulas (list[Formula]): Список объектов формул для данного пакета

            error_text (str): Строка описания ошибки, если таковая есть. Иначе - None
        :param expressions: Список строк формул
        """

        self.variables = None
        self._value_vars = None
        self.formulas: [Formula] = [Formula(e) for e in expressions]
        self.error_text = None

        self._get_variables()

        if self.variables is not None:
            self._value_vars: dict[str, float | None] = {}
            for v in self.variables:
                self._value_vars[v] = None

    def _get_variables(self):
        """
        Получаем переменные из формул, определяем, какие вычисляемые, а какие нет + валидируем докучи
        :return:
        """

        is_valid = True

        variables: dict[str, bool] = {}  # переменная, вычисляемая ли

        for f in self.formulas:
            if f.error_text is not None:
                self.error_text = 'Ошибка в формуле пакета'
                is_valid = False
            else:
                if f.res_variables is not None:
                    if f.res_variables in variables:
                        if variables[f.res_variables]:
                            self.error_text = 'Одну и ту же переменную () вычисляем по 2-м формулам'
                            is_valid = False
                        else:
                            variables[f.res_variables] = True
                    else:
                        variables[f.res_variables] = True

                for v in f.variables:
                    if v not in variables:
                        variables[v] = False

        if is_valid:
            self.variables: list[str] = []
            for v in variables:
                if not variables[v]:
                    self.variables.append(v)

    def set_variables(self, variables: dict[str, float]):
        """
        Заполняем значения переменных. Эффект суммируется
        :param variables: Переменные, и их значения. Если чего-то нет в формуле, мы это не вставим
        :return:
        """
        for v in variables:
            if v in self._value_vars:
                self._value_vars[v] = variables[v]

    def calculate(self, accuracy: int = 5) -> dict[str, float] | None:
        """
        Непосредственно расчёт значений переменных. Данные должны заранее быть загружены через set_variables
        :return: Словарь с вычислеными значениями переменных. Всех, которые вычислялись (те, что дали тут отсутсвуют).
        Если случилась ошибка - то вернём None
        """
        if any([f.expression is None for f in self.formulas]):
            return None

        if any([v is None for v in self._value_vars.values()]):
            return None

        current_vars: list[str] = list(self._value_vars.keys())
        formulas_left: list[Formula] = self.formulas.copy()
        res: dict[str, float] = {}

        while len(formulas_left) > 0:
            for f in formulas_left:
                if all([v in current_vars for v in f.variables]):
                    f.set_variables({v: self._value_vars[v] for v in f.variables})
                    v = f.calculate_result(accuracy)
                    if v is None:
                        return None
                    if f.res_variables is not None:
                        res[f.res_variables] = self._value_vars[f.res_variables] = v
                        current_vars.append(f.res_variables)
                    else:
                        res["None"] = v
                    formulas_left.remove(f)

        for v in res.keys():
            self._value_vars[v] = None  # Очищаем, чтобы потом можно было пересчитать
        return res

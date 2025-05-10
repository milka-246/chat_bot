from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import re
from pymorphy2 import MorphAnalyzer


morph = MorphAnalyzer()

import re
from pymorphy2 import MorphAnalyzer

morph = MorphAnalyzer()

def normalize_words(value):
    if not value:
        return []

    if isinstance(value, str):
        # Разбиваем строку на слова по пробелам и пунктуации
        value = re.findall(r'\w+', value.lower())

    elif isinstance(value, list):
        # Склеиваем все элементы, разбиваем, и обрабатываем
        joined = ' '.join(value)
        value = re.findall(r'\w+', joined.lower())

    return [morph.parse(word)[0].normal_form for word in value if isinstance(word, str)]

class ActionProcessingAffirm(Action):
    def name(self) -> str:
        return "action_processing_affirm"
    def run(self, dispatcher, tracker, domain):
        if tracker.get_slot("wait_affirm"):  # Упростили проверку
            if any(e["entity"] == "affirm" for e in tracker.latest_message.get("entities", [])):
                suggested = tracker.get_slot("suggested_task_number")  # Исправлено: было suggested_task_number
                dispatcher.utter_message(text=f"Вы подтвердили {suggested}.")
        return [SlotSet("wait_affirm", False), SlotSet("notreset_slots", False)]


class ActionResetSlots(Action):
    def name(self) -> str:
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        if not tracker.get_slot("notreset_slots"):
#            dispatcher.utter_message(text="Сбрасываем слоты")
            return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", 
                           "suggested_task_number", "wait_affirm"]
            ]
        return [SlotSet("notreset_slots", None)]

# Словарь для числительных
numerals_dict = {
    "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
    "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
    "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20,
    "двадцать один": 21, "двадцать два": 22, "двадцать три": 23, "двадцать четыре": 24, "двадцать пять": 25,
    "двадцать шесть": 26, "двадцать семь": 27, "первое": 1, "второе": 2, "третье": 3, "четвертое": 4,
    "пятое": 5, "шестое": 6, "седьмое": 7, "восьмое": 8, "девятое": 9, "десятое": 10,
    "одиннадцатое": 11, "двенадцатое": 12, "тринадцатое": 13, "четырнадцатое": 14, "пятнадцатое": 15,
    "шестнадцатое": 16, "семнадцатое": 17, "восемнадцатое": 18, "девятнадцатое": 19, "двадцатое": 20,
    "двадцать первое": 21, "двадцать второе": 22, "двадцать третье": 23, "двадцать четвертое": 24,
    "двадцать пятое": 25, "двадцать шестое": 26, "двадцать седьмое": 27,
    "1-е": 1, "2-е": 2, "3-е": 3, "4-е": 4, "5-е": 5, "6-е": 6, "7-е": 7, "8-е": 8, "9-е": 9, "10-е": 10,
    "11-е": 11, "12-е": 12, "13-е": 13, "14-е": 14, "15-е": 15, "16-е": 16, "17-е": 17, "18-е": 18,
    "19-е": 19, "20-е": 20, "21-е": 21, "22-е": 22, "23-е": 23, "24-е": 24, "25-е": 25, "26-е": 26, "27-е": 27,
    "№1": 1, "№2": 2, "№3": 3, "№4": 4, "№5": 5, "№6": 6, "№7": 7, "№8": 8, "№9": 9, "№10": 10,
    "№11": 11, "№12": 12, "№13": 13, "№14": 14, "№15": 15, "№16": 16, "№17": 17, "№18": 18,
    "№19": 19, "№20": 20, "№21": 21, "№22": 22, "№23": 23, "№24": 24, "№25": 25, "№26": 26, "№27": 27
}


def extract_task_number(text):
    # Попытка найти числительное в строке
    text = text.lower()  # Приводим текст к нижнему регистру

    # Проверка на наличие числительных
    for numeral, number in numerals_dict.items():
        if numeral in text:
            return number

    # Проверка на наличие чисел в текстах типа "номер 7"
    match = re.search(r"(номер|задача|задание)\s*(\d+)", text)
    if match:
        return int(match.group(2))  # Возвращаем число

    # Если числовых данных нет, возвращаем None
    return None


def get_matching_task_numbers(normalized_detail, normalized_topic, flag_entities, delta=0):
    task_scores = []
    for number, criteria in TASK_MAPPING.items():
        score = 0
        for key, value in criteria.items():
            if isinstance(value, list):
                norm_value = normalize_words(value)
                if key == "task_detail":
                    score += sum(1 for v in norm_value if v in normalized_detail)
                elif key == "task_topic":
                    score += sum(1 for v in norm_value if v in normalized_topic)
            elif value is True:
                if key in flag_entities:
                    score += 2                  #за присутствующий флаг я увеличу на 2
        task_scores.append((number, score))

    if not task_scores:
        return []

    sorted_scores = sorted(task_scores, key=lambda x: x[1], reverse=True)
    max_score = sorted_scores[0][1]
    if max_score == 0:
        return []

    top_matches = [num for num, score in sorted_scores if score >= max_score - delta]
    return top_matches


    # Сортируем по убыванию и выбираем все с максимальным значением
    sorted_scores = sorted(task_scores, key=lambda x: x[1], reverse=True)
    max_score = sorted_scores[0][1]
    if max_score == 0:
        return []

    top_matches = [num for num, score in sorted_scores if score == max_score]
    return top_matches



TASK_MAPPING1111 = {
    1: {"task_topic": ["поиск"], "task_detail": ["таблица"]},
    2: {"logic": True, "task_detail": ["таблица истинности"]},
    3: {"encoding": True, "task_detail": ["длина кода", "избыточность"]},
    4: {"encoding": True, "task_detail": ["равномерное", "неравномерное"]},
    5: {"num_system": True, "task_detail": ["арифметика"]},
    6: {"programming": True, "task_detail": ["анализ переменных"]},
    7: {"files": True, "task_detail": ["обработка строк"]},
    8: {"data_structure": True, "task_detail": ["трассировка"]},
    9: {"coordinates": True},
    10: {"number_theory": True},
    11: {"graph_algorithm": True, "task_detail": ["кратчайший путь"]},
    12: {"graph_algorithm": True, "task_detail": ["количество маршрутов"]},
    13: {"graph_algorithm": True, "task_detail": ["оптимизация"]},
    14: {"num_system": True, "number_theory": True},
    15: {"logic": True, "task_detail": ["сложные логические формулы"]},
    16: {"os_concept": True},
    17: {"math_concept": True, "bruteforce": True},
    18: {"encoding": True, "task_detail": ["скорость передачи"]},
    19: {"game": True, "task_detail": ["один ход"]},
    20: {"game": True, "task_detail": ["2 хода"]},
    21: {"game": True, "task_detail": ["стратегия"]},
    22: {"programming": True, "sorting": True},
    23: {"dynamic_programming": True},
    24: {"programming": True, "task_detail": ["массив", "цикл"]},
    25: {"debugging": True},
    26: {"conditional_logic": True},
    27: {"bruteforce": True, "task_detail": ["все случаи"]},
}

TASK_MAPPING = {
    1: {
        "task_topic": ["информационные модели", "моделирование"],
        "task_detail": ["выбрать верный вариант", "определить тип модели", "проанализировать ситуацию"],
        "math": True
    },
    2: {
        "task_topic": ["логические схемы", "таблицы истинности"],
        "task_detail": ["определить соответствие", "выбрать схему", "найти правильный вариант"],
        "logic": True,
        "table_truth": True
    },
    3: {
        "task_topic": [
            "база данных", "базы данных", "таблица", "таблицы", 
            "реляционная модель", "связанные таблицы", "товар", "магазин", "торговля"
        ],
        "task_detail": [
            "определить количество товара",
            "найти выручку",
            "определить массу",
            "вычислить количество упаковок",
            "определить общий объём",
            "выбрать записи по условию",
            "найти дату с максимальной выручкой",
            "определить ID магазина",
            "определить изменение запаса",
            "найти продажи по отделу",
            "посчитать сумму в рублях",
            "определить район по объёму поставок"
        ],
        "keywords": [
            "дата", "поставка", "продажа", "район", "отдел", "количество", "вес", "масса",
            "стоимость", "объём", "операция", "ID магазина", "адрес", "название", 
            "артикул", "упаковка", "сметана", "макароны", "молоко", "сахар", "зефир", "чай", "спагетти", "сода"
        ],
        "data": True,
        "task_number_3": True
    },
    4: {
        "task_topic": ["логика", "логические выражения"],
        "task_detail": ["упростить выражение", "преобразовать логическое выражение", "определить результат выражения"],
        "logic": True
    },
    5: {
        "task_topic": ["таблицы истинности", "логика"],
        "task_detail": ["найти логическое значение", "указать значение переменной", "определить истинность выражения"],
        "logic": True,
        "table_truth": True
    },
    6: {
        "task_topic": ["исполнитель", "черепашка", "робот", "команды", "маршрут", "перемещение", "движение", "путь", "сетка", "поле", "клетка"],
        "task_detail": [
            "построить маршрут", 
            "перемещение вправо", 
            "перемещение вниз", 
            "движение по сетке", 
            "определить количество путей", 
            "написать программу",
            "пройти путь",
            "найти путь",
            "программа движения"
        ],
        "keywords": ["вправо", "влево", "вверх", "вниз", "диагональ"],
        "turtle": True,
        "programming": True,
        "grid_movement": True
    },
    7: {
        "task_topic": ["изображения", "звуки", "форматы файлов"],
        "task_detail": ["определить результат обработки", "выбрать правильный формат", "определить параметры изображения"],
        "data": True
    },
    8: {
        "task_topic": ["сортировка", "алгоритмы"],
        "task_detail": ["указать количество операций", "определить количество сравнений", "вычислить количество шагов"],
        "programming": True,
        "sorting": True
    },
    9: {
        "task_topic": [
            "строки", "анализ строк", "таблицы", "таблицы данных", "электронные таблицы",
            "повторения", "повторяющиеся значения", "уникальные значения", 
            "числовые закономерности", "статистические показатели", "фильтрация данных"
        ],
        "task_detail": [
            "анализировать строки с числами",
            "среднее арифметическое",
            "средние значения",
            "сравнивать суммы чисел",
            "повторяются дважды",
            "повторяется трижды",
            "интересная строка",
            "анализ повторений",
            "сравнение чисел",
            "условия с максимумом и минимумом",
            "сравнить средние арифметические",
            "арифметика со строками",
            "удовлетворяют условиям",
            "одинаковые числа",
            "все числа различны",
            "количество строк",
            "максимальное число",
            "минимальное число",
            "фильтрация данных"
        ],
        "programming": True,
        "conditional_logic": True,
        "task_number_9": True
    },
    10: {
        "task_topic": ["трассировка", "отладка", "исполнители"],
        "task_detail": ["проследить выполнение программы", "указать вывод программы", "определить значение после выполнения"],
        "programming": True,
        "debugging": True
    },
    11: {
        "task_topic": ["массивы", "циклы"],
        "task_detail": ["найти максимальное значение", "вычислить количество элементов", "обработать массив"],
        "programming": True
    },
    12: {
        "task_topic": ["строки", "символьные данные"],
        "task_detail": ["определить длину строки", "подсчитать количество символов", "обработать строку"],
        "data": True
    },
    13: {
        "task_topic": ["координаты", "адресация"],
        "task_detail": ["вычислить адрес устройства", "определить номер ячейки", "найти адрес элемента"],
        "coordinates": True
    },
    14: {
        "task_topic": ["маршруты", "графы"],
        "task_detail": ["найти кратчайший путь", "определить длину маршрута", "вычислить расстояние"],
        "graph": True
    },
    15: {
        "task_topic": ["графы", "деревья"],
        "task_detail": ["найти количество путей", "рассчитать маршруты", "определить количество маршрутов"],
        "graph": True
    },
    16: {
        "task_topic": ["перебор", "рекурсия"],
        "task_detail": ["найти количество решений", "перебрать варианты", "реализовать алгоритм перебора"],
        "programming": True
    },
    17: {
        "task_topic": ["последовательности", "арифметика"],
        "task_detail": ["вычислить значение по формуле", "подставить значения", "рассчитать результат"],
        "math": True
    },
    18: {
        "task_topic": ["электронные таблицы", "формулы"],
        "task_detail": ["построить формулу", "составить логическое выражение", "определить структуру выражения"],
        "data": True
    },
    19: {
        "task_topic": ["теория игр", "стратегия"],
        "task_detail": ["определить выигрышную стратегию", "указать победный ход", "найти условие выигрыша"],
        "game": True,
        "task_number_19": True
    },
    20: {
        "task_topic": ["теория игр", "выигрышные стратегии"],
        "task_detail": ["найти оптимальную стратегию", "определить выигрышную позицию", "выбрать ход для победы"],
        "game": True,
        "task_number_20": True
    },
    21: {
        "task_topic": ["теория игр", "дерево решений"],
        "task_detail": ["построить дерево игры", "проследить ходы игроков", "проанализировать дерево решений"],
        "game": True,
        "task_number_21": True
    },
    22: {
        "task_topic": ["архитектура", "команды", "исполнители"],
        "task_detail": ["определить результат исполнения", "выбрать верный порядок действий", "проанализировать команды"],
        "os_concept": True
    },
    23: {
        "task_topic": ["анализ алгоритмов", "оценка сложности"],
        "task_detail": ["выбрать правильный фрагмент", "определить корректный алгоритм", "сравнить алгоритмы"],
        "math": True
    },
    24: {
        "task_topic": [
            "текстовый файл", "строки", "символы", "латинский алфавит", "буквы", "файл",
            "цепочка", "непрерывная цепочка", "последовательность", "непрерывная последовательность",
            "подстрока", "фрагмент", "группы символов", "пары символов", "подряд", "по порядку",
            "латинские буквы", "заглавные буквы", "повторяющиеся символы", "арифметические выражения"
        ],
        "task_detail": [
            "максимальное количество", "определить длину цепочки", "найти подстроку", 
            "сравнение частоты символов", "анализ последовательности", "фильтрация строк",
            "определить цепочку", "длина фрагмента", "символ после", "буква между",
            "удалить разделители", "найти символ", "поиск закономерности", "анализ групп символов",
            "найти фрагмент", "найти интересную последовательность", "поиск совпадений"
        ],
        "keywords": [
            "непрерывная последовательность", "подстрока", "фрагмент", "группы символов",
            "пары символов", "по порядку", "символ", "заглавные буквы", "латинского алфавита",
            "подряд", "цепочка", "максимальное количество", "длина", "после двух одинаковых",
            "между одинаковыми", "после буквы", "разделители", "файл", "анализ строки",
            "шаблон", "повторяющийся символ", "последовательность LDR", "выражение", "арифметика"
        ],
        "data": True,
        "programming": True,
        "task_number_24": True
    },
    25: {
        "task_topic": ["числовая информация", "булева логика"],
        "task_detail": ["преобразовать число", "найти остаток", "провести логические вычисления"],
        "logic": True,
        "num_system": True
    },
    26: {
        "task_topic": [
            "заявка", "заявки", "событие", "события", "расписание", "время начала", "время окончания",
            "отрезки времени", "интервалы", "период", "размещение", "активность", "конференц-зал",
            "входной файл", "выходной файл", "файл данных", "строка файла", "целые числа",
            "список чисел", "диапазон значений", "парные числа", "соседние элементы", "файл"
        ],
        "task_detail": [
            "определить количество событий",
            "найти максимальное количество одновременных заявок",
            "определить пересечения",
            "рассчитать пересекающиеся интервалы",
            "определить пиковую нагрузку",
            "проанализировать временные отрезки",
            "сортировка списка",
            "определить минимальное и максимальное значение",
            "посчитать количество элементов в диапазоне",
            "выделить удовлетворяющие условию пары",
            "выбрать нужные элементы по индексу",
            "поиск оптимального размещения",
            "обработка входного файла",
            "вывод результата в файл",
            "определить соседние элементы",
            "поиск границ диапазона",
            "условие отбора по времени"
        ],
        "keywords": [
            "время начала", "время окончания", "пересекаются", "одновременно", "пересечение",
            "максимальное количество", "минимальное количество", "график", "отрезки", "интервалы",
            "количество заявок", "активных одновременно", "файл данных", "входной файл", "строка файла",
            "сортировка", "список чисел", "диапазон значений", "индекс элемента", "парные числа",
            "соседние элементы", "расчет загрузки", "оптимальное размещение", "максимум", "минимум"
        ],
        "data": True,
        "task_number_26": True
    },
    27: {
        "task_topic": [
            "большой объем", "два файла", "входные данные", "подпоследовательность чисел",
            "сумма элементов", "максимальная сумма", "минимальная сумма",
            "остаток от деления", "разбиение по модулю", "пара чисел", "массив",
            "кластер", "кластеризация", "центр кластера", "евклидово расстояние",
            "средняя точка", "центр масс", "координаты точек", "координатная плоскость"
        ],
        "task_detail": [
            "найти сумму элементов с условием",
            "определить подпоследовательность",
            "вычислить остаток от деления",
            "оптимизировать по модулю",
            "найти максимальную сумму пар",
            "поиск минимального остатка",
            "поиск группы с наибольшей суммой",
            "распределить по признаку",
            "разделить числа по модулю",
            "объединить по остаткам",
            "обработка чисел из двух файлов",
            "расчёт расстояния между точками",
            "определение центра масс",
            "поиск оптимального распределения"
        ],
        "keywords": [
            "модуль", "остаток", "остаток от деления", "максимальная сумма", "минимальная сумма",
            "пара чисел", "сумма элементов", "массив", "группа чисел", "сравнение остатков",
            "евклидово расстояние", "расстояние между точками", "кластер", "центроид",
            "разделение на кластеры", "поиск центра", "большой объем", "два файла",
            "файл с числами", "файл с координатами"
        ],
        "data": True,
        "dynamic_programming": True,
        "task_number_27": True
    },
}



class ActionIdentifyTaskNumber(Action):
    def name(self) -> Text:
        return "action_identify_task_number"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        task_detail = tracker.get_slot("task_detail")
        task_topic = tracker.get_slot("task_topic")

        normalized_detail = normalize_words(task_detail if isinstance(task_detail, list) else [task_detail]) if task_detail else []
        normalized_topic = normalize_words(task_topic if isinstance(task_topic, list) else [task_topic]) if task_topic else []

        # Все сущности, кроме task_number, task_topic и task_detail — это флаги
        flag_entities = set(
            ent["entity"] for ent in tracker.latest_message.get("entities", [])
            if ent["entity"] not in ["task_number", "task_topic", "task_detail"]
        )

        top_matches = get_matching_task_numbers(normalized_detail, normalized_topic, flag_entities, delta=1)

        task_number = tracker.get_slot("task_number")
        int_task_number = extract_task_number(task_number) if task_number else None

        dispatcher.utter_message(text=f"Распозналось: number: {task_number}, topic: {task_topic}, detail: {task_detail}, flags: {list(flag_entities)}")
        dispatcher.utter_message(text=f"Наиболее подходящие задания по описанию: {top_matches}")

        if int_task_number is not None and not (task_detail or task_topic or flag_entities):
            dispatcher.utter_message(text=f"Вы указали задание номер {int_task_number}.")
            return [SlotSet("task_number", int_task_number)]

        if int_task_number is not None:
            if len(top_matches) == 1 and top_matches[0] == int_task_number:
                dispatcher.utter_message(text=f"Хорошо, задание номер {int_task_number}.")
                return [SlotSet("task_number", int_task_number)]
            elif len(top_matches) > 0 and int_task_number not in top_matches:
                options = ", ".join(str(n) for n in top_matches)
                dispatcher.utter_message(text=f"Вы указали номер {int_task_number}, но по описанию похоже на задание(я) {options}. Это оно?")
                return [SlotSet("suggested_task_number", top_matches[0])]

        if int_task_number is None and len(top_matches) == 1:
            dispatcher.utter_message(text=f"Похоже, вы имеете в виду задание номер {top_matches[0]}. Подтвердите, пожалуйста.")
            return [SlotSet("suggested_task_number", top_matches[0]), SlotSet("wait_affirm", 1), SlotSet("notreset_slots", 1)]

        if int_task_number is None and len(top_matches) > 1:
            options = ", ".join(str(n) for n in top_matches)
            dispatcher.utter_message(
                text=f"По описанию подходит несколько заданий: {options}. Уточните, пожалуйста, какое вы имеете в виду.")
            return [SlotSet("suggested_task_number", top_matches[0])]

        dispatcher.utter_message(response="utter_cannot_understand_task")
        return []


class ActionConfirmSuggestedTask(Action):
    def name(self) -> Text:
        return "action_confirm_suggested_task"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        suggested = tracker.get_slot("suggested_task_number")

        if tracker.latest_message.get("intent", {}).get("name") == "affirm" and suggested:
            dispatcher.utter_message(text=f"Отлично, работаем с заданием номер {suggested}.")
            return [SlotSet("task_number", suggested), SlotSet("suggested_task_number", None)]

        elif tracker.latest_message.get("intent", {}).get("name") == "deny":
            dispatcher.utter_message(response="utter_ask_task_disambiguation")
            return [SlotSet("suggested_task_number", None)]

        dispatcher.utter_message(response="utter_cannot_understand_task")
        return []

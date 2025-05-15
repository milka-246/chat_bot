from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import re
from pymorphy2 import MorphAnalyzer


from rasa_sdk import Action
from rasa_sdk.events import SlotSet

class ActionDefaultFallback(Action):
    def name(self) -> str:
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):
        # Отправляем сообщение пользователю, если не удается распознать интент
        dispatcher.utter_message(text="Извините, я не смог вас понять. Могу помочь чем-то другим?")
        return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]



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
        wait = tracker.get_slot("wait_affirm")
        dispatcher.utter_message(text=f"Ждём ли {wait}.")
        if tracker.get_slot("wait_affirm"):  # Упростили проверку
            if any(e["entity"] == "affirm" for e in tracker.latest_message.get("entities", [])):
                suggested = tracker.get_slot("suggested_task_number")
                dispatcher.utter_message(text=f"Вы подтвердили {suggested}.")
        return [SlotSet("wait_affirm", False), SlotSet("notreset_slots", False)]

class ActionCannotUnderstandTask(Action):
    def name(self) -> str:
        return "action_cannot_understand_task"

    def run(self, dispatcher, tracker, domain):
        if tracker.get_slot("wait_affirm"):
            dispatcher.utter_message(text="Я пока не понял, о каком задании идёт речь. Попробуй уточнить номер или тему.")
            return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]


class ActionResetSlots(Action):
    def name(self) -> str:
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        if not tracker.get_slot("notreset_slots"):
            #dispatcher.utter_message(text="Сбрасываем слоты")
            return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]
        else:
            return [SlotSet("notreset_slots", False)]

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
    text = text.lower().strip()  # Приводим к нижнему регистру и убираем пробелы
    
    # 1. Проверка на числительные (первое, второе...)
    for numeral, number in numerals_dict.items():
        if numeral in text:
            return number
    
    # 2. Проверка форматов:
    # - "задание 19"
    # - "19 задание"
    # - "номер 19"
    # - "задача 19"
    match = re.search(r"(?:номер|задача|задание)\s*(\d+)|(\d+)\s*(?:номер|задача|задание)", text)
    if match:
        return int(match.group(1) or match.group(2))  # Возвращаем найденное число
    
    # 3. Проверка на просто число (только если оно отдельно)
    if re.fullmatch(r"\d+", text.strip()):
        return int(text.strip())
    
    return None


def get_matching_task_numbers(normalized_detail, normalized_topic, flag_entities, delta=0):
    task_scores = []
    for number, criteria in TASK_MAPPING.items():
        score = 0
        for key, value in criteria.items():
            if isinstance(value, list):
                norm_value = normalize_words(value)
                if key == "task_detail":
                    score += sum(2 for v in norm_value if v in normalized_detail)
                elif key == "task_topic":
                    score += sum(2 for v in norm_value if v in normalized_topic)
            elif value is True:
                if key in flag_entities:
                    score += 5                  #за присутствующий флаг я увеличу на 2
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


TASK_MAPPING = {
    1: {
        "task_topic": ["графы", "маршруты", "дорога"],
        "task_detail": ["определить номера населенных пунктов", "определить длину дороги", "определить сумму дорог"],
        "task_number_1": True,
        "graph": True
    },
    2: {
        
    },
    3: {
        "task_topic": [
            "база данных", "реляционная модель", "связанные таблицы", "товар", "магазин", "торговля"
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
        "task_number_3": True
    },
    4: {
        "task_topic": ["кодирование","декодирование","передача информации"],
        "task_detail": ["закодировать информацию", "декодировать информацию"],
        "task_number_4": True
    },
    5: {
        "task_topic": ["построение алгоритмов", "анализ алгоритмов"],
        "task_detail": ["найти результат алгоритма", "указать наименьшее число", "указать наибольшее число"],
        "task_number_5": True
    },
    6: {
        "task_topic": ["исполнитель черепаха", "рисует"],
        "task_detail": ["количество точек в области", "точки с целочисленными координатами"],
        "task_number_6": True
    },
    7: {
        "task_topic": ["изображения", "документы" "звуки", "форматы файлов", "хранение"],
        "task_detail": ["найти объем", "выбрать правильный формат", "найти размер"],
        "task_number_7": True
    },
    8: {
        "task_topic": ["комбинаторика", "системы счисления", "кодовые слова", "перестановки", "буквенные комбинации", "последовательности"],
        "task_detail": ["найти первое слово", "записать слово", "подсчитать варианты", "определить позицию", "найти все комбинации"],
        "task_number_8": True
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
        "task_number_9": True
    },
    10: {
        
    },
    11: {
        "task_topic": ["пароль", "символы", "кодирование паролей"],
        "task_detail": ["определить объём памяти", "количество байт"],
        "task_number_11": True
    },
    12: {
        "task_topic": ["строки", "символьные данные", "алгоритм исполнителя"],
        "task_detail": ["определить длину строки", "подсчитать количество символов", "определить наименьшее значение", "определить наибольшее значение", "определить строку", "найти максимальное значение", "найти минимальное значение"],
        "task_number_12": True
    },
    13: {
       
    },
    14: {
        
    },
    15: {
        
    },
    16: {
        
    },
    17: {
        "task_topic": ["обработка последовательностей"],
        "task_detail": ["определить количество чисел", "вывести пары чисел", "сгруппировать элементы по свойству"],
        "task_number_17": True
    },
    18: {
        "task_topic": ["динамическое программирование"],
        "task_detail": ["найти максимум пути","найти минимум пути"],
        "task_number_18": True
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
        "task_topic": ["параллельные процессы", "последовательные процессы", "вычислительные процессы","время вычисления"],
        "task_detail": ["определить результат исполнения", "найти время выполнения процесса", "определить время"],
        "task_number_22": True
    },
    23: {
        "task_topic": ["последовательность команд", "траектория"],
        "task_detail": ["количество программ"],
        "task_number_23": True
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
        "task_number_24": True
    },
    25: {
        "task_topic": ["маски", "делители числа"],
        "task_detail": ["найти числа, которые соответствуют маске",  "найти остаток", "результат деления"],
        "task_number_25": True
    },
    26: {
        "task_topic": [
            "заявка", "событие", "расписание", "время начала", "время окончания",
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
        if int_task_number is not None and (not isinstance(int_task_number, int) or int_task_number < 1 or int_task_number > 27):
            int_task_number = None

        dispatcher.utter_message(text=f"Распозналось: number: {task_number}, topic: {task_topic}, detail: {task_detail}, flags: {list(flag_entities)}")
        dispatcher.utter_message(text=f"Наиболее подходящие задания по описанию: {top_matches}")
        #dispatcher.utter_message(text=f"Распозналось {int_task_number}.")
        if int_task_number is not None and not (task_detail or task_topic or flag_entities):
            dispatcher.utter_message(text=f"Вы указали задание номер {int_task_number}.")
            return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]

        if int_task_number is not None:
            if len(top_matches) == 1 and top_matches[0] == int_task_number:
                dispatcher.utter_message(text=f"Хорошо, задание номер {int_task_number}.")
                return [SlotSet("task_number", int_task_number)]
            elif len(top_matches) > 0 and int_task_number not in top_matches:
                options = ", ".join(str(n) for n in top_matches)
                dispatcher.utter_message(text=f"Вы указали номер {int_task_number}, но по описанию похоже на задание(я) {options}. Это оно?")
                return [SlotSet("suggested_task_number", top_matches[0]), SlotSet("wait_affirm", True), SlotSet("notreset_slots", True)]

        if int_task_number is None and len(top_matches) == 1:
            dispatcher.utter_message(text=f"Похоже, вы имеете в виду задание номер {top_matches[0]}. Подтвердите, пожалуйста.")
            dispatcher.utter_message(text="Я тут")
            return [SlotSet("suggested_task_number", top_matches[0]), SlotSet("wait_affirm", True), SlotSet("notreset_slots", True)]

        if int_task_number is None and len(top_matches) > 1:
            options = ", ".join(str(n) for n in top_matches)
            dispatcher.utter_message(
                text=f"По описанию подходит несколько заданий: {options}. Уточните, пожалуйста, какое вы имеете в виду.")
            return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]

        dispatcher.utter_message(response="utter_cannot_understand_task")
        return [
                SlotSet(slot, None)
                for slot in ["task_number", "task_topic", "task_detail", "suggested_task_number"]
            ] + [
                SlotSet("wait_affirm", False),
                SlotSet("notreset_slots", False)
            ]

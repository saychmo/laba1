# automaton_searcher.py
# Модуль для поиска подстрок с использованием конечного автомата

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class AutomatonState(Enum):
    """Состояния автомата для поиска цитат в одинарных кавычках"""
    START = 0           # Начальное состояние
    IN_QUOTE = 1        # Внутри цитаты
    ESCAPE = 2          # Встретили экранирующий символ \
    QUOTE_END = 3       # Нашли закрывающую кавычку


@dataclass
class AutomatonMatch:
    """Класс для хранения информации о найденной подстроке"""
    text: str
    start_line: int
    start_pos: int
    end_line: int
    end_pos: int
    absolute_start: int
    absolute_end: int
    length: int
    
    def __repr__(self):
        return f"AutomatonMatch(text='{self.text}', line={self.start_line}, pos={self.start_pos})"


class AutomatonSearcher:
    """
    Конечный автомат для поиска цитат в одинарных кавычках.
    Поддерживает экранированные символы: \' \\ \n \t и др.
    """
    
    def __init__(self):
        """Инициализация автомата"""
        self.current_state = AutomatonState.START
        self.quote_start_pos = -1
        self.quote_start_line = -1
        self.quote_start_col = -1
        self.quote_chars = []
        
        # Множество символов, которые могут быть экранированы
        self.escape_chars = {"'", "\\", "n", "t", "r", "f", "b", "v", "0"}
        
    def reset(self):
        """Сброс автомата в начальное состояние"""
        self.current_state = AutomatonState.START
        self.quote_start_pos = -1
        self.quote_start_line = -1
        self.quote_start_col = -1
        self.quote_chars = []
    
    def _update_line_info(self, text: str, position: int) -> Tuple[int, int, int]:
        """
        Определяет номер строки и позицию в строке по абсолютной позиции
        
        Returns:
            tuple: (номер_строки, позиция_в_строке, абсолютная_позиция_начала_строки)
        """
        lines = text[:position + 1].split('\n')
        line_num = len(lines) - 1
        line_start = position - len(lines[-1]) if line_num > 0 else 0
        col_num = position - line_start
        return line_num, col_num, line_start
    
    def find_matches(self, text: str) -> List[AutomatonMatch]:
        """
        Поиск всех цитат в тексте с использованием конечного автомата
        
        Алгоритм:
        1. Проходит по каждому символу текста
        2. В зависимости от текущего состояния и символа переходит в новое состояние
        3. При обнаружении закрывающей кавычки сохраняет найденную цитату
        
        Args:
            text: исходный текст
            
        Returns:
            Список найденных цитат
        """
        matches = []
        self.reset()
        
        i = 0
        length = len(text)
        
        while i < length:
            char = text[i]
            next_state = self._transition(char)
            
            # Обработка действий при переходе
            action_result = self._action(char, i, text)
            if action_result is not None:
                matches.append(action_result)
            
            self.current_state = next_state
            i += 1
        
        # Если остались незакрытые кавычки - игнорируем
        if self.current_state == AutomatonState.IN_QUOTE:
            # Незакрытая цитата - не сохраняем
            pass
        
        return matches
    
    def _transition(self, char: str) -> AutomatonState:
        """
        Функция переходов автомата
        
        Таблица переходов:
        ┌─────────────┬─────────┬──────────┬────────┐
        │ Состояние   │  '      │  \       │ other  │
        ├─────────────┼─────────┼──────────┼────────┤
        │ START       │ IN_QUOTE│ START    │ START  │
        │ IN_QUOTE    │ QUOTE_END│ ESCAPE  │ IN_QUOTE│
        │ ESCAPE      │ IN_QUOTE│ IN_QUOTE │ IN_QUOTE│
        │ QUOTE_END   │ IN_QUOTE│ QUOTE_END│ START  │
        └─────────────┴─────────┴──────────┴────────┘
        """
        if self.current_state == AutomatonState.START:
            if char == "'":
                return AutomatonState.IN_QUOTE
            return AutomatonState.START
            
        elif self.current_state == AutomatonState.IN_QUOTE:
            if char == "'":
                return AutomatonState.QUOTE_END
            elif char == "\\":
                return AutomatonState.ESCAPE
            return AutomatonState.IN_QUOTE
            
        elif self.current_state == AutomatonState.ESCAPE:
            # После escape переходим обратно в IN_QUOTE (любой символ)
            return AutomatonState.IN_QUOTE
            
        elif self.current_state == AutomatonState.QUOTE_END:
            if char == "'":
                # Вложенная кавычка? Начинаем новую цитату
                return AutomatonState.IN_QUOTE
            else:
                # Возвращаемся в START
                return AutomatonState.START
        
        return AutomatonState.START
    
    def _action(self, char: str, position: int, text: str) -> Optional[AutomatonMatch]:
        """
        Действия при переходах между состояниями
        
        Действия:
        - START -> IN_QUOTE: запомнить начало цитаты
        - IN_QUOTE: добавить символ в буфер
        - IN_QUOTE -> QUOTE_END: сохранить найденную цитату
        - ESCAPE: добавить экранированный символ (с обработкой)
        """
        
        if self.current_state == AutomatonState.START and char == "'":
            # Начало цитаты
            self.quote_start_pos = position
            line, col, _ = self._update_line_info(text, position)
            self.quote_start_line = line
            self.quote_start_col = col
            self.quote_chars = []
            
        elif self.current_state == AutomatonState.IN_QUOTE:
            if char != "\\":  # Не escape символ
                self.quote_chars.append(char)
            else:
                # Escape символ - добавим его в следующем шаге
                pass
                
        elif self.current_state == AutomatonState.ESCAPE:
            # Обработка экранированного символа
            escaped_char = self._process_escape(char)
            self.quote_chars.append(escaped_char)
            
        elif self.current_state == AutomatonState.QUOTE_END:
            # Нашли закрывающую кавычку - сохраняем цитату
            if self.quote_chars:
                quote_text = ''.join(self.quote_chars)
                
                # Вычисляем позиции конца
                end_line, end_col, _ = self._update_line_info(text, position)
                
                # Начальная абсолютная позиция (кавычка не включается)
                absolute_start = self.quote_start_pos + 1
                absolute_end = position  # позиция закрывающей кавычки
                
                match = AutomatonMatch(
                    text=quote_text,
                    start_line=self.quote_start_line + 1,  # 1-based для пользователя
                    start_pos=self.quote_start_col + 2,    # +2 т.к. после открывающей кавычки
                    end_line=end_line + 1,
                    end_pos=end_col,
                    absolute_start=absolute_start,
                    absolute_end=absolute_end,
                    length=len(quote_text)
                )
                
                # Сброс для следующей цитаты
                self.quote_chars = []
                return match
        
        return None
    
    def _process_escape(self, char: str) -> str:
        """
        Обработка escape-последовательностей
        
        Поддерживаются:
        \\' - одинарная кавычка
        \\\\ - обратный слеш
        \\n - новая строка
        \\t - табуляция
        \\r - возврат каретки
        \\f - подача страницы
        \\b - backspace
        \\v - вертикальная табуляция
        \\0 - null символ
        """
        escape_map = {
            "'": "'",
            "\\": "\\",
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "f": "\f",
            "b": "\b",
            "v": "\v",
            "0": "\0"
        }
        
        if char in escape_map:
            return escape_map[char]
        return char  # Неизвестная escape-последовательность - оставляем как есть
    
    def get_state_diagram(self) -> str:
        """
        Возвращает текстовое представление диаграммы состояний автомата
        """
        diagram = """
        Диаграмма состояний конечного автомата для поиска цитат:
        
                              ┌─────────────────┐
                              │                 │
                              ▼                 │
        ┌───────┐    '     ┌─────────┐    '    ┌───────────┐
        │ START │─────────►│ IN_QUOTE│────────►│ QUOTE_END │
        └───────┘          └─────────┘         └───────────┘
           │  ▲                 │  ▲                 │  ▲
           │  │                 │  │                 │  │
           │  │ other           │  │ other          │  │ '
           │  │                 │  │                 │  │
           │  └─────────────────┘  │                 │  │
           │         other         │                 │  │
           │                       │                 │  │
           │    ┌─────────┐        │                 │  │
           └────┤ ESCAPE  │◄───────┘                 │  │
                └─────────┘        \                 │  │
                    │                                 │  │
                    └─────────────────────────────────┘  │
                              any char                   │
                                                         │
                    ┌────────────────────────────────────┘
                    │
                    ▼
              (сохранить цитату)
        """
        return diagram


class AutomatonVisualizer:
    """Класс для визуализации работы автомата (для отладки)"""
    
    @staticmethod
    def trace_search(text: str, searcher: AutomatonSearcher) -> List[Dict]:
        """
        Трассировка работы автомата: запись всех переходов
        """
        trace = []
        searcher.reset()
        
        i = 0
        length = len(text)
        
        while i < length:
            char = text[i]
            old_state = searcher.current_state
            new_state = searcher._transition(char)
            
            trace.append({
                'position': i,
                'char': char,
                'old_state': old_state.name,
                'new_state': new_state.name,
                'is_quote_start': (old_state == AutomatonState.START and char == "'"),
                'is_quote_end': (old_state == AutomatonState.IN_QUOTE and char == "'")
            })
            
            # Выполняем действие (но не сохраняем в trace)
            searcher._action(char, i, text)
            searcher.current_state = new_state
            i += 1
        
        return trace
    
    @staticmethod
    def print_trace(trace: List[Dict]):
        """Вывод трассировки в консоль"""
        print("\n" + "="*80)
        print("Трассировка работы автомата:")
        print("="*80)
        print(f"{'Поз.':<6} {'Символ':<8} {'Состояние→':<15} {'Событие':<30}")
        print("-"*80)
        
        for step in trace:
            pos = step['position']
            char = repr(step['char'])[1:-1] if step['char'] != '\n' else '\\n'
            trans = f"{step['old_state']} → {step['new_state']}"
            
            if step['is_quote_start']:
                event = "🔵 НАЧАЛО ЦИТАТЫ"
            elif step['is_quote_end']:
                event = "🟢 КОНЕЦ ЦИТАТЫ"
            else:
                event = ""
            
            print(f"{pos:<6} {char:<8} {trans:<15} {event:<30}")
        
        print("="*80 + "\n")
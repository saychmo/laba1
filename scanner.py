# scanner.py
# Модуль лексического анализатора для объявления перечислений F#

from enum import Enum
from typing import List, Tuple, Optional


class TokenType(Enum):
    """Типы лексем"""
    KEYWORD = 1      # type
    IDENTIFIER = 2   # Day, Monday, Tuesday...
    OPERATOR = 3     # =
    PIPE = 4         # |
    SEPARATOR = 5    # ;
    WHITESPACE = 6   # пробелы, табуляция, перевод строки
    ERROR = -1       # ошибочный символ


class Token:
    """Класс лексемы"""
    def __init__(self, token_type: TokenType, value: str, line: int, start_pos: int, end_pos: int):
        self.type = token_type          # тип лексемы
        self.code = token_type.value    # числовой код
        self.value = value              # значение лексемы
        self.line = line                 # номер строки (1-based)
        self.start_pos = start_pos       # начальная позиция (0-based)
        self.end_pos = end_pos           # конечная позиция (0-based)
    
    def __str__(self):
        return f"[{self.code:2d}] {self.type.name:10s} '{self.value}' стр.{self.line} [{self.start_pos}:{self.end_pos}]"
    
    def to_table_row(self) -> Tuple:
        """Для отображения в таблице"""
        type_name = {
            TokenType.KEYWORD: "Ключевое слово",
            TokenType.IDENTIFIER: "Идентификатор",
            TokenType.OPERATOR: "Оператор",
            TokenType.PIPE: "Разделитель вариантов",
            TokenType.SEPARATOR: "Разделитель",
            TokenType.WHITESPACE: "Пробельный символ",
            TokenType.ERROR: "Ошибка"
        }.get(self.type, "Неизвестный тип")
        
        return (self.code, type_name, self.value, f"{self.line}:{self.start_pos}-{self.end_pos}")


class Scanner:
    """Конечный автомат для лексического анализа"""
    
    def __init__(self):
        # Состояния автомата
        self.START = 0          # начальное состояние
        self.IN_KEYWORD = 1     # чтение "type"
        self.IN_IDENTIFIER = 2  # чтение идентификатора
        self.IN_OPERATOR = 3    # чтение "="
        self.IN_PIPE = 4        # чтение "|"
        self.IN_SEPARATOR = 5   # чтение ";"
        self.IN_WHITESPACE = 6  # пропуск пробелов
        self.IN_ERROR = 7       # ошибочное состояние
        
        # Контекст для проверки корректности
        self.expecting_type_keyword = True  # Ожидаем ключевое слово "type" в начале
        self.type_found = False  # Было ли найдено ключевое слово "type"
        self.equal_found = False  # Был ли найден оператор "="
        
        self.current_state = self.START
        self.tokens = []
        self.current_token = ""
        self.current_line = 1
        self.line_start_pos = 0
        self.token_start_pos = 0
        self.current_pos = 0
        self.error_token = ""  # для накопления ошибочных символов
        self.error_start_pos = 0  # начальная позиция ошибки
    
    def reset(self):
        """Сброс автомата перед новым анализом"""
        self.current_state = self.START
        self.tokens = []
        self.current_token = ""
        self.current_line = 1
        self.line_start_pos = 0
        self.current_pos = 0
        self.token_start_pos = 0
        self.error_token = ""
        self.error_start_pos = 0
        
        # Сброс контекста
        self.expecting_type_keyword = True
        self.type_found = False
        self.equal_found = False
    
    def is_letter(self, c: str) -> bool:
        """Проверка, является ли символ буквой"""
        return c.isalpha()
    
    def is_digit(self, c: str) -> bool:
        """Проверка, является ли символ цифрой"""
        return c.isdigit()
    
    def is_whitespace(self, c: str) -> bool:
        """Проверка, является ли символ пробельным"""
        return c in ' \t\r'
    
    def is_valid_identifier_start(self, c: str) -> bool:
        """Проверка, может ли символ начинать идентификатор"""
        return self.is_letter(c)
    
    def is_valid_identifier_char(self, c: str) -> bool:
        """Проверка, может ли символ быть частью идентификатора"""
        return self.is_letter(c) or self.is_digit(c) or c == '_'
    
    def add_token(self, token_type: TokenType):
        """Добавить лексему в список"""
        if self.current_token:
            relative_start = self.token_start_pos - self.line_start_pos
            token_end_global = self.token_start_pos + len(self.current_token) - 1
            relative_end = token_end_global - self.line_start_pos
            
            token = Token(
                token_type,
                self.current_token,
                self.current_line,
                relative_start,
                relative_end
            )
            if token_type != TokenType.WHITESPACE:
                self.tokens.append(token)
                
                # Обновляем контекст в зависимости от типа лексемы
                if token_type == TokenType.KEYWORD and self.current_token == "type":
                    self.type_found = True
                    self.expecting_type_keyword = False
                elif token_type == TokenType.OPERATOR and self.current_token == "=":
                    self.equal_found = True
                    
            self.current_token = ""
    
    def add_error_token(self):
        """Добавить лексему ошибки, объединяя все накопленные ошибочные символы"""
        if self.error_token:
            relative_start = self.error_start_pos - self.line_start_pos
            token_end_global = self.error_start_pos + len(self.error_token) - 1
            relative_end = token_end_global - self.line_start_pos
            
            token = Token(
                TokenType.ERROR,
                self.error_token,
                self.current_line,
                relative_start,
                relative_end
            )
            self.tokens.append(token)
            self.error_token = ""
            self.error_start_pos = 0
    
    def scan(self, text: str) -> List[Token]:
        """Анализ входного текста, возвращает список лексем"""
        self.reset()
        
        i = 0
        length = len(text)
        
        while i < length:
            c = text[i]
            self.current_pos = i
            
            if self.current_state == self.START:
                self.token_start_pos = i
                
                if c == 't':
                    self.current_token += c
                    self.current_state = self.IN_KEYWORD
                    i += 1
                elif self.is_letter(c):
                    # Проверяем контекст: если ожидаем "type", то любая другая буква - ошибка
                    if self.expecting_type_keyword:
                        # Начинаем накопление ошибки
                        self.error_token = c
                        self.error_start_pos = i
                        self.current_state = self.IN_ERROR
                        i += 1
                    else:
                        self.current_token += c
                        self.current_state = self.IN_IDENTIFIER
                        i += 1
                elif c == '=':
                    self.current_token += c
                    self.current_state = self.IN_OPERATOR
                    i += 1
                elif c == '|':
                    self.current_token += c
                    self.current_state = self.IN_PIPE
                    i += 1
                elif c == ';':
                    self.current_token += c
                    self.current_state = self.IN_SEPARATOR
                    i += 1
                elif self.is_whitespace(c):
                    self.current_token += c
                    self.current_state = self.IN_WHITESPACE
                    i += 1
                elif c == '\n':
                    self.current_line += 1
                    self.line_start_pos = i + 1
                    i += 1
                else:
                    # Неожиданный символ - начинаем накопление ошибки
                    self.error_token = c
                    self.error_start_pos = i
                    self.current_state = self.IN_ERROR
                    i += 1
            
            elif self.current_state == self.IN_KEYWORD:
                if self.is_letter(c):
                    self.current_token += c
                    i += 1
                    
                    # Проверяем, является ли текущая строка префиксом "type"
                    if not "type".startswith(self.current_token):
                        # Если это не префикс "type", проверяем контекст
                        if self.expecting_type_keyword:
                            # Должно быть "type", значит это ошибка - переносим всё в ошибку
                            self.error_token = self.current_token
                            self.error_start_pos = self.token_start_pos
                            self.current_token = ""
                            self.current_state = self.IN_ERROR
                        else:
                            # Уже нашли "type" ранее, значит это обычный идентификатор
                            self.current_state = self.IN_IDENTIFIER
                else:
                    # Встретили не-букву, завершаем текущую лексему
                    if self.current_token == "type":
                        self.add_token(TokenType.KEYWORD)
                    else:
                        if self.expecting_type_keyword:
                            # Должно быть "type", значит это ошибка
                            self.error_token = self.current_token
                            self.error_start_pos = self.token_start_pos
                            self.add_error_token()
                        else:
                            self.add_token(TokenType.IDENTIFIER)
                    
                    self.current_state = self.START
                    # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_IDENTIFIER:
                if self.is_valid_identifier_char(c):
                    self.current_token += c
                    i += 1
                else:
                    self.add_token(TokenType.IDENTIFIER)
                    self.current_state = self.START
                    # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_OPERATOR:
                self.add_token(TokenType.OPERATOR)
                self.current_state = self.START
                # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_PIPE:
                self.add_token(TokenType.PIPE)
                self.current_state = self.START
                # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_SEPARATOR:
                self.add_token(TokenType.SEPARATOR)
                self.current_state = self.START
                # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_WHITESPACE:
                if self.is_whitespace(c):
                    self.current_token += c
                    i += 1
                elif c == '\n':
                    self.add_token(TokenType.WHITESPACE)
                    self.current_line += 1
                    self.line_start_pos = i + 1
                    self.current_state = self.START
                    i += 1
                else:
                    self.add_token(TokenType.WHITESPACE)
                    self.current_state = self.START
                    # Не увеличиваем i, чтобы обработать текущий символ заново в START
            
            elif self.current_state == self.IN_ERROR:
                # Проверяем, является ли текущий символ допустимым
                is_valid = (self.is_valid_identifier_char(c) or 
                           c == '=' or c == '|' or c == ';' or 
                           self.is_whitespace(c) or c == '\n')
                
                # Также проверяем контекст для букв
                if self.is_letter(c) and self.expecting_type_keyword and c != 't':
                    is_valid = False  # В контексте ожидания "type" другие буквы недопустимы
                
                if not is_valid:
                    # Продолжаем накапливать ошибочные символы
                    self.error_token += c
                    i += 1
                else:
                    # Встретили допустимый символ - завершаем ошибку
                    self.add_error_token()
                    self.current_state = self.START
                    # Не увеличиваем i, чтобы обработать текущий символ заново в START
        
        # Конец строки - добавляем последнюю лексему или ошибку
        if self.current_token:
            if self.current_state == self.IN_KEYWORD:
                if self.current_token == "type":
                    self.add_token(TokenType.KEYWORD)
                else:
                    if self.expecting_type_keyword:
                        self.error_token = self.current_token
                        self.error_start_pos = self.token_start_pos
                        self.add_error_token()
                    else:
                        self.add_token(TokenType.IDENTIFIER)
            elif self.current_state == self.IN_IDENTIFIER:
                self.add_token(TokenType.IDENTIFIER)
            elif self.current_state == self.IN_OPERATOR:
                self.add_token(TokenType.OPERATOR)
            elif self.current_state == self.IN_PIPE:
                self.add_token(TokenType.PIPE)
            elif self.current_state == self.IN_SEPARATOR:
                self.add_token(TokenType.SEPARATOR)
            elif self.current_state == self.IN_WHITESPACE:
                self.add_token(TokenType.WHITESPACE)
        
        # Добавляем последнюю накопленную ошибку, если есть
        if self.error_token:
            self.add_error_token()
        
        return self.tokens
    
    def scan_with_errors(self, text: str) -> Tuple[List[Token], List[str]]:
        """Анализ с возвратом списка ошибок (как строк)"""
        tokens = self.scan(text)
        errors = []
        for t in tokens:
            if t.type == TokenType.ERROR:
                if len(t.value) == 1:
                    errors.append(f"Недопустимый символ '{t.value}' в строке {t.line}, позиция {t.start_pos}")
                else:
                    errors.append(f"Недопустимые символы '{t.value}' в строке {t.line}, позиции {t.start_pos}-{t.end_pos}")
        return tokens, errors


def analyze_text(text: str) -> Tuple[List[Token], List[str]]:
    """Анализирует текст и возвращает лексемы и список строк с ошибками"""
    scanner = Scanner()
    return scanner.scan_with_errors(text)


# Пример использования
if __name__ == "__main__":
    print("="*60)
    print("Тест 1: Корректное объявление перечисления")
    print("="*60)
    
    test_text = """type Day =
    | Monday
    | Tuesday
    | Wednesday
    | Thursday
    | Friday
    | Saturday
    | Sunday;"""
    
    scanner = Scanner()
    tokens = scanner.scan(test_text)
    
    print("Результаты лексического анализа:")
    print("-" * 60)
    print(f"{'Код':4} {'Тип':15} {'Лексема':20} {'Позиция'}")
    print("-" * 60)
    
    for token in tokens:
        if token.type != TokenType.WHITESPACE:
            print(f"{token.code:4} {token.type.name:15} {token.value:20} {token.line}:{token.start_pos}-{token.end_pos}")
    
    print("\n" + "="*60)
    print("Тест 2: Ошибка 'gjjgg type Day'")
    print("="*60)
    
    error_text = "gjjgg type Day"
    tokens, errors = analyze_text(error_text)
    
    print("\nЛексемы:")
    for token in tokens:
        if token.type != TokenType.WHITESPACE:
            print(f"{token.code:4} {token.type.name:15} {token.value:20} {token.line}:{token.start_pos}-{token.end_pos}")
    
    print("\nОшибки:")
    for error in errors:
        print(error)
    
    print("\n" + "="*60)
    print("Тест 3: Несколько ошибок подряд '123!@# type Day'")
    print("="*60)
    
    error_text2 = "123!@# type Day"
    tokens, errors = analyze_text(error_text2)
    
    print("\nЛексемы:")
    for token in tokens:
        if token.type != TokenType.WHITESPACE:
            print(f"{token.code:4} {token.type.name:15} {token.value:20} {token.line}:{token.start_pos}-{token.end_pos}")
    
    print("\nОшибки:")
    for error in errors:
        print(error)
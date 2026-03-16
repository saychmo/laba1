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
        
        self.current_state = self.START
        self.tokens = []
        self.current_token = ""
        self.current_line = 1
        self.line_start_pos = 0
        self.token_start_pos = 0
        self.current_pos = 0
    
    def reset(self):
        """Сброс автомата перед новым анализом"""
        self.current_state = self.START
        self.tokens = []
        self.current_token = ""
        self.current_line = 1
        self.line_start_pos = 0
        self.current_pos = 0
        self.token_start_pos = 0
    
    def is_letter(self, c: str) -> bool:
        """Проверка, является ли символ буквой"""
        return c.isalpha()
    
    def is_digit(self, c: str) -> bool:
        """Проверка, является ли символ цифрой"""
        return c.isdigit()
    
    def is_whitespace(self, c: str) -> bool:
        """Проверка, является ли символ пробельным"""
        return c in ' \t\r'
    
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
            self.current_token = ""
    
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
                elif self.is_letter(c):
                    self.current_token += c
                    self.current_state = self.IN_IDENTIFIER
                elif c == '=':
                    self.current_token += c
                    self.current_state = self.IN_OPERATOR
                elif c == '|':
                    self.current_token += c
                    self.current_state = self.IN_PIPE
                elif c == ';':
                    self.current_token += c
                    self.current_state = self.IN_SEPARATOR
                elif self.is_whitespace(c):
                    self.current_token += c
                    self.current_state = self.IN_WHITESPACE
                elif c == '\n':
                    self.current_line += 1
                    self.line_start_pos = i + 1
                else:
                    self.current_token += c
                    self.current_state = self.IN_ERROR
                    self.add_token(TokenType.ERROR)
                    self.current_state = self.START
            
            elif self.current_state == self.IN_KEYWORD:
                if self.is_letter(c):
                    self.current_token += c
                    if not "type".startswith(self.current_token):
                        self.current_state = self.IN_IDENTIFIER
                else:
                    if self.current_token == "type":
                        self.add_token(TokenType.KEYWORD)
                    else:
                        token_type = TokenType.IDENTIFIER
                        self.add_token(token_type)
                    
                    self.current_state = self.START
                    continue 
            
            elif self.current_state == self.IN_IDENTIFIER:
                if self.is_letter(c) or self.is_digit(c) or c == '_':
                    self.current_token += c
                else:
                    self.add_token(TokenType.IDENTIFIER)
                    self.current_state = self.START
                    continue
            
            elif self.current_state == self.IN_OPERATOR:
                self.add_token(TokenType.OPERATOR)
                self.current_state = self.START
                continue
            
            elif self.current_state == self.IN_PIPE:
                self.add_token(TokenType.PIPE)
                self.current_state = self.START
                continue
            
            elif self.current_state == self.IN_SEPARATOR:
                self.add_token(TokenType.SEPARATOR)
                self.current_state = self.START
                continue
            
            elif self.current_state == self.IN_WHITESPACE:
                if self.is_whitespace(c):
                    self.current_token += c
                elif c == '\n':
                    self.add_token(TokenType.WHITESPACE)
                    self.current_line += 1
                    self.line_start_pos = i + 1
                    self.current_state = self.START
                else:
                    self.add_token(TokenType.WHITESPACE)
                    self.current_state = self.START
                    continue
            
            i += 1
        
        if self.current_token:
            if self.current_state == self.IN_KEYWORD:
                if self.current_token == "type":
                    self.add_token(TokenType.KEYWORD)
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
        
        return self.tokens
    
    def scan_with_errors(self, text: str) -> Tuple[List[Token], List[str]]:
        """Анализ с возвратом списка ошибок (как строк)"""
        tokens = self.scan(text)
        errors = [f"Недопустимый символ '{t.value}' в строке {t.line}, позиция {t.start_pos}" 
                  for t in tokens if t.type == TokenType.ERROR]
        return tokens, errors

def analyze_text(text: str) -> Tuple[List[Token], List[str]]:
    """Анализирует текст и возвращает лексемы и список строк с ошибками"""
    scanner = Scanner()
    return scanner.scan_with_errors(text)

# Пример использования
if __name__ == "__main__":
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
        if token.type != TokenType.WHITESPACE:  # Пропускаем пробелы для читаемости
            print(f"{token.code:4} {token.type.name:15} {token.value:20} {token.line}:{token.start_pos}-{token.end_pos}")
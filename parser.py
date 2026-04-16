# parser.py
# Модуль синтаксического анализатора для объявления перечислений F#

from typing import List, Optional, Tuple
from enum import Enum
from scanner import Token, TokenType


# ==================== КЛАССЫ ДЛЯ AST ====================

class ASTNode:
    """Базовый класс для узлов AST"""
    def __init__(self, node_type: str, line: int = 0, start_pos: int = 0):
        self.node_type = node_type
        self.line = line
        self.start_pos = start_pos
        self.children: List['ASTNode'] = []
    
    def add_child(self, child: 'ASTNode'):
        self.children.append(child)
    
    def __str__(self, level: int = 0) -> str:
        indent = "  " * level
        result = f"{indent}{self.node_type}"
        if hasattr(self, 'value'):
            result += f": {self.value}"
        result += "\n"
        for child in self.children:
            result += child.__str__(level + 1)
        return result


class EnumDeclarationNode(ASTNode):
    """Узел: объявление перечисления"""
    def __init__(self, type_name: str, cases: List['CaseNode'], line: int = 0, start_pos: int = 0):
        super().__init__("EnumDeclaration", line, start_pos)
        self.type_name = type_name
        self.cases = cases
        for case in cases:
            self.add_child(case)
    
    def __str__(self, level: int = 0) -> str:
        indent = "  " * level
        result = f"{indent}{self.node_type}\n"
        result += f"{indent}  type_name: {self.type_name}\n"
        result += f"{indent}  cases:\n"
        for case in self.cases:
            result += case.__str__(level + 2)
        return result


class CaseNode(ASTNode):
    """Узел: вариант перечисления"""
    def __init__(self, name: str, line: int = 0, start_pos: int = 0):
        super().__init__("Case", line, start_pos)
        self.name = name
        self.value = name
    
    def __str__(self, level: int = 0) -> str:
        indent = "  " * level
        return f"{indent}{self.node_type}: {self.name}\n"


# ==================== ПАРСЕР ====================

class Parser:
    """
    Синтаксический анализатор (рекурсивный спуск)
    Грамматика:
        EnumDeclaration ::= "type" TypeName "=" CaseList ";"
        TypeName         ::= IDENTIFIER
        CaseList         ::= Case+
        Case             ::= "|" IDENTIFIER
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
        self.position = 0
        self.errors: List[str] = []
    
    def current_token(self) -> Optional[Token]:
        """Возвращает текущий токен"""
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None
    
    def peek_token(self, offset: int = 1) -> Optional[Token]:
        """Заглядывает вперёд на offset токенов"""
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None
    
    def consume(self, expected_type: TokenType, expected_value: Optional[str] = None) -> Optional[Token]:
        """
        Проверяет и потребляет токен.
        Если токен не соответствует ожидаемому, добавляет ошибку.
        """
        token = self.current_token()
        
        if token is None:
            self.errors.append(f"Ошибка: ожидался '{expected_type.name}', достигнут конец файла")
            return None
        
        if token.type != expected_type:
            self.errors.append(
                f"Синтаксическая ошибка в строке {token.line}, позиция {token.start_pos}: "
                f"ожидался {expected_type.name}, найден {token.type.name} '{token.value}'"
            )
            return None
        
        if expected_value is not None and token.value != expected_value:
            self.errors.append(
                f"Синтаксическая ошибка в строке {token.line}, позиция {token.start_pos}: "
                f"ожидался '{expected_value}', найден '{token.value}'"
            )
            return None
        
        self.position += 1
        return token
    
    def parse(self) -> Tuple[Optional[EnumDeclarationNode], List[str]]:
        """
        Запускает синтаксический анализ
        Возвращает: (AST, список ошибок)
        """
        try:
            ast = self.parse_enum_declaration()
            
            # Проверяем, что все токены обработаны
            if self.current_token() is not None:
                token = self.current_token()
                if token is not None:
                    self.errors.append(
                        f"Предупреждение: лишний токен '{token.value}' в строке {token.line}, "
                        f"позиция {token.start_pos} (после завершения разбора)"
                    )
            
            return ast, self.errors
            
        except Exception as e:
            self.errors.append(f"Критическая ошибка: {str(e)}")
            return None, self.errors
    
    def parse_enum_declaration(self) -> Optional[EnumDeclarationNode]:
        """EnumDeclaration ::= "type" TypeName "=" CaseList ";" """
        start_token = self.current_token()
        start_line = start_token.line if start_token else 0
        start_pos = start_token.start_pos if start_token else 0
        
        # type
        if self.consume(TokenType.KEYWORD, "type") is None:
            return None
        
        # TypeName
        type_name = self.parse_type_name()
        if type_name is None:
            return None
        
        # =
        if self.consume(TokenType.OPERATOR, "=") is None:
            return None
        
        # CaseList
        cases = self.parse_case_list()
        if cases is None:
            return None
        
        # ;
        if self.consume(TokenType.SEPARATOR, ";") is None:
            return None
        
        return EnumDeclarationNode(type_name, cases, start_line, start_pos)
    
    def parse_type_name(self) -> Optional[str]:
        """TypeName ::= IDENTIFIER"""
        token = self.consume(TokenType.IDENTIFIER)
        if token is None:
            return None
        return token.value
    
    def parse_case_list(self) -> Optional[List[CaseNode]]:
        """CaseList ::= Case+"""
        cases = []
        
        # Первый case (обязателен)
        case = self.parse_case()
        if case is None:
            return None
        cases.append(case)
        
        # Последующие case (необязательные)
        while True:
            next_token = self.current_token()
            if next_token and next_token.type == TokenType.PIPE:
                case = self.parse_case()
                if case:
                    cases.append(case)
                else:
                    break
            else:
                break
        
        return cases
    
    def parse_case(self) -> Optional[CaseNode]:
        """Case ::= "|" IDENTIFIER"""
        start_token = self.current_token()
        start_line = start_token.line if start_token else 0
        start_pos = start_token.start_pos if start_token else 0
        
        # |
        if self.consume(TokenType.PIPE, "|") is None:
            return None
        
        # IDENTIFIER
        token = self.consume(TokenType.IDENTIFIER)
        if token is None:
            return None
        
        return CaseNode(token.value, start_line, start_pos)
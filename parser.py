from typing import List, Optional, Tuple
from scanner import Token, TokenType


class ParserError:
    def __init__(self,
                 fragment: str,
                 line: int,
                 position: int,
                 message: str):

        self.fragment = fragment
        self.line = line
        self.position = position
        self.message = message

    def __str__(self):
        return f"{self.line}:{self.position} -> {self.message}"


class ASTNode:

    def __init__(self, node_type: str):

        self.node_type = node_type

        self.children: List['ASTNode'] = []

    def add_child(self, child):

        self.children.append(child)


class CaseNode(ASTNode):

    def __init__(self, name: str):

        super().__init__("CaseNode")

        self.name = name

        
class EnumDeclarationNode(ASTNode):

    def __init__(self, type_name: str):

        super().__init__("EnumDeclarationNode")

        self.type_name = type_name


class Parser:

    """
    Грамматика:

    EnumDeclaration ::= "type" IDENTIFIER "=" CaseList ";"

    CaseList ::= Case { Case }

    Case ::= "|" IDENTIFIER
    """

    def __init__(self, tokens: List[Token]):

        self.tokens = [
            t for t in tokens
            if t.type != TokenType.WHITESPACE
        ]

        self.position = 0

        self.errors: List[ParserError] = []

    def current_token(self) -> Optional[Token]:
        """
        Возвращает текущий токен без побочных эффектов.
        ERROR-токены не пропускаются здесь: их обрабатывает
        consume() как "джокер" (лексер уже сообщил об ошибке,
        парсер не должен дублировать диагностику).
        """

        if self.position < len(self.tokens):
            return self.tokens[self.position]

        return None

    def next_token(self):

        self.position += 1

    def synchronize(self):

        """
        Синхронизация после ошибки.
        Пропускаем токены до ближайшего
        безопасного символа.
        """

        sync_tokens = {
            TokenType.PIPE,
            TokenType.SEPARATOR
        }

        while self.current_token():

            token = self.current_token()

            if token.type in sync_tokens:
                return

            self.position += 1

    _WORD_LIKE_TYPES = {TokenType.KEYWORD, TokenType.IDENTIFIER}

    def consume(self, expected_type, expected_value=None):

        if expected_type not in self._WORD_LIKE_TYPES:
            while (self.position < len(self.tokens)
                   and self.tokens[self.position].type == TokenType.ERROR):
                self.position += 1

        token = self.current_token()

        if token is not None and token.type == TokenType.ERROR:
            self.position += 1
            return token

        if token is None:

            last_token = self.tokens[-1] if len(self.tokens) > 0 else None

            if last_token is not None:

                self.errors.append(
                    ParserError(
                        "EOF",
                        last_token.line,
                        last_token.end_pos + 1,
                        f"Ожидался {expected_type.name}"
                    )
                )

            return None

        if token.type != expected_type:

            self.errors.append(
                ParserError(
                    token.value,
                    token.line,
                    token.start_pos,
                    f"Ожидался {expected_type.name}"
                )
            )

            self.position += 1

            return None

        if expected_value is not None and token.value != expected_value:

            self.errors.append(
                ParserError(
                    token.value,
                    token.line,
                    token.start_pos,
                    f"Ожидался '{expected_value}'"
                )
            )

            self.position += 1

            return None

        self.position += 1

        return token

    def parse(self):
        """
        Главный метод синтаксического анализа
        """
        ast = self.parse_enum_declaration()

        if ast is None:
            return None, self.errors

        current = self.current_token()

        if current is not None:
            self.errors.append(
                ParserError(
                    fragment=current.value,
                    line=current.line,
                    position=current.start_pos,
                    message="Лишний текст после завершения конструкции"
                )
            )

        return ast, self.errors


    def parse_enum_declaration(self):

        keyword = self.consume(TokenType.KEYWORD, "type")

        if keyword is None:

            while self.current_token() is not None:

                token = self.current_token()

                if token is None:
                    break

                if token.type == TokenType.IDENTIFIER:
                    break

                self.position += 1

        type_name = self.parse_type_name()

        if type_name is None:
            type_name = "UNKNOWN"

        eq = self.consume(TokenType.OPERATOR, "=")

        if eq is None:

            while self.current_token() is not None:

                token = self.current_token()

                if token is None:
                    break

                # нашли начало cases
                if token.type == TokenType.PIPE:
                    break

                # нашли ;
                if (
                    token.type == TokenType.SEPARATOR
                    and token.value == ";"
                ):
                    break

                self.position += 1


        cases = []

        parsed_cases = self.parse_case_list()

        if parsed_cases is not None:
            cases = parsed_cases

        self.consume(TokenType.SEPARATOR, ";")

        node = EnumDeclarationNode(type_name)

        for case in cases:
            node.add_child(case)

        return node

    def parse_type_name(self) -> Optional[str]:
        """
        TypeName ::= IDENTIFIER
        """

        token = self.consume(TokenType.IDENTIFIER)

        if token is None:
            return None

        return token.value

    def parse_case_list(self):

        cases = []

        while self.current_token():

            token = self.current_token()

            if token is None:
                break

            if token.type == TokenType.SEPARATOR:
                break

            if token.type == TokenType.ERROR:
                self.position += 1
                continue

            case = self.parse_case()

            if case:
                cases.append(case)

        return cases

    def parse_case(self):

        # |
        if self.consume(TokenType.PIPE, "|") is None:

            self.synchronize()

            current = self.current_token()

            if current is not None:
                if current.type == TokenType.PIPE:
                    return self.parse_case()

            return None

        token = self.consume(TokenType.IDENTIFIER)

        if token is None:

            self.synchronize()

            return None

        return CaseNode(token.value)
    
def build_ast_text(node, indent="", is_last=True):

    if node is None:
        return ""

    result = indent

    if is_last:
        result += "└── "
        new_indent = indent + "    "
    else:
        result += "├── "
        new_indent = indent + "│   "

    result += node.node_type

    # Атрибуты

    if isinstance(node, EnumDeclarationNode):
        result += f": {node.type_name}"

    elif isinstance(node, CaseNode):
        result += f": {node.name}"

    result += "\n"

    # Рекурсивный вывод детей

    for i, child in enumerate(node.children):

        result += build_ast_text(
            child,
            new_indent,
            i == len(node.children) - 1
        )

    return result
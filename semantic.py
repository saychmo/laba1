from parser import EnumDeclarationNode, CaseNode


class SemanticError:

    def __init__(
        self,
        fragment: str,
        line: int,
        position: int,
        message: str
    ):

        self.fragment = fragment
        self.line = line
        self.position = position
        self.message = message


class SymbolTable:

    def __init__(self):

        self.symbols = {}

    # ==========================================
    # declare
    # ==========================================

    def declare(self, name, symbol_type):

        self.symbols[name] = symbol_type

    # ==========================================
    # lookup
    # ==========================================

    def lookup(self, name):

        return self.symbols.get(name)

    # ==========================================
    # checkDuplicate
    # ==========================================

    def check_duplicate(self, name):

        return name in self.symbols
    

class SemanticAnalyzer:

    def __init__(self):

        self.errors = []

        # таблица символов
        self.symbol_table = SymbolTable()

    def analyze(self, ast):

        if isinstance(ast, EnumDeclarationNode):

            self.check_enum(ast)

        return self.errors

    def check_enum(self, node):

        if self.symbol_table.check_duplicate(node.type_name):

            self.errors.append(
                SemanticError(
                    f"Перечисление '{node.type_name}' уже существует"
                )
            )

        if not node.type_name[0].isupper():

            self.errors.append(
                SemanticError(
                    node.type_name,
                    1,
                    1,
                    "Имя типа должно начинаться с заглавной буквы"
                )
            )

        else:

            self.symbol_table.declare(
                node.type_name,
                "enum"
            )

        used_cases = set()
        if len(node.children) == 0:

            self.errors.append(
                SemanticError(
                    node.type_name,
                    1,
                    1,
                    "Enum не может быть пустым"
                )
            )
        for case in node.children:

            if case.name in used_cases:

                self.errors.append(
                    SemanticError(
                        f"Повторяющийся элемент '{case.name}'"
                    )
                )

            if not case.name[0].isupper():

                self.errors.append(
                    SemanticError(
                        case.name,
                        1,
                        1,
                        "Имя enum-константы должно начинаться с заглавной буквы"
                    )
                )

            used_cases.add(case.name)
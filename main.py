import sys
import os
from datetime import datetime
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QToolBar, QStatusBar, QMessageBox, QFileDialog,
    QSplitter, QTableWidget, QTableWidgetItem  
)
from PyQt6.QtGui import QAction, QCloseEvent, QTextCursor, QFont, QKeySequence
from PyQt6.QtCore import Qt
from typing import Optional
from PyQt6.QtWidgets import QStyle
from PyQt6.QtCore import Qt
from scanner import analyze_text, TokenType


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_modified = False  
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Новый документ - Текстовый редактор")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 11))
        splitter.addWidget(self.editor)

        self.output_table = QTableWidget()
        self.output_table.setColumnCount(4)
        self.output_table.setHorizontalHeaderLabels(["Код", "Тип лексемы", "Лексема", "Местоположение"])
        self.output_table.setAlternatingRowColors(True)
        self.output_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        self.output_table.cellClicked.connect(self.on_error_clicked)
        splitter.addWidget(self.output_table)

        splitter.setSizes([600, 200])
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        self.create_menu()
        self.create_toolbar()
        self.update_window_title()

    def run_parser_table(self):
        """Запуск лексического анализатора с выводом в таблицу"""
        text = self.editor.toPlainText()
        
        if not text.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите текст для анализа")
            return
        
        try:
            tokens, errors = analyze_text(text)
            self.output_table.setRowCount(0)
            valid_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
            self.output_table.setRowCount(len(valid_tokens))
            
            for row, token in enumerate(valid_tokens):
                self.output_table.setItem(row, 0, QTableWidgetItem(str(token.code)))
                type_name = {
                    TokenType.KEYWORD: "Ключевое слово",
                    TokenType.IDENTIFIER: "Идентификатор",
                    TokenType.OPERATOR: "Оператор",
                    TokenType.PIPE: "Разделитель |",
                    TokenType.SEPARATOR: "Разделитель ;",
                    TokenType.ERROR: "ОШИБКА"
                }.get(token.type, token.type.name)
                self.output_table.setItem(row, 1, QTableWidgetItem(type_name))
                self.output_table.setItem(row, 2, QTableWidgetItem(token.value))
                pos = f"{token.line}:{token.start_pos}-{token.end_pos}"
                self.output_table.setItem(row, 3, QTableWidgetItem(pos))

            self.output_table.resizeColumnsToContents()
            
            if errors:
                error_msg = "\n".join([f"❌ '{e.value}' в строке {e.line}, позиция {e.start_pos}" for e in errors])
                QMessageBox.warning(self, "Ошибки анализа", f"Обнаружено {len(errors)} ошибок:\n{error_msg}")
            else:
                QMessageBox.information(self, "Анализ завершен", f"Успешно распознано {len(valid_tokens)} лексем")
            
            self.status_bar.showMessage(f"Анализ завершен: {len(valid_tokens)} лексем, {len(errors)} ошибок")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при анализе:\n{str(e)}")

    def connect_signals(self):
        """Подключение сигналов для отслеживания изменений"""
        self.editor.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        """Обработчик изменения текста"""
        if not self.is_modified:
            self.is_modified = True
            self.update_window_title()
            self.status_bar.showMessage("✎ Изменено")

    def update_window_title(self):
        """Обновление заголовка окна с учетом статуса изменений"""
        if self.current_file:
            file_name = os.path.basename(self.current_file)
        else:
            file_name = "Новый документ"
        
        modified_mark = " *" if self.is_modified else ""
        self.setWindowTitle(f"{file_name}{modified_mark} - Текстовый редактор")

    def check_save_before_action(self, action_name="продолжить"):
        """
        Проверка необходимости сохранения перед действием
        
        Возвращает:
            True - можно продолжать (сохранено или отмена не нужна)
            False - пользователь отменил действие
        """
        if not self.is_modified:
            return True  
        
        reply = QMessageBox.question(
            self,
            "Несохраненные изменения",
            f"Документ был изменен. Сохранить изменения перед {action_name}?",
            QMessageBox.StandardButton.Save | 
            QMessageBox.StandardButton.Discard | 
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        
        if reply == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:
            return False

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        """Обработчик закрытия окна (выход из программы)"""
        if self.check_save_before_action("выходом"):
            if event:
                event.accept()
        else:
            if event:
                event.ignore()
    
    def on_error_clicked(self, row: int, column: int):
        """
        Обработчик клика по ячейке таблицы.
        """
        try:
            code_item = self.output_table.item(row, 0)
            if not code_item or code_item.text() != "-1":
                return
            
            pos_item = self.output_table.item(row, 3)
            if not pos_item:
                return
            
            pos_text = pos_item.text()
            print(f"Нажата ошибка: позиция '{pos_text}'")
            self.debug_line_count()
            
            if ':' in pos_text:
                parts = pos_text.split(':')
                if len(parts) >= 2:
                    try:
                        line = int(parts[0])

                        if '-' in parts[1]:
                            start_pos = int(parts[1].split('-')[0])
                        else:
                            start_pos = int(parts[1])
                        
                        print(f"Переход к строке {line}, позиция {start_pos}")
                        
                        self.navigate_to_error_absolute(line, start_pos)
                        
                    except ValueError as e:
                        print(f"Ошибка преобразования чисел: {e}")
        except Exception as e:
            print(f"Общая ошибка: {e}")

    def navigate_to_error_absolute(self, line: int, position: int):
        """
        Перемещает курсор в редакторе на указанную позицию через абсолютные координаты
        с защитой от выхода за границы
        """
        text = self.editor.toPlainText()
        lines = text.splitlines(True)
        editor_line_count = self.editor.document().blockCount()
        print(f"Строк в редакторе: {editor_line_count}, запрошена строка: {line}")
        
        if line < 1:
            line = 1
        elif line > editor_line_count:
            print(f"Строка {line} вне диапазона. Используем последнюю строку ({editor_line_count})")
            line = editor_line_count
        
        text_lines = text.split('\n')
        
        if line < 1 or line > len(text_lines):
            print(f"Строка {line} вне диапазона text_lines (всего: {len(text_lines)})")
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)
            self.editor.setFocus()
            self.editor.ensureCursorVisible()
            self.status_bar.showMessage(f"Не удалось найти строку {line}, переход в конец")
            return
        
        abs_pos = 0
        for i in range(line - 1):
            abs_pos += len(text_lines[i]) + 1 
        
        max_pos = len(text_lines[line - 1])
        if position > max_pos:
            print(f"Позиция {position} больше длины строки ({max_pos}). Используем {max_pos}")
            position = max_pos
        
        abs_pos += position
        
        print(f"Переход: строка {line}, позиция {position}, абсолютная позиция: {abs_pos}")
        
        cursor = self.editor.textCursor()
        cursor.setPosition(abs_pos)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self.editor.ensureCursorVisible()
        
        self.status_bar.showMessage(f"Переход к ошибке: строка {line}, позиция {position}")

    def debug_line_count(self):
        """Временный метод для отладки количества строк"""
        text = self.editor.toPlainText()
        lines_split = text.split('\n')
        block_count = self.editor.document().blockCount()
        
        print(f"len(split('\\n')): {len(lines_split)}")
        print(f"blockCount(): {block_count}")
        print(f"Всего символов: {len(text)}")
        
        for i, line in enumerate(lines_split):
            print(f"Строка {i+1}: длина {len(line)}, символы: '{line}'")
        
        return block_count

    def new_file(self):
        if not self.check_save_before_action("созданием нового документа"):
            return
    
        self.editor.clear()
        self.current_file = None
        self.is_modified = False
        self.update_window_title()
    
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem("СИСТ"))
        self.output_table.setItem(row, 1, QTableWidgetItem("Система"))
        self.output_table.setItem(row, 2, QTableWidgetItem("Создан новый документ"))
        self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
    
        self.status_bar.showMessage("Новый документ создан")
    
    def open_file(self):
        """Открыть файл"""
        if not self.check_save_before_action("открытием другого файла"):
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                
                self.editor.setText(text)
                self.current_file = file_path
                self.is_modified = False
                self.update_window_title()
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("СИСТ"))
                self.output_table.setItem(row, 1, QTableWidgetItem("Система"))
                self.output_table.setItem(row, 2, QTableWidgetItem(f"Открыт: {os.path.basename(file_path)}"))
                self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
                
                self.status_bar.showMessage(f"Открыт файл: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")

    def save_file(self):
        """Сохранить файл"""
        if self.current_file:
            try:
                text = self.editor.toPlainText()
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(text)
                
                self.is_modified = False
                self.update_window_title()
                
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("СИСТ"))
                self.output_table.setItem(row, 1, QTableWidgetItem("Система"))
                self.output_table.setItem(row, 2, QTableWidgetItem(f"Сохранен: {os.path.basename(self.current_file)}"))
                self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
                
                self.status_bar.showMessage(f"Файл сохранен: {os.path.basename(self.current_file)}")
                return True
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
                return False
        else:
            return self.save_file_as()
        
    def save_file_as(self):
        """Сохранить файл с новым именем"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл как",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            if not file_path.endswith('.txt'):
                file_path += '.txt'
            
            self.current_file = file_path
            return self.save_file()
        
        return False

    def delete_text(self):
        """Удалить выделенный текст"""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
            
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("ПРАВКА"))
            self.output_table.setItem(row, 1, QTableWidgetItem("Система"))
            self.output_table.setItem(row, 2, QTableWidgetItem("Текст удален"))
            self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def create_menu(self):
        """Создание меню"""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        
        new_action = QAction("Создать", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Открыть", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Сохранить как", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)  # close вызовет closeEvent
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Правка")
        
        undo_action = QAction("Отменить", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Повторить", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Вырезать", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Копировать", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Вставить", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        
        delete_action = QAction("Удалить", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_text)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Выделить все", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)

        text_menu = menubar.addMenu("Текст")
        text_menu.addAction("Постановка задачи", lambda: self.show_info("Постановка задачи"))
        text_menu.addAction("Грамматика", lambda: self.show_info("Грамматика"))
        text_menu.addAction("Классификация грамматики", lambda: self.show_info("Классификация грамматики"))
        text_menu.addAction("Метод анализа", lambda: self.show_info("Метод анализа"))
        text_menu.addAction("Тестовый пример", lambda: self.show_info("Тестовый пример"))
        text_menu.addAction("Список литературы", lambda: self.show_info("Список литературы"))
        text_menu.addAction("Исходный код программы", lambda: self.show_info("Исходный код программы"))

        start_menu = menubar.addMenu("Пуск")
        start_action = QAction("Запустить синтаксический анализ", self)
        start_action.triggered.connect(self.run_parser)
        start_menu.addAction(start_action)

        help_menu = menubar.addMenu("Справка")
        help_action = QAction("Вызов справки", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Создание панели инструментов с иконками"""
        toolbar = QToolBar("Панель инструментов")
        toolbar.setIconSize(QtCore.QSize(24, 24))  # Размер иконок
        self.addToolBar(toolbar)

        new_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        new_action = QAction(new_icon, "Создать", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)

        open_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        open_action = QAction(open_icon, "Открыть", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
    
        save_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        save_action = QAction(save_icon, "Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
    
        toolbar.addSeparator()
    
        undo_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        undo_action = QAction(undo_icon, "Отменить", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.editor.undo)
        toolbar.addAction(undo_action)

        redo_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        redo_action = QAction(redo_icon, "Повторить", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.editor.redo)
        toolbar.addAction(redo_action)
    
        toolbar.addSeparator()

        copy_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon) 
        copy_action = QAction(copy_icon, "Копировать", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.editor.copy)
        toolbar.addAction(copy_action)
    
        cut_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon) 
        cut_action = QAction(cut_icon, "Вырезать", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.editor.cut)
        toolbar.addAction(cut_action)
    
        paste_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart) 
        paste_action = QAction(paste_icon, "Вставить", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.editor.paste)
        toolbar.addAction(paste_action)
    
        toolbar.addSeparator()

        run_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        run_action = QAction(run_icon, "Запуск анализа", self)
        run_action.triggered.connect(self.run_parser)
        toolbar.addAction(run_action)
    
        toolbar.addSeparator()

        help_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton)
        help_action = QAction(help_icon, "Справка", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

        info_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        info_action = QAction(info_icon, "О программе", self)
        info_action.triggered.connect(self.show_about)
        toolbar.addAction(info_action)

        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

    def show_info(self, item_name):
        """Показать информацию в области вывода"""
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem("ИНФО"))
        self.output_table.setItem(row, 1, QTableWidgetItem("Информация"))
        self.output_table.setItem(row, 2, QTableWidgetItem(f"=== {item_name} ==="))
        self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def run_parser(self):
        """Запуск лексического анализатора"""
        text = self.editor.toPlainText()
        
        if not text.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите текст для анализа")
            return
        
        try:
            tokens, error_messages = analyze_text(text)
            
            self.output_table.setRowCount(0)
            
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("Код"))
            self.output_table.setItem(row, 1, QTableWidgetItem("Тип"))
            self.output_table.setItem(row, 2, QTableWidgetItem("Лексема"))
            self.output_table.setItem(row, 3, QTableWidgetItem("Позиция"))
            
            current_line = 1
            line_tokens = []
            
            valid_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
            
            for token in valid_tokens:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)

                code_item = QTableWidgetItem(str(token.code))
                self.output_table.setItem(row, 0, code_item)
                
                type_name = {
                    TokenType.KEYWORD: "Ключевое слово",
                    TokenType.IDENTIFIER: "Идентификатор",
                    TokenType.OPERATOR: "Оператор",
                    TokenType.PIPE: "Разделитель |",
                    TokenType.SEPARATOR: "Разделитель ;",
                    TokenType.ERROR: "ОШИБКА"
                }.get(token.type, token.type.name)
                type_item = QTableWidgetItem(type_name)
                self.output_table.setItem(row, 1, type_item)
                
                value_item = QTableWidgetItem(token.value)
                self.output_table.setItem(row, 2, value_item)

                pos_text = f"{token.line}:{token.start_pos}-{token.end_pos}"
                pos_item = QTableWidgetItem(pos_text)
                self.output_table.setItem(row, 3, pos_item)
                
                if token.type == TokenType.ERROR:
                    for col in range(4):
                        item = self.output_table.item(row, col)
                        if item:
                            item.setBackground(Qt.GlobalColor.red)
                            item.setForeground(Qt.GlobalColor.white)
            
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("---"))

            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            error_count = len([t for t in valid_tokens if t.type == TokenType.ERROR])
            self.output_table.setItem(row, 2, QTableWidgetItem(f"Всего лексем: {len(valid_tokens)}, Ошибок: {error_count}"))
            
            self.output_table.resizeColumnsToContents()
            
            if error_count > 0:
                QMessageBox.warning(self, "Ошибки анализа", f"Обнаружено {error_count} ошибок")
                self.status_bar.showMessage(f"Анализ завершен: {len(valid_tokens)} лексем, {error_count} ошибок")
            else:
                QMessageBox.information(self, "Анализ завершен", f"Успешно распознано {len(valid_tokens)} лексем")
                self.status_bar.showMessage(f"Анализ завершен: {len(valid_tokens)} лексем, ошибок нет")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при анализе:\n{str(e)}")
    
    def show_help(self):
        """Показать справку"""
        help_text = """
        РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ
        
        Файл: Создание, открытие, сохранение файлов
        Правка: Редактирование текста
        Текст: Информация о лабораторной работе
        Пуск: Запуск лексического анализатора
        Справка: Информация о программе
        
        Горячие клавиши:
        Ctrl+N - Создать
        Ctrl+O - Открыть
        Ctrl+S - Сохранить
        Ctrl+Z - Отменить
        Ctrl+Y - Повторить
        Ctrl+X - Вырезать
        Ctrl+C - Копировать
        Ctrl+V - Вставить
        Ctrl+A - Выделить все
        """
        
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem("СПРАВКА"))
        self.output_table.setItem(row, 1, QTableWidgetItem(""))
        self.output_table.setItem(row, 2, QTableWidgetItem(help_text))
        self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
        QMessageBox.information(self, "Справка", help_text)
    
    def show_about(self):
        """Информация о программе"""
        about_text = """
        <h3>Текстовый редактор с языковым процессором</h3>
        <p><b>Версия:</b> 2.0</p>
        <p><b>Автор:</b> Студентка 3 курса</p>
        <p><b>Год:</b> 2025</p>
        <p>Вариант 72: Объявление перечисления на языке F#</p>
        """
        
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem("О ПРОГРАММЕ"))
        self.output_table.setItem(row, 1, QTableWidgetItem(""))
        self.output_table.setItem(row, 2, QTableWidgetItem("Информация о программе"))
        self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
        QMessageBox.about(self, "О программе", about_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextEditor()
    window.show()
    sys.exit(app.exec())
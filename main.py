import sys
import os
import re  # ДОБАВИТЬ
from datetime import datetime
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QToolBar, QStatusBar, QMessageBox, QFileDialog,
    QSplitter, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QGroupBox, QHeaderView,
    QStyle, QLineEdit  # ДОБАВИТЬ QLineEdit
)
from PyQt6.QtGui import QAction, QCloseEvent, QTextCursor, QFont, QKeySequence, QTextCharFormat, QColor
from PyQt6.QtCore import Qt
from typing import Optional

from scanner import analyze_text, TokenType
from parser import Parser, EnumDeclarationNode
from searcher import QuoteSearcher, QuoteMatch, SearchType  # ДОБАВИТЬ SearchType


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_modified = False
        self.searcher = QuoteSearcher()
        self.current_matches = []
        self.current_highlighted_match = None
        self._updating = False  # ДОБАВИТЬ флаг защиты от рекурсии
        
        # Инициализируем атрибуты для таблиц
        self.output_table = None
        self.results_table = None
        
        self.init_ui()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editor.textChanged.connect(self.on_text_changed)

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Новый документ - Текстовый редактор")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Создаем вертикальный сплиттер
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Верхняя часть: редактор и панель поиска
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Панель поиска (ОБНОВЛЕНА)
        search_panel = self.create_search_panel()
        top_layout.addWidget(search_panel)
        
        # Редактор текста
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 11))
        top_layout.addWidget(self.editor)
        
        main_splitter.addWidget(top_widget)
        
        # Нижняя часть: таблица результатов поиска (ОБНОВЛЕНА)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)  # ИЗМЕНЕНО: 3 колонки вместо 4
        self.results_table.setHorizontalHeaderLabels([
            "Найденная подстрока", 
            "Начальная позиция", 
            "Длина"
        ])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.cellClicked.connect(self.on_result_clicked)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        main_splitter.addWidget(self.results_table)
        
        # Создаем третий виджет для таблицы вывода парсера
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица для вывода результатов парсинга
        self.output_table = QTableWidget()
        self.output_table.setColumnCount(4)
        self.output_table.setHorizontalHeaderLabels(["Код", "Тип лексемы", "Лексема", "Местоположение"])
        self.output_table.setAlternatingRowColors(True)
        self.output_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.output_table.cellClicked.connect(self.on_error_clicked)
        bottom_layout.addWidget(self.output_table)
        
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([500, 150, 150])
        main_layout.addWidget(main_splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        self.create_menu()
        self.create_toolbar()
        self.update_window_title()

    def create_search_panel(self) -> QGroupBox:
        """Создание панели поиска с выбором типа"""
        search_group = QGroupBox("Поиск подстрок")
        layout = QHBoxLayout()
        
        # Метка
        self.search_label = QLabel("Тип поиска:")
        layout.addWidget(self.search_label)
        
        # ВЫПАДАЮЩИЙ СПИСОК ДЛЯ ВЫБОРА ТИПА ПОИСКА
        self.search_type_combo = QComboBox()
        search_types = self.searcher.get_search_types_list()
        for search_type, type_name in search_types:
            self.search_type_combo.addItem(type_name, search_type)
        self.search_type_combo.setMinimumWidth(250)
        self.search_type_combo.currentIndexChanged.connect(self.on_search_type_changed)
        layout.addWidget(self.search_type_combo)
        
        # Поле для пользовательского шаблона (изначально скрыто)
        self.custom_pattern_edit = QLineEdit()
        self.custom_pattern_edit.setPlaceholderText("Введите регулярное выражение...")
        self.custom_pattern_edit.setVisible(False)
        self.custom_pattern_edit.setMinimumWidth(200)
        layout.addWidget(self.custom_pattern_edit)
        
        # Кнопка применения пользовательского шаблона
        self.apply_custom_btn = QPushButton("Применить")
        self.apply_custom_btn.setVisible(False)
        self.apply_custom_btn.clicked.connect(self.apply_custom_pattern)
        layout.addWidget(self.apply_custom_btn)
        
        # Кнопка запуска поиска
        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search_quotes)
        self.search_button.setMinimumWidth(80)
        layout.addWidget(self.search_button)
        
        # Кнопка автоматного поиска
        self.automaton_button = QPushButton("Автоматный поиск комментариев")
        self.automaton_button.clicked.connect(self.search_comments_automaton)
        self.automaton_button.setMinimumWidth(180)
        self.automaton_button.setToolTip("Поиск комментариев C++ с использованием конечного автомата")
        layout.addWidget(self.automaton_button)
    
        # Кнопка трассировки автомата
        self.trace_button = QPushButton("Трассировка")
        self.trace_button.clicked.connect(self.show_automaton_trace)
        self.trace_button.setMinimumWidth(100)
        self.trace_button.setToolTip("Показать трассировку работы конечного автомата (пошаговый разбор)")
        layout.addWidget(self.trace_button)

        # Кнопка очистки результатов
        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.clear_results)
        layout.addWidget(self.clear_button)
        
        # Метка для отображения количества найденных совпадений
        self.count_label = QLabel("Найдено: 0")
        self.count_label.setStyleSheet("QLabel { font-weight: bold; color: #2c3e50; }")
        layout.addWidget(self.count_label)
        self.info_label = QLabel("💡 Поддерживаются: комментарии C++, MAC-адреса, цитаты, числа, слова | 🔍 Автоматный поиск комментариев C++")
        self.info_label.setStyleSheet("QLabel { color: #7f8c8d; font-size: 10pt; }")
        layout.addWidget(self.info_label)
        layout.addStretch()
        search_group.setLayout(layout)
        
        return search_group

    def on_search_type_changed(self, index: int):
        """Обработчик изменения типа поиска"""
        search_type = self.search_type_combo.currentData()
        
        # Показываем поле для пользовательского шаблона только при выборе CUSTOM
        is_custom = (search_type == SearchType.CUSTOM)
        self.custom_pattern_edit.setVisible(is_custom)
        self.apply_custom_btn.setVisible(is_custom)
        
        # Устанавливаем тип поиска в searcher
        self.searcher.set_search_type(search_type)
        
        # Если не пользовательский шаблон, очищаем поле
        if not is_custom:
            self.custom_pattern_edit.clear()
        
        # Обновляем статус
        if is_custom:
            self.custom_pattern_edit.setFocus()
            self.status_bar.showMessage("Введите регулярное выражение и нажмите 'Применить'")
        else:
            self.status_bar.showMessage(f"Выбран тип поиска: {self.search_type_combo.currentText()}")

    def apply_custom_pattern(self):
        """Применение пользовательского шаблона"""
        pattern = self.custom_pattern_edit.text().strip()
        
        if not pattern:
            QMessageBox.warning(self, "Предупреждение", "Введите регулярное выражение")
            return
        
        # Проверяем корректность шаблона
        if self.searcher.validate_pattern(pattern):
            self.searcher.set_custom_pattern(pattern)
            self.status_bar.showMessage(f"Пользовательский шаблон применен: {pattern}")
            QMessageBox.information(self, "Успешно", "Пользовательский шаблон успешно применен")
        else:
            QMessageBox.critical(self, "Ошибка", f"Неверное регулярное выражение:\n{pattern}")

    def search_quotes(self):
        """Поиск подстрок в тексте с учетом выбранного типа"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            text = self.editor.toPlainText()
            
            if not text.strip():
                QMessageBox.warning(self, "Предупреждение", "Введите текст для поиска")
                return
            
            # Для пользовательского шаблона проверяем, что он установлен
            if self.search_type_combo.currentData() == SearchType.CUSTOM:
                pattern = self.searcher.get_pattern()
                if not pattern:
                    QMessageBox.warning(self, "Предупреление", 
                        "Сначала введите и примените пользовательский шаблон")
                    return
            
            # Выполняем поиск
            self.current_matches = self.searcher.find_matches(text)
            
            # Очищаем таблицу
            self.results_table.setRowCount(0)
            
            if not self.current_matches:
                self.count_label.setText("Найдено: 0")
                QMessageBox.information(self, "Результаты поиска", "Совпадения не найдены")
                self.status_bar.showMessage("Совпадения не найдены")
                return
            
            # Заполняем таблицу результатов
            for row, match in enumerate(self.current_matches):
                self.results_table.insertRow(row)
                
                # Найденная подстрока
                self.results_table.setItem(row, 0, QTableWidgetItem(match.text))
                # Начальная позиция (номер строки, номер символа)
                position_text = f"строка {match.line}, символ {match.start_pos}"
                self.results_table.setItem(row, 1, QTableWidgetItem(position_text))
                # Длина
                self.results_table.setItem(row, 2, QTableWidgetItem(str(match.length)))
            
            # Обновляем счетчик
            self.count_label.setText(f"Найдено: {len(self.current_matches)}")
            
            # Добавляем запись в лог
            if self.output_table:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("ПОИСК"))
                self.output_table.setItem(row, 1, QTableWidgetItem("Информация"))
                self.output_table.setItem(row, 2, QTableWidgetItem(
                    f"Найдено совпадений: {len(self.current_matches)} (тип: {self.search_type_combo.currentText()})"
                ))
                self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
            
            self.status_bar.showMessage(f"Найдено совпадений: {len(self.current_matches)}")
            
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка регулярного выражения", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске:\n{str(e)}")
        finally:
            self._updating = False
    
    def clear_results(self):
        """Очистка результатов поиска"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            self.results_table.setRowCount(0)
            self.current_matches = []
            self.count_label.setText("Найдено: 0")
            self.clear_highlight()
            self.status_bar.showMessage("Результаты поиска очищены")
            
            # Добавляем запись в лог
            if self.output_table:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("ПОИСК"))
                self.output_table.setItem(row, 1, QTableWidgetItem("Информация"))
                self.output_table.setItem(row, 2, QTableWidgetItem("Результаты поиска очищены"))
                self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        finally:
            self._updating = False
    
    def on_result_clicked(self, row: int, column: int):
        """Обработчик клика по строке в таблице результатов"""
        if self._updating:
            return
        
        try:
            if row >= len(self.current_matches):
                return
            
            match = self.current_matches[row]
            self.highlight_quote(match)
            
            # Добавляем запись в лог
            if self.output_table:
                row_idx = self.output_table.rowCount()
                self.output_table.insertRow(row_idx)
                self.output_table.setItem(row_idx, 0, QTableWidgetItem("ПОИСК"))
                self.output_table.setItem(row_idx, 1, QTableWidgetItem("Навигация"))
                self.output_table.setItem(row_idx, 2, QTableWidgetItem(
                    f"Выбрана подстрока: {match.text} (строка {match.line}, символ {match.start_pos})"
                ))
                self.output_table.setItem(row_idx, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
            
            self.status_bar.showMessage(f"Выделена подстрока: {match.text}")
            
        except Exception as e:
            print(f"Ошибка при выборе результата: {e}")
    
    def highlight_quote(self, match: QuoteMatch):
        """Подсвечивает подстроку в редакторе"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            # Сохраняем текущий курсор
            cursor = self.editor.textCursor()
            
            # Устанавливаем позицию курсора на начало подстроки
            cursor.setPosition(match.absolute_pos)
            
            # Выделяем текст подстроки
            cursor.setPosition(match.absolute_pos + match.length, QTextCursor.MoveMode.KeepAnchor)
            
            # Устанавливаем формат выделения
            format = QTextCharFormat()
            format.setBackground(QColor(255, 255, 0, 100))  # Полупрозрачный желтый фон
            format.setForeground(QColor(0, 0, 0))  # Черный текст
            
            cursor.mergeCharFormat(format)
            
            # Устанавливаем курсор и прокручиваем к выделенному тексту
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
            
            # Запоминаем текущее выделенное совпадение
            self.current_highlighted_match = match
        finally:
            self._updating = False
    
    def clear_highlight(self):
        """Очищает подсветку всех подстрок"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            # Создаем курсор для всего текста
            cursor = self.editor.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            
            # Сбрасываем формат для всего текста
            format = QTextCharFormat()
            format.setBackground(QColor(255, 255, 255))  # Белый фон
            format.setForeground(QColor(0, 0, 0))  # Черный текст
            
            cursor.mergeCharFormat(format)
            
            # Сбрасываем текущее выделение
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)
            
            self.current_highlighted_match = None
        finally:
            self._updating = False
    
    def on_text_changed(self):
        """Обработчик изменения текста"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            if not self.is_modified:
                self.is_modified = True
                self.update_window_title()
                self.status_bar.showMessage("✎ Изменено")
            
            # При изменении текста очищаем подсветку
            self.clear_highlight()
        finally:
            self._updating = False
    
    # Остальные методы остаются без изменений
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
        
        # Очищаем результаты поиска
        self.clear_results()
    
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
                
                # Очищаем результаты поиска
                self.clear_results()
                
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
        exit_action.triggered.connect(self.close)
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

        # Добавляем меню поиска
        search_menu = menubar.addMenu("Поиск")
        
        search_action = QAction("Найти цитаты", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.search_quotes)
        search_menu.addAction(search_action)
        
        clear_action = QAction("Очистить результаты", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        clear_action.triggered.connect(self.clear_results)
        search_menu.addAction(clear_action)
        
        search_menu.addSeparator()
        
        count_action = QAction("Показать количество цитат", self)
        count_action.triggered.connect(self.show_quote_count)
        search_menu.addAction(count_action)

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

    def show_quote_count(self):
        """Показать количество цитат в текущем тексте"""
        text = self.editor.toPlainText()
        count = self.searcher.get_match_count(text)
        QMessageBox.information(self, "Количество цитат", f"В тексте найдено цитат: {count}")

    def create_toolbar(self):
        """Создание панели инструментов с иконками"""
        toolbar = QToolBar("Панель инструментов")
        toolbar.setIconSize(QtCore.QSize(24, 24))
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

        # Добавляем кнопку поиска на панель инструментов
        search_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        search_action = QAction(search_icon, "Поиск цитат", self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.search_quotes)
        toolbar.addAction(search_action)

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
        """Запуск лексического и синтаксического анализатора"""
        text = self.editor.toPlainText()
        
        if not text.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите текст для анализа")
            return
        
        try:
            # 1. ЛЕКСИЧЕСКИЙ АНАЛИЗ
            tokens, lex_errors = analyze_text(text)
            
            # 2. СИНТАКСИЧЕСКИЙ АНАЛИЗ
            parser = Parser(tokens)
            ast, syntax_errors = parser.parse()
            
            # 3. ОЧИЩАЕМ ТАБЛИЦУ
            self.output_table.setRowCount(0)
            
            # 4. ВЫВОДИМ ЗАГОЛОВОК
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("==="))
            self.output_table.setItem(row, 1, QTableWidgetItem("РЕЗУЛЬТАТЫ АНАЛИЗА"))
            self.output_table.setItem(row, 2, QTableWidgetItem(""))
            self.output_table.setItem(row, 3, QTableWidgetItem(""))
            
            # 5. ВЫВОДИМ ЛЕКСЕМЫ
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("ЛЕКСЕМЫ"))
            self.output_table.setItem(row, 1, QTableWidgetItem(""))
            self.output_table.setItem(row, 2, QTableWidgetItem(""))
            self.output_table.setItem(row, 3, QTableWidgetItem(""))
            
            valid_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
            for token in valid_tokens:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                
                type_name = {
                    TokenType.KEYWORD: "KEYWORD",
                    TokenType.IDENTIFIER: "IDENTIFIER",
                    TokenType.OPERATOR: "OPERATOR",
                    TokenType.PIPE: "PIPE",
                    TokenType.SEPARATOR: "SEPARATOR",
                    TokenType.ERROR: "ERROR"
                }.get(token.type, str(token.type))
                
                self.output_table.setItem(row, 0, QTableWidgetItem(str(token.code)))
                self.output_table.setItem(row, 1, QTableWidgetItem(type_name))
                self.output_table.setItem(row, 2, QTableWidgetItem(token.value))
                self.output_table.setItem(row, 3, QTableWidgetItem(f"{token.line}:{token.start_pos}"))
            
            # 6. ВЫВОДИМ AST
            row = self.output_table.rowCount()
            self.output_table.insertRow(row)
            self.output_table.setItem(row, 0, QTableWidgetItem("AST"))
            self.output_table.setItem(row, 1, QTableWidgetItem(""))
            self.output_table.setItem(row, 2, QTableWidgetItem(""))
            self.output_table.setItem(row, 3, QTableWidgetItem(""))
            
            if ast:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("├─"))
                self.output_table.setItem(row, 1, QTableWidgetItem("EnumDeclaration"))
                self.output_table.setItem(row, 2, QTableWidgetItem(f"type_name: {ast.type_name}"))
                self.output_table.setItem(row, 3, QTableWidgetItem(""))
                
                for i, case in enumerate(ast.cases):
                    row = self.output_table.rowCount()
                    self.output_table.insertRow(row)
                    prefix = "└─" if i == len(ast.cases) - 1 else "├─"
                    self.output_table.setItem(row, 0, QTableWidgetItem(f"  {prefix}"))
                    self.output_table.setItem(row, 1, QTableWidgetItem("Case"))
                    self.output_table.setItem(row, 2, QTableWidgetItem(case.name))
                    self.output_table.setItem(row, 3, QTableWidgetItem(""))
            else:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 1, QTableWidgetItem("AST построить не удалось"))
            
            # 7. ВЫВОДИМ ОШИБКИ
            all_errors = lex_errors + syntax_errors
            
            if all_errors:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("ОШИБКИ"))
                self.output_table.setItem(row, 1, QTableWidgetItem(""))
                self.output_table.setItem(row, 2, QTableWidgetItem(""))
                self.output_table.setItem(row, 3, QTableWidgetItem(""))
                
                for error in all_errors:
                    row = self.output_table.rowCount()
                    self.output_table.insertRow(row)
                    self.output_table.setItem(row, 0, QTableWidgetItem("❌"))
                    self.output_table.setItem(row, 1, QTableWidgetItem(""))
                    self.output_table.setItem(row, 2, QTableWidgetItem(error))
                    self.output_table.setItem(row, 3, QTableWidgetItem(""))
                
                QMessageBox.warning(self, "Ошибки анализа", f"Обнаружено {len(all_errors)} ошибок")
                self.status_bar.showMessage(f"Анализ завершен с ошибками: {len(all_errors)}")
            else:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 1, QTableWidgetItem("✅ Анализ выполнен успешно"))
                
                QMessageBox.information(self, "Анализ завершен", 
                    f"Успешно распознано {len(valid_tokens)} лексем\n"
                    f"Построено AST: тип={ast.type_name}, вариантов={len(ast.cases)}")
                self.status_bar.showMessage(f"Анализ завершен: {len(valid_tokens)} лексем, ошибок нет")
            
            self.output_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при анализе:\n{str(e)}")
    
    def show_help(self):
        """Показать справку"""
        help_text = """
        РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ
        
        Файл: Создание, открытие, сохранение файлов
        Правка: Редактирование текста
        Поиск: Поиск подстрок с поддержкой различных типов:
            
        1. Цитаты:
        - В одинарных кавычках: 'текст'
        - В двойных кавычках: "текст"
        - Любые кавычки
    
        2. Комментарии C++:
        - Однострочные: // текст комментария
        - Многострочные: /* текст комментария */
        - Все комментарии вместе
    
        3. MAC-адреса:
        - С разделителями (: или -): 00:1A:2B:3C:4D:5E
        - Без разделителей: 001A2B3C4D5E
        - С точками: 001A.2B3C.4D5E
        - Все форматы вместе
    
        4. Слова с заглавной буквы: Пример Слово
    
        5. Числа: 123, 45.67
    
        6. Пользовательский шаблон: любое регулярное выражение
    
        Текст: Информация о лабораторной работе
        Пуск: Запуск лексического и синтаксического анализатора
        Справка: Информация о программе
        
        Горячие клавиши:
        Ctrl+N - Создать
        Ctrl+O - Открыть
        Ctrl+S - Сохранить
        Ctrl+F - Найти цитаты
        Ctrl+Shift+F - Очистить результаты поиска
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
    
    def search_comments_automaton(self):
        """Поиск комментариев C++ с использованием конечного автомата"""
        if self._updating:
            return
    
        self._updating = True
    
        try:
            text = self.editor.toPlainText()
        
            if not text.strip():
                QMessageBox.warning(self, "Предупреждение", "Введите текст для поиска")
                return
        
            # Выполняем автоматный поиск комментариев
            self.current_matches = self.searcher.find_matches_comments_automaton(text)
        
            # Очищаем таблицу
            self.results_table.setRowCount(0)
        
            if not self.current_matches:
                self.count_label.setText("Найдено: 0")
                QMessageBox.information(self, "Результаты поиска", "Комментарии не найдены")
                self.status_bar.showMessage("Комментарии не найдены")
                return
        
            # Заполняем таблицу результатов
            for row, match in enumerate(self.current_matches):
                self.results_table.insertRow(row)
                self.results_table.setItem(row, 0, QTableWidgetItem(match.text))
                position_text = f"строка {match.line}, символ {match.start_pos}"
                self.results_table.setItem(row, 1, QTableWidgetItem(position_text))
                self.results_table.setItem(row, 2, QTableWidgetItem(str(match.length)))
        
            self.count_label.setText(f"Найдено: {len(self.current_matches)}")
        
            # Логирование
            if self.output_table:
                row = self.output_table.rowCount()
                self.output_table.insertRow(row)
                self.output_table.setItem(row, 0, QTableWidgetItem("АВТОМАТ"))
                self.output_table.setItem(row, 1, QTableWidgetItem("Конечный автомат"))
                self.output_table.setItem(row, 2, QTableWidgetItem(
                    f"Найдено комментариев C++: {len(self.current_matches)}"
                ))
                self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
            self.status_bar.showMessage(f"Автоматный поиск: найдено {len(self.current_matches)} комментариев")
        
            # Показываем трассировку в таблице
            self.show_automaton_trace(text[:200])  # Показываем трассировку первых 200 символов
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске:\n{str(e)}")
        finally:
            self._updating = False


    def show_automaton_trace(self):
        """Показать трассировку работы автомата"""
        text = self.editor.toPlainText()
    
        if not text.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите текст для трассировки")
            return
    
    # Получаем трассировку
        trace = self.searcher.trace_automaton_search(text[:100])  # Ограничим 100 символами
    
    # Формируем текст для вывода
        trace_text = "ТРАССИРОВКА РАБОТЫ АВТОМАТА\n"
        trace_text += "="*60 + "\n"
        trace_text += f"{'Поз.':<6} {'Символ':<8} {'Переход':<20} {'Событие'}\n"
        trace_text += "-"*60 + "\n"
    
        for step in trace:
            char = repr(step['char'])[1:-1] if step['char'] != '\n' else '\\n'
            trans = f"{step['old_state']} → {step['new_state']}"
            event = ""
            if step['is_quote_start']:
                event = "🔵 НАЧАЛО ЦИТАТЫ"
            elif step['is_quote_end']:
                event = "🟢 КОНЕЦ ЦИТАТЫ"
        
            trace_text += f"{step['position']:<6} {char:<8} {trans:<20} {event}\n"
    
        trace_text += "="*60 + "\n"
    
    # Выводим в таблицу
        row = self.output_table.rowCount()
        self.output_table.insertRow(row)
        self.output_table.setItem(row, 0, QTableWidgetItem("ТРАССИРОВКА"))
        self.output_table.setItem(row, 1, QTableWidgetItem("Автомат"))
        self.output_table.setItem(row, 2, QTableWidgetItem(trace_text))
        self.output_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
    
        QMessageBox.information(self, "Трассировка автомата", 
            "Трассировка добавлена в таблицу результатов\n\n"
            "Легенда:\n"
            "🔵 - начало цитаты (открывающая кавычка)\n"
            "🟢 - конец цитаты (закрывающая кавычка)\n"
            "START → IN_QUOTE - переход в режим чтения цитаты\n"
            "IN_QUOTE → QUOTE_END - завершение цитаты")

    def show_about(self):
        """Информация о программе"""
        about_text = """
        <h3>Текстовый редактор с языковым процессором</h3>
        <p><b>Версия:</b> 3.0</p>
        <p><b>Автор:</b> Студентка 3 курса</p>
        <p><b>Год:</b> 2025</p>
        <p>Вариант 72: Объявление перечисления на языке F#</p>
        <p><b>Дополнительно:</b> Поиск цитат в одинарных кавычках</p>
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
import sys
import os
from datetime import datetime
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QMenuBar, QToolBar, QStatusBar, QMessageBox, QFileDialog,
    QSplitter
)
from PyQt6.QtGui import QAction, QFont, QKeySequence, QCloseEvent
from PyQt6.QtCore import Qt
from typing import Optional
from PyQt6.QtWidgets import QStyle
from PyQt6.QtCore import Qt, QSize


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_modified = False  # Флаг: были ли изменения после последнего сохранения
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Новый документ - Текстовый редактор")
        self.setGeometry(100, 100, 1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout(central_widget)

        # Сплиттер для областей
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Область редактирования
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 11))
        splitter.addWidget(self.editor)

        # Область вывода (read-only)
        self.output_area = QTextEdit()
        self.output_area.setFont(QFont("Courier New", 11))
        self.output_area.setReadOnly(True)
        self.output_area.setPlaceholderText("Результаты работы языкового процессора будут здесь...")
        splitter.addWidget(self.output_area)

        splitter.setSizes([600, 200])
        main_layout.addWidget(splitter)

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        # Создание меню и панели инструментов
        self.create_menu()
        self.create_toolbar()

        # Обновление заголовка окна
        self.update_window_title()

    def connect_signals(self):
        """Подключение сигналов для отслеживания изменений"""
        # Сигнал изменения текста в редакторе
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
        
        # Добавляем звездочку, если есть несохраненные изменения
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
            return True  # Нет несохраненных изменений
        
        # Спрашиваем пользователя
        reply = QMessageBox.question(
            self,
            "Несохраненные изменения",
            f"Документ был изменен. Сохранить изменения перед {action_name}?",
            QMessageBox.StandardButton.Save | 
            QMessageBox.StandardButton.Discard | 
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save  # Кнопка по умолчанию
        )
        
        if reply == QMessageBox.StandardButton.Save:
            # Сохраняем файл
            return self.save_file()
        elif reply == QMessageBox.StandardButton.Discard:
            # Не сохраняем, просто продолжаем
            return True
        else:  # Cancel
            # Отменяем действие
            return False

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        """Обработчик закрытия окна (выход из программы)"""
        if self.check_save_before_action("выходом"):
            if event:
                event.accept()  # Разрешаем закрытие
        else:
            if event:
                event.ignore()  # Отменяем закрытие
    # ==================== РАБОТА С ФАЙЛАМИ ====================

    def new_file(self):
        """Создать новый файл с проверкой сохранения"""
        if not self.check_save_before_action("созданием нового документа"):
            return  # Пользователь отменил создание
        
        self.editor.clear()
        self.current_file = None
        self.is_modified = False
        self.update_window_title()
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_area.append(f"[{timestamp}] [СИСТЕМА] Создан новый документ")
        self.status_bar.showMessage("Новый документ создан")

    def open_file(self):
        """Открыть файл с проверкой сохранения"""
        if not self.check_save_before_action("открытием другого файла"):
            return  # Пользователь отменил открытие
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "examples/",
            "Все поддерживаемые форматы (*.txt *.py *.kotik *.mrk);;"
            "Текстовые файлы (*.txt);;"
            "Все файлы (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                
                self.editor.setText(text)
                self.current_file = file_path
                self.is_modified = False  # 👈 Важно: сбрасываем флаг
                self.update_window_title()
                
                # Вывод информации
                file_name = os.path.basename(file_path)
                line_count = len(text.splitlines())
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.output_area.append(f"\n[{timestamp}] [СИСТЕМА] Загружен файл: {file_name}")
                self.output_area.append(f"[СИСТЕМА] Строк: {line_count}")
                self.output_area.append("─" * 50)
                
                self.status_bar.showMessage(f"Открыт файл: {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")

    def save_file(self):
        """Сохранить файл"""
        if self.current_file:
            try:
                text = self.editor.toPlainText()
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(text)
                
                self.is_modified = False  # 👈 Сбрасываем флаг
                self.update_window_title()
                
                file_name = os.path.basename(self.current_file)
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.output_area.append(f"[{timestamp}] [СИСТЕМА] Сохранен файл: {file_name}")
                self.status_bar.showMessage(f"Файл сохранен: {file_name}")
                
                return True  # Успешно сохранено
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
                return False  # Ошибка сохранения
        else:
            return self.save_file_as()  # Перенаправляем на "Сохранить как"

    def save_file_as(self):
        """Сохранить файл с новым именем"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл как",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            # Добавляем расширение .txt, если не указано
            if not file_path.endswith('.txt'):
                file_path += '.txt'
            
            self.current_file = file_path
            return self.save_file()  # Вызываем обычное сохранение
        
        return False  # Пользователь отменил сохранение

    # ==================== МЕТОДЫ РЕДАКТИРОВАНИЯ ====================

    def delete_text(self):
        """Удалить выделенный текст"""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
            # Флаг is_modified обновится автоматически через сигнал textChanged

    # ==================== ПРОЧИЕ МЕТОДЫ ====================

    def create_menu(self):
        """Создание меню"""
        menubar = self.menuBar()

        # Файл
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

        # Правка
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

        # Текст
        text_menu = menubar.addMenu("Текст")
        text_menu.addAction("Постановка задачи", lambda: self.show_info("Постановка задачи"))
        text_menu.addAction("Грамматика", lambda: self.show_info("Грамматика"))
        text_menu.addAction("Классификация грамматики", lambda: self.show_info("Классификация грамматики"))
        text_menu.addAction("Метод анализа", lambda: self.show_info("Метод анализа"))
        text_menu.addAction("Тестовый пример", lambda: self.show_info("Тестовый пример"))
        text_menu.addAction("Список литературы", lambda: self.show_info("Список литературы"))
        text_menu.addAction("Исходный код программы", lambda: self.show_info("Исходный код программы"))

        # Пуск
        start_menu = menubar.addMenu("Пуск")
        start_action = QAction("Запустить синтаксический анализ", self)
        start_action.triggered.connect(self.run_parser)
        start_menu.addAction(start_action)

        # Справка
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
    
        # 1. Создать
        new_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        new_action = QAction(new_icon, "Создать", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
    
        # 2. Открыть
        open_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        open_action = QAction(open_icon, "Открыть", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
    
        # 3. Сохранить
        save_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        save_action = QAction(save_icon, "Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
    
        toolbar.addSeparator()
    
        # 4. Отменить
        undo_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        undo_action = QAction(undo_icon, "Отменить", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.editor.undo)
        toolbar.addAction(undo_action)
    
        # 5. Повторить
        redo_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        redo_action = QAction(redo_icon, "Повторить", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.editor.redo)
        toolbar.addAction(redo_action)
    
        toolbar.addSeparator()
    
        # 6. Копировать
        copy_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)  # Заменим на свою
        copy_action = QAction(copy_icon, "Копировать", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.editor.copy)
        toolbar.addAction(copy_action)
    
        # 7. Вырезать
        cut_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)  # Заменим на свою
        cut_action = QAction(cut_icon, "Вырезать", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.editor.cut)
        toolbar.addAction(cut_action)
    
        # 8. Вставить
        paste_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart)  # Заменим
        paste_action = QAction(paste_icon, "Вставить", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.editor.paste)
        toolbar.addAction(paste_action)
    
        toolbar.addSeparator()
    
        # 9. Запуск анализа
        run_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        run_action = QAction(run_icon, "Запуск анализа", self)
        run_action.triggered.connect(self.run_parser)
        toolbar.addAction(run_action)
    
        toolbar.addSeparator()
    
        # 10. Справка
        help_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton)
        help_action = QAction(help_icon, "Справка", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
    
        # 11. О программе
        info_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        info_action = QAction(info_icon, "О программе", self)
        info_action.triggered.connect(self.show_about)
        toolbar.addAction(info_action)
    
        # Добавляем всплывающие подсказки
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

    def show_info(self, item_name):
        """Показать информацию в области вывода"""
        info_text = f"===== {item_name} =====\n"
        info_text += "Этот раздел будет заполнен в рамках лабораторной работы.\n"
        self.output_area.append(info_text)

    def run_parser(self):
        """Запуск анализатора"""
        text = self.editor.toPlainText()
        if not text.strip():
            self.output_area.append("[ПАРСЕР] Ошибка: Нет текста для анализа!")
            return
        
        char_count = len(text)
        word_count = len(text.split())
        line_count = len(text.split('\n'))
        
        result = f"""
[РЕЗУЛЬТАТ АНАЛИЗА]
Символов: {char_count}
Слов: {word_count}
Строк: {line_count}
        """
        self.output_area.append(result)
        self.status_bar.showMessage("Анализ завершен")

    def show_help(self):
        """Показать справку"""
        QMessageBox.information(self, "Справка", "Руководство пользователя...")

    def show_about(self):
        """О программе"""
        QMessageBox.about(self, "О программе", 
            "<h3>Текстовый редактор с языковым процессором</h3>"
            "<p>Версия 2.0 с автосохранением</p>")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextEditor()
    window.show()
    sys.exit(app.exec())
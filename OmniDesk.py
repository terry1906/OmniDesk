import sys
import os
import json
import csv
import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTextEdit, QFileDialog,
    QToolBar, QFontComboBox, QComboBox, QLabel, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtCore import Qt, QTimer

#############################################
# 1. Список дел (TodoTab) с архивированием, восстановлением из архива,
#    экспортом в CSV и историей изменений
#############################################
class TodoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.file_path = "tasks.json"          # файл для активных задач
        self.archive_path = "tasks_archive.json"  # файл для архивированных задач
        self.history_path = "tasks_history.json"  # файл для истории изменений
        self.initUI()
        self.loadTasks()

    def initUI(self):
        layout = QVBoxLayout()

        # Ввод новой задачи: текст, приоритет, категория и кнопка добавления
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Введите новую задачу")
        input_layout.addWidget(self.task_input)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Низкий", "Средний", "Высокий"])
        input_layout.addWidget(QLabel("Приоритет:"))
        input_layout.addWidget(self.priority_combo)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Общее", "Работа", "Дом", "Учёба", "Другое"])
        input_layout.addWidget(QLabel("Категория:"))
        input_layout.addWidget(self.category_combo)

        self.add_button = QPushButton("Добавить")
        self.add_button.clicked.connect(self.addTask)
        input_layout.addWidget(self.add_button)
        layout.addLayout(input_layout)

        # Фильтр по категории и приоритету
        filter_layout = QHBoxLayout()
        self.filter_category = QComboBox()
        self.filter_category.addItem("Все категории")
        self.filter_category.addItems(["Общее", "Работа", "Дом", "Учёба", "Другое"])
        self.filter_category.currentTextChanged.connect(self.updateTaskFilter)
        filter_layout.addWidget(QLabel("Фильтр по категории:"))
        filter_layout.addWidget(self.filter_category)

        self.filter_priority = QComboBox()
        self.filter_priority.addItem("Все приоритеты")
        self.filter_priority.addItems(["Низкий", "Средний", "Высокий"])
        self.filter_priority.currentTextChanged.connect(self.updateTaskFilter)
        filter_layout.addWidget(QLabel("Фильтр по приоритету:"))
        filter_layout.addWidget(self.filter_priority)
        layout.addLayout(filter_layout)

        # Список задач
        self.task_list = QListWidget()
        self.task_list.itemChanged.connect(self.onItemChanged)
        layout.addWidget(self.task_list)

        # Кнопки для удаления, архивирования, показа архива, истории и экспорта
        btn_layout = QHBoxLayout()
        self.delete_button = QPushButton("Удалить выполненные")
        self.delete_button.clicked.connect(self.deleteCompletedTasks)
        btn_layout.addWidget(self.delete_button)

        self.archive_button = QPushButton("Архивировать выполненные")
        self.archive_button.clicked.connect(self.archiveCompletedTasks)
        btn_layout.addWidget(self.archive_button)

        self.show_archive_button = QPushButton("Показать архив")
        self.show_archive_button.clicked.connect(self.openArchiveDialog)
        btn_layout.addWidget(self.show_archive_button)

        self.show_history_button = QPushButton("Показать историю")
        self.show_history_button.clicked.connect(self.showHistory)
        btn_layout.addWidget(self.show_history_button)

        self.export_csv_button = QPushButton("Экспорт в CSV")
        self.export_csv_button.clicked.connect(self.exportToCSV)
        btn_layout.addWidget(self.export_csv_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def addTask(self):
        text = self.task_input.text().strip()
        if not text:
            return
        priority = self.priority_combo.currentText()
        category = self.category_combo.currentText()
        timestamp = datetime.datetime.now().isoformat()
        task_data = {
            "text": text,
            "completed": False,
            "priority": priority,
            "category": category,
            "timestamp": timestamp
        }
        item = QListWidgetItem(f"{text} (Приоритет: {priority}, Категория: {category})")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, task_data)
        self.task_list.addItem(item)
        self.task_input.clear()
        self.logHistory("added", task_data)
        self.saveTasks()
        self.updateTaskFilter()

    def onItemChanged(self, item):
        task_data = item.data(Qt.ItemDataRole.UserRole)
        if task_data:
            task_data["completed"] = (item.checkState() == Qt.CheckState.Checked)
            # Обновляем текст, если он изменён
            full_text = item.text()
            if " (Приоритет:" in full_text:
                new_text = full_text.split(" (Приоритет:")[0]
            else:
                new_text = full_text
            task_data["text"] = new_text
            item.setData(Qt.ItemDataRole.UserRole, task_data)
            item.setText(f"{task_data['text']} (Приоритет: {task_data['priority']}, Категория: {task_data['category']})")
            self.logHistory("changed", task_data)
            self.saveTasks()
            self.updateTaskFilter()

    def deleteCompletedTasks(self):
        for index in range(self.task_list.count() - 1, -1, -1):
            item = self.task_list.item(index)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            if task_data and task_data.get("completed"):
                self.task_list.takeItem(index)
        self.saveTasks()

    def archiveCompletedTasks(self):
        archived = []
        for index in range(self.task_list.count() - 1, -1, -1):
            item = self.task_list.item(index)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            if task_data and task_data.get("completed"):
                archived.append(task_data)
                self.logHistory("archived", task_data)
                self.task_list.takeItem(index)
        if os.path.exists(self.archive_path):
            with open(self.archive_path, 'r', encoding='utf-8') as f:
                archive_list = json.load(f)
        else:
            archive_list = []
        archive_list.extend(archived)
        with open(self.archive_path, 'w', encoding='utf-8') as f:
            json.dump(archive_list, f, ensure_ascii=False, indent=4)
        self.saveTasks()

    def openArchiveDialog(self):
        dialog = ArchiveDialog(self.archive_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Восстанавливаем выбранные задачи
            restored_tasks = dialog.getRestoredTasks()
            for task in restored_tasks:
                self.restoreTask(task)
            # Если архив очищен, удаляем файл архива
            if dialog.archiveCleared:
                if os.path.exists(self.archive_path):
                    os.remove(self.archive_path)
        # После закрытия диалога обновляем архив
        remaining = dialog.getRemainingTasks()
        with open(self.archive_path, 'w', encoding='utf-8') as f:
            json.dump(remaining, f, ensure_ascii=False, indent=4)

    def showHistory(self):
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                history_list = json.load(f)
        else:
            history_list = []
        text = ""
        for entry in history_list:
            text += f"{entry['timestamp']}: {entry['action']} – {entry['task']['text']}\n"
        QMessageBox.information(self, "История задач", text if text else "История пуста.")

    def updateTaskFilter(self):
        cat_filter = self.filter_category.currentText()
        prio_filter = self.filter_priority.currentText()
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            show = True
            if task_data:
                if cat_filter != "Все категории" and task_data.get("category") != cat_filter:
                    show = False
                if prio_filter != "Все приоритеты" and task_data.get("priority") != prio_filter:
                    show = False
            item.setHidden(not show)

    def exportToCSV(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Экспорт задач в CSV", "", "CSV Files (*.csv)")
        if file_name:
            with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["text", "completed", "priority", "category", "timestamp"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for i in range(self.task_list.count()):
                    item = self.task_list.item(i)
                    task_data = item.data(Qt.ItemDataRole.UserRole)
                    if task_data:
                        writer.writerow(task_data)
            QMessageBox.information(self, "Экспорт", "Экспорт задач завершен.")

    def saveTasks(self):
        tasks = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            if task_data:
                tasks.append(task_data)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)

    def loadTasks(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            self.task_list.blockSignals(True)
            self.task_list.clear()
            for task in tasks:
                item = QListWidgetItem(f"{task['text']} (Приоритет: {task['priority']}, Категория: {task['category']})")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
                item.setCheckState(Qt.CheckState.Checked if task.get("completed") else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, task)
                self.task_list.addItem(item)
            self.task_list.blockSignals(False)

    def restoreTask(self, task_data):
        # Добавляем восстановленную задачу в активный список
        item = QListWidgetItem(f"{task_data['text']} (Приоритет: {task_data['priority']}, Категория: {task_data['category']})")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
        item.setCheckState(Qt.CheckState.Checked if task_data.get("completed") else Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, task_data)
        self.task_list.addItem(item)
        self.logHistory("restored", task_data)
        self.saveTasks()

    def logHistory(self, action, task):
        entry = {
            "action": action,
            "task": task,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        history.append(entry)
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

#############################################
# Диалог для работы с архивом: позволяет выбрать задачи для восстановления
# и очистить архив
#############################################
class ArchiveDialog(QDialog):
    def __init__(self, archive_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Архив задач")
        self.archive_path = archive_path
        self.restored_tasks = []
        self.archiveCleared = False
        self.initUI()
        self.loadArchive()

    def initUI(self):
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.restore_button = QPushButton("Восстановить выбранные")
        self.restore_button.clicked.connect(self.restoreSelected)
        btn_layout.addWidget(self.restore_button)

        self.clear_button = QPushButton("Очистить архив")
        self.clear_button.clicked.connect(self.clearArchive)
        btn_layout.addWidget(self.clear_button)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def loadArchive(self):
        self.archived_tasks = []
        self.list_widget.clear()
        if os.path.exists(self.archive_path):
            with open(self.archive_path, 'r', encoding='utf-8') as f:
                self.archived_tasks = json.load(f)
            for task in self.archived_tasks:
                item_text = f"{task['text']} (Приоритет: {task['priority']}, Категория: {task['category']})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, task)
                self.list_widget.addItem(item)

    def restoreSelected(self):
        selected_items = self.list_widget.selectedItems()
        for item in selected_items:
            task = item.data(Qt.ItemDataRole.UserRole)
            self.restored_tasks.append(task)
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            self.archived_tasks.remove(task)

    def clearArchive(self):
        reply = QMessageBox.question(self, "Очистить архив", "Вы уверены, что хотите очистить архив?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.archived_tasks = []
            self.list_widget.clear()
            self.archiveCleared = True

    def getRestoredTasks(self):
        return self.restored_tasks

    def getRemainingTasks(self):
        return self.archived_tasks

#############################################
# 2. Текстовый редактор с поддержкой работы с несколькими файлами,
#    форматированием, историей версий и функцией поиска
#############################################
class EditorTab(QWidget):
    def __init__(self, file_path=None, content=""):
        super().__init__()
        self.file_path = file_path
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(content)
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

class MultiFileTextEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.toolbar = QToolBar()

        new_action = QAction("Новый", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.newFile)
        self.toolbar.addAction(new_action)

        open_action = QAction("Открыть", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.openFile)
        self.toolbar.addAction(open_action)

        save_action = QAction("Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.saveFile)
        self.toolbar.addAction(save_action)

        bold_action = QAction("Жирный", self)
        bold_action.setShortcut(QKeySequence("Ctrl+B"))
        bold_action.triggered.connect(self.setBold)
        self.toolbar.addAction(bold_action)

        italic_action = QAction("Курсив", self)
        italic_action.setShortcut(QKeySequence("Ctrl+I"))
        italic_action.triggered.connect(self.setItalic)
        self.toolbar.addAction(italic_action)

        underline_action = QAction("Подчеркнутый", self)
        underline_action.setShortcut(QKeySequence("Ctrl+U"))
        underline_action.triggered.connect(self.setUnderline)
        self.toolbar.addAction(underline_action)

        find_action = QAction("Найти", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self.findText)
        self.toolbar.addAction(find_action)

        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.changeFont)
        self.toolbar.addWidget(self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.size_combo.addItems([str(s) for s in range(8, 30, 2)])
        self.size_combo.currentTextChanged.connect(self.changeFontSize)
        self.toolbar.addWidget(self.size_combo)

        layout.addWidget(self.toolbar)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        # Создаем первую вкладку по умолчанию
        self.newFile()

    def currentEditor(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, EditorTab):
            return current_widget
        return None

    def newFile(self):
        editor = EditorTab()
        index = self.tab_widget.addTab(editor, "Безымянный")
        self.tab_widget.setCurrentIndex(index)

    def openFile(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r', encoding='utf-8') as f:
                content = f.read()
            editor = EditorTab(file_path=file_name, content=content)
            index = self.tab_widget.addTab(editor, os.path.basename(file_name))
            self.tab_widget.setCurrentIndex(index)

    def saveFile(self):
        editor = self.currentEditor()
        if editor:
            if editor.file_path is None:
                file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "Text Files (*.txt);;All Files (*)")
                if file_name:
                    editor.file_path = file_name
                    self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_name))
                else:
                    return
            content = editor.text_edit.toPlainText()
            with open(editor.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.saveVersion(editor.file_path, content)

    def saveVersion(self, file_path, content):
        history_dir = "file_history"
        os.makedirs(history_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.basename(file_path)
        backup_file = os.path.join(history_dir, f"{base}_{timestamp}.txt")
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def changeFont(self, font: QFont):
        editor = self.currentEditor()
        if editor:
            cursor = editor.text_edit.textCursor()
            if not cursor.hasSelection():
                editor.text_edit.selectAll()
            editor.text_edit.setCurrentFont(font)

    def changeFontSize(self, size: str):
        try:
            size_int = int(size)
        except ValueError:
            return
        editor = self.currentEditor()
        if editor:
            editor.text_edit.setFontPointSize(size_int)

    def setBold(self):
        editor = self.currentEditor()
        if editor:
            fmt = editor.text_edit.currentCharFormat()
            weight = QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal
            fmt.setFontWeight(weight)
            editor.text_edit.mergeCurrentCharFormat(fmt)

    def setItalic(self):
        editor = self.currentEditor()
        if editor:
            fmt = editor.text_edit.currentCharFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            editor.text_edit.mergeCurrentCharFormat(fmt)

    def setUnderline(self):
        editor = self.currentEditor()
        if editor:
            fmt = editor.text_edit.currentCharFormat()
            fmt.setFontUnderline(not fmt.fontUnderline())
            editor.text_edit.mergeCurrentCharFormat(fmt)

    def findText(self):
        editor = self.currentEditor()
        if editor:
            text, ok = QInputDialog.getText(self, "Найти", "Введите текст для поиска:")
            if ok and text:
                # Перемещаем курсор в начало документа и ищем текст
                editor.text_edit.moveCursor(editor.text_edit.textCursor().MoveOperation.Start)
                found = editor.text_edit.find(text)
                if not found:
                    QMessageBox.information(self, "Найти", "Текст не найден.")

#############################################
# 3. Органайзер заметок с возможностью создания, редактирования,
#    удаления и добавления заметок из быстрой заметки
#############################################
class NotesOrganizer(QWidget):
    def __init__(self):
        super().__init__()
        self.notes_file = "notes.json"
        self.notes = []  # список заметок (каждая заметка — словарь с ключами "title" и "content")
        self.initUI()
        self.loadNotes()

    def initUI(self):
        layout = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.loadNoteIntoEditor)
        layout.addWidget(self.list_widget, 1)

        editor_layout = QVBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Заголовок заметки")
        self.title_edit.editingFinished.connect(self.updateCurrentNoteTitle)
        editor_layout.addWidget(self.title_edit)
        self.text_edit = QTextEdit()
        self.text_edit.textChanged.connect(self.autoSaveNote)
        editor_layout.addWidget(self.text_edit, 1)

        btn_layout = QHBoxLayout()
        self.new_note_button = QPushButton("Новая заметка")
        self.new_note_button.clicked.connect(self.newNote)
        btn_layout.addWidget(self.new_note_button)
        self.delete_note_button = QPushButton("Удалить заметку")
        self.delete_note_button.clicked.connect(self.deleteNote)
        btn_layout.addWidget(self.delete_note_button)
        editor_layout.addLayout(btn_layout)

        layout.addLayout(editor_layout, 2)
        self.setLayout(layout)

        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(1000)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.saveNotes)

    def newNote(self):
        new_note = {"title": "Без названия", "content": ""}
        self.notes.append(new_note)
        self.list_widget.addItem(new_note["title"])
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        self.loadNoteIntoEditor(self.list_widget.currentItem())
        self.saveNotes()

    def deleteNote(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.notes.pop(row)
            self.list_widget.takeItem(row)
            self.clearEditor()
            self.saveNotes()

    def loadNoteIntoEditor(self, item):
        row = self.list_widget.row(item)
        if 0 <= row < len(self.notes):
            note = self.notes[row]
            self.title_edit.setText(note["title"])
            self.text_edit.blockSignals(True)
            self.text_edit.setPlainText(note["content"])
            self.text_edit.blockSignals(False)

    def updateCurrentNoteTitle(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.notes):
            new_title = self.title_edit.text()
            self.notes[row]["title"] = new_title
            self.list_widget.currentItem().setText(new_title)
            self.saveNotes()

    def autoSaveNote(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.notes):
            self.notes[row]["content"] = self.text_edit.toPlainText()
        self.autosave_timer.start()

    def clearEditor(self):
        self.title_edit.clear()
        self.text_edit.clear()

    def saveNotes(self):
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=4)

    def loadNotes(self):
        if os.path.exists(self.notes_file):
            with open(self.notes_file, 'r', encoding='utf-8') as f:
                self.notes = json.load(f)
            self.list_widget.clear()
            for note in self.notes:
                self.list_widget.addItem(note["title"])

    def addNoteFromQuick(self, content):
        # Добавляем новую заметку с содержимым из быстрой заметки
        new_note = {"title": "Быстрая заметка", "content": content}
        self.notes.append(new_note)
        self.list_widget.addItem(new_note["title"])
        self.saveNotes()
        QMessageBox.information(self, "Заметки", "Быстрая заметка добавлена в заметки.")

#############################################
# 4. Быстрая заметка – окно, позволяющее быстро набрать текст и сохранить его
#    в органайзере заметок (через переданный callback)
#############################################
class QuickNoteWidget(QDialog):
    def __init__(self, save_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Быстрая заметка")
        self.resize(300, 200)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить в заметках")
        self.save_button.clicked.connect(self.saveNote)
        btn_layout.addWidget(self.save_button)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)
        self.save_callback = save_callback

    def saveNote(self):
        content = self.text_edit.toPlainText().strip()
        if content:
            self.save_callback(content)
        self.accept()

#############################################
# 5. Настройки – диалог для изменения параметров приложения
#############################################
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.settings_file = "settings.json"
        self.initUI()
        self.loadSettings()

    def initUI(self):
        layout = QFormLayout()
        self.autosave_interval_edit = QLineEdit()
        layout.addRow("Интервал автосохранения (мс):", self.autosave_interval_edit)
        self.default_save_path_edit = QLineEdit()
        layout.addRow("Путь сохранения файлов:", self.default_save_path_edit)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Русский", "English"])
        layout.addRow("Язык интерфейса:", self.language_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

    def loadSettings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            self.autosave_interval_edit.setText(str(settings.get("autosave_interval", 1000)))
            self.default_save_path_edit.setText(settings.get("default_save_path", ""))
            lang = settings.get("language", "Русский")
            index = self.language_combo.findText(lang)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
        else:
            self.autosave_interval_edit.setText("1000")
            self.default_save_path_edit.setText("")
            self.language_combo.setCurrentIndex(0)

    def getSettings(self):
        return {
            "autosave_interval": int(self.autosave_interval_edit.text()),
            "default_save_path": self.default_save_path_edit.text(),
            "language": self.language_combo.currentText()
        }

    def accept(self):
        settings = self.getSettings()
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        super().accept()

#############################################
# 6. Главное окно – объединяет все режимы, без переключения тем,
#    с переупорядоченными вкладками: «Заметки», «Список дел», «Текстовый редактор»
#############################################
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Объединенное приложение")
        self.resize(1000, 700)
        self.initUI()
        self.quick_note_widget = None

    def initUI(self):
        self.tab_widget = QTabWidget()
        # Изменён порядок вкладок: сначала Заметки, затем Список дел и Текстовый редактор
        self.notes_organizer = NotesOrganizer()
        self.todo_tab = TodoTab()
        self.text_editor = MultiFileTextEditor()

        self.tab_widget.addTab(self.notes_organizer, "Заметки")
        self.tab_widget.addTab(self.todo_tab, "Список дел")
        self.tab_widget.addTab(self.text_editor, "Текстовый редактор")

        self.setCentralWidget(self.tab_widget)
        self.createMenu()

    def createMenu(self):
        menubar = self.menuBar()
        # Удаляем меню для смены темы
        settings_menu = menubar.addMenu("Настройки")
        settings_action = QAction("Открыть настройки", self)
        settings_action.triggered.connect(self.openSettings)
        settings_menu.addAction(settings_action)

        sync_menu = menubar.addMenu("Синхронизация")
        sync_action = QAction("Синхронизировать данные", self)
        sync_action.triggered.connect(self.syncData)
        sync_menu.addAction(sync_action)

        quick_menu = menubar.addMenu("Быстрая заметка")
        quick_action = QAction("Открыть быструю заметку", self)
        quick_action.triggered.connect(self.openQuickNote)
        quick_menu.addAction(quick_action)

    def openSettings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.getSettings()
            self.notes_organizer.autosave_timer.setInterval(settings.get("autosave_interval", 1000))

    def syncData(self):
        QMessageBox.information(self, "Синхронизация", "Синхронизация данных завершена.")

    def openQuickNote(self):
        if self.quick_note_widget is None:
            # Передаем callback для добавления заметки в NotesOrganizer
            self.quick_note_widget = QuickNoteWidget(self.notes_organizer.addNoteFromQuick, self)
        self.quick_note_widget.show()
        self.quick_note_widget.raise_()
        self.quick_note_widget.activateWindow()

def main():
    app = QApplication(sys.argv)
    # Применяем стиль Fusion
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

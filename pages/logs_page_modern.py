"""
Страница системных логов
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QScrollArea, QFrame, QLineEdit,
    QComboBox, QMessageBox, QDialog, QTextEdit,
    QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QClipboard
from .base_page_modern import BasePage
import datetime
import win32evtlog
import win32evtlogutil
import win32security
import win32api
import traceback


class LogsWorker(QThread):
    """Поток для получения логов Windows"""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, log_type='All', max_count=300, filter_text=''):
        super().__init__()
        self.log_type = log_type
        self.max_count = max_count
        self.filter_text = filter_text
        self._is_running = True

    def run(self):
        try:
            logs = []

            # Определяем какие журналы читать
            if self.log_type == 'All':
                log_types = ['Application', 'System', 'Security', 'Setup']
            else:
                log_types = [self.log_type]

            for log_type in log_types:
                if not self._is_running:
                    break

                try:
                    log_handle = win32evtlog.OpenEventLog(None, log_type)

                    # Читаем события
                    events = win32evtlog.ReadEventLog(
                        log_handle,
                        win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
                        0
                    )

                    for event in events:
                        if not self._is_running:
                            break

                        # Получаем информацию о событии
                        time_generated = event.TimeGenerated
                        if hasattr(time_generated, 'Format'):
                            time_str = time_generated.Format()
                        else:
                            time_str = str(time_generated)

                        # Определяем тип события
                        event_type = self._get_event_type(event.EventType)

                        # Получаем имя источника
                        source = event.SourceName or 'Unknown'

                        # Получаем описание события
                        try:
                            message = win32evtlogutil.SafeFormatMessage(event, log_handle)
                        except:
                            message = 'Описание события недоступно'

                        log_entry = {
                            'time': time_str,
                            'type': event_type,
                            'source': source,
                            'event_id': event.EventID,
                            'message': message,
                            'log_type': log_type,
                            'raw': event
                        }

                        # Применяем фильтр если задан
                        if self.filter_text:
                            if (self.filter_text.lower() not in source.lower() and
                                    self.filter_text.lower() not in message.lower() and
                                    self.filter_text not in str(event.EventID)):
                                continue

                        logs.append(log_entry)

                        if len(logs) >= self.max_count:
                            break

                    win32evtlog.CloseEventLog(log_handle)

                except Exception as e:
                    # Пропускаем журналы к которым нет доступа
                    continue

            # Сортируем по времени (сначала новые)
            logs.sort(key=lambda x: x['time'], reverse=True)

            self.finished.emit(logs[:self.max_count])

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

    @staticmethod
    def _get_event_type(event_type):
        """Преобразует тип события в читаемый вид"""
        types = {
            1: 'Ошибка',
            2: 'Предупреждение',
            3: 'Информация',
            4: 'Аудит успеха',
            5: 'Аудит отказа'
        }
        return types.get(event_type, f'Тип {event_type}')


class LogDetailsDialog(QDialog):
    """Диалог с  описанием лога"""

    def __init__(self, log_entry, parent=None):
        super().__init__(parent)
        self.log_entry = log_entry
        self.setWindowTitle("Детали события")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("""
            QDialog {
                background: #0a0e17;
            }
            QLabel {
                color: #8b9eb0;
                background: transparent;
                border: none;
            }
            QTextEdit {
                background: rgba(13, 17, 23, 0.3);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
            }
            QPushButton {
                background: rgba(74, 158, 255, 0.08);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.15);
                color: #e8edf3;
            }
            QTabWidget::pane {
                background: transparent;
                border: none;
            }
            QTabBar::tab {
                background: transparent;
                color: #6b7d95;
                padding: 8px 16px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                color: #e8edf3;
                border-bottom: 2px solid #4a9eff;
            }
            QTabBar::tab:hover {
                color: #8b9eb0;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # --- ЗАГОЛОВОК ---
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Тип и цвет
        type_colors = {
            'Ошибка': '#da3633',
            'Предупреждение': '#f0883e',
            'Информация': '#3fb950',
            'Аудит успеха': '#3fb950',
            'Аудит отказа': '#da3633'
        }
        color = type_colors.get(self.log_entry['type'], '#8b9eb0')

        type_label = QLabel(self.log_entry['type'])
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        header_layout.addWidget(type_label)

        header_layout.addStretch()

        # Журнал
        log_label = QLabel(f"Журнал: {self.log_entry['log_type']}")
        log_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(log_label)

        layout.addWidget(header)

        # --- ТАБЫ ---
        tabs = QTabWidget()

        # Вкладка "Общие"
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(0, 8, 0, 0)
        general_layout.setSpacing(12)

        # Информация
        info_grid = QWidget()
        info_grid_layout = QVBoxLayout(info_grid)
        info_grid_layout.setContentsMargins(0, 0, 0, 0)
        info_grid_layout.setSpacing(8)

        info_items = [
            ("Дата и время:", self.log_entry['time']),
            ("Источник:", self.log_entry['source']),
            ("Код события:", str(self.log_entry['event_id'])),
            ("Журнал:", self.log_entry['log_type']),
            ("Тип:", self.log_entry['type']),
        ]

        for label, value in info_items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 2, 0, 2)

            label_widget = QLabel(label)
            label_widget.setFixedWidth(120)
            label_widget.setStyleSheet("color: #6b7d95; font-size: 12px; background: transparent; border: none;")
            item_layout.addWidget(label_widget)

            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #8b9eb0; font-size: 12px; background: transparent; border: none;")
            value_widget.setWordWrap(True)
            item_layout.addWidget(value_widget, stretch=1)

            info_grid_layout.addWidget(item_widget)

        general_layout.addWidget(info_grid)

        # Сообщение
        msg_label = QLabel("Сообщение:")
        msg_label.setStyleSheet(
            "color: #6b7d95; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        general_layout.addWidget(msg_label)

        msg_text = QTextEdit()
        msg_text.setPlainText(self.log_entry['message'])
        msg_text.setReadOnly(True)
        msg_text.setMinimumHeight(150)
        general_layout.addWidget(msg_text)

        tabs.addTab(general_tab, "Общие")

        # Вкладка "Подробно"
        detailed_tab = QWidget()
        detailed_layout = QVBoxLayout(detailed_tab)
        detailed_layout.setContentsMargins(0, 8, 0, 0)

        detailed_text = QTextEdit()
        detailed_text.setReadOnly(True)
        detailed_text.setFont(QFont("Consolas", 11))

        # Собираем всю доступную информацию
        details = []
        details.append("=" * 60)
        details.append("ПОЛНАЯ ИНФОРМАЦИЯ О СОБЫТИИ")
        details.append("=" * 60)
        details.append("")
        details.append(f"Дата и время: {self.log_entry['time']}")
        details.append(f"Источник: {self.log_entry['source']}")
        details.append(f"Код события: {self.log_entry['event_id']}")
        details.append(f"Журнал: {self.log_entry['log_type']}")
        details.append(f"Тип: {self.log_entry['type']}")
        details.append("")
        details.append("-" * 60)
        details.append("ПОЛНОЕ СООБЩЕНИЕ:")
        details.append("-" * 60)
        details.append(self.log_entry['message'])

        # Добавляем информацию из raw события если доступна
        try:
            raw = self.log_entry.get('raw')
            if raw:
                details.append("")
                details.append("-" * 60)
                details.append("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
                details.append("-" * 60)
                if hasattr(raw, 'EventID'):
                    details.append(f"Event ID: {raw.EventID}")
                if hasattr(raw, 'EventType'):
                    details.append(f"Event Type: {raw.EventType}")
                if hasattr(raw, 'Category'):
                    details.append(f"Category: {raw.Category}")
                if hasattr(raw, 'NumStrings'):
                    details.append(f"String Count: {raw.NumStrings}")
        except:
            pass

        detailed_text.setPlainText("\n".join(details))
        detailed_layout.addWidget(detailed_text)

        tabs.addTab(detailed_tab, "Подробно")

        layout.addWidget(tabs, stretch=1)

        # --- КНОПКИ ---
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        # Кнопка копирования
        copy_btn = QPushButton("📋 Копировать")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        buttons_layout.addWidget(copy_btn)

        buttons_layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        buttons_layout.addWidget(close_btn)

        layout.addWidget(buttons)

    def copy_to_clipboard(self):
        """Копирует информацию в буфер обмена"""
        text = f"""
=== Событие ===
Дата и время: {self.log_entry['time']}
Источник: {self.log_entry['source']}
Код события: {self.log_entry['event_id']}
Журнал: {self.log_entry['log_type']}
Тип: {self.log_entry['type']}

Сообщение:
{self.log_entry['message']}
"""
        clipboard = QClipboard()
        clipboard.setText(text.strip())

        # Показываем уведомление
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Успешно")
        msg.setText("Информация скопирована в буфер обмена")
        msg.setStyleSheet("""
            QMessageBox {
                background: #0a0e17;
                color: #8b9eb0;
            }
            QLabel {
                color: #8b9eb0;
            }
            QPushButton {
                background: rgba(74, 158, 255, 0.08);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.15);
                color: #e8edf3;
            }
        """)
        msg.exec()


class LogsPage(BasePage):
    def __init__(self):
        super().__init__(
            "Системные журналы",
            "Просмотр и управление системными событиями"
        )

        self.worker = None
        self.logs = []
        self.filtered_logs = []
        self.current_log_type = 'All'

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # Выбор типа лога
        log_type_label = QLabel("Журнал:")
        log_type_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        controls_layout.addWidget(log_type_label)

        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems([
            'Все',
            'Application',
            'System',
            'Security',
            'Setup',
            'ForwardedEvents'
        ])
        self.log_type_combo.setFixedWidth(140)
        self.log_type_combo.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 400;
            }
            QComboBox:hover {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6b7d95;
            }
            QComboBox QAbstractItemView {
                background: #161b22;
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.2);
                selection-background-color: rgba(74, 158, 255, 0.1);
            }
        """)
        self.log_type_combo.currentTextChanged.connect(self.on_log_type_changed)
        controls_layout.addWidget(self.log_type_combo)

        controls_layout.addSpacing(20)

        # Количество записей
        count_label = QLabel("Записей:")
        count_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        controls_layout.addWidget(count_label)

        self.count_combo = QComboBox()
        self.count_combo.addItems(['100', '200', '300', '500', '1000'])
        self.count_combo.setCurrentText('300')
        self.count_combo.setFixedWidth(70)
        self.count_combo.setStyleSheet(self.log_type_combo.styleSheet())
        self.count_combo.currentTextChanged.connect(self.load_logs)
        controls_layout.addWidget(self.count_combo)

        controls_layout.addSpacing(20)

        # Кнопка обновления
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
                border-color: rgba(74, 158, 255, 0.15);
            }
        """)
        self.btn_refresh.clicked.connect(self.load_logs)
        controls_layout.addWidget(self.btn_refresh)

        controls_layout.addStretch()

        # Поиск
        search_label = QLabel("Поиск:")
        search_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        controls_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по источнику, ID или сообщению...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 400;
            }
            QLineEdit:focus {
                border-color: rgba(74, 158, 255, 0.2);
                background: rgba(13, 17, 23, 0.3);
            }
            QLineEdit::placeholder {
                color: #4a5a6a;
            }
        """)
        self.search_input.textChanged.connect(self.apply_filter)
        controls_layout.addWidget(self.search_input)

        self.content_layout.addWidget(controls)

        # --- ФИЛЬТРЫ ПО ТИПУ СОБЫТИЙ ---
        filter_widget = QWidget()
        filter_widget.setStyleSheet("background: transparent;")
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 6, 0, 0)
        filter_layout.setSpacing(6)

        filter_types = [
            ("Все", ""),
            ("Ошибки", "#da3633"),
            ("Предупреждения", "#f0883e"),
            ("Информация", "#3fb950"),
        ]

        self.filter_buttons = []
        for text, color in filter_types:
            btn = QPushButton(text)
            btn.setProperty('filter_type', text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #6b7d95;
                    border: 1px solid rgba(48, 54, 61, 0.08);
                    border-radius: 13px;
                    padding: 0 14px;
                    font-size: 11px;
                    font-weight: 400;
                }}
                QPushButton:hover {{
                    background: rgba(74, 158, 255, 0.045);
                    color: #e8edf3;
                }}
                QPushButton:checked {{
                    background: rgba(74, 158, 255, 0.06);
                    color: {color if color else '#8b9eb0'};
                    border-color: {color if color else 'rgba(48, 54, 61, 0.15)'};
                }}
            """)
            btn.setCheckable(True)
            if text == "Все":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=text: self.on_filter_type_changed(t))
            filter_layout.addWidget(btn)
            self.filter_buttons.append(btn)

        filter_layout.addStretch()

        # Кнопка экспорта
        btn_export = QPushButton("Экспортировать")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setFixedHeight(26)
        btn_export.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.08);
                border-radius: 6px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
            }
        """)
        btn_export.clicked.connect(self.export_logs)
        filter_layout.addWidget(btn_export)

        self.content_layout.addWidget(filter_widget)

        # --- ОБЛАСТЬ ЛОГОВ ---
        self.logs_area = QScrollArea()
        self.logs_area.setWidgetResizable(True)
        self.logs_area.setFrameShape(QScrollArea.NoFrame)
        self.logs_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(48, 54, 61, 0.15);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(74, 158, 255, 0.15);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.logs_container = QWidget()
        self.logs_container.setStyleSheet("background: transparent; border: none;")
        self.logs_layout = QVBoxLayout(self.logs_container)
        self.logs_layout.setContentsMargins(0, 8, 0, 8)
        self.logs_layout.setSpacing(2)

        self.logs_area.setWidget(self.logs_container)
        self.content_layout.addWidget(self.logs_area, stretch=1)

        # --- СТАТУСНАЯ ПАНЕЛЬ ---
        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer.setFixedHeight(30)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 4, 0, 0)

        self.status_label = QLabel("Загрузка логов...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.logs_count_label = QLabel("0 записей")
        self.logs_count_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        footer_layout.addWidget(self.logs_count_label)

        self.content_layout.addWidget(footer)

        # --- ТАЙМЕР АВТООБНОВЛЕНИЯ ---
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.load_logs)
        self.update_timer.start(15000)  # Обновление каждые 15 секунд

        # Загружаем логи
        self.load_logs()

    def on_log_type_changed(self, log_type):
        """Обработка смены типа лога"""
        if log_type == 'Все':
            self.current_log_type = 'All'
        else:
            self.current_log_type = log_type
        self.load_logs()

    def on_filter_type_changed(self, filter_type):
        """Обработка смены фильтра по типу"""
        for btn in self.filter_buttons:
            if btn.property('filter_type') == filter_type:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        self.apply_filter()

    def load_logs(self):
        """Загружает логи в отдельном потоке"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.btn_refresh.setText("Загрузка...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Загрузка логов...")
        self.clear_logs()

        max_count = int(self.count_combo.currentText())

        self.worker = LogsWorker(
            log_type=self.current_log_type,
            max_count=max_count,
            filter_text=self.search_input.text()
        )
        self.worker.finished.connect(self.on_logs_loaded)
        self.worker.error.connect(self.on_logs_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_logs_loaded(self, logs):
        """Обработка загруженных логов"""
        self.logs = logs
        self.apply_filter()

        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Загружено {len(logs)} записей")
        self.logs_count_label.setText(f"{len(self.filtered_logs)} записей")

    def on_logs_error(self, error):
        """Обработка ошибки загрузки"""
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Ошибка: {error}")

        if "Security" in str(error):
            self.show_error_message(
                "Доступ к журналу безопасности ограничен.\n"
                "Для просмотра системных логов запустите приложение от имени администратора."
            )

    def on_progress(self, count):
        """Обновление прогресса загрузки"""
        self.status_label.setText(f"Загрузка логов... {count}")

    def clear_logs(self):
        """Очищает область логов"""
        while self.logs_layout.count():
            child = self.logs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def apply_filter(self):
        """Применяет фильтры к логам"""
        selected_type = None
        for btn in self.filter_buttons:
            if btn.isChecked():
                type_text = btn.property('filter_type')
                if type_text != "Все":
                    selected_type = type_text
                break

        if selected_type:
            self.filtered_logs = [log for log in self.logs if log['type'] == selected_type]
        else:
            self.filtered_logs = self.logs.copy()

        self.display_logs()
        self.logs_count_label.setText(f"{len(self.filtered_logs)} записей")

    def display_logs(self):
        """Отображает логи в списке"""
        self.clear_logs()

        if not self.filtered_logs:
            empty_label = QLabel("Нет записей для отображения")
            empty_label.setStyleSheet("""
                QLabel {
                    color: #3a4a5a;
                    font-size: 13px;
                    font-weight: 300;
                    background: transparent;
                    border: none;
                    padding: 40px 0;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            self.logs_layout.addWidget(empty_label)
            return

        for log in self.filtered_logs:
            # Определяем цвет в зависимости от типа
            if log['type'] == 'Ошибка':
                color = '#da3633'
            elif log['type'] == 'Предупреждение':
                color = '#f0883e'
            else:
                color = '#3fb950'

            # Строка лога
            row = QFrame()
            row.setObjectName("logRow")
            row.setCursor(Qt.PointingHandCursor)
            row.setStyleSheet(f"""
                QFrame#logRow {{
                    background: transparent;
                    border: none;
                    border-left: 3px solid {color};
                    border-radius: 0;
                    padding: 0;
                }}
                QFrame#logRow:hover {{
                    background: rgba(74, 158, 255, 0.04);
                }}
            """)

            # Клик для открытия деталей
            row.mousePressEvent = lambda e, l=log: self.show_log_details(l)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            row_layout.setSpacing(12)

            # Время
            time_label = QLabel(log['time'])
            time_label.setFixedWidth(160)
            time_label.setStyleSheet("""
                QLabel {
                    color: #6b7d95;
                    font-size: 11px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
            """)
            row_layout.addWidget(time_label)

            # Тип события
            type_label = QLabel(log['type'])
            type_label.setFixedWidth(120)
            type_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 11px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }}
            """)
            row_layout.addWidget(type_label)

            # Источник
            source_label = QLabel(log['source'])
            source_label.setFixedWidth(150)
            source_label.setStyleSheet("""
                QLabel {
                    color: #8b9eb0;
                    font-size: 11px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
            """)
            row_layout.addWidget(source_label)

            # ID события
            event_id_label = QLabel(str(log['event_id']))
            event_id_label.setFixedWidth(60)
            event_id_label.setStyleSheet("""
                QLabel {
                    color: #6b7d95;
                    font-size: 11px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
            """)
            row_layout.addWidget(event_id_label)

            # Журнал
            log_type_label = QLabel(log['log_type'])
            log_type_label.setFixedWidth(100)
            log_type_label.setStyleSheet("""
                QLabel {
                    color: #4a5a6a;
                    font-size: 10px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
            """)
            row_layout.addWidget(log_type_label)

            # Сообщение
            message = log['message'][:150] + '...' if len(log['message']) > 150 else log['message']
            message_label = QLabel(message)
            message_label.setStyleSheet("""
                QLabel {
                    color: #8b9eb0;
                    font-size: 11px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }
            """)
            message_label.setWordWrap(True)
            row_layout.addWidget(message_label, stretch=1)

            # Иконка "подробнее"
            detail_icon = QLabel("›")
            detail_icon.setFixedWidth(20)
            detail_icon.setStyleSheet("""
                QLabel {
                    color: #4a5a6a;
                    font-size: 16px;
                    font-weight: 300;
                    background: transparent;
                    border: none;
                }
            """)
            row_layout.addWidget(detail_icon)

            self.logs_layout.addWidget(row)

    def show_log_details(self, log_entry):
        """Показывает диалог с деталями лога"""
        dialog = LogDetailsDialog(log_entry, self)
        dialog.exec()

    def export_logs(self):
        """Экспортирует логи в файл"""
        if not self.filtered_logs:
            QMessageBox.information(self, "Информация", "Нет данных для экспорта")
            return

        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить логи",
            f"logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Текстовый файл (*.txt)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("СИСТЕМНЫЕ ЛОГИ\n")
                f.write("=" * 80 + "\n")
                f.write(f"Экспортировано: {datetime.datetime.now()}\n")
                f.write(f"Всего записей: {len(self.filtered_logs)}\n")
                f.write(f"Журнал: {self.current_log_type}\n")
                f.write("=" * 80 + "\n\n")

                for log in self.filtered_logs:
                    f.write(f"[{log['time']}] {log['type']}\n")
                    f.write(f"  Источник: {log['source']}\n")
                    f.write(f"  ID: {log['event_id']}\n")
                    f.write(f"  Журнал: {log['log_type']}\n")
                    f.write(f"  Сообщение: {log['message']}\n")
                    f.write("-" * 40 + "\n")

            QMessageBox.information(
                self,
                "Успешно",
                f"Логи экспортированы в:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать логи:\n{str(e)}")

    def show_error_message(self, message):
        """Показывает сообщение об ошибке"""
        error_widget = QWidget()
        error_widget.setStyleSheet("background: transparent;")
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)

        error_label = QLabel(message)
        error_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 13px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 40px 20px;
            }
        """)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)

        self.clear_logs()
        self.logs_layout.addWidget(error_widget)

    def on_show(self):
        """Страница показана - обновляем"""
        self.load_logs()

    def closeEvent(self, event):
        """Закрытие страницы"""
        self.update_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()
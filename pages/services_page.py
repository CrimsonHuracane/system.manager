"""
Страница управления службами Windows
Просмотр, запуск, остановка, перезапуск служб
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from .base_page_modern import BasePage
import win32service
import time


class ServicesWorker(QThread):
    """Поток для получения списка служб"""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        try:
            services = []

            scm_handle = win32service.OpenSCManager(
                None,
                None,
                win32service.SC_MANAGER_ENUMERATE_SERVICE | win32service.SC_MANAGER_CONNECT
            )

            try:
                service_statuses = win32service.EnumServicesStatus(
                    scm_handle,
                    win32service.SERVICE_WIN32,
                    win32service.SERVICE_STATE_ALL
                )
            except:
                service_statuses = win32service.EnumServicesStatus(
                    scm_handle,
                    win32service.SERVICE_WIN32,
                    win32service.SERVICE_ACTIVE | win32service.SERVICE_INACTIVE
                )

            for i, service_status in enumerate(service_statuses):
                if not self._is_running:
                    break

                try:
                    name = service_status[0]
                    display_name = service_status[1]
                    status = service_status[2][1]

                    try:
                        service_handle = win32service.OpenService(
                            scm_handle,
                            name,
                            win32service.SERVICE_QUERY_CONFIG
                        )
                        config = win32service.QueryServiceConfig(service_handle)
                        start_type = config[1]
                        win32service.CloseServiceHandle(service_handle)
                    except:
                        start_type = 0

                    services.append({
                        'name': name,
                        'display_name': display_name,
                        'status': status,
                        'status_text': self._get_status_text(status),
                        'start_type': start_type,
                        'start_type_text': self._get_start_type_text(start_type),
                    })

                except:
                    continue

                self.progress.emit(i + 1)

            win32service.CloseServiceHandle(scm_handle)
            services.sort(key=lambda x: x['display_name'].lower())

            self.finished.emit(services)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

    @staticmethod
    def _get_status_text(status):
        status_map = {
            win32service.SERVICE_STOPPED: 'Остановлена',
            win32service.SERVICE_START_PENDING: 'Запускается',
            win32service.SERVICE_STOP_PENDING: 'Останавливается',
            win32service.SERVICE_RUNNING: 'Работает',
            win32service.SERVICE_CONTINUE_PENDING: 'Продолжается',
            win32service.SERVICE_PAUSE_PENDING: 'Приостанавливается',
            win32service.SERVICE_PAUSED: 'Приостановлена',
        }
        return status_map.get(status, 'Неизвестно')

    @staticmethod
    def _get_start_type_text(start_type):
        type_map = {
            win32service.SERVICE_AUTO_START: 'Авто',
            win32service.SERVICE_BOOT_START: 'Загрузка',
            win32service.SERVICE_DEMAND_START: 'Вручную',
            win32service.SERVICE_DISABLED: 'Отключена',
            win32service.SERVICE_SYSTEM_START: 'Системная',
        }
        return type_map.get(start_type, 'Неизвестно')


class ServiceActionWorker(QThread):
    """Поток для выполнения действий со службой"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, service_name, action):
        super().__init__()
        self.service_name = service_name
        self.action = action
        self._is_running = True

    def run(self):
        try:
            scm_handle = win32service.OpenSCManager(
                None,
                None,
                win32service.SC_MANAGER_ALL_ACCESS
            )

            service_handle = win32service.OpenService(
                scm_handle,
                self.service_name,
                win32service.SERVICE_START | win32service.SERVICE_STOP | win32service.SERVICE_QUERY_STATUS
            )

            if self.action == 'start':
                win32service.StartService(service_handle, None)
                time.sleep(0.5)
                self.finished.emit(f"Служба {self.service_name} запущена")
            elif self.action == 'stop':
                win32service.ControlService(service_handle, win32service.SERVICE_CONTROL_STOP)
                time.sleep(0.5)
                self.finished.emit(f"Служба {self.service_name} остановлена")
            elif self.action == 'restart':
                win32service.ControlService(service_handle, win32service.SERVICE_CONTROL_STOP)
                time.sleep(1)
                win32service.StartService(service_handle, None)
                self.finished.emit(f"Служба {self.service_name} перезапущена")

            win32service.CloseServiceHandle(service_handle)
            win32service.CloseServiceHandle(scm_handle)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


class ServicesPage(BasePage):
    def __init__(self):
        super().__init__(
            "Службы Windows",
            "Управление системными службами"
        )

        self.worker = None
        self.action_worker = None
        self.services = []
        self.filtered_services = []

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        filter_label = QLabel("Фильтр:")
        filter_label.setStyleSheet("color: #6b7d95; font-size: 11px; background: transparent; border: none;")
        controls_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Все', 'Работает', 'Остановлена'])
        self.filter_combo.setFixedWidth(110)
        self.filter_combo.setFixedHeight(26)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 400;
            }
            QComboBox:hover {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QComboBox QAbstractItemView {
                background: #161b22;
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.2);
                selection-background-color: rgba(74, 158, 255, 0.1);
            }
        """)
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        controls_layout.addWidget(self.filter_combo)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(26)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
                border-color: rgba(74, 158, 255, 0.15);
            }
        """)
        self.btn_refresh.clicked.connect(self.load_services)
        controls_layout.addWidget(self.btn_refresh)

        controls_layout.addStretch()

        search_label = QLabel("Поиск:")
        search_label.setStyleSheet("color: #6b7d95; font-size: 11px; background: transparent; border: none;")
        controls_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setFixedWidth(140)
        self.search_input.setFixedHeight(26)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 400;
            }
            QLineEdit:focus {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QLineEdit::placeholder {
                color: #4a5a6a;
            }
        """)
        self.search_input.textChanged.connect(self.apply_filter)
        controls_layout.addWidget(self.search_input)

        self.content_layout.addWidget(controls)

        # --- ТАБЛИЦА СЛУЖБ ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Имя службы", "Отображаемое имя", "Статус", "Тип запуска", "Действия"
        ])

        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(13, 17, 23, 0.06);
                border: 1px solid rgba(48, 54, 61, 0.04);
                border-radius: 6px;
                gridline-color: rgba(48, 54, 61, 0.03);
                selection-background-color: rgba(74, 158, 255, 0.05);
                selection-color: #e8edf3;
            }
            QTableWidget::item {
                background: transparent;
                color: #8b9eb0;
                padding: 2px 4px;
                border: none;
                font-size: 11px;
                font-weight: 400;
            }
            QTableWidget::item:selected {
                background: rgba(74, 158, 255, 0.05);
            }
            QTableWidget::item:hover {
                background: rgba(74, 158, 255, 0.02);
            }
            QHeaderView::section {
                background: rgba(13, 17, 23, 0.15);
                color: #4a5a6a;
                padding: 2px 4px;
                border: none;
                border-bottom: 1px solid rgba(48, 54, 61, 0.04);
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(48, 54, 61, 0.15);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(74, 158, 255, 0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Настройка колонок - делаем колонку действий шире
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 160)  # Увеличена ширина колонки действий

        # Уменьшаем высоту строк
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.verticalHeader().setMinimumSectionSize(22)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.content_layout.addWidget(self.table, stretch=1)

        # --- СТАТУСНАЯ ПАНЕЛЬ ---
        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer.setFixedHeight(22)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Загрузка служб...")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.count_label = QLabel("0 служб")
        self.count_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.count_label)

        self.content_layout.addWidget(footer)

        self.load_services()

    def load_services(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.btn_refresh.setText("Загрузка...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Загрузка служб...")
        self.table.setRowCount(0)

        self.worker = ServicesWorker()
        self.worker.finished.connect(self.on_services_loaded)
        self.worker.error.connect(self.on_services_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_services_loaded(self, services):
        self.services = services
        self.apply_filter()

        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Загружено {len(services)} служб")
        self.count_label.setText(f"{len(self.filtered_services)} служб")

    def on_services_error(self, error):
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Ошибка: {error}")

        QMessageBox.warning(
            self,
            "Ошибка",
            f"Не удалось загрузить службы:\n{error}\n\n"
            "Возможно, требуются права администратора."
        )

    def on_progress(self, count):
        self.status_label.setText(f"Загрузка служб... {count}")

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()

        self.filtered_services = []

        for service in self.services:
            if filter_text != 'Все' and service['status_text'] != filter_text:
                continue

            if search_text:
                if (search_text not in service['name'].lower() and
                        search_text not in service['display_name'].lower()):
                    continue

            self.filtered_services.append(service)

        self.display_services()
        self.count_label.setText(f"{len(self.filtered_services)} служб")

    def display_services(self):
        self.table.setRowCount(len(self.filtered_services))

        for row, service in enumerate(self.filtered_services):
            # Имя службы
            name_item = QTableWidgetItem(service['name'])
            name_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 0, name_item)

            # Отображаемое имя
            display_item = QTableWidgetItem(service['display_name'])
            display_item.setForeground(QColor('#a5b3c2'))
            self.table.setItem(row, 1, display_item)

            # Статус
            status_color = self.get_status_color(service['status'])
            status_item = QTableWidgetItem(service['status_text'])
            status_item.setForeground(QColor(status_color))
            self.table.setItem(row, 2, status_item)

            # Тип запуска
            start_text = service['start_type_text']
            start_item = QTableWidgetItem(start_text)
            start_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 3, start_item)

            # Кнопки действий - теперь они шире
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)

            if service['status'] == win32service.SERVICE_RUNNING:
                btn_stop = self.create_action_button("Остановить", "#da3633")
                btn_stop.clicked.connect(lambda checked, s=service: self.action_service(s, 'stop'))
                actions_layout.addWidget(btn_stop)

                btn_restart = self.create_action_button("Перезапустить", "#f0883e")
                btn_restart.clicked.connect(lambda checked, s=service: self.action_service(s, 'restart'))
                actions_layout.addWidget(btn_restart)
            else:
                btn_start = self.create_action_button("Запустить", "#3fb950")
                btn_start.clicked.connect(lambda checked, s=service: self.action_service(s, 'start'))
                actions_layout.addWidget(btn_start)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 4, actions_widget)

        self.table.verticalHeader().setVisible(False)

    def create_action_button(self, text, color):
        """Создает кнопку действия - шире и лучше видно"""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(20)
        btn.setFixedWidth(70)  # Увеличена ширина кнопки
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color};
                border-radius: 4px;
                padding: 0 4px;
                font-size: 9px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(0, 0, 0, 0.08);
            }}
            QPushButton:pressed {{
                background: rgba(0, 0, 0, 0.15);
            }}
        """)
        return btn

    def get_status_color(self, status):
        if status == win32service.SERVICE_RUNNING:
            return '#3fb950'
        elif status == win32service.SERVICE_STOPPED:
            return '#da3633'
        elif status in [win32service.SERVICE_START_PENDING, win32service.SERVICE_STOP_PENDING]:
            return '#f0883e'
        else:
            return '#6b7d95'

    def action_service(self, service, action):
        try:
            scm_handle = win32service.OpenSCManager(
                None,
                None,
                win32service.SC_MANAGER_CONNECT
            )
            service_handle = win32service.OpenService(
                scm_handle,
                service['name'],
                win32service.SERVICE_QUERY_STATUS | win32service.SERVICE_START | win32service.SERVICE_STOP
            )
            win32service.CloseServiceHandle(service_handle)
            win32service.CloseServiceHandle(scm_handle)
        except:
            QMessageBox.warning(
                self,
                "Ошибка доступа",
                f"Недостаточно прав для управления службой {service['display_name']}.\n"
                "Запустите приложение от имени администратора."
            )
            return

        if action in ['stop', 'restart']:
            action_text = 'остановить' if action == 'stop' else 'перезапустить'
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы уверены, что хотите {action_text} службу\n"
                f"'{service['display_name']}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        if self.action_worker and self.action_worker.isRunning():
            return

        self.status_label.setText(f"Выполняется {action}...")

        self.action_worker = ServiceActionWorker(service['name'], action)
        self.action_worker.finished.connect(self.on_action_finished)
        self.action_worker.error.connect(self.on_action_error)
        self.action_worker.start()

    def on_action_finished(self, message):
        self.status_label.setText(message)
        QMessageBox.information(self, "Успешно", message)
        self.load_services()

    def on_action_error(self, error):
        self.status_label.setText(f"Ошибка: {error}")
        QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить действие:\n{error}")

    def on_show(self):
        self.load_services()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        if self.action_worker and self.action_worker.isRunning():
            self.action_worker.stop()
            self.action_worker.wait()
        event.accept()
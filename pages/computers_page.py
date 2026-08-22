"""
Страница подключенных компьютеров
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from .base_page_modern import BasePage
import socket
import subprocess
import win32net
import time


class ComputersWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, scan_type='network'):
        super().__init__()
        self.scan_type = scan_type
        self._is_running = True

    def run(self):
        try:
            computers = []

            if self.scan_type == 'network':
                computers = self.scan_network()
            else:
                computers = self.scan_ad()

            self.finished.emit(computers)

        except Exception as e:
            self.error.emit(str(e))

    def scan_network(self):
        computers = []
        try:
            server_info = win32net.NetServerEnum(
                None,
                100,
                win32net.SV_TYPE_WORKSTATION | win32net.SV_TYPE_SERVER,
                None,
                None
            )

            for server in server_info[0]:
                if not self._is_running:
                    break

                computer_name = server['name']
                try:
                    ip = socket.gethostbyname(computer_name)
                    status = self.check_computer_status(computer_name)
                    os_info = self.get_computer_os(computer_name)
                    user_count = self.get_active_users(computer_name)
                except:
                    ip = 'Недоступен'
                    status = 'Офлайн'
                    os_info = 'Неизвестно'
                    user_count = 0

                computers.append({
                    'name': computer_name,
                    'ip': ip,
                    'status': status,
                    'os': os_info,
                    'users': user_count,
                    'type': 'Станция'
                })

                self.progress.emit(len(computers))

        except Exception as e:
            computers = self.scan_network_alternative()

        return computers

    def scan_network_alternative(self):
        computers = []
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        ip_parts = local_ip.split('.')
        subnet = '.'.join(ip_parts[:3])

        for i in range(1, 255):
            if not self._is_running:
                break

            ip = f"{subnet}.{i}"
            try:
                # Пинг БЕЗ КОНСОЛИ
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', '300', ip],
                    capture_output=True,
                    text=True,
                    timeout=1,
                    creationflags=subprocess.CREATE_NO_WINDOW  # ⬅️ БЕЗ КОНСОЛИ
                )

                if result.returncode == 0:
                    try:
                        name = socket.gethostbyaddr(ip)[0]
                    except:
                        name = ip

                    computers.append({
                        'name': name,
                        'ip': ip,
                        'status': 'Доступен',
                        'os': 'Неизвестно',
                        'users': 0,
                        'type': 'Станция'
                    })
            except:
                continue

            if len(computers) % 10 == 0:
                self.progress.emit(len(computers))

        return computers

    def scan_ad(self):
        computers = []
        try:
            import win32com.client
            ad = win32com.client.GetObject("LDAP://rootDSE")
            default_naming_context = ad.Get("defaultNamingContext")

            computers_list = ad.ExecQuery(
                f"SELECT name, distinguishedName, operatingSystem "
                f"FROM '{default_naming_context}' WHERE objectClass='computer'"
            )

            for computer in computers_list:
                if not self._is_running:
                    break

                name = computer.Name
                os_info = computer.OperatingSystem if hasattr(computer, 'OperatingSystem') else 'Неизвестно'

                try:
                    ip = socket.gethostbyname(name)
                    status = 'Доступен'
                except:
                    ip = 'Недоступен'
                    status = 'Офлайн'

                computers.append({
                    'name': name,
                    'ip': ip,
                    'status': status,
                    'os': os_info,
                    'users': 0,
                    'type': 'AD',
                })

                self.progress.emit(len(computers))

        except:
            computers = self.scan_network()

        return computers

    def check_computer_status(self, computer_name):
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '-w', '500', computer_name],
                capture_output=True,
                text=True,
                timeout=1,
                creationflags=subprocess.CREATE_NO_WINDOW  # ⬅️ БЕЗ КОНСОЛИ
            )
            if result.returncode == 0:
                return 'Доступен'
            return 'Офлайн'
        except:
            return 'Офлайн'

    def get_computer_os(self, computer_name):
        try:
            import wmi
            c = wmi.WMI(computer=computer_name)
            for os in c.Win32_OperatingSystem():
                return os.Caption
        except:
            return 'Неизвестно'

    def get_active_users(self, computer_name):
        try:
            import wmi
            c = wmi.WMI(computer=computer_name)
            users = c.Win32_ComputerSystem()
            for user in users:
                return user.UserName or 0
            return 0
        except:
            return 0

    def stop(self):
        self._is_running = False


class ComputersPage(BasePage):
    def __init__(self):
        super().__init__(
            "Подключенные компьютеры",
            "Список компьютеров в сети и Active Directory"
        )

        self.worker = None
        self.computers = []
        self.filtered_computers = []

        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        scan_label = QLabel("Сканировать:")
        scan_label.setStyleSheet("color: #6b7d95; font-size: 11px; background: transparent; border: none;")
        controls_layout.addWidget(scan_label)

        self.scan_combo = QComboBox()
        self.scan_combo.addItems(['Сеть', 'Active Directory'])
        self.scan_combo.setFixedWidth(140)
        self.scan_combo.setFixedHeight(26)
        self.scan_combo.setStyleSheet("""
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
        self.scan_combo.currentTextChanged.connect(self.load_computers)
        controls_layout.addWidget(self.scan_combo)

        self.btn_refresh = QPushButton("Сканировать")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(26)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
                border-color: rgba(74, 158, 255, 0.15);
            }
        """)
        self.btn_refresh.clicked.connect(self.load_computers)
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

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Имя компьютера", "IP-адрес", "Статус", "ОС", "Пользователи", "Тип"
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

        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 80)

        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.verticalHeader().setMinimumSectionSize(22)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.content_layout.addWidget(self.table, stretch=1)

        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer.setFixedHeight(22)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Готов к сканированию...")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.count_label = QLabel("0 компьютеров")
        self.count_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.count_label)

        self.content_layout.addWidget(footer)

        self.load_computers()

    def load_computers(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        scan_type = 'ad' if self.scan_combo.currentText() == 'Active Directory' else 'network'

        self.btn_refresh.setText("Сканирование...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Сканирование сети...")
        self.table.setRowCount(0)

        self.worker = ComputersWorker(scan_type)
        self.worker.finished.connect(self.on_computers_loaded)
        self.worker.error.connect(self.on_computers_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_computers_loaded(self, computers):
        self.computers = computers
        self.apply_filter()

        self.btn_refresh.setText("Сканировать")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Найдено {len(computers)} компьютеров")
        self.count_label.setText(f"{len(self.filtered_computers)} компьютеров")

    def on_computers_error(self, error):
        self.btn_refresh.setText("Сканировать")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Ошибка: {error}")

        if 'AD' in str(error) or 'ldap' in str(error).lower():
            self.scan_combo.setCurrentText('Сеть')

    def on_progress(self, count):
        self.status_label.setText(f"Сканирование... Найдено: {count}")

    def apply_filter(self):
        search_text = self.search_input.text().lower()

        if search_text:
            self.filtered_computers = [
                c for c in self.computers
                if search_text in c['name'].lower() or search_text in c['ip'].lower()
            ]
        else:
            self.filtered_computers = self.computers.copy()

        self.display_computers()
        self.count_label.setText(f"{len(self.filtered_computers)} компьютеров")

    def display_computers(self):
        self.table.setRowCount(len(self.filtered_computers))

        for row, computer in enumerate(self.filtered_computers):
            name_item = QTableWidgetItem(computer['name'])
            name_item.setForeground(QColor('#a5b3c2'))
            self.table.setItem(row, 0, name_item)

            ip_item = QTableWidgetItem(computer['ip'])
            ip_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 1, ip_item)

            status_color = '#3fb950' if computer['status'] == 'Доступен' else '#da3633'
            status_item = QTableWidgetItem(computer['status'])
            status_item.setForeground(QColor(status_color))
            self.table.setItem(row, 2, status_item)

            os_item = QTableWidgetItem(computer['os'])
            os_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 3, os_item)

            users_item = QTableWidgetItem(str(computer['users']))
            users_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 4, users_item)

            type_item = QTableWidgetItem(computer['type'])
            type_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 5, type_item)

        self.table.verticalHeader().setVisible(False)

    def on_show(self):
        self.load_computers()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()
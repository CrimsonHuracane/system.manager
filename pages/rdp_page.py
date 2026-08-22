"""
Страница удаленного рабочего стола
Быстрое подключение к компьютерам по RDP
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QMessageBox, QDialog, QFormLayout,
    QCheckBox, QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QColor
from .base_page_modern import BasePage
import subprocess
import os
import socket
import winreg


class RdpPage(BasePage):
    def __init__(self):
        super().__init__(
            "Удаленный рабочий стол",
            "Быстрое подключение к компьютерам по RDP"
        )

        # Сохраненные подключения
        self.saved_connections = []
        self.load_saved_connections()

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # Поле для быстрого подключения
        quick_label = QLabel("Быстрое подключение:")
        quick_label.setStyleSheet("color: #6b7d95; font-size: 11px; background: transparent; border: none;")
        controls_layout.addWidget(quick_label)

        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText("IP или имя компьютера")
        self.quick_input.setFixedWidth(180)
        self.quick_input.setFixedHeight(26)
        self.quick_input.setStyleSheet("""
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
        self.quick_input.returnPressed.connect(self.quick_connect)
        controls_layout.addWidget(self.quick_input)

        self.btn_quick = QPushButton("Подключиться")
        self.btn_quick.setCursor(Qt.PointingHandCursor)
        self.btn_quick.setFixedHeight(26)
        self.btn_quick.setStyleSheet("""
            QPushButton {
                background: rgba(74, 158, 255, 0.15);
                color: #8b9eb0;
                border: 1px solid rgba(74, 158, 255, 0.15);
                border-radius: 5px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.25);
                color: #e8edf3;
                border-color: rgba(74, 158, 255, 0.25);
            }
        """)
        self.btn_quick.clicked.connect(self.quick_connect)
        controls_layout.addWidget(self.btn_quick)

        controls_layout.addStretch()

        # Кнопка добавления
        self.btn_add = QPushButton("+ Добавить подключение")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFixedHeight(26)
        self.btn_add.setStyleSheet("""
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
        self.btn_add.clicked.connect(self.show_add_dialog)
        controls_layout.addWidget(self.btn_add)

        self.content_layout.addWidget(controls)

        # --- ТАБЛИЦА СОХРАНЕННЫХ ПОДКЛЮЧЕНИЙ ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Имя", "Компьютер", "Пользователь", "Порт", "Разрешение", "Действия"
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

        # Настройка колонок
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 200)

        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setMinimumSectionSize(28)

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

        self.status_label = QLabel("Готов к подключению")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.count_label = QLabel("0 подключений")
        self.count_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.count_label)

        self.content_layout.addWidget(footer)

        # Отображаем сохраненные подключения
        self.display_connections()

    def load_saved_connections(self):
        """Загружает сохраненные подключения из реестра"""
        try:
            key_path = r"Software\InfinitySystem\RDPConnections"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)

            i = 0
            while True:
                try:
                    name = winreg.EnumKey(key, i)
                    sub_key = winreg.OpenKey(key, name)

                    connection = {
                        'name': name,
                        'computer': winreg.QueryValueEx(sub_key, 'Computer')[0],
                        'username': winreg.QueryValueEx(sub_key, 'Username')[0],
                        'password': winreg.QueryValueEx(sub_key, 'Password')[0] if self._key_exists(sub_key,
                                                                                                    'Password') else '',
                        'port': winreg.QueryValueEx(sub_key, 'Port')[0] if self._key_exists(sub_key, 'Port') else 3389,
                        'resolution': winreg.QueryValueEx(sub_key, 'Resolution')[0] if self._key_exists(sub_key,
                                                                                                        'Resolution') else 'Полный экран',
                        'save_password': winreg.QueryValueEx(sub_key, 'SavePassword')[0] if self._key_exists(sub_key,
                                                                                                             'SavePassword') else False
                    }

                    self.saved_connections.append(connection)
                    winreg.CloseKey(sub_key)
                    i += 1
                except WindowsError:
                    break

            winreg.CloseKey(key)
        except:
            # Если ключа нет - создаем
            try:
                key_path = r"Software\InfinitySystem\RDPConnections"
                winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            except:
                pass

    def _key_exists(self, key, value_name):
        """Проверяет существование значения в ключе реестра"""
        try:
            winreg.QueryValueEx(key, value_name)
            return True
        except:
            return False

    def save_connection(self, connection):
        """Сохраняет подключение в реестр"""
        try:
            key_path = r"Software\InfinitySystem\RDPConnections"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

            sub_key = winreg.CreateKey(key, connection['name'])

            winreg.SetValueEx(sub_key, 'Computer', 0, winreg.REG_SZ, connection['computer'])
            winreg.SetValueEx(sub_key, 'Username', 0, winreg.REG_SZ, connection['username'])
            winreg.SetValueEx(sub_key, 'Port', 0, winreg.REG_DWORD, connection['port'])
            winreg.SetValueEx(sub_key, 'Resolution', 0, winreg.REG_SZ, connection['resolution'])
            winreg.SetValueEx(sub_key, 'SavePassword', 0, winreg.REG_DWORD, 1 if connection['save_password'] else 0)

            if connection['save_password'] and connection.get('password'):
                winreg.SetValueEx(sub_key, 'Password', 0, winreg.REG_SZ, connection['password'])

            winreg.CloseKey(sub_key)
            winreg.CloseKey(key)

            # Добавляем в список
            self.saved_connections.append(connection)
            self.display_connections()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить подключение:\n{str(e)}")

    def delete_connection(self, name):
        """Удаляет подключение из реестра"""
        try:
            key_path = r"Software\InfinitySystem\RDPConnections"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            # Удаляем ключ
            import winreg
            winreg.DeleteKey(key, name)

            winreg.CloseKey(key)

            # Удаляем из списка
            self.saved_connections = [c for c in self.saved_connections if c['name'] != name]
            self.display_connections()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить подключение:\n{str(e)}")

    def quick_connect(self):
        """Быстрое подключение по IP или имени"""
        computer = self.quick_input.text().strip()
        if not computer:
            QMessageBox.warning(self, "Ошибка", "Введите IP-адрес или имя компьютера")
            return

        # Проверяем доступность
        try:
            socket.gethostbyname(computer)
        except:
            reply = QMessageBox.question(
                self,
                "Внимание",
                f"Компьютер {computer} не найден в сети.\nПопробовать подключиться?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.connect_rdp(computer, None, None, 3389)

    def show_add_dialog(self):
        """Показывает диалог добавления подключения"""
        dialog = AddConnectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            connection = dialog.get_connection()
            self.save_connection(connection)
            self.status_label.setText(f"Подключение '{connection['name']}' сохранено")

    def connect_rdp(self, computer, username=None, password=None, port=3389, resolution='Полный экран'):
        """Подключается к компьютеру по RDP"""
        self.status_label.setText(f"Подключение к {computer}...")

        try:
            # Создаем временный RDP файл
            rdp_content = self.generate_rdp_file(computer, username, password, port, resolution)

            # Сохраняем в временный файл
            import tempfile
            import os

            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.rdp', delete=False)
            temp_file.write(rdp_content)
            temp_file.close()

            # Запускаем mstsc с RDP файлом
            subprocess.Popen(['mstsc', temp_file.name])

            self.status_label.setText(f"Подключение к {computer} запущено")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось подключиться:\n{str(e)}")
            self.status_label.setText(f"Ошибка подключения к {computer}")

    def generate_rdp_file(self, computer, username, password, port, resolution):
        """Генерирует содержимое RDP файла"""
        lines = [
            f"full address:s:{computer}:{port}",
            "prompt for credentials:i:0",
            "authentication level:i:0",
        ]

        if username:
            lines.append(f"username:s:{username}")

        if password:
            lines.append(f"password 51:b:{self.encode_password(password)}")

        # Настройки разрешения
        if resolution == 'Полный экран':
            lines.append("screen mode id:i:1")
            lines.append("use multimon:i:0")
        elif resolution == '1920x1080':
            lines.append("screen mode id:i:0")
            lines.append("desktopwidth:i:1920")
            lines.append("desktopheight:i:1080")
        elif resolution == '1366x768':
            lines.append("screen mode id:i:0")
            lines.append("desktopwidth:i:1366")
            lines.append("desktopheight:i:768")
        elif resolution == '1024x768':
            lines.append("screen mode id:i:0")
            lines.append("desktopwidth:i:1024")
            lines.append("desktopheight:i:768")

        # Общие настройки
        lines.extend([
            "redirectdrives:i:0",
            "redirectprinters:i:0",
            "redirectcomports:i:0",
            "redirectsmartcards:i:0",
            "redirectclipboard:i:1",
            "redirectposdevices:i:0",
            "bitmapcachepersistenable:i:0",
            "audiomode:i:0",
            "enableworkspacereconnect:i:0",
            "disableconnectionsharing:i:1",
            "disablefullwindowdrag:i:1",
            "disablemenu anims:i:1",
            "disable themes:i:1",
            "disable cursor setting:i:1",
            "disable full window drag:i:1",
            "disable menu anims:i:1",
            "disable themes:i:1",
            "disable cursor setting:i:1"
        ])

        return '\n'.join(lines)

    def encode_password(self, password):
        """Кодирует пароль для RDP файла (упрощенная версия)"""
        # В реальности здесь должно быть шифрование, но для простоты оставляем как есть
        # Windows ожидает зашифрованный пароль, но это требует сложного шифрования
        # Поэтому просто возвращаем пустую строку (пользователь введет пароль при подключении)
        return ''

    def display_connections(self):
        """Отображает сохраненные подключения"""
        self.table.setRowCount(len(self.saved_connections))

        for row, conn in enumerate(self.saved_connections):
            # Имя
            name_item = QTableWidgetItem(conn['name'])
            name_item.setForeground(QColor('#a5b3c2'))
            self.table.setItem(row, 0, name_item)

            # Компьютер
            computer_item = QTableWidgetItem(conn['computer'])
            computer_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 1, computer_item)

            # Пользователь
            user_item = QTableWidgetItem(conn['username'] if conn['username'] else 'Не указан')
            user_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 2, user_item)

            # Порт
            port_item = QTableWidgetItem(str(conn['port']))
            port_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 3, port_item)

            # Разрешение
            res_item = QTableWidgetItem(conn['resolution'])
            res_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 4, res_item)

            # Кнопки действий
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(4)

            btn_connect = self.create_action_button("Подключиться", "#3fb950")
            btn_connect.clicked.connect(lambda checked, c=conn: self.connect_rdp(
                c['computer'], c['username'], c.get('password', ''), c['port'], c['resolution']
            ))
            actions_layout.addWidget(btn_connect)

            btn_edit = self.create_action_button("Изменить", "#4a9eff")
            btn_edit.clicked.connect(lambda checked, c=conn: self.edit_connection(c))
            actions_layout.addWidget(btn_edit)

            btn_delete = self.create_action_button("Удалить", "#da3633")
            btn_delete.clicked.connect(lambda checked, c=conn: self.delete_connection(c['name']))
            actions_layout.addWidget(btn_delete)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 5, actions_widget)

        self.table.verticalHeader().setVisible(False)
        self.count_label.setText(f"{len(self.saved_connections)} подключений")

    def create_action_button(self, text, color):
        """Создает кнопку действия"""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(22)
        btn.setFixedWidth(70)
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

    def edit_connection(self, connection):
        """Редактирует существующее подключение"""
        dialog = EditConnectionDialog(connection, self)
        if dialog.exec() == QDialog.Accepted:
            # Удаляем старую запись
            self.delete_connection(connection['name'])
            # Сохраняем новую
            new_conn = dialog.get_connection()
            self.save_connection(new_conn)
            self.status_label.setText(f"Подключение '{new_conn['name']}' обновлено")

    def on_show(self):
        """Страница показана"""
        self.display_connections()


class AddConnectionDialog(QDialog):
    """Диалог добавления подключения"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить подключение")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background: #0a0e17;
            }
            QLabel {
                color: #8b9eb0;
                background: transparent;
                border: none;
            }
            QLineEdit, QComboBox, QSpinBox {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 400;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QCheckBox {
                color: #8b9eb0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid rgba(48, 54, 61, 0.25);
                background: rgba(13, 17, 23, 0.2);
            }
            QCheckBox::indicator:checked {
                background: rgba(74, 158, 255, 0.5);
                border-color: rgba(74, 158, 255, 0.3);
            }
            QPushButton {
                background: rgba(74, 158, 255, 0.15);
                color: #8b9eb0;
                border: 1px solid rgba(74, 158, 255, 0.15);
                border-radius: 5px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.25);
                color: #e8edf3;
            }
            QPushButton[color="primary"] {
                background: rgba(74, 158, 255, 0.3);
                color: #e8edf3;
                border: 1px solid rgba(74, 158, 255, 0.3);
            }
            QPushButton[color="primary"]:hover {
                background: rgba(74, 158, 255, 0.4);
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Форма
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        # Имя подключения
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Сервер-1")
        form.addRow("Имя:", self.name_edit)

        # Компьютер
        self.computer_edit = QLineEdit()
        self.computer_edit.setPlaceholderText("IP или имя компьютера")
        form.addRow("Компьютер:", self.computer_edit)

        # Пользователь
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Имя пользователя")
        form.addRow("Пользователь:", self.username_edit)

        # Пароль
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль (опционально)")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self.password_edit)

        # Порт
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(3389)
        form.addRow("Порт:", self.port_spin)

        # Разрешение
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            'Полный экран',
            '1920x1080',
            '1366x768',
            '1024x768'
        ])
        form.addRow("Разрешение:", self.resolution_combo)

        # Сохранять пароль
        self.save_password_check = QCheckBox("Сохранять пароль")
        form.addRow("", self.save_password_check)

        layout.addLayout(form)

        # Кнопки
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_ok = QPushButton("Сохранить")
        btn_ok.setProperty('color', 'primary')
        btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addWidget(buttons)

    def get_connection(self):
        """Возвращает данные подключения"""
        return {
            'name': self.name_edit.text().strip(),
            'computer': self.computer_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip(),
            'port': self.port_spin.value(),
            'resolution': self.resolution_combo.currentText(),
            'save_password': self.save_password_check.isChecked()
        }


class EditConnectionDialog(AddConnectionDialog):
    """Диалог редактирования подключения"""

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать подключение")

        # Заполняем поля
        self.name_edit.setText(connection['name'])
        self.computer_edit.setText(connection['computer'])
        self.username_edit.setText(connection['username'])
        self.password_edit.setText(connection.get('password', ''))
        self.port_spin.setValue(connection['port'])

        index = self.resolution_combo.findText(connection['resolution'])
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)

        self.save_password_check.setChecked(connection.get('save_password', False))
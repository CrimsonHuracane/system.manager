"""
Страница управления пользователями Windows
Просмотр, создание, удаление, управление группами
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QMessageBox, QDialog, QFormLayout,
    QCheckBox, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from .base_page_modern import BasePage
import win32net
import win32netcon
import win32security
import win32api
import win32con
import subprocess


class UsersWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        try:
            users = []

            try:
                user_info = win32net.NetUserEnum(
                    None,
                    3,
                    win32netcon.FILTER_NORMAL_ACCOUNT,
                    None,
                    None
                )

                for user in user_info[0]:
                    if not self._is_running:
                        break

                    username = user['name']

                    try:
                        user_detail = win32net.NetUserGetInfo(None, username, 3)

                        groups = []
                        try:
                            group_info = win32net.NetUserGetGroups(None, username)
                            groups = [g['name'] for g in group_info[0]]
                        except:
                            pass

                        users.append({
                            'username': username,
                            'full_name': user_detail.get('full_name', ''),
                            'comment': user_detail.get('comment', ''),
                            'groups': groups,
                            'status': 'Активен' if user_detail.get('flags', 0) & 0x0002 == 0 else 'Отключен',
                            'password_age': user_detail.get('password_age', 0),
                            'priv': user_detail.get('priv', 0),
                            'flags': user_detail.get('flags', 0)
                        })
                    except:
                        pass
            except Exception as e:
                users = self.get_users_wmic()

            self.finished.emit(users)

        except Exception as e:
            self.error.emit(str(e))

    def get_users_wmic(self):
        users = []
        try:
            result = subprocess.run(
                ['wmic', 'useraccount', 'get', 'name,fullname,status'],
                capture_output=True,
                text=True,
                encoding='cp866'
            )

            lines = result.stdout.strip().split('\n')[1:]
            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    username = parts[0]
                    full_name = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
                    status = 'Активен' if parts[-1].strip().lower() == 'yes' else 'Отключен'

                    users.append({
                        'username': username,
                        'full_name': full_name,
                        'comment': '',
                        'groups': [],
                        'status': status,
                        'password_age': 0,
                        'priv': 0,
                        'flags': 0
                    })
        except:
            pass

        return users

    def stop(self):
        self._is_running = False


class UserActionWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, action, username, **kwargs):
        super().__init__()
        self.action = action
        self.username = username
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        try:
            if self.action == 'create':
                self.create_user()
            elif self.action == 'delete':
                self.delete_user()
            elif self.action == 'disable':
                self.disable_user()
            elif self.action == 'enable':
                self.enable_user()
            elif self.action == 'reset_password':
                self.reset_password()
            elif self.action == 'add_to_group':
                self.add_to_group()
            elif self.action == 'remove_from_group':
                self.remove_from_group()

        except Exception as e:
            self.error.emit(str(e))

    def create_user(self):
        try:
            user_info = {
                'name': self.username,
                'password': self.kwargs.get('password', ''),
                'full_name': self.kwargs.get('full_name', ''),
                'comment': self.kwargs.get('comment', ''),
                'flags': win32netcon.UF_SCRIPT | win32netcon.UF_NORMAL_ACCOUNT
            }

            win32net.NetUserAdd(None, 3, user_info)

            group = self.kwargs.get('group', '')
            if group:
                try:
                    win32net.NetLocalGroupAddMembers(None, group, 3, [{'lgrmi3_domainandname': self.username}])
                except:
                    pass

            self.finished.emit(f"Пользователь {self.username} создан")
        except Exception as e:
            self.error.emit(str(e))

    def delete_user(self):
        try:
            win32net.NetUserDel(None, self.username)
            self.finished.emit(f"Пользователь {self.username} удален")
        except Exception as e:
            self.error.emit(str(e))

    def disable_user(self):
        try:
            user_info = win32net.NetUserGetInfo(None, self.username, 3)
            user_info['flags'] = user_info.get('flags', 0) | 0x0002
            win32net.NetUserSetInfo(None, self.username, 3, user_info)
            self.finished.emit(f"Пользователь {self.username} отключен")
        except Exception as e:
            self.error.emit(str(e))

    def enable_user(self):
        try:
            user_info = win32net.NetUserGetInfo(None, self.username, 3)
            user_info['flags'] = user_info.get('flags', 0) & ~0x0002
            win32net.NetUserSetInfo(None, self.username, 3, user_info)
            self.finished.emit(f"Пользователь {self.username} включен")
        except Exception as e:
            self.error.emit(str(e))

    def reset_password(self):
        try:
            new_password = self.kwargs.get('new_password', '')
            user_info = win32net.NetUserGetInfo(None, self.username, 3)
            user_info['password'] = new_password
            win32net.NetUserSetInfo(None, self.username, 3, user_info)
            self.finished.emit(f"Пароль для {self.username} изменен")
        except Exception as e:
            self.error.emit(str(e))

    def add_to_group(self):
        try:
            group = self.kwargs.get('group', '')
            win32net.NetLocalGroupAddMembers(None, group, 3, [{'lgrmi3_domainandname': self.username}])
            self.finished.emit(f"Пользователь {self.username} добавлен в группу {group}")
        except Exception as e:
            self.error.emit(str(e))

    def remove_from_group(self):
        try:
            group = self.kwargs.get('group', '')
            win32net.NetLocalGroupDelMembers(None, group, 3, [{'lgrmi3_domainandname': self.username}])
            self.finished.emit(f"Пользователь {self.username} удален из группы {group}")
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать пользователя")
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
            QLineEdit, QComboBox {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 400;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: rgba(74, 158, 255, 0.2);
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

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Имя пользователя")
        form.addRow("Имя:", self.username_edit)

        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText("Полное имя")
        form.addRow("Полное имя:", self.fullname_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self.password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("Повторите пароль")
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Подтверждение:", self.confirm_edit)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Описание")
        form.addRow("Описание:", self.comment_edit)

        self.group_combo = QComboBox()
        self.group_combo.addItems(['', 'Администраторы', 'Пользователи', 'Гости', 'Backup Operators', 'Power Users'])
        form.addRow("Группа:", self.group_combo)

        layout.addLayout(form)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_ok = QPushButton("Создать")
        btn_ok.setProperty('color', 'primary')
        btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addWidget(buttons)

    def get_user_data(self):
        return {
            'username': self.username_edit.text().strip(),
            'full_name': self.fullname_edit.text().strip(),
            'password': self.password_edit.text(),
            'comment': self.comment_edit.text().strip(),
            'group': self.group_combo.currentText()
        }


class ResetPasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Сброс пароля - {username}")
        self.username = username
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog {
                background: #0a0e17;
            }
            QLabel {
                color: #8b9eb0;
                background: transparent;
                border: none;
            }
            QLineEdit {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 400;
                min-height: 24px;
            }
            QLineEdit:focus {
                border-color: rgba(74, 158, 255, 0.2);
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
                background: rgba(218, 54, 51, 0.3);
                color: #e8edf3;
                border: 1px solid rgba(218, 54, 51, 0.3);
            }
            QPushButton[color="primary"]:hover {
                background: rgba(218, 54, 51, 0.4);
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        info_label = QLabel(f"Сброс пароля для пользователя: {self.username}")
        info_label.setStyleSheet("color: #a5b3c2; font-size: 13px; font-weight: 500;")
        form.addRow("", info_label)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setPlaceholderText("Новый пароль")
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Новый пароль:", self.new_password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("Повторите пароль")
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Подтверждение:", self.confirm_edit)

        layout.addLayout(form)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_ok = QPushButton("Сбросить пароль")
        btn_ok.setProperty('color', 'primary')
        btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addWidget(buttons)

    def get_new_password(self):
        return self.new_password_edit.text()


class UsersPage(BasePage):
    def __init__(self):
        super().__init__(
            "Управление пользователями",
            "Просмотр и управление пользователями системы"
        )

        self.worker = None
        self.action_worker = None
        self.users = []
        self.filtered_users = []

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.btn_refresh = QPushButton("Обновить")
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
        self.btn_refresh.clicked.connect(self.load_users)
        controls_layout.addWidget(self.btn_refresh)

        self.btn_add = QPushButton("+ Создать пользователя")
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
        self.btn_add.clicked.connect(self.show_add_user_dialog)
        controls_layout.addWidget(self.btn_add)

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

        # --- ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Имя", "Полное имя", "Статус", "Группы", "Описание", "Действия"
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

        # ⬇️ УВЕЛИЧИВАЕМ ШИРИНУ КОЛОНКИ С ДЕЙСТВИЯМИ
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 280)  # ⬅️ УВЕЛИЧЕНО!

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

        self.status_label = QLabel("Загрузка пользователей...")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.count_label = QLabel("0 пользователей")
        self.count_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.count_label)

        self.content_layout.addWidget(footer)

        self.load_users()

    def load_users(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.btn_refresh.setText("Загрузка...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Загрузка пользователей...")
        self.table.setRowCount(0)

        self.worker = UsersWorker()
        self.worker.finished.connect(self.on_users_loaded)
        self.worker.error.connect(self.on_users_error)
        self.worker.start()

    def on_users_loaded(self, users):
        self.users = users
        self.apply_filter()

        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Загружено {len(users)} пользователей")
        self.count_label.setText(f"{len(self.filtered_users)} пользователей")

    def on_users_error(self, error):
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Ошибка: {error}")

        QMessageBox.warning(
            self,
            "Ошибка",
            f"Не удалось загрузить пользователей:\n{error}\n\n"
            "Возможно, требуются права администратора."
        )

    def apply_filter(self):
        search_text = self.search_input.text().lower()

        if search_text:
            self.filtered_users = [
                u for u in self.users
                if search_text in u['username'].lower() or
                   search_text in u['full_name'].lower() or
                   search_text in u.get('comment', '').lower()
            ]
        else:
            self.filtered_users = self.users.copy()

        self.display_users()
        self.count_label.setText(f"{len(self.filtered_users)} пользователей")

    def display_users(self):
        self.table.setRowCount(len(self.filtered_users))

        for row, user in enumerate(self.filtered_users):
            name_item = QTableWidgetItem(user['username'])
            name_item.setForeground(QColor('#a5b3c2'))
            self.table.setItem(row, 0, name_item)

            fullname_item = QTableWidgetItem(user['full_name'] or '')
            fullname_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 1, fullname_item)

            status_color = '#3fb950' if user['status'] == 'Активен' else '#da3633'
            status_item = QTableWidgetItem(user['status'])
            status_item.setForeground(QColor(status_color))
            self.table.setItem(row, 2, status_item)

            groups_text = ', '.join(user['groups']) if user['groups'] else 'Нет'
            groups_item = QTableWidgetItem(groups_text)
            groups_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 3, groups_item)

            comment_item = QTableWidgetItem(user.get('comment', ''))
            comment_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 4, comment_item)

            # ⬇️ КНОПКИ - БОЛЕЕ КОМПАКТНЫЕ
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(2)

            btn_reset = self.create_action_button("Сброс пароля", "#f0883e")
            btn_reset.clicked.connect(lambda checked, u=user: self.reset_password(u))
            actions_layout.addWidget(btn_reset)

            btn_groups = self.create_action_button("Группы", "#4a9eff")
            btn_groups.clicked.connect(lambda checked, u=user: self.manage_groups(u))
            actions_layout.addWidget(btn_groups)

            if user['status'] == 'Активен':
                btn_disable = self.create_action_button("Отключить", "#da3633")
                btn_disable.clicked.connect(lambda checked, u=user: self.disable_user(u))
                actions_layout.addWidget(btn_disable)
            else:
                btn_enable = self.create_action_button("Включить", "#3fb950")
                btn_enable.clicked.connect(lambda checked, u=user: self.enable_user(u))
                actions_layout.addWidget(btn_enable)

            btn_delete = self.create_action_button("Удалить", "#da3633")
            btn_delete.clicked.connect(lambda checked, u=user: self.delete_user(u))
            actions_layout.addWidget(btn_delete)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 5, actions_widget)

        self.table.verticalHeader().setVisible(False)

    def create_action_button(self, text, color):
        """Создает МАКСИМАЛЬНО КОМПАКТНУЮ кнопку"""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(16)  # ⬅️ МИНИМАЛЬНАЯ ВЫСОТА
        btn.setFixedWidth(36)  # ⬅️ МИНИМАЛЬНАЯ ШИРИНА
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color};
                border-radius: 2px;
                padding: 0 1px;
                font-size: 6px;  /* ⬅️ МИНИМАЛЬНЫЙ ШРИФТ */
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

    def show_add_user_dialog(self):
        dialog = AddUserDialog(self)
        if dialog.exec() == QDialog.Accepted:
            user_data = dialog.get_user_data()

            if not user_data['username']:
                QMessageBox.warning(self, "Ошибка", "Введите имя пользователя")
                return

            if user_data['password'] != dialog.confirm_edit.text():
                QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
                return

            if len(user_data['password']) < 6:
                QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
                return

            self.action_worker = UserActionWorker(
                'create',
                user_data['username'],
                password=user_data['password'],
                full_name=user_data['full_name'],
                comment=user_data['comment'],
                group=user_data['group']
            )
            self.action_worker.finished.connect(self.on_action_finished)
            self.action_worker.error.connect(self.on_action_error)
            self.action_worker.start()

    def reset_password(self, user):
        dialog = ResetPasswordDialog(user['username'], self)
        if dialog.exec() == QDialog.Accepted:
            new_password = dialog.get_new_password()

            if len(new_password) < 6:
                QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
                return

            if new_password != dialog.confirm_edit.text():
                QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
                return

            self.action_worker = UserActionWorker(
                'reset_password',
                user['username'],
                new_password=new_password
            )
            self.action_worker.finished.connect(self.on_action_finished)
            self.action_worker.error.connect(self.on_action_error)
            self.action_worker.start()

    def disable_user(self, user):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите отключить пользователя {user['username']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.action_worker = UserActionWorker('disable', user['username'])
            self.action_worker.finished.connect(self.on_action_finished)
            self.action_worker.error.connect(self.on_action_error)
            self.action_worker.start()

    def enable_user(self, user):
        self.action_worker = UserActionWorker('enable', user['username'])
        self.action_worker.finished.connect(self.on_action_finished)
        self.action_worker.error.connect(self.on_action_error)
        self.action_worker.start()

    def delete_user(self, user):
        if user['username'] in ['Administrator', 'Guest']:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить системного пользователя")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить пользователя {user['username']}?\nЭто действие необратимо!",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.action_worker = UserActionWorker('delete', user['username'])
            self.action_worker.finished.connect(self.on_action_finished)
            self.action_worker.error.connect(self.on_action_error)
            self.action_worker.start()

    def manage_groups(self, user):
        dialog = ManageGroupsDialog(user, self)
        dialog.exec()
        self.load_users()

    def on_action_finished(self, message):
        self.status_label.setText(message)
        QMessageBox.information(self, "Успешно", message)
        self.load_users()

    def on_action_error(self, error):
        self.status_label.setText(f"Ошибка: {error}")
        QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить действие:\n{error}")

    def on_show(self):
        self.load_users()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        if self.action_worker and self.action_worker.isRunning():
            self.action_worker.stop()
            self.action_worker.wait()
        event.accept()


class ManageGroupsDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.parent_page = parent
        self.setWindowTitle(f"Группы пользователя - {user['username']}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QDialog {
                background: #0a0e17;
            }
            QLabel {
                color: #8b9eb0;
                background: transparent;
                border: none;
            }
            QListWidget {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 4px;
                font-size: 12px;
                font-weight: 400;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: rgba(74, 158, 255, 0.15);
                color: #e8edf3;
            }
            QListWidget::item:hover {
                background: rgba(74, 158, 255, 0.05);
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
            QPushButton[color="danger"] {
                background: rgba(218, 54, 51, 0.3);
                color: #e8edf3;
                border: 1px solid rgba(218, 54, 51, 0.3);
            }
            QPushButton[color="danger"]:hover {
                background: rgba(218, 54, 51, 0.4);
            }
        """)

        self.setup_ui()
        self.load_groups()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel(f"Управление группами для: {self.user['username']}")
        info_label.setStyleSheet("color: #a5b3c2; font-size: 14px; font-weight: 500;")
        layout.addWidget(info_label)

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setSpacing(12)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("Доступные группы:")
        left_label.setStyleSheet("color: #6b7d95; font-size: 11px; padding-bottom: 4px;")
        left_layout.addWidget(left_label)

        self.available_list = QListWidget()
        self.available_list.setMinimumHeight(200)
        left_layout.addWidget(self.available_list)

        container_layout.addWidget(left_widget, stretch=1)

        buttons_widget = QWidget()
        buttons_widget.setFixedWidth(50)
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignCenter)
        buttons_layout.setSpacing(8)

        btn_add = QPushButton("→")
        btn_add.setProperty('color', 'primary')
        btn_add.setFixedSize(36, 32)
        btn_add.clicked.connect(self.add_to_group)
        buttons_layout.addWidget(btn_add)

        btn_remove = QPushButton("←")
        btn_remove.setProperty('color', 'danger')
        btn_remove.setFixedSize(36, 32)
        btn_remove.clicked.connect(self.remove_from_group)
        buttons_layout.addWidget(btn_remove)

        container_layout.addWidget(buttons_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_label = QLabel("Группы пользователя:")
        right_label.setStyleSheet("color: #6b7d95; font-size: 11px; padding-bottom: 4px;")
        right_layout.addWidget(right_label)

        self.user_groups_list = QListWidget()
        self.user_groups_list.setMinimumHeight(200)
        right_layout.addWidget(self.user_groups_list)

        container_layout.addWidget(right_widget, stretch=1)

        layout.addWidget(container, stretch=1)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_close = QPushButton("Закрыть")
        btn_close.setProperty('color', 'primary')
        btn_close.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_close)

        layout.addWidget(buttons)

    def load_groups(self):
        self.available_list.clear()
        self.user_groups_list.clear()

        all_groups = []
        try:
            groups_info = win32net.NetLocalGroupEnum(None, 0, None, None)
            all_groups = [g['name'] for g in groups_info[0]]
        except:
            all_groups = ['Администраторы', 'Пользователи', 'Гости', 'Backup Operators', 'Power Users']

        user_groups = self.user.get('groups', [])

        for group in sorted(all_groups):
            if group not in user_groups:
                self.available_list.addItem(group)

        for group in sorted(user_groups):
            self.user_groups_list.addItem(group)

    def add_to_group(self):
        current_item = self.available_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Информация", "Выберите группу для добавления")
            return

        group = current_item.text()
        username = self.user['username']

        try:
            win32net.NetLocalGroupAddMembers(None, group, 3, [{'lgrmi3_domainandname': username}])

            self.user_groups_list.addItem(group)
            self.available_list.takeItem(self.available_list.currentRow())

            QMessageBox.information(self, "Успешно", f"Пользователь {username} добавлен в группу {group}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось добавить пользователя в группу:\n{str(e)}")

    def remove_from_group(self):
        current_item = self.user_groups_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Информация", "Выберите группу для удаления")
            return

        group = current_item.text()
        username = self.user['username']

        if group == 'Администраторы' and username == 'Administrator':
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить администратора из группы Администраторы")
            return

        try:
            win32net.NetLocalGroupDelMembers(None, group, 3, [{'lgrmi3_domainandname': username}])

            self.available_list.addItem(group)
            self.user_groups_list.takeItem(self.user_groups_list.currentRow())

            QMessageBox.information(self, "Успешно", f"Пользователь {username} удален из группы {group}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить пользователя из группы:\n{str(e)}")
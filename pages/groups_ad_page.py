"""
Страница управления группами
Создание групп
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QMessageBox, QDialog, QFormLayout,
    QComboBox, QTabWidget, QCheckBox,
    QTextEdit, QListWidget, QListWidgetItem,
    QProgressBar, QSpinBox, QGroupBox, QProgressDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from .base_page_modern import BasePage
import win32net
import win32netcon
import win32security
import win32api
import subprocess
import os
import tempfile
import json
import re


try:
    import ldap3
    from ldap3 import Server, Connection, ALL, NTLM, ALL_ATTRIBUTES

    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

try:
    import pyad
    from pyad import aduser, adgroup, adcontainer

    PYAD_AVAILABLE = True
except ImportError:
    PYAD_AVAILABLE = False


class ActiveDirectoryWorker(QThread):
    """Поток для работы с Active Directory"""
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, action, **kwargs):
        super().__init__()
        self.action = action
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        try:
            if not LDAP_AVAILABLE:
                self.error.emit("Библиотека ldap3 не установлена. Установите: pip install ldap3")
                return

            if self.action == 'create_group':
                self.create_ad_group()
            elif self.action == 'delete_group':
                self.delete_ad_group()
            elif self.action == 'list_groups':
                self.list_ad_groups()
            elif self.action == 'add_member':
                self.add_ad_member()
            elif self.action == 'remove_member':
                self.remove_ad_member()
            elif self.action == 'apply_policies':
                self.apply_gpo()

        except Exception as e:
            self.error.emit(str(e))

    def connect_ad(self):
        """Подключение к Active Directory"""
        try:
            domain = self.kwargs.get('domain', '')
            username = self.kwargs.get('username', '')
            password = self.kwargs.get('password', '')

            if not domain:
                # Автоматически определяем домен
                import socket
                domain = socket.getfqdn().split('.', 1)[1] if '.' in socket.getfqdn() else ''

            # Пытаемся подключиться через текущего пользователя
            server = Server(domain, get_info=ALL)
            conn = Connection(server, auto_bind=True)
            return conn

        except Exception as e:
            raise Exception(f"Не удалось подключиться к AD: {str(e)}\n"
                            f"Проверьте подключение к домену и права доступа.")

    def create_ad_group(self):
        """Создает группу в Active Directory"""
        try:
            group_name = self.kwargs.get('name', '')
            group_type = self.kwargs.get('type', 'Security')
            group_scope = self.kwargs.get('scope', 'Global')
            description = self.kwargs.get('description', '')
            ou_path = self.kwargs.get('ou', '')
            members = self.kwargs.get('members', [])

            self.progress.emit(10)

            # Подключаемся к AD
            conn = self.connect_ad()
            self.progress.emit(30)

            # Определяем DN для группы
            if not ou_path:
                # Используем стандартный OU
                base_dn = conn.server.info.other['defaultNamingContext'][0]
                ou_path = f"CN=Users,{base_dn}"

            # Определяем тип группы
            group_type_map = {
                'Security': 0x80000002,  # Security Group Global
                'Distribution': 0x80000000,  # Distribution Group Global
                'Universal': 0x80000008,  # Security Group Universal
            }

            group_type_value = group_type_map.get(group_type, 0x80000002)

            # Создаем группу
            group_dn = f"CN={group_name},{ou_path}"

            # Проверяем, существует ли группа
            conn.search(ou_path, f'(cn={group_name})', attributes=['distinguishedName'])
            if conn.entries:
                self.error.emit(f"Группа {group_name} уже существует в AD")
                return

            # Создаем группу
            attributes = {
                'objectClass': ['top', 'group'],
                'cn': group_name,
                'sAMAccountName': group_name,
                'groupType': group_type_value,
                'description': description
            }

            conn.add(group_dn, attributes=attributes)
            self.progress.emit(60)

            # Добавляем участников
            if members:
                for member in members:
                    try:
                        # Ищем пользователя в AD
                        conn.search(base_dn, f'(sAMAccountName={member})', attributes=['distinguishedName'])
                        if conn.entries:
                            member_dn = conn.entries[0].distinguishedName.value
                            conn.modify(group_dn, {'member': [(ldap3.MODIFY_ADD, [member_dn])]})
                    except:
                        pass
                self.progress.emit(80)

            # Применяем GPO если нужно
            if self.kwargs.get('create_gpo', False):
                self.create_gpo_for_group(group_name)

            self.progress.emit(100)

            self.finished.emit({
                'name': group_name,
                'dn': group_dn,
                'type': group_type,
                'scope': group_scope,
                'members': members
            })

        except Exception as e:
            self.error.emit(str(e))

    def delete_ad_group(self):
        """Удаляет группу из Active Directory"""
        try:
            group_dn = self.kwargs.get('dn', '')
            group_name = self.kwargs.get('name', '')

            conn = self.connect_ad()

            # Проверяем, существует ли группа
            conn.search(group_dn, '(objectClass=group)', attributes=['cn'])
            if not conn.entries:
                self.error.emit(f"Группа {group_name} не найдена в AD")
                return

            # Удаляем группу
            conn.delete(group_dn)

            self.finished.emit(f"Группа {group_name} удалена из AD")

        except Exception as e:
            self.error.emit(str(e))

    def list_ad_groups(self):
        """Получает список групп из AD"""
        try:
            conn = self.connect_ad()
            base_dn = conn.server.info.other['defaultNamingContext'][0]

            # Ищем все группы
            conn.search(
                base_dn,
                '(objectClass=group)',
                attributes=['cn', 'description', 'groupType', 'member']
            )

            groups = []
            for entry in conn.entries:
                group_name = entry.cn.value if hasattr(entry, 'cn') else 'Unknown'
                description = entry.description.value if hasattr(entry, 'description') else ''

                groups.append({
                    'name': group_name,
                    'dn': entry.distinguishedName.value,
                    'description': description,
                    'type': self.get_group_type(entry.groupType.value) if hasattr(entry, 'groupType') else 'Security',
                    'members_count': len(entry.member.value) if hasattr(entry, 'member') else 0
                })

            self.finished.emit(groups)

        except Exception as e:
            self.error.emit(str(e))

    def add_ad_member(self):
        """Добавляет участника в группу AD"""
        try:
            group_dn = self.kwargs.get('group_dn', '')
            member_name = self.kwargs.get('member', '')

            conn = self.connect_ad()

            # Ищем участника
            base_dn = conn.server.info.other['defaultNamingContext'][0]
            conn.search(base_dn, f'(sAMAccountName={member_name})', attributes=['distinguishedName'])

            if not conn.entries:
                self.error.emit(f"Пользователь {member_name} не найден в AD")
                return

            member_dn = conn.entries[0].distinguishedName.value

            # Добавляем в группу
            conn.modify(group_dn, {'member': [(ldap3.MODIFY_ADD, [member_dn])]})

            self.finished.emit(f"Пользователь {member_name} добавлен в группу")

        except Exception as e:
            self.error.emit(str(e))

    def remove_ad_member(self):
        """Удаляет участника из группы AD"""
        try:
            group_dn = self.kwargs.get('group_dn', '')
            member_name = self.kwargs.get('member', '')

            conn = self.connect_ad()

            # Ищем участника
            base_dn = conn.server.info.other['defaultNamingContext'][0]
            conn.search(base_dn, f'(sAMAccountName={member_name})', attributes=['distinguishedName'])

            if not conn.entries:
                self.error.emit(f"Пользователь {member_name} не найден в AD")
                return

            member_dn = conn.entries[0].distinguishedName.value

            # Удаляем из группы
            conn.modify(group_dn, {'member': [(ldap3.MODIFY_REMOVE, [member_dn])]})

            self.finished.emit(f"Пользователь {member_name} удален из группы")

        except Exception as e:
            self.error.emit(str(e))

    def apply_gpo(self):
        """Создает и применяет GPO для группы"""
        try:
            group_name = self.kwargs.get('name', '')
            policies = self.kwargs.get('policies', {})

            # Используем PowerShell для создания GPO
            ps_script = self.generate_gpo_script(group_name, policies)

            # Сохраняем скрипт
            script_path = os.path.join(tempfile.gettempdir(), f'create_gpo_{group_name}.ps1')
            with open(script_path, 'w') as f:
                f.write(ps_script)

            # Выполняем PowerShell
            result = subprocess.run([
                'powershell', '-ExecutionPolicy', 'Bypass', '-File', script_path
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                raise Exception(f"Ошибка создания GPO: {result.stderr}")

            self.finished.emit(f"GPO для группы {group_name} создан и применен")

        except Exception as e:
            self.error.emit(str(e))

    def generate_gpo_script(self, group_name, policies):
        """Генерирует PowerShell скрипт для создания GPO"""
        script_lines = [
            "# PowerShell скрипт для создания GPO",
            "Import-Module GroupPolicy",
            "",
            f"$GroupName = '{group_name}'",
            f"$GPOName = 'GPO_{group_name}'",
            "",
            "# Создаем новый GPO",
            "New-GPO -Name $GPOName -Comment 'GPO для группы $GroupName'",
            "",
            "# Настраиваем политики",
        ]

        # Добавляем политики
        if policies.get('allow_remote_logon', True):
            script_lines.append("# Разрешаем удаленный вход")
            script_lines.append(
                "$GPOName | Set-GPRegistryValue -Key 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ValueName 'AllowRemoteRDC' -Type DWord -Value 1")

        if policies.get('allow_network_access', True):
            script_lines.append("# Разрешаем доступ к сети")
            script_lines.append(
                "$GPOName | Set-GPRegistryValue -Key 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ValueName 'EnableNetworkAccess' -Type DWord -Value 1")

        if policies.get('restrict_registry', False):
            script_lines.append("# Ограничиваем доступ к реестру")
            script_lines.append(
                "$GPOName | Set-GPRegistryValue -Key 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ValueName 'DisableRegistryTools' -Type DWord -Value 1")

        if policies.get('enable_audit', False):
            script_lines.append("# Включаем аудит")
            script_lines.append(
                "$GPOName | Set-GPRegistryValue -Key 'HKLM\\System\\CurrentControlSet\\Control\\Lsa\\Audit' -ValueName 'AuditBaseObjects' -Type DWord -Value 1")

        script_lines.append("")
        script_lines.append("# Связываем GPO с OU (по умолчанию с корнем домена)")
        script_lines.append("$GPOName | New-GPLink -Target 'DC=domain,DC=local' -LinkEnabled Yes")
        script_lines.append("")
        script_lines.append("Write-Host 'GPO создан и применен'")

        return '\n'.join(script_lines)

    def get_group_type(self, type_value):
        """Определяет тип группы AD"""
        if type_value & 0x80000000:  # Distribution group
            return 'Distribution'
        elif type_value & 0x80000002:  # Security group
            return 'Security'
        elif type_value & 0x80000008:  # Universal group
            return 'Universal'
        else:
            return 'Security'

    def stop(self):
        self._is_running = False


class ADLoginDialog(QDialog):
    """Диалог входа в Active Directory"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подключение к Active Directory")
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
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel("Подключение к Active Directory")
        info_label.setStyleSheet("color: #a5b3c2; font-size: 14px; font-weight: 500;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("domain.local")
        form.addRow("Домен:", self.domain_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Administrator")
        form.addRow("Пользователь:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self.password_edit)

        layout.addLayout(form)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_ok = QPushButton("Подключиться")
        btn_ok.setProperty('color', 'primary')
        btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addWidget(buttons)

    def get_credentials(self):
        return {
            'domain': self.domain_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text()
        }


class CreateADGroupDialog(QDialog):
    """Диалог создания группы в AD"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать группу в Active Directory")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self.setStyleSheet("""
            QDialog {
                background: #0a0e17;
            }
            QLabel {
                color: #8b9eb0;
                background: transparent;
                border: none;
            }
            QLineEdit, QComboBox, QTextEdit {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 400;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QTextEdit {
                min-height: 60px;
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

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                background: transparent;
                border: none;
                padding: 4px 0;
            }
            QTabBar::tab {
                background: transparent;
                color: #6b7d95;
                padding: 6px 12px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                color: #e8edf3;
                border-bottom: 2px solid #4a9eff;
            }
        """)

        # --- ОСНОВНЫЕ ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя группы (без пробелов)")
        form.addRow("Имя группы:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Описание группы")
        self.description_edit.setMaximumHeight(60)
        form.addRow("Описание:", self.description_edit)

        self.ou_edit = QLineEdit()
        self.ou_edit.setPlaceholderText("OU=Users,DC=domain,DC=local")
        form.addRow("OU путь:", self.ou_edit)

        self.group_type = QComboBox()
        self.group_type.addItems(['Security', 'Distribution', 'Universal'])
        form.addRow("Тип группы:", self.group_type)

        self.group_scope = QComboBox()
        self.group_scope.addItems(['Global', 'Domain Local', 'Universal'])
        form.addRow("Область:", self.group_scope)

        general_layout.addLayout(form)
        general_layout.addStretch()
        tabs.addTab(general_tab, "Основные")

        # --- ПОЛИТИКИ ---
        policies_tab = QWidget()
        policies_layout = QVBoxLayout(policies_tab)
        policies_layout.setSpacing(10)

        info_label = QLabel("Настройка политик безопасности")
        info_label.setStyleSheet("color: #a5b3c2; font-size: 13px; font-weight: 500;")
        policies_layout.addWidget(info_label)

        # Группа политик
        policy_group = QWidget()
        policy_group.setStyleSheet("background: rgba(13, 17, 23, 0.15); border-radius: 5px; padding: 4px;")
        policy_layout = QVBoxLayout(policy_group)

        self.create_gpo_check = QCheckBox("Создать GPO для этой группы")
        self.create_gpo_check.setChecked(True)
        policy_layout.addWidget(self.create_gpo_check)

        self.allow_remote = QCheckBox("Разрешить удаленный вход (RDP)")
        self.allow_remote.setChecked(True)
        policy_layout.addWidget(self.allow_remote)

        self.allow_network = QCheckBox("Разрешить доступ к сетевым ресурсам")
        self.allow_network.setChecked(True)
        policy_layout.addWidget(self.allow_network)

        self.restrict_registry = QCheckBox("Ограничить доступ к реестру")
        self.restrict_registry.setChecked(False)
        policy_layout.addWidget(self.restrict_registry)

        self.enable_audit = QCheckBox("Включить аудит действий")
        self.enable_audit.setChecked(False)
        policy_layout.addWidget(self.enable_audit)

        policies_layout.addWidget(policy_group)
        policies_layout.addStretch()
        tabs.addTab(policies_tab, "Политики")

        # --- УЧАСТНИКИ ---
        members_tab = QWidget()
        members_layout = QVBoxLayout(members_tab)
        members_layout.setSpacing(8)

        members_label = QLabel("Начальные участники группы:")
        members_label.setStyleSheet("color: #8b9eb0; font-size: 12px; font-weight: 500;")
        members_layout.addWidget(members_label)

        self.members_edit = QTextEdit()
        self.members_edit.setPlaceholderText("Имена пользователей (по одному на строку)")
        self.members_edit.setMaximumHeight(100)
        members_layout.addWidget(self.members_edit)

        members_hint = QLabel("Введите имена пользователей без домена (например: Administrator, User1)")
        members_hint.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        members_layout.addWidget(members_hint)

        members_layout.addStretch()
        tabs.addTab(members_tab, "Участники")

        layout.addWidget(tabs)

        # --- КНОПКИ ---
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        btn_ok = QPushButton("Создать группу в AD")
        btn_ok.setProperty('color', 'primary')
        btn_ok.setFixedWidth(180)
        btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        layout.addWidget(buttons)

    def get_group_data(self):
        """Возвращает данные группы"""
        policies = {
            'allow_remote_logon': self.allow_remote.isChecked(),
            'allow_network_access': self.allow_network.isChecked(),
            'restrict_registry': self.restrict_registry.isChecked(),
            'enable_audit': self.enable_audit.isChecked()
        }

        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'ou': self.ou_edit.text().strip(),
            'type': self.group_type.currentText(),
            'scope': self.group_scope.currentText(),
            'members': [m.strip() for m in self.members_edit.toPlainText().strip().split('\n') if m.strip()],
            'create_gpo': self.create_gpo_check.isChecked(),
            'policies': policies
        }


class GroupsADPage(BasePage):
    """Страница управления группами в Active Directory"""

    def __init__(self):
        super().__init__(
            "Группы AD",
            "Управление группами в Active Directory (видно в GPMC.msc)"
        )

        self.worker = None
        self.action_worker = None
        self.groups = []
        self.filtered_groups = []
        self.ad_connected = False
        self.ad_credentials = {}

        # Проверка доступности LDAP
        if not LDAP_AVAILABLE:
            self.show_ldap_error()

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ ---
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.btn_connect = QPushButton("Подключиться к AD")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setFixedHeight(26)
        self.btn_connect.setStyleSheet("""
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
            }
        """)
        self.btn_connect.clicked.connect(self.connect_to_ad)
        controls_layout.addWidget(self.btn_connect)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(26)
        self.btn_refresh.setEnabled(False)
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
        self.btn_refresh.clicked.connect(self.load_groups)
        controls_layout.addWidget(self.btn_refresh)

        self.btn_create = QPushButton("+ Создать группу AD")
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.setFixedHeight(26)
        self.btn_create.setEnabled(False)
        self.btn_create.setStyleSheet("""
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
        self.btn_create.clicked.connect(self.show_create_group_dialog)
        controls_layout.addWidget(self.btn_create)

        controls_layout.addStretch()

        # Статус подключения
        self.status_indicator = QLabel("● Не подключен")
        self.status_indicator.setStyleSheet("color: #da3633; font-size: 11px; background: transparent; border: none;")
        controls_layout.addWidget(self.status_indicator)

        self.content_layout.addWidget(controls)

        # --- ТАБЛИЦА ГРУПП AD ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Имя группы", "Описание", "Участников", "Тип", "Действия"
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

        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 220)

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

        self.status_label = QLabel("Подключитесь к AD для просмотра групп")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.count_label = QLabel("0 групп")
        self.count_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")
        footer_layout.addWidget(self.count_label)

        self.content_layout.addWidget(footer)

    def show_ldap_error(self):
        """Показывает ошибку о отсутствии ldap3"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)

        error_label = QLabel(
            "❌ Библиотека ldap3 не установлена\n\n"
            "Для работы с Active Directory необходимо установить:\n"
            "pip install ldap3\n\n"
            "или используйте локальные группы (вкладка 'Группы')"
        )
        error_label.setStyleSheet("""
            QLabel {
                color: #8b9eb0;
                font-size: 13px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 40px 20px;
                text-align: center;
            }
        """)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)

        self.content_layout.addWidget(error_widget)

    def connect_to_ad(self):
        """Подключение к Active Directory"""
        dialog = ADLoginDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.ad_credentials = dialog.get_credentials()
            self.ad_connected = True

            self.status_indicator.setText("● Подключен")
            self.status_indicator.setStyleSheet(
                "color: #3fb950; font-size: 11px; background: transparent; border: none;")

            self.btn_refresh.setEnabled(True)
            self.btn_create.setEnabled(True)

            self.load_groups()

    def load_groups(self):
        """Загружает группы из AD"""
        if not self.ad_connected:
            return

        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.btn_refresh.setText("Загрузка...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Загрузка групп из AD...")
        self.table.setRowCount(0)

        self.worker = ActiveDirectoryWorker(
            'list_groups',
            **self.ad_credentials
        )
        self.worker.finished.connect(self.on_groups_loaded)
        self.worker.error.connect(self.on_groups_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_groups_loaded(self, groups):
        self.groups = groups
        self.apply_filter()

        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Загружено {len(groups)} групп из AD")
        self.count_label.setText(f"{len(self.filtered_groups)} групп")

    def on_groups_error(self, error):
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Ошибка: {error}")

        QMessageBox.warning(
            self,
            "Ошибка AD",
            f"Не удалось загрузить группы из AD:\n{error}\n\n"
            "Проверьте:\n"
            "1. Подключение к домену\n"
            "2. Права доступа\n"
            "3. Установку ldap3 (pip install ldap3)"
        )

    def on_progress(self, value):
        self.status_label.setText(f"Загрузка... {value}%")

    def apply_filter(self):
        search_text = self.search_input.text().lower() if hasattr(self, 'search_input') else ''

        if search_text:
            self.filtered_groups = [
                g for g in self.groups
                if search_text in g['name'].lower() or
                   search_text in g.get('description', '').lower()
            ]
        else:
            self.filtered_groups = self.groups.copy()

        self.display_groups()
        self.count_label.setText(f"{len(self.filtered_groups)} групп")

    def display_groups(self):
        self.table.setRowCount(len(self.filtered_groups))

        for row, group in enumerate(self.filtered_groups):
            name_item = QTableWidgetItem(group['name'])
            name_item.setForeground(QColor('#a5b3c2'))
            self.table.setItem(row, 0, name_item)

            desc_item = QTableWidgetItem(group.get('description', ''))
            desc_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 1, desc_item)

            members_item = QTableWidgetItem(str(group.get('members_count', 0)))
            members_item.setForeground(QColor('#8b9eb0'))
            self.table.setItem(row, 2, members_item)

            type_item = QTableWidgetItem(group.get('type', 'Security'))
            type_item.setForeground(QColor('#6b7d95'))
            self.table.setItem(row, 3, type_item)

            # Кнопки действий
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(3)

            btn_members = self.create_action_button("Участники", "#4a9eff")
            btn_members.clicked.connect(lambda checked, g=group: self.manage_members(g))
            actions_layout.addWidget(btn_members)

            btn_gpo = self.create_action_button("GPO", "#f0883e")
            btn_gpo.clicked.connect(lambda checked, g=group: self.manage_gpo(g))
            actions_layout.addWidget(btn_gpo)

            btn_delete = self.create_action_button("Удалить", "#da3633")
            btn_delete.clicked.connect(lambda checked, g=group: self.delete_group(g))
            actions_layout.addWidget(btn_delete)

            actions_layout.addStretch()
            self.table.setCellWidget(row, 4, actions_widget)

        self.table.verticalHeader().setVisible(False)

    def create_action_button(self, text, color):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(22)
        btn.setFixedWidth(65)
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

    def show_create_group_dialog(self):
        """Показывает диалог создания группы в AD"""
        dialog = CreateADGroupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_group_data()

            if not data['name']:
                QMessageBox.warning(self, "Ошибка", "Введите имя группы")
                return

            # Показываем прогресс
            progress_dialog = QProgressDialog("Создание группы в AD...", "Отмена", 0, 100, self)
            progress_dialog.setWindowTitle("Выполняется")
            progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background: #0a0e17;
                    color: #8b9eb0;
                }
                QProgressBar {
                    border: 1px solid rgba(48, 54, 61, 0.1);
                    border-radius: 5px;
                    background: rgba(13, 17, 23, 0.2);
                    height: 20px;
                }
                QProgressBar::chunk {
                    background: #4a9eff;
                    border-radius: 5px;
                }
                QPushButton {
                    background: rgba(74, 158, 255, 0.15);
                    color: #8b9eb0;
                    border: 1px solid rgba(74, 158, 255, 0.15);
                    border-radius: 5px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background: rgba(74, 158, 255, 0.25);
                    color: #e8edf3;
                }
            """)
            progress_dialog.show()

            self.action_worker = ActiveDirectoryWorker(
                'create_group',
                **self.ad_credentials,
                name=data['name'],
                description=data['description'],
                ou=data['ou'],
                type=data['type'],
                scope=data['scope'],
                members=data['members'],
                create_gpo=data['create_gpo'],
                policies=data['policies']
            )
            self.action_worker.progress.connect(progress_dialog.setValue)
            self.action_worker.finished.connect(lambda msg: self.on_action_finished(msg, progress_dialog))
            self.action_worker.error.connect(lambda err: self.on_action_error(err, progress_dialog))
            self.action_worker.start()

    def delete_group(self, group):
        """Удаляет группу из AD"""
        if group['name'] in ['Domain Admins', 'Enterprise Admins', 'Schema Admins']:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить системную группу AD")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить группу {group['name']} из AD?\n"
            "Группа будет удалена из Active Directory.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.action_worker = ActiveDirectoryWorker(
                'delete_group',
                **self.ad_credentials,
                name=group['name'],
                dn=group.get('dn', '')
            )
            self.action_worker.finished.connect(self.on_action_finished)
            self.action_worker.error.connect(self.on_action_error)
            self.action_worker.start()

    def manage_members(self, group):
        """Управление участниками группы AD"""
        QMessageBox.information(
            self,
            "Управление участниками",
            f"Управление участниками группы {group['name']}\n\n"
            "Функция в разработке.\n"
            "Используйте оснастку 'Active Directory Users and Computers'"
        )

    def manage_gpo(self, group):
        """Управление GPO для группы"""
        QMessageBox.information(
            self,
            "Управление GPO",
            f"Управление GPO для группы {group['name']}\n\n"
            "GPO создан и применен к группе.\n"
            "Для настройки используйте оснастку 'Group Policy Management Console' (GPMC.msc)"
        )

    def on_action_finished(self, message, dialog=None):
        self.status_label.setText(str(message) if isinstance(message, str) else "Готово")
        if dialog:
            dialog.close()
        if isinstance(message, str):
            QMessageBox.information(self, "Успешно", message)
        else:
            QMessageBox.information(self, "Успешно", f"Группа {message.get('name', '')} создана в AD")
        self.load_groups()

    def on_action_error(self, error, dialog=None):
        self.status_label.setText(f"Ошибка: {error}")
        if dialog:
            dialog.close()
        QMessageBox.warning(self, "Ошибка AD", f"Не удалось выполнить действие:\n{error}")

    def on_show(self):
        if self.ad_connected:
            self.load_groups()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        if self.action_worker and self.action_worker.isRunning():
            self.action_worker.stop()
            self.action_worker.wait()
        event.accept()
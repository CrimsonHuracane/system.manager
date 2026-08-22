"""
Страница быстрого доступа
Горячие кнопки для часто используемых инструментов
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QGridLayout, QFrame, QScrollArea,
    QMessageBox, QMenu
)
from PySide6.QtCore import Qt
from .base_page_modern import BasePage
import subprocess
import ctypes
import os


class QuickAccessPage(BasePage):
    def __init__(self):
        super().__init__(
            "Быстрый доступ",
            "Часто используемые инструменты"
        )

        self.admin_required = {}

        grid = QGridLayout()
        grid.setSpacing(16)

        tools = [
            # Системные инструменты
            {
                'name': 'Диспетчер задач',
                'description': 'Управление процессами и производительностью',
                'icon': '⚙',
                'color': '#4a9eff',
                'command': 'taskmgr.exe',
                'args': [],
                'category': 'Системные',
                'admin': False
            },
            {
                'name': 'Управление компьютером',
                'description': 'Управление дисками, службами, пользователями',
                'icon': '🖥',
                'color': '#3fb950',
                'command': 'compmgmt.msc',
                'args': [],
                'category': 'Системные',
                'admin': True
            },
            {
                'name': 'Просмотр событий',
                'description': 'Системные журналы и события',
                'icon': '📋',
                'color': '#f0883e',
                'command': 'eventvwr.msc',
                'args': [],
                'category': 'Системные',
                'admin': False
            },
            {
                'name': 'Службы',
                'description': 'Управление службами Windows',
                'icon': '🔧',
                'color': '#8b9eb0',
                'command': 'services.msc',
                'args': [],
                'category': 'Системные',
                'admin': True
            },

            # Инструменты администрирования
            {
                'name': 'GPO Управление',
                'description': 'Управление групповыми политиками',
                'icon': '📊',
                'color': '#da3633',
                'command': 'gpmc.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'Active Directory',
                'description': 'Пользователи и компьютеры AD',
                'icon': '👥',
                'color': '#4a9eff',
                'command': 'dsa.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'DNS',
                'description': 'Управление DNS зонами и записями',
                'icon': '🌐',
                'color': '#3fb950',
                'command': 'dnsmgmt.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'DHCP',
                'description': 'Управление DHCP сервером',
                'icon': '📡',
                'color': '#f0883e',
                'command': 'dhcpmgmt.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },

            # Сетевые инструменты
            {
                'name': 'Командная строка',
                'description': 'Windows Command Prompt (от имени админа)',
                'icon': '⌨',
                'color': '#8b9eb0',
                'command': 'cmd.exe',
                'args': ['/k', 'title Командная строка (Администратор)'],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'PowerShell',
                'description': 'PowerShell командная оболочка (от имени админа)',
                'icon': '💻',
                'color': '#4a9eff',
                'command': 'powershell.exe',
                'args': ['-NoExit', '-Command', 'Write-Host "PowerShell (Администратор)" -ForegroundColor Green'],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'Сетевые подключения',
                'description': 'Настройка сетевых адаптеров',
                'icon': '🔌',
                'color': '#3fb950',
                'command': 'ncpa.cpl',
                'args': [],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'Брандмауэр',
                'description': 'Настройка Windows Firewall',
                'icon': '🛡',
                'color': '#da3633',
                'command': 'wf.msc',
                'args': [],
                'category': 'Сетевые',
                'admin': True
            },

            # Инструменты диагностики
            {
                'name': 'Системная информация',
                'description': 'Информация о системе и железе',
                'icon': 'ℹ',
                'color': '#8b9eb0',
                'command': 'msinfo32.exe',
                'args': [],
                'category': 'Диагностика',
                'admin': False
            },
            {
                'name': 'DirectX диагностика',
                'description': 'Диагностика DirectX и драйверов',
                'icon': '🎮',
                'color': '#4a9eff',
                'command': 'dxdiag.exe',
                'args': [],
                'category': 'Диагностика',
                'admin': False
            },
            {
                'name': 'Монитор ресурсов',
                'description': 'Детальный мониторинг ресурсов',
                'icon': '📈',
                'color': '#f0883e',
                'command': 'perfmon.exe',
                'args': ['/res'],
                'category': 'Диагностика',
                'admin': True
            },
            {
                'name': 'Удаленный рабочий стол',
                'description': 'Подключение к удаленным компьютерам',
                'icon': '🖥',
                'color': '#3fb950',
                'command': 'mstsc.exe',
                'args': [],
                'category': 'Диагностика',
                'admin': False
            },
        ]

        for i, tool in enumerate(tools):
            row = i // 4
            col = i % 4
            button = self.create_tool_button(tool)
            grid.addWidget(button, row, col)
            self.admin_required[tool['name']] = tool['admin']

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid_widget.setLayout(grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("""
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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        scroll.setWidget(grid_widget)
        self.content_layout.addWidget(scroll, stretch=1)

        self.status_label = QLabel("Готов к запуску инструментов")
        self.status_label.setStyleSheet("color: #4a5a6a; font-size: 10px; background: transparent; border: none;")

        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer.setFixedHeight(22)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        self.content_layout.addWidget(footer)

    def create_tool_button(self, tool):
        button = QPushButton()
        button.setFixedHeight(120)
        button.setCursor(Qt.PointingHandCursor)

        admin_indicator = " 🔑" if tool['admin'] else ""
        button.setStyleSheet(f"""
            QPushButton {{
                background: rgba(16, 22, 36, 0.3);
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 10px;
                text-align: left;
                padding: 12px 14px;
            }}
            QPushButton:hover {{
                background: rgba(74, 158, 255, 0.06);
                border-color: rgba(74, 158, 255, 0.15);
            }}
            QPushButton:pressed {{
                background: rgba(74, 158, 255, 0.10);
            }}
        """)

        layout = QVBoxLayout(button)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        icon_label = QLabel(tool['icon'])
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {tool['color']};
                font-size: 22px;
                background: transparent;
                border: none;
                padding: 0;
            }}
        """)
        icon_label.setFixedWidth(30)
        header_layout.addWidget(icon_label)

        name_label = QLabel(f"{tool['name']}{admin_indicator}")
        name_label.setStyleSheet("""
            QLabel {
                color: #e8edf3;
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 0;
            }
        """)
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        layout.addWidget(header_widget)

        desc_label = QLabel(tool['description'])
        desc_label.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 0;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        category_widget = QWidget()
        category_layout = QHBoxLayout(category_widget)
        category_layout.setContentsMargins(0, 0, 0, 0)

        category_label = QLabel(tool['category'])
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {tool['color']};
                font-size: 9px;
                font-weight: 500;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                background: rgba(0, 0, 0, 0.2);
                padding: 2px 10px;
                border-radius: 10px;
                border: none;
            }}
        """)
        category_layout.addWidget(category_label)

        if tool['admin']:
            admin_label = QLabel("Требует админа")
            admin_label.setStyleSheet("""
                QLabel {
                    color: #f0883e;
                    font-size: 8px;
                    font-weight: 400;
                    background: rgba(240, 136, 62, 0.1);
                    padding: 2px 8px;
                    border-radius: 10px;
                    border: 1px solid rgba(240, 136, 62, 0.2);
                }
            """)
            category_layout.addWidget(admin_label)

        category_layout.addStretch()
        layout.addWidget(category_widget)

        button.setProperty('command', tool['command'])
        button.setProperty('args', tool['args'])
        button.setProperty('tool_name', tool['name'])
        button.setProperty('admin', tool['admin'])
        button.clicked.connect(
            lambda checked, cmd=tool['command'], args=tool['args'],
            name=tool['name'], admin=tool['admin']:
            self.launch_tool(cmd, args, name, admin)
        )

        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, cmd=tool['command'], args=tool['args'], name=tool['name'], admin=tool['admin']:
            self.show_context_menu(pos, cmd, args, name, admin)
        )

        return button

    def show_context_menu(self, pos, command, args, name, admin):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #161b22;
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.2);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(74, 158, 255, 0.1);
                color: #e8edf3;
            }
        """)

        action_normal = menu.addAction("Запустить")
        action_normal.triggered.connect(
            lambda: self.launch_tool(command, args, name, admin)
        )

        if admin:
            action_admin = menu.addAction("Запустить от имени администратора")
            action_admin.triggered.connect(
                lambda: self.launch_tool_as_admin(command, args, name)
            )

        menu.addSeparator()
        action_cancel = menu.addAction("Отмена")

        menu.exec(self.sender().mapToGlobal(pos))

    def launch_tool(self, command, args, name, admin=False):
        """Запускает инструмент БЕЗ КОНСОЛИ"""
        try:
            if admin:
                self.launch_tool_as_admin(command, args, name)
                return

            # Запуск БЕЗ консольного окна
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            if command.endswith('.msc'):
                subprocess.Popen(
                    ['mmc', command],
                    startupinfo=startupinfo,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                if args:
                    subprocess.Popen(
                        [command] + args,
                        startupinfo=startupinfo,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(
                        [command],
                        startupinfo=startupinfo,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )

            self.status_label.setText(f"✅ Запущен: {name}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось запустить {name}:\n{str(e)}"
            )
            self.status_label.setText(f" Ошибка запуска: {name}")

    def launch_tool_as_admin(self, command, args, name):
        """Запускает инструмент от имени администратора БЕЗ КОНСОЛИ"""
        try:
            if command.endswith('.msc'):
                cmd = 'mmc'
                full_args = [command] + args if args else [command]
            else:
                cmd = command
                full_args = args if args else []

            # Запускаем с флагом SW_HIDE (0)
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                cmd,
                ' '.join(f'"{arg}"' for arg in full_args) if full_args else None,
                None,
                0  # SW_HIDE - полностью скрывает окно
            )

            self.status_label.setText(f" Запущен от имени админа: {name}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось запустить {name} от имени администратора:\n{str(e)}"
            )
            self.status_label.setText(f" Ошибка запуска админа: {name}")

    def on_show(self):
        self.status_label.setText("Готов к запуску инструментов")
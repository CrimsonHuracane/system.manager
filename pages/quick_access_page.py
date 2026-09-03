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
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from .base_page_modern import BasePage
import subprocess
import ctypes
import os


class IconWidget(QLabel):
    """виджет для иконок"""

    def __init__(self, icon_type, color, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.color = color
        self.setFixedSize(28, 28)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(self.color))
        pen.setWidth(2)
        painter.setPen(pen)

        center_x = self.width() // 2
        center_y = self.height() // 2
        size = 14

        if self.icon_type == 'monitor':
            # Монитор/Экран
            painter.drawRect(center_x - size // 2, center_y - size // 2 + 2, size, size - 4)
            painter.drawLine(center_x - 3, center_y + size // 2 - 2, center_x + 3, center_y + size // 2 + 2)

        elif self.icon_type == 'computer':
            # Компьютер/Управление
            painter.drawRect(center_x - size // 2, center_y - size // 2, size, size - 4)
            painter.drawLine(center_x - 4, center_y + size // 2 - 2, center_x + 4, center_y + size // 2 + 2)
            painter.drawLine(center_x - 2, center_y - size // 2 + 4, center_x + 2, center_y - size // 2 + 4)

        elif self.icon_type == 'list':
            # Список/Логи
            for i in range(3):
                y = center_y - size // 2 + 2 + i * 5
                painter.drawLine(center_x - size // 2 + 2, y, center_x + size // 2 - 2, y)

        elif self.icon_type == 'settings':
            # Шестеренка/Службы
            rect = painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)
            for i in range(6):
                angle = i * 60 * 3.14159 / 180
                x1 = center_x + 6 * (angle)
                y1 = center_y + 6 * (angle)
                painter.drawLine(center_x + 4 * (angle), center_y + 4 * (angle),
                                 center_x + 8 * (angle), center_y + 8 * (angle))

        elif self.icon_type == 'chart':
            # График/Мониторинг
            painter.drawLine(center_x - size // 2 + 2, center_y + size // 2 - 2,
                             center_x - size // 4, center_y - size // 4)
            painter.drawLine(center_x - size // 4, center_y - size // 4,
                             center_x, center_y + 2)
            painter.drawLine(center_x, center_y + 2,
                             center_x + size // 4, center_y - size // 4 + 2)
            painter.drawLine(center_x + size // 4, center_y - size // 4 + 2,
                             center_x + size // 2 - 2, center_y + size // 2 - 2)

        elif self.icon_type == 'users':
            # Пользователи
            painter.drawEllipse(center_x - 4, center_y - 8, 8, 8)
            painter.drawArc(center_x - 7, center_y - 2, 14, 10, 0, 180 * 16)
            painter.drawEllipse(center_x + 8, center_y - 6, 6, 6)
            painter.drawArc(center_x + 6, center_y - 1, 10, 8, 0, 180 * 16)

        elif self.icon_type == 'folder':
            # Папка/Файлы
            painter.drawRect(center_x - size // 2, center_y - size // 4, size, size // 2)
            painter.drawLine(center_x - size // 2, center_y - size // 4,
                             center_x - size // 4, center_y - size // 2)
            painter.drawLine(center_x - size // 4, center_y - size // 2,
                             center_x + size // 4, center_y - size // 2)
            painter.drawLine(center_x + size // 4, center_y - size // 2,
                             center_x + size // 2, center_y - size // 4)

        elif self.icon_type == 'terminal':
            # Терминал/Консоль
            painter.drawRect(center_x - size // 2, center_y - size // 2 + 2, size, size - 4)
            painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
            painter.drawLine(center_x, center_y + 2, center_x - 4, center_y + 6)
            painter.drawLine(center_x + 2, center_y + 6, center_x + 6, center_y + 6)

        elif self.icon_type == 'network':
            # Сеть
            painter.drawEllipse(center_x, center_y - 6, 3, 3)
            painter.drawArc(center_x - 6, center_y - 8, 12, 12, 0, 180 * 16)
            painter.drawArc(center_x - 9, center_y - 11, 18, 18, 0, 180 * 16)
            painter.drawArc(center_x - 12, center_y - 14, 24, 24, 0, 180 * 16)

        elif self.icon_type == 'shield':
            # Щит/Брандмауэр
            path = QPainterPath()
            path.moveTo(center_x, center_y - size // 2)
            path.lineTo(center_x + size // 2, center_y - size // 2 + 3)
            path.lineTo(center_x + size // 2 - 2, center_y + size // 4)
            path.lineTo(center_x, center_y + size // 2 - 2)
            path.lineTo(center_x - size // 2 + 2, center_y + size // 4)
            path.lineTo(center_x - size // 2, center_y - size // 2 + 3)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == 'info':
            # Информация
            painter.drawEllipse(center_x - size // 2, center_y - size // 2, size, size)
            painter.drawLine(center_x, center_y - 3, center_x, center_y + 5)
            painter.drawLine(center_x, center_y + 7, center_x + 1, center_y + 7)

        elif self.icon_type == 'grid':
            # Сетка/Панель
            for i in range(3):
                for j in range(3):
                    x = center_x - size // 2 + 4 + i * 5
                    y = center_y - size // 2 + 4 + j * 5
                    painter.drawRect(x, y, 3, 3)

        elif self.icon_type == 'arrow':
            # Стрелка/Навигация
            painter.drawLine(center_x - size // 2 + 2, center_y, center_x + size // 2 - 2, center_y)
            painter.drawLine(center_x + size // 4, center_y - size // 4, center_x + size // 2 - 2, center_y)
            painter.drawLine(center_x + size // 4, center_y + size // 4, center_x + size // 2 - 2, center_y)


class QuickAccessPage(BasePage):
    def __init__(self):
        super().__init__(
            "Быстрый доступ",
            "Часто используемые инструменты системного администратора"
        )

        self.admin_required = {}

        grid = QGridLayout()
        grid.setSpacing(14)

        tools = [
            # Системные инструменты
            {
                'name': 'Диспетчер задач',
                'description': 'Управление процессами и производительностью',
                'icon': 'monitor',
                'color': '#4a9eff',
                'command': 'taskmgr.exe',
                'args': [],
                'category': 'Системные',
                'admin': False
            },
            {
                'name': 'Управление компьютером',
                'description': 'Управление дисками, службами, пользователями',
                'icon': 'computer',
                'color': '#3fb950',
                'command': 'compmgmt.msc',
                'args': [],
                'category': 'Системные',
                'admin': True
            },
            {
                'name': 'Просмотр событий',
                'description': 'Системные журналы и события',
                'icon': 'list',
                'color': '#f0883e',
                'command': 'eventvwr.msc',
                'args': [],
                'category': 'Системные',
                'admin': False
            },
            {
                'name': 'Службы',
                'description': 'Управление службами Windows',
                'icon': 'settings',
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
                'icon': 'folder',
                'color': '#da3633',
                'command': 'gpmc.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'Active Directory',
                'description': 'Пользователи и компьютеры AD',
                'icon': 'users',
                'color': '#4a9eff',
                'command': 'dsa.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'DNS',
                'description': 'Управление DNS зонами и записями',
                'icon': 'network',
                'color': '#3fb950',
                'command': 'dnsmgmt.msc',
                'args': [],
                'category': 'Администрирование',
                'admin': True
            },
            {
                'name': 'DHCP',
                'description': 'Управление DHCP сервером',
                'icon': 'network',
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
                'icon': 'terminal',
                'color': '#8b9eb0',
                'command': 'cmd.exe',
                'args': ['/k', 'title Командная строка (Администратор)'],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'PowerShell',
                'description': 'PowerShell командная оболочка (от имени админа)',
                'icon': 'terminal',
                'color': '#4a9eff',
                'command': 'powershell.exe',
                'args': ['-NoExit', '-Command', 'Write-Host "PowerShell (Администратор)" -ForegroundColor Green'],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'Сетевые подключения',
                'description': 'Настройка сетевых адаптеров',
                'icon': 'network',
                'color': '#3fb950',
                'command': 'ncpa.cpl',
                'args': [],
                'category': 'Сетевые',
                'admin': True
            },
            {
                'name': 'Брандмауэр',
                'description': 'Настройка Windows Firewall',
                'icon': 'shield',
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
                'icon': 'info',
                'color': '#8b9eb0',
                'command': 'msinfo32.exe',
                'args': [],
                'category': 'Диагностика',
                'admin': False
            },
            {
                'name': 'DirectX диагностика',
                'description': 'Диагностика DirectX и драйверов',
                'icon': 'grid',
                'color': '#4a9eff',
                'command': 'dxdiag.exe',
                'args': [],
                'category': 'Диагностика',
                'admin': False
            },
            {
                'name': 'Монитор ресурсов',
                'description': 'Детальный мониторинг ресурсов',
                'icon': 'chart',
                'color': '#f0883e',
                'command': 'perfmon.exe',
                'args': ['/res'],
                'category': 'Диагностика',
                'admin': True
            },
            {
                'name': 'Удаленный рабочий стол',
                'description': 'Подключение к удаленным компьютерам',
                'icon': 'monitor',
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
        button.setFixedHeight(115)
        button.setCursor(Qt.PointingHandCursor)

        admin_indicator = "" if not tool['admin'] else " 🔑"
        button.setStyleSheet(f"""
            QPushButton {{
                background: rgba(16, 22, 36, 0.3);
                border: 1px solid rgba(48, 54, 61, 0.08);
                border-radius: 10px;
                text-align: left;
                padding: 10px 14px;
            }}
            QPushButton:hover {{
                background: rgba(74, 158, 255, 0.05);
                border-color: rgba(74, 158, 255, 0.12);
            }}
            QPushButton:pressed {{
                background: rgba(74, 158, 255, 0.08);
            }}
        """)

        layout = QVBoxLayout(button)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Иконка
        icon_widget = IconWidget(tool['icon'], tool['color'])
        header_layout.addWidget(icon_widget)

        # Название
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

        # Описание
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

        # Категория
        category_label = QLabel(tool['category'])
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {tool['color']};
                font-size: 8px;
                font-weight: 500;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                background: rgba(0, 0, 0, 0.15);
                padding: 2px 10px;
                border-radius: 10px;
                border: none;
            }}
        """)
        layout.addWidget(category_label, alignment=Qt.AlignLeft)

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
        try:
            if admin:
                self.launch_tool_as_admin(command, args, name)
                return

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

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

            self.status_label.setText(f" Запущен: {name}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось запустить {name}:\n{str(e)}"
            )
            self.status_label.setText(f" Ошибка запуска: {name}")

    def launch_tool_as_admin(self, command, args, name):
        try:
            if command.endswith('.msc'):
                cmd = 'mmc'
                full_args = [command] + args if args else [command]
            else:
                cmd = command
                full_args = args if args else []

            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                cmd,
                ' '.join(f'"{arg}"' for arg in full_args) if full_args else None,
                None,
                0
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
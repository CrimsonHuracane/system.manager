from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QFrame, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QCloseEvent

from pages.monitoring_page import MonitoringPage
from pages.processes_page_modern import ProcessesPage
from pages.services_page import ServicesPage
from pages.computers_page import ComputersPage
from pages.rdp_page import RdpPage
from pages.users_page import UsersPage
from pages.groups_ad_page import GroupsADPage
from pages.quick_access_page import QuickAccessPage
from pages.logs_page_modern import LogsPage
from pages.settings_page_modern import SettingsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Настройки окна
        self.setWindowTitle("Infinity System Manager")
        self.setGeometry(100, 100, 1300, 800)
        self.setMinimumSize(1000, 700)

        # Шрифт
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.PreferFullHinting)
        self.setFont(font)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- БОКОВОЕ МЕНЮ ---
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # --- ОСНОВНАЯ ОБЛАСТЬ КОНТЕНТА ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0e17, stop:1 #141b2b);
            }
        """)
        main_layout.addWidget(self.content_stack, stretch=1)

        # --- ИНИЦИАЛИЗАЦИЯ СТРАНИЦ ---
        self.pages = {}
        self.init_pages()

        # По умолчанию показываем мониторинг
        self.switch_page('monitoring')

    def create_sidebar(self):
        """Создает боковую панель навигации"""
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f141f, stop:1 #161e2e);
                border-right: 1px solid rgba(48, 54, 61, 0.2);
            }
        """)

        # Тень для панели
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(4, 0)
        sidebar.setGraphicsEffect(shadow)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- ЛОГОТИП ---
        logo_widget = QWidget()
        logo_widget.setFixedHeight(90)
        logo_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161e2e, stop:1 #0f141f);
                border-bottom: 1px solid rgba(48, 54, 61, 0.15);
            }
        """)

        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(24, 20, 24, 20)

        logo_label = QLabel("Infinity")
        logo_label.setStyleSheet("""
            QLabel {
                color: #e8edf3;
                font-size: 20px;
                font-weight: 300;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }
        """)
        logo_layout.addWidget(logo_label)

        subtitle_label = QLabel("System Management")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 11px;
                font-weight: 400;
                letter-spacing: 1px;
                text-transform: uppercase;
                background: transparent;
                border: none;
            }
        """)
        logo_layout.addWidget(subtitle_label)

        layout.addWidget(logo_widget)

        # --- МЕНЮ НАВИГАЦИИ ---
        menu_widget = QWidget()
        menu_widget.setStyleSheet("background: transparent;")
        menu_layout = QVBoxLayout(menu_widget)
        menu_layout.setContentsMargins(12, 20, 12, 12)
        menu_layout.setSpacing(2)

        # Заголовок раздела
        section_label = QLabel("Навигация")
        section_label.setStyleSheet("""
            QLabel {
                color: #3a4a5a;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
                padding: 6px 12px;
                background: transparent;
                border: none;
            }
        """)
        menu_layout.addWidget(section_label)

        # Кнопки меню
        btn_quick = self.create_menu_button("Быстрый доступ", 'quick_access')
        menu_layout.addWidget(btn_quick)

        btn_monitoring = self.create_menu_button("Мониторинг", 'monitoring')
        menu_layout.addWidget(btn_monitoring)

        btn_processes = self.create_menu_button("Процессы", 'processes')
        menu_layout.addWidget(btn_processes)

        btn_services = self.create_menu_button("Службы", 'services')
        menu_layout.addWidget(btn_services)

        btn_computers = self.create_menu_button("Компьютеры", 'computers')
        menu_layout.addWidget(btn_computers)

        btn_rdp = self.create_menu_button("RDP", 'rdp')
        menu_layout.addWidget(btn_rdp)

        btn_users = self.create_menu_button("Пользователи", 'users')
        menu_layout.addWidget(btn_users)

        btn_groups_ad = self.create_menu_button("Группы AD", 'groups_ad')
        menu_layout.addWidget(btn_groups_ad)

        btn_logs = self.create_menu_button("Журналы", 'logs')
        menu_layout.addWidget(btn_logs)

        btn_settings = self.create_menu_button("Настройки", 'settings')
        menu_layout.addWidget(btn_settings)

        menu_layout.addStretch()
        layout.addWidget(menu_widget)

        # --- НИЖНЯЯ ЧАСТЬ ---
        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(70)
        bottom_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f141f, stop:1 #0a0e17);
                border-top: 1px solid rgba(48, 54, 61, 0.15);
            }
        """)

        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(24, 12, 24, 12)

        status_label = QLabel("● Система активна")
        status_label.setStyleSheet("""
            QLabel {
                color: #7a8a9a;
                font-size: 12px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        bottom_layout.addWidget(status_label)

        version_label = QLabel("Enterprise v2.0")
        version_label.setStyleSheet("""
            QLabel {
                color: #2a3a4a;
                font-size: 10px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        bottom_layout.addWidget(version_label)

        layout.addWidget(bottom_widget)

        return sidebar

    def create_menu_button(self, text, page_id):
        """Создает кнопку меню"""
        btn = QPushButton(text)
        btn.setProperty('page_id', page_id)
        btn.setFixedHeight(40)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 16px;
                padding-right: 12px;
                font-size: 13px;
                font-weight: 400;
                letter-spacing: 0.2px;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.06);
                color: #e8edf3;
            }
            QPushButton:pressed {
                background: rgba(74, 158, 255, 0.10);
            }
        """)
        btn.clicked.connect(lambda checked=False, pid=page_id: self.switch_page(pid))
        return btn

    def init_pages(self):
        """Инициализирует все страницы и добавляет их в стек"""
        page_classes = {
            'quick_access': QuickAccessPage,
            'monitoring': MonitoringPage,
            'processes': ProcessesPage,
            'services': ServicesPage,
            'computers': ComputersPage,
            'rdp': RdpPage,
            'users': UsersPage,
            'groups_ad': GroupsADPage,
            'logs': LogsPage,
            'settings': SettingsPage,
        }

        for page_id, page_class in page_classes.items():
            try:
                print(f"Инициализация страницы: {page_id}...")
                page = page_class()
                self.pages[page_id] = page
                self.content_stack.addWidget(page)
                print(f"✓ Страница {page_id} инициализирована")
            except Exception as e:
                print(f"✗ Ошибка при инициализации страницы {page_id}: {e}")
                import traceback
                traceback.print_exc()

                # Создаем заглушку вместо сломанной страницы
                from pages.base_page_modern import BasePage
                error_page = BasePage(page_id, f"Ошибка инициализации: {e}")
                self.pages[page_id] = error_page
                self.content_stack.addWidget(error_page)

    def switch_page(self, page_id):
        """Переключает страницу по ID"""
        if page_id in self.pages:
            # Останавливаем потоки на предыдущей странице
            current_page = self.content_stack.currentWidget()
            if current_page and hasattr(current_page, 'stop_worker'):
                current_page.stop_worker()

            # Переключаемся
            self.content_stack.setCurrentWidget(self.pages[page_id])

            # Вызываем on_show для новой страницы
            page = self.pages[page_id]
            if hasattr(page, 'on_show'):
                page.on_show()

    def closeEvent(self, event: QCloseEvent):
        """Корректное завершение при закрытии окна"""
        print("Закрытие приложения...")

        # Останавливаем все потоки на всех страницах
        for page_id, page in self.pages.items():
            # Останавливаем worker
            if hasattr(page, 'worker') and page.worker and page.worker.isRunning():
                print(f"Останавливаем worker на странице {page_id}...")
                try:
                    page.worker.stop()
                    page.worker.wait(1000)
                except:
                    pass

            # Останавливаем action_worker
            if hasattr(page, 'action_worker') and page.action_worker and page.action_worker.isRunning():
                print(f"Останавливаем action_worker на странице {page_id}...")
                try:
                    page.action_worker.stop()
                    page.action_worker.wait(1000)
                except:
                    pass

            # Останавливаем таймеры
            if hasattr(page, 'update_timer') and page.update_timer.isActive():
                print(f"Останавливаем таймер на странице {page_id}...")
                page.update_timer.stop()

            # Вызываем closeEvent страницы
            if hasattr(page, 'closeEvent'):
                try:
                    page.closeEvent(QCloseEvent())
                except:
                    pass

        # Принудительно завершаем все оставшиеся потоки через 2 секунды
        QTimer.singleShot(2000, self.force_quit_threads)

        event.accept()

    def force_quit_threads(self):
        """Принудительное завершение всех потоков"""
        print("Принудительное завершение потоков...")
        for page_id, page in self.pages.items():
            # Жестко останавливаем worker
            if hasattr(page, 'worker') and page.worker:
                try:
                    if page.worker.isRunning():
                        page.worker.terminate()  # Жесткое завершение
                        page.worker.wait(100)
                except:
                    pass

            # Жестко останавливаем action_worker
            if hasattr(page, 'action_worker') and page.action_worker:
                try:
                    if page.action_worker.isRunning():
                        page.action_worker.terminate()
                        page.action_worker.wait(100)
                except:
                    pass
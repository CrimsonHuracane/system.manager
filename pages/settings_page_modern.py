"""
Страница настроек
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QCheckBox,
    QWidget, QVBoxLayout, QSpinBox,
    QFileDialog, QMessageBox, QLineEdit,
    QScrollArea
)
from PySide6.QtCore import Qt, QSettings
from .base_page_modern import BasePage
import os
import sys


class SettingsPage(BasePage):
    def __init__(self):
        super().__init__(
            "Настройки",
            "Конфигурация системы и параметры работы"
        )

        # Загружаем сохраненные настройки
        self.settings = QSettings('InfinitySystem', 'SystemManager')

        # --- СКРОЛЛ ОБЛАСТЬ ---
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
                width: 3px;
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

        # --- КОНТЕЙНЕР С НАСТРОЙКАМИ ---
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 4, 0)
        main_layout.setSpacing(10)

        # --- ГРУППА 1: ОБЩИЕ НАСТРОЙКИ ---
        group1 = self.create_group("Общие настройки")

        self.autostart_check = self.create_checkbox(
            group1,
            "Запускать при старте системы",
            self.get_setting('autostart', False)
        )

        self.notifications_check = self.create_checkbox(
            group1,
            "Показывать уведомления",
            self.get_setting('notifications', True)
        )

        main_layout.addWidget(group1)

        # --- ГРУППА 2: МОНИТОРИНГ ---
        group2 = self.create_group("Мониторинг")

        # Интервал обновления
        interval_widget = QWidget()
        interval_widget.setStyleSheet("background: transparent;")
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 2, 0, 2)
        interval_layout.setSpacing(8)

        interval_label = QLabel("Интервал обновления:")
        interval_label.setStyleSheet("color: #8b9eb0; font-size: 12px; background: transparent; border: none;")
        interval_layout.addWidget(interval_label)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(200, 2000)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setSuffix(" мс")
        self.interval_spin.setValue(self.get_setting('monitoring_interval', 500))
        self.interval_spin.setFixedWidth(90)
        self.interval_spin.setStyleSheet(self.spinbox_style())
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()

        group2.layout().addWidget(interval_widget)

        # Автообновление
        self.auto_refresh_check = self.create_checkbox(
            group2,
            "Автоматически обновлять данные",
            self.get_setting('auto_refresh', True)
        )

        # Показывать графики
        self.graphs_check = self.create_checkbox(
            group2,
            "Показывать графики",
            self.get_setting('show_graphs', True)
        )

        main_layout.addWidget(group2)

        # --- ГРУППА 3: ПРОЦЕССЫ ---
        group3 = self.create_group("Управление процессами")

        self.confirm_kill_check = self.create_checkbox(
            group3,
            "Подтверждать завершение процессов",
            self.get_setting('confirm_kill', True)
        )

        self.show_system_check = self.create_checkbox(
            group3,
            "Показывать системные процессы",
            self.get_setting('show_system_processes', True)
        )

        main_layout.addWidget(group3)

        # --- ГРУППА 4: ЛОГИ ---
        group4 = self.create_group("Системные логи")

        self.log_auto_refresh = self.create_checkbox(
            group4,
            "Автоматически обновлять логи",
            self.get_setting('log_auto_refresh', True)
        )

        # Интервал обновления логов
        log_interval_widget = QWidget()
        log_interval_widget.setStyleSheet("background: transparent;")
        log_interval_layout = QHBoxLayout(log_interval_widget)
        log_interval_layout.setContentsMargins(0, 2, 0, 2)
        log_interval_layout.setSpacing(8)

        log_interval_label = QLabel("Интервал обновления логов:")
        log_interval_label.setStyleSheet("color: #8b9eb0; font-size: 12px; background: transparent; border: none;")
        log_interval_layout.addWidget(log_interval_label)

        self.log_interval_spin = QSpinBox()
        self.log_interval_spin.setRange(5, 60)
        self.log_interval_spin.setSuffix(" сек")
        self.log_interval_spin.setValue(self.get_setting('log_refresh_interval', 15))
        self.log_interval_spin.setFixedWidth(80)
        self.log_interval_spin.setStyleSheet(self.spinbox_style())
        log_interval_layout.addWidget(self.log_interval_spin)
        log_interval_layout.addStretch()

        group4.layout().addWidget(log_interval_widget)

        # Папка для экспорта
        export_widget = QWidget()
        export_widget.setStyleSheet("background: transparent;")
        export_layout = QHBoxLayout(export_widget)
        export_layout.setContentsMargins(0, 2, 0, 2)
        export_layout.setSpacing(8)

        export_label = QLabel("Папка для экспорта:")
        export_label.setStyleSheet("color: #8b9eb0; font-size: 12px; background: transparent; border: none;")
        export_layout.addWidget(export_label)

        self.export_path_edit = QLineEdit()
        default_path = os.path.expanduser("~/Documents/Logs")
        self.export_path_edit.setText(self.get_setting('export_path', default_path))
        self.export_path_edit.setFixedHeight(26)
        self.export_path_edit.setStyleSheet("""
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
        """)
        export_layout.addWidget(self.export_path_edit, stretch=1)

        btn_browse = QPushButton("Обзор")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setFixedHeight(26)
        btn_browse.setFixedWidth(60)
        btn_browse.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 5px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
            }
        """)
        btn_browse.clicked.connect(self.browse_export_path)
        export_layout.addWidget(btn_browse)

        group4.layout().addWidget(export_widget)

        main_layout.addWidget(group4)
        main_layout.addStretch()

        scroll.setWidget(container)
        self.content_layout.addWidget(scroll, stretch=1)

        # --- КНОПКИ ВНИЗУ ---
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_widget.setFixedHeight(50)
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 8, 0, 0)
        buttons_layout.setSpacing(10)

        btn_save = QPushButton("Сохранить настройки")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(34)
        btn_save.setFixedWidth(170)
        btn_save.setStyleSheet("""
            QPushButton {
                background: rgba(74, 158, 255, 0.8);
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.9);
            }
            QPushButton:pressed {
                background: rgba(74, 158, 255, 0.6);
            }
        """)
        btn_save.clicked.connect(self.save_settings)
        buttons_layout.addWidget(btn_save)

        btn_reset = QPushButton("Сбросить")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setFixedHeight(34)
        btn_reset.setFixedWidth(120)
        btn_reset.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: 1px solid rgba(48, 54, 61, 0.15);
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(218, 54, 51, 0.06);
                color: #da3633;
                border-color: rgba(218, 54, 51, 0.15);
            }
            QPushButton:pressed {
                background: rgba(218, 54, 51, 0.12);
            }
        """)
        btn_reset.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(btn_reset)

        buttons_layout.addStretch()

        self.content_layout.addWidget(buttons_widget)

    def create_group(self, title):
        """Создает компактную группу настроек"""
        group = QWidget()
        group.setStyleSheet("""
            QWidget {
                background: rgba(16, 22, 36, 0.10);
                border: 1px solid rgba(48, 54, 61, 0.05);
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #e8edf3;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.3px;
                background: transparent;
                border: none;
                padding-bottom: 2px;
            }
        """)
        layout.addWidget(title_label)

        return group

    def create_checkbox(self, parent, text, checked=False):
        """Создает компактный чекбокс"""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #8b9eb0;
                font-size: 12px;
                font-weight: 400;
                spacing: 8px;
                background: transparent;
                padding: 2px 0;
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
            QCheckBox::indicator:hover {
                border-color: rgba(74, 158, 255, 0.3);
            }
        """)
        parent.layout().addWidget(checkbox)
        return checkbox

    def spinbox_style(self):
        """Стиль для спинбоксов"""
        return """
            QSpinBox {
                background: rgba(13, 17, 23, 0.2);
                color: #8b9eb0;
                border: 1px solid rgba(48, 54, 61, 0.1);
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                font-weight: 400;
            }
            QSpinBox:hover {
                border-color: rgba(74, 158, 255, 0.2);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: rgba(13, 17, 23, 0.3);
                border: none;
                border-radius: 2px;
                width: 14px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(74, 158, 255, 0.1);
            }
        """

    def get_setting(self, key, default):
        """Получает значение настройки"""
        value = self.settings.value(key, default)
        if value == 'true':
            return True
        elif value == 'false':
            return False
        return value

    def save_settings(self):
        """Сохраняет все настройки"""
        try:
            # Общие
            self.settings.setValue('autostart', self.autostart_check.isChecked())
            self.settings.setValue('notifications', self.notifications_check.isChecked())

            # Мониторинг
            self.settings.setValue('monitoring_interval', self.interval_spin.value())
            self.settings.setValue('auto_refresh', self.auto_refresh_check.isChecked())
            self.settings.setValue('show_graphs', self.graphs_check.isChecked())

            # Процессы
            self.settings.setValue('confirm_kill', self.confirm_kill_check.isChecked())
            self.settings.setValue('show_system_processes', self.show_system_check.isChecked())

            # Логи
            self.settings.setValue('log_auto_refresh', self.log_auto_refresh.isChecked())
            self.settings.setValue('log_refresh_interval', self.log_interval_spin.value())
            self.settings.setValue('export_path', self.export_path_edit.text())

            # Применяем настройки
            self.apply_settings()

            QMessageBox.information(
                self,
                "Успешно",
                "Настройки сохранены и применены"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сохранить настройки:\n{str(e)}"
            )

    def apply_settings(self):
        """Применяет настройки к приложению"""
        self.set_autostart(self.autostart_check.isChecked())

        interval = self.interval_spin.value()

        main_window = self.window()
        if hasattr(main_window, 'pages') and 'monitoring' in main_window.pages:
            monitoring_page = main_window.pages['monitoring']
            if hasattr(monitoring_page, 'update_timer'):
                monitoring_page.update_timer.setInterval(interval)
                if self.auto_refresh_check.isChecked():
                    if not monitoring_page.update_timer.isActive():
                        monitoring_page.update_timer.start()
                else:
                    monitoring_page.update_timer.stop()

        if hasattr(main_window, 'pages') and 'monitoring' in main_window.pages:
            monitoring_page = main_window.pages['monitoring']
            if hasattr(monitoring_page, 'graphs_widget'):
                monitoring_page.graphs_widget.setVisible(self.graphs_check.isChecked())

        if hasattr(main_window, 'pages') and 'logs' in main_window.pages:
            logs_page = main_window.pages['logs']
            if hasattr(logs_page, 'update_timer'):
                log_interval = self.log_interval_spin.value() * 1000
                logs_page.update_timer.setInterval(log_interval)
                if self.log_auto_refresh.isChecked():
                    if not logs_page.update_timer.isActive():
                        logs_page.update_timer.start()
                else:
                    logs_page.update_timer.stop()

    def set_autostart(self, enable):
        """Устанавливает автозапуск в реестре Windows"""
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            if enable:
                if getattr(sys, 'frozen', False):
                    app_path = sys.executable
                else:
                    main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
                    app_path = f'"{sys.executable}" "{main_path}"'

                winreg.SetValueEx(
                    key,
                    "InfinitySystemManager",
                    0,
                    winreg.REG_SZ,
                    app_path
                )
            else:
                try:
                    winreg.DeleteValue(key, "InfinitySystemManager")
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
        except Exception as e:
            print(f"Ошибка при настройке автозапуска: {e}")

    def reset_settings(self):
        """Сбрасывает настройки по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        try:
            self.settings.clear()

            self.autostart_check.setChecked(False)
            self.notifications_check.setChecked(True)
            self.interval_spin.setValue(500)
            self.auto_refresh_check.setChecked(True)
            self.graphs_check.setChecked(True)
            self.confirm_kill_check.setChecked(True)
            self.show_system_check.setChecked(True)
            self.log_auto_refresh.setChecked(True)
            self.log_interval_spin.setValue(15)
            self.export_path_edit.setText(os.path.expanduser("~/Documents/Logs"))

            self.apply_settings()

            QMessageBox.information(
                self,
                "Успешно",
                "Настройки сброшены к значениям по умолчанию"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сбросить настройки:\n{str(e)}"
            )

    def browse_export_path(self):
        """Выбор папки для экспорта логов"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для экспорта логов",
            self.export_path_edit.text()
        )
        if path:
            self.export_path_edit.setText(path)

    def on_show(self):
        """Страница показана"""
        pass
"""
Страница управления процессами
Использует psutil для получения информации о процессах
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QFrame,
    QVBoxLayout, QWidget, QLineEdit, QScrollArea,
    QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .base_page_modern import BasePage
import psutil
import os


class ProcessWorker(QThread):
    """Поток для получения списка процессов"""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                if not self._is_running:
                    break
                try:
                    proc_info = proc.info
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'] or 'Unknown',
                        'cpu': round(proc_info['cpu_percent'] or 0, 1),
                        'memory': self._format_memory(proc_info['memory_info'].rss if proc_info['memory_info'] else 0),
                        'status': self._translate_status(proc_info['status']),
                        'exe': proc.exe() if hasattr(proc, 'exe') and proc.exe() else '',
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self.finished.emit(processes)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

    @staticmethod
    def _format_memory(bytes_value):
        """Форматирует байты в читаемый вид"""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.1f} MB"
        else:
            return f"{bytes_value / (1024 ** 3):.2f} GB"

    @staticmethod
    def _translate_status(status):
        """Переводит статус процесса на русский"""
        status_map = {
            'running': 'активен',
            'sleeping': 'ожидание',
            'disk-sleep': 'ожидание диска',
            'stopped': 'остановлен',
            'zombie': 'зомби',
            'idle': 'ожидание',
            'waiting': 'ожидание',
            'locked': 'заблокирован',
        }
        return status_map.get(status, status)


class ProcessesPage(BasePage):
    def __init__(self):
        super().__init__(
            "Управление процессами",
            "Список активных процессов и управление ими"
        )

        self.processes = []
        self.filtered_processes = []
        self.worker = None
        self.search_text = ""
        self.sort_column = 0  # 0 - name, 1 - pid, 2 - cpu, 3 - memory, 4 - status
        self.sort_ascending = False

        # --- СТАТИСТИКА ---
        self.stats_widget = QWidget()
        self.stats_widget.setStyleSheet("background: transparent;")
        self.stats_widget.setFixedHeight(86)

        self.stats_layout = QHBoxLayout(self.stats_widget)
        self.stats_layout.setContentsMargins(0, 3, 0, 0)
        self.stats_layout.setSpacing(64)

        # Создаем элементы статистики
        self.stats_labels = {}
        stats_data = [
            ("total", "0", "всего процессов"),
            ("active", "0", "активных"),
            ("idle", "0", "ожидание"),
            ("cpu", "0%", "нагрузка CPU"),
        ]

        for key, value, caption in stats_data:
            item = QWidget()
            item.setStyleSheet("background: transparent;")
            layout = QVBoxLayout(item)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            value_label = QLabel(value)
            value_label.setObjectName(f"stat_{key}")
            value_label.setStyleSheet("""
                QLabel {
                    color: #e8edf3;
                    font-size: 29px;
                    font-weight: 300;
                    background: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            layout.addWidget(value_label)
            self.stats_labels[key] = value_label

            caption_label = QLabel(caption.upper())
            caption_label.setStyleSheet("""
                QLabel {
                    color: #4a5a6a;
                    font-size: 8px;
                    font-weight: 600;
                    letter-spacing: 0.9px;
                    background: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            layout.addWidget(caption_label)

            self.stats_layout.addWidget(item)

        self.stats_layout.addStretch()
        self.content_layout.addWidget(self.stats_widget)

        # --- TOOLBAR ---
        toolbar = QWidget()
        toolbar.setStyleSheet("background: transparent;")
        toolbar.setFixedHeight(43)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 4, 0, 4)
        toolbar_layout.setSpacing(2)

        # Кнопка обновления
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7d95;
                border: none;
                border-radius: 5px;
                padding: 5px 9px;
                font-size: 12px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #dbe4ee;
            }
            QPushButton:pressed {
                background: rgba(74, 158, 255, 0.075);
            }
        """)
        self.btn_refresh.clicked.connect(self.load_processes)
        toolbar_layout.addWidget(self.btn_refresh)

        toolbar_layout.addStretch()

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск процессов")
        self.search_input.setFixedSize(180, 29)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.012);
                color: #8b9eb0;
                border: none;
                border-bottom: 1px solid rgba(74, 158, 255, 0.09);
                padding: 0 2px 2px 2px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-bottom-color: rgba(74, 158, 255, 0.30);
            }
            QLineEdit::placeholder {
                color: #3a4a5a;
            }
        """)
        self.search_input.textChanged.connect(self.on_search)
        toolbar_layout.addWidget(self.search_input)

        self.content_layout.addWidget(toolbar)

        # --- СПИСОК ПРОЦЕССОВ ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("""
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
                background: rgba(48, 54, 61, 0.10);
                border-radius: 2px;
                min-height: 26px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(74, 158, 255, 0.18);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent; border: none;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 8, 0, 8)
        self.list_layout.setSpacing(2)

        # Заголовки с возможностью сортировки
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("background: transparent;")
        self.header_widget.setCursor(Qt.PointingHandCursor)

        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(8, 0, 2, 5)
        self.header_layout.setSpacing(0)

        # Заголовки колонок
        header_config = [
            ("ПРОЦЕСС", 205, 0),
            ("PID", 55, 1),
            ("CPU", 70, 2),
            ("ПАМЯТЬ", 90, 3),
            ("СОСТОЯНИЕ", 100, 4),
        ]

        self.header_labels = []
        for text, width, col in header_config:
            label = QLabel(text)
            label.setFixedWidth(width)
            label.setProperty('col', col)
            label.setStyleSheet("""
                QLabel {
                    color: #344353;
                    font-size: 8px;
                    font-weight: 600;
                    letter-spacing: 0.9px;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
                QLabel:hover {
                    color: #6b7d95;
                }
            """)
            label.mousePressEvent = lambda e, c=col: self.on_header_click(c)
            self.header_layout.addWidget(label)
            self.header_labels.append(label)

        # Индикатор сортировки
        self.sort_indicator = QLabel("")
        self.sort_indicator.setFixedWidth(30)
        self.sort_indicator.setStyleSheet("""
            QLabel {
                color: #4a9eff;
                font-size: 10px;
                font-weight: 400;
                background: transparent;
                border: none;
                padding: 0;
            }
        """)
        self.header_layout.addWidget(self.sort_indicator)

        self.header_layout.addStretch()
        self.list_layout.addWidget(self.header_widget)

        # Контейнер для строк процессов
        self.processes_container = QWidget()
        self.processes_container.setStyleSheet("background: transparent;")
        self.processes_layout = QVBoxLayout(self.processes_container)
        self.processes_layout.setContentsMargins(0, 0, 0, 0)
        self.processes_layout.setSpacing(2)
        self.list_layout.addWidget(self.processes_container)

        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        self.content_layout.addWidget(self.scroll, stretch=1)

        # --- FOOTER ---
        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer.setFixedHeight(25)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 2, 0, 0)

        self.footer_info = QLabel("Загрузка процессов...")
        self.footer_info.setStyleSheet("""
            QLabel {
                color: #3a4a5a;
                font-size: 10px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        footer_layout.addWidget(self.footer_info)
        footer_layout.addStretch()

        self.content_layout.addWidget(footer)

        # Загружаем процессы при открытии
        self.load_processes()

    def on_header_click(self, col):
        """Обработка клика по заголовку для сортировки"""
        if self.sort_column == col:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = col
            self.sort_ascending = True

        self.apply_filter()
        self.update_sort_indicator()

    def update_sort_indicator(self):
        """Обновляет индикатор сортировки"""
        arrow = "↑" if self.sort_ascending else "↓"
        col_names = ["Имя", "PID", "CPU", "Память", "Состояние"]
        self.sort_indicator.setText(f"{col_names[self.sort_column]} {arrow}")

    def load_processes(self):
        """Загружает список процессов в отдельном потоке"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.btn_refresh.setText("Загрузка...")
        self.btn_refresh.setEnabled(False)
        self.footer_info.setText("Загрузка процессов...")

        self.worker = ProcessWorker()
        self.worker.finished.connect(self.on_processes_loaded)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def on_processes_loaded(self, processes):
        """Обработка загруженных процессов"""
        self.processes = processes
        self.update_stats()
        self.apply_filter()

        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.footer_info.setText(f"Показано: {len(self.filtered_processes)} из {len(self.processes)} процессов")
        self.update_sort_indicator()

    def on_process_error(self, error):
        """Обработка ошибки загрузки"""
        self.btn_refresh.setText("Обновить")
        self.btn_refresh.setEnabled(True)
        self.footer_info.setText(f"Ошибка: {error}")
        QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить процессы:\n{error}")

    def update_stats(self):
        """Обновляет статистику"""
        total = len(self.processes)
        active = sum(1 for p in self.processes if p['status'] == 'активен')
        idle = sum(1 for p in self.processes if p['status'] == 'ожидание')
        cpu_avg = round(sum(p['cpu'] for p in self.processes) / total if total > 0 else 0, 1)

        self.stats_labels['total'].setText(str(total))
        self.stats_labels['active'].setText(str(active))
        self.stats_labels['idle'].setText(str(idle))
        self.stats_labels['cpu'].setText(f"{cpu_avg}%")

    def apply_filter(self):
        """Применяет фильтр поиска и сортировку"""
        search = self.search_text.lower().strip()

        # Фильтрация
        if search:
            self.filtered_processes = [
                p for p in self.processes
                if search in p['name'].lower() or str(p['pid']) == search
            ]
        else:
            self.filtered_processes = self.processes.copy()

        # Сортировка
        sort_key = ['name', 'pid', 'cpu', 'memory', 'status'][self.sort_column]

        def get_sort_value(item):
            val = item[sort_key]
            if sort_key == 'pid':
                return int(val)
            elif sort_key == 'cpu':
                return float(val)
            elif sort_key == 'memory':
                # Парсим размер памяти для сортировки
                mem_str = val
                try:
                    if 'GB' in mem_str:
                        return float(mem_str.replace(' GB', '')) * 1024
                    elif 'MB' in mem_str:
                        return float(mem_str.replace(' MB', ''))
                    elif 'KB' in mem_str:
                        return float(mem_str.replace(' KB', '')) / 1024
                    else:
                        return 0
                except:
                    return 0
            else:
                return str(val).lower()

        self.filtered_processes.sort(
            key=get_sort_value,
            reverse=not self.sort_ascending
        )

        self.display_processes()
        self.footer_info.setText(f"Показано: {len(self.filtered_processes)} из {len(self.processes)} процессов")

    def display_processes(self):
        """Отображает процессы в списке"""
        # Очищаем контейнер
        while self.processes_layout.count():
            child = self.processes_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.filtered_processes:
            # Пустое состояние
            empty_label = QLabel("Нет процессов для отображения")
            empty_label.setStyleSheet("""
                QLabel {
                    color: #2a3a4a;
                    font-size: 13px;
                    font-weight: 300;
                    background: transparent;
                    border: none;
                    padding: 40px 0;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            self.processes_layout.addWidget(empty_label)
            return

        for proc in self.filtered_processes:
            row = QFrame()
            row.setObjectName("processRow")
            row.setFixedHeight(44)
            row.setStyleSheet("""
                QFrame#processRow {
                    background: transparent;
                    border: none;
                    border-radius: 7px;
                }
                QFrame#processRow:hover {
                    background: rgba(74, 158, 255, 0.035);
                }
            """)

            # Сохраняем PID для кнопки завершения
            row.setProperty('pid', proc['pid'])

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 0, 2, 0)
            row_layout.setSpacing(0)

            # Маркер
            marker = QLabel("·")
            marker.setFixedWidth(13)
            marker.setStyleSheet("""
                QLabel {
                    color: #4a9eff;
                    font-size: 20px;
                    font-weight: 300;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            row_layout.addWidget(marker)

            # Имя
            name = QLabel(proc['name'])
            name.setFixedWidth(192)
            name.setStyleSheet("""
                QLabel {
                    color: #a5b3c2;
                    font-size: 13px;
                    font-weight: 450;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            row_layout.addWidget(name)

            # PID
            pid = QLabel(str(proc['pid']))
            pid.setFixedWidth(55)
            pid.setStyleSheet("""
                QLabel {
                    color: #64768b;
                    font-size: 12px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            row_layout.addWidget(pid)

            # CPU
            cpu_text = f"{proc['cpu']}%"
            cpu_label = QLabel(cpu_text)
            cpu_label.setFixedWidth(70)
            cpu_label.setStyleSheet("""
                QLabel {
                    color: #8393a5;
                    font-size: 12px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            row_layout.addWidget(cpu_label)

            # Память
            mem = QLabel(proc['memory'])
            mem.setFixedWidth(90)
            mem.setStyleSheet("""
                QLabel {
                    color: #64768b;
                    font-size: 12px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            row_layout.addWidget(mem)

            # Статус
            status_color = "#3fb950" if proc['status'] == 'активен' else "#68798d"
            status_box = QWidget()
            status_box.setStyleSheet("background: transparent;")
            status_layout = QHBoxLayout(status_box)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setSpacing(6)

            dot = QLabel("●")
            dot.setStyleSheet(f"""
                QLabel {{
                    color: {status_color};
                    font-size: 6px;
                    background: transparent;
                    border: none;
                }}
            """)
            status_layout.addWidget(dot)

            status = QLabel(proc['status'])
            status.setStyleSheet(f"""
                QLabel {{
                    color: {status_color};
                    font-size: 11px;
                    font-weight: 400;
                    background: transparent;
                    border: none;
                }}
            """)
            status_layout.addWidget(status)
            status_layout.addStretch()

            status_box.setFixedWidth(100)
            row_layout.addWidget(status_box)

            row_layout.addStretch()

            # Кнопка завершения
            close = QPushButton("×")
            close.setCursor(Qt.PointingHandCursor)
            close.setFixedSize(26, 26)
            close.setProperty('pid', proc['pid'])
            close.setStyleSheet("""
                QPushButton {
                    color: #344353;
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    font-size: 15px;
                    font-weight: 300;
                    padding: 0;
                }
                QPushButton:hover {
                    color: #da3633;
                    background: rgba(218, 54, 51, 0.07);
                }
            """)
            close.clicked.connect(lambda checked, p=proc: self.kill_process(p['pid'], p['name']))
            row_layout.addWidget(close)

            self.processes_layout.addWidget(row)

    def on_search(self, text):
        """Обработка поиска"""
        self.search_text = text
        self.apply_filter()

    def kill_process(self, pid, name):
        """Завершает процесс с обработкой ошибок доступа"""
        # Проверяем, не системный ли это процесс
        system_processes = [0, 4, 8, 12, 14, 16, 20]  # Типичные системные PID
        if pid in system_processes:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Невозможно завершить системный процесс {name} (PID: {pid})"
            )
            return

        # Проверяем, не является ли процесс системным
        try:
            proc = psutil.Process(pid)
            # Проверяем, системный ли это процесс
            if proc.name() in ['csrss.exe', 'lsass.exe', 'winlogon.exe', 'services.exe', 'smss.exe', 'svchost.exe']:
                # Некоторые svchost можно завершить, но лучше предупредить
                if pid <= 1000:
                    QMessageBox.warning(
                        self,
                        "Осторожно",
                        f"Это системный процесс {name} (PID: {pid}). Завершение может привести к нестабильности системы."
                    )
        except:
            pass

        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите завершить процесс {name} (PID: {pid})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        try:
            proc = psutil.Process(pid)

            # Пробуем сначала terminate (мягкое завершение)
            try:
                proc.terminate()
                # Даем время на завершение
                proc.wait(timeout=3)
                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Процесс {name} (PID: {pid}) успешно завершен"
                )
                self.load_processes()  # Обновляем список
                return
            except psutil.AccessDenied:
                # Если terminate не сработал, пробуем kill (принудительное)
                reply_force = QMessageBox.question(
                    self,
                    "Ошибка доступа",
                    f"Недостаточно прав для мягкого завершения процесса {name}.\n"
                    f"Хотите попробовать принудительно завершить процесс?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply_force == QMessageBox.Yes:
                    try:
                        proc.kill()
                        QMessageBox.information(
                            self,
                            "Успешно",
                            f"Процесс {name} (PID: {pid}) принудительно завершен"
                        )
                        self.load_processes()
                    except psutil.AccessDenied:
                        QMessageBox.warning(
                            self,
                            "Ошибка доступа",
                            f"Недостаточно прав для завершения процесса {name} (PID: {pid}).\n"
                            f"Попробуйте запустить программу от имени администратора."
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            f"Не удалось завершить процесс {name} (PID: {pid}):\n{str(e)}"
                        )
                return

        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Ошибка", f"Процесс {name} (PID: {pid}) уже не существует")
            self.load_processes()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось завершить процесс {name} (PID: {pid}):\n{str(e)}"
            )

    def on_show(self):
        """Страница показана - обновляем данные"""
        self.load_processes()
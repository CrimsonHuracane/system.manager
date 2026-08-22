"""
Страница мониторинга системы
"""

from PySide6.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QWidget, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from .base_page_modern import BasePage
import psutil
import datetime
import time
import numpy as np
import pyqtgraph as pg


class SystemMonitorWorker(QThread):
    """Поток для получения данных мониторинга"""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        try:
            data = {}

            # CPU
            data['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            data['cpu_count'] = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            data['cpu_freq'] = cpu_freq.current if cpu_freq else 0

            # Память
            mem = psutil.virtual_memory()
            data['memory_total'] = mem.total
            data['memory_used'] = mem.used
            data['memory_percent'] = mem.percent
            data['memory_available'] = mem.available

            # Диски
            disks = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    })
                except:
                    continue
            data['disks'] = disks

            # Сеть
            net = psutil.net_io_counters()
            data['net_sent'] = net.bytes_sent
            data['net_recv'] = net.bytes_recv

            # Система
            data['boot_time'] = psutil.boot_time()
            data['process_count'] = len(psutil.pids())

            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


class CollapsibleGraph(QWidget):
    """Компактный виджет с графиком и кнопкой сворачивания"""

    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.color = color
        self.title = title
        self.data_history = []
        self.max_points = 60
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # --- ЗАГОЛОВОК С КНОПКОЙ ---
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: rgba(16, 22, 36, 0.12);
                border-radius: 6px;
                border: 1px solid rgba(48, 54, 61, 0.04);
            }
            QWidget:hover {
                background: rgba(16, 22, 36, 0.20);
            }
        """)
        header.setFixedHeight(34)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 6, 0)
        header_layout.setSpacing(10)

        # --- НАЗВАНИЕ ---
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #8b9eb0;
                font-size: 11px;
                font-weight: 500;
                letter-spacing: 0.3px;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(title_label)

        # --- СТАТИСТИКА ---
        self.stats_label = QLabel("0%")
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        header_layout.addWidget(self.stats_label)

        header_layout.addStretch()

        # --- КНОПКА СВОРАЧИВАНИЯ ---
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setText("−")
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(74, 158, 255, 0.06);
                color: #6b7d95;
                border: 1px solid rgba(74, 158, 255, 0.06);
                border-radius: 5px;
                font-size: 14px;
                font-weight: 300;
                padding: 0;
            }}
            QPushButton:hover {{
                background: rgba(74, 158, 255, 0.12);
                color: #e8edf3;
                border-color: rgba(74, 158, 255, 0.12);
            }}
            QPushButton:pressed {{
                background: rgba(74, 158, 255, 0.18);
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_btn)

        # --- СТАТУС ДОТ ---
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-size: 5px;
                background: transparent;
                border: none;
                padding: 0 2px 0 0;
            }}
        """)
        header_layout.addWidget(self.status_dot)

        layout.addWidget(header)

        # --- КОНТЕЙНЕР ГРАФИКА ---
        self.graph_container = QWidget()
        self.graph_container.setStyleSheet("""
            QWidget {
                background: rgba(13, 17, 23, 0.10);
                border-radius: 6px;
                border: 1px solid rgba(48, 54, 61, 0.04);
            }
        """)

        graph_layout = QVBoxLayout(self.graph_container)
        graph_layout.setContentsMargins(0, 0, 0, 0)

        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0a0e17')
        self.plot_widget.setLabel('left', '', color='#6b7d95')
        self.plot_widget.setLabel('bottom', '', color='#6b7d95')
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.05)
        self.plot_widget.setMinimumHeight(80)
        self.plot_widget.setMaximumHeight(120)

        # Скрываем оси для компактности
        self.plot_widget.getAxis('left').setStyle(tickLength=0)
        self.plot_widget.getAxis('bottom').setStyle(tickLength=0)
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color='#2a3a4a'))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#2a3a4a'))

        # Линия графика
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color=self.color, width=2))

        # Заливка под графиком
        self.fill = pg.FillBetweenItem(
            self.curve,
            pg.PlotDataItem([], [], pen=pg.mkPen(color=self.color, width=0)),
            brush=pg.mkBrush(color=self.color, alpha=20)
        )
        self.plot_widget.addItem(self.fill)

        graph_layout.addWidget(self.plot_widget)
        layout.addWidget(self.graph_container)

        # Анимация
        self.animation = QPropertyAnimation(self.graph_container, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.setMinimumHeight(130)

    def toggle_collapse(self):
        """Сворачивает/разворачивает график"""
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.animation.setEndValue(0)
            self.animation.start()
            self.toggle_btn.setText("+")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(74, 158, 255, 0.04);
                    color: #6b7d95;
                    border: 1px solid rgba(74, 158, 255, 0.04);
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: 300;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(74, 158, 255, 0.10);
                    color: #e8edf3;
                    border-color: rgba(74, 158, 255, 0.10);
                }
            """)
            self.setMaximumHeight(42)
        else:
            self.animation.setEndValue(16777215)
            self.animation.start()
            self.toggle_btn.setText("−")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(74, 158, 255, 0.06);
                    color: #6b7d95;
                    border: 1px solid rgba(74, 158, 255, 0.06);
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: 300;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(74, 158, 255, 0.12);
                    color: #e8edf3;
                    border-color: rgba(74, 158, 255, 0.12);
                }
            """)
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(130)

    def update_data(self, value):
        """Обновляет данные графика"""
        self.data_history.append(value)
        if len(self.data_history) > self.max_points:
            self.data_history.pop(0)

        x = np.arange(len(self.data_history))
        self.curve.setData(x, self.data_history)

        if self.data_history:
            current = self.data_history[-1]
            self.stats_label.setText(f"{current:.1f}%")

            if current > 80:
                self.stats_label.setStyleSheet(
                    "color: #da3633; font-size: 12px; font-weight: 600; background: transparent; border: none;")
                self.status_dot.setStyleSheet(
                    "color: #da3633; font-size: 5px; background: transparent; border: none; padding: 0 2px 0 0;")
            elif current > 60:
                self.stats_label.setStyleSheet(
                    f"color: #f0883e; font-size: 12px; font-weight: 600; background: transparent; border: none;")
                self.status_dot.setStyleSheet(
                    "color: #f0883e; font-size: 5px; background: transparent; border: none; padding: 0 2px 0 0;")
            else:
                self.stats_label.setStyleSheet(
                    f"color: {self.color}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
                self.status_dot.setStyleSheet(
                    f"color: {self.color}; font-size: 5px; background: transparent; border: none; padding: 0 2px 0 0;")


class MonitoringPage(BasePage):
    def __init__(self):
        super().__init__(
            "Мониторинг системы",
            "Актуальное состояние серверной инфраструктуры"
        )

        self.worker = None
        self.prev_net_sent = 0
        self.prev_net_recv = 0
        self.prev_time = 0

        # --- ОСНОВНЫЕ МЕТРИКИ (3 в ряд) ---
        self.metrics_widget = QWidget()
        self.metrics_widget.setStyleSheet("background: transparent;")
        metrics_layout = QHBoxLayout(self.metrics_widget)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(16)

        self.cpu_card = self.create_metric_card("Процессор", "0%", "#4a9eff", 0)
        self.memory_card = self.create_metric_card("Память", "0%", "#3fb950", 0)
        self.disk_card = self.create_metric_card("Диск", "0%", "#f0883e", 0)

        metrics_layout.addWidget(self.cpu_card)
        metrics_layout.addWidget(self.memory_card)
        metrics_layout.addWidget(self.disk_card)

        self.content_layout.addWidget(self.metrics_widget)

        # --- ГРАФИКИ (3 в ряд) ---
        self.graphs_widget = QWidget()
        self.graphs_widget.setStyleSheet("background: transparent;")
        graphs_layout = QHBoxLayout(self.graphs_widget)
        graphs_layout.setContentsMargins(0, 8, 0, 0)
        graphs_layout.setSpacing(12)

        self.cpu_graph = CollapsibleGraph("CPU", "#4a9eff")
        self.memory_graph = CollapsibleGraph("Память", "#3fb950")
        self.disk_graph = CollapsibleGraph("Диск", "#f0883e")

        graphs_layout.addWidget(self.cpu_graph)
        graphs_layout.addWidget(self.memory_graph)
        graphs_layout.addWidget(self.disk_graph)

        self.content_layout.addWidget(self.graphs_widget)

        # --- ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ  ---
        info_grid = QWidget()
        info_grid.setStyleSheet("background: transparent;")
        info_layout = QHBoxLayout(info_grid)
        info_layout.setContentsMargins(0, 10, 0, 0)
        info_layout.setSpacing(12)

        self.processes_count = self.create_info_card("Процессы", "0", "#4a9eff")
        self.uptime_card = self.create_info_card("Время работы", "0", "#3fb950")
        self.network_card = self.create_info_card("Сеть", "0 B/s", "#da3633")
        self.cpu_freq_card = self.create_info_card("Частота CPU", "0 MHz", "#f0883e")

        info_layout.addWidget(self.processes_count)
        info_layout.addWidget(self.uptime_card)
        info_layout.addWidget(self.network_card)
        info_layout.addWidget(self.cpu_freq_card)
        info_layout.addStretch()

        self.content_layout.addWidget(info_grid)

        # --- СТАТУСНАЯ ПАНЕЛЬ ---
        status_panel = QWidget()
        status_panel.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(0, 10, 0, 0)
        status_layout.setSpacing(12)

        dot = QLabel("●")
        dot.setStyleSheet("""
            QLabel {
                color: #3fb950;
                font-size: 6px;
                background: transparent;
                border: none;
            }
        """)
        status_layout.addWidget(dot)

        self.status_text = QLabel("Система загружается...")
        self.status_text.setStyleSheet("""
            QLabel {
                color: #6b7d95;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()

        btn_refresh = QPushButton("Обновить")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setFixedHeight(26)
        btn_refresh.setStyleSheet("""
            QPushButton {
                color: #6b7d95;
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 0 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(74, 158, 255, 0.045);
                color: #e8edf3;
            }
        """)
        btn_refresh.clicked.connect(self.force_update)
        status_layout.addWidget(btn_refresh)

        self.content_layout.addWidget(status_panel)
        self.content_layout.addStretch()

        # --- ТАЙМЕР ---
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.load_data)
        self.update_timer.start(500)

        # Загружаем данные
        self.load_data()

    def create_metric_card(self, title, value, color, progress):
        """Создает компактную карточку метрики"""
        card = QWidget()
        card.setStyleSheet("background: transparent;")
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(1)

        title_label = QLabel(title.upper())
        title_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 7px;
                font-weight: 600;
                letter-spacing: 0.8px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName(f"metric_value")
        value_label.setStyleSheet(f"""
            QLabel {{
                color: #e8edf3;
                font-size: 26px;
                font-weight: 300;
                background: transparent;
                border: none;
                padding: 0;
            }}
        """)
        layout.addWidget(value_label)

        sub_label = QLabel("")
        sub_label.setObjectName(f"metric_sub")
        sub_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 9px;
                font-weight: 400;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(sub_label)

        progress_bar = QProgressBar()
        progress_bar.setObjectName(f"progress")
        progress_bar.setRange(0, 100)
        progress_bar.setValue(progress)
        progress_bar.setFixedHeight(2)
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.03);
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 1px;
            }}
        """)
        layout.addWidget(progress_bar)

        return card

    def create_info_card(self, title, value, color):
        """Создает компактную карточку информации"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: rgba(16, 22, 36, 0.10);
                border-radius: 6px;
                border: 1px solid rgba(48, 54, 61, 0.04);
            }
        """)
        card.setMinimumWidth(110)
        card.setFixedHeight(55)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)

        title_label = QLabel(title.upper())
        title_label.setStyleSheet("""
            QLabel {
                color: #4a5a6a;
                font-size: 7px;
                font-weight: 600;
                letter-spacing: 0.8px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName(f"info_value")
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: 300;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(value_label)

        return card

    def force_update(self):
        self.load_data()
        self.status_text.setText("Обновление...")

    def load_data(self):
        if self.worker and self.worker.isRunning():
            return

        self.worker = SystemMonitorWorker()
        self.worker.finished.connect(self.on_data_loaded)
        self.worker.error.connect(self.on_data_error)
        self.worker.start()

    def on_data_loaded(self, data):
        try:
            # --- CPU ---
            cpu_percent = data['cpu_percent']
            cpu_label = self.cpu_card.findChild(QLabel, "metric_value")
            cpu_progress = self.cpu_card.findChild(QProgressBar, "progress")
            cpu_sub = self.cpu_card.findChild(QLabel, "metric_sub")

            if cpu_label:
                cpu_label.setText(f"{cpu_percent:.1f}%")
            if cpu_progress:
                cpu_progress.setValue(int(cpu_percent))
            if cpu_sub:
                freq = data['cpu_freq']
                cpu_sub.setText(f"{freq:.0f} MHz")

            self.cpu_graph.update_data(cpu_percent)

            # --- Память ---
            memory_percent = data['memory_percent']
            mem_label = self.memory_card.findChild(QLabel, "metric_value")
            mem_progress = self.memory_card.findChild(QProgressBar, "progress")
            mem_sub = self.memory_card.findChild(QLabel, "metric_sub")

            if mem_label:
                mem_label.setText(f"{memory_percent:.1f}%")
            if mem_progress:
                mem_progress.setValue(int(memory_percent))
            if mem_sub:
                used_gb = data['memory_used'] / (1024 ** 3)
                total_gb = data['memory_total'] / (1024 ** 3)
                mem_sub.setText(f"{used_gb:.1f} / {total_gb:.1f} GB")

            self.memory_graph.update_data(memory_percent)

            # --- Диск ---
            if data['disks']:
                disk = data['disks'][0]
                disk_percent = disk['percent']
                disk_label = self.disk_card.findChild(QLabel, "metric_value")
                disk_progress = self.disk_card.findChild(QProgressBar, "progress")
                disk_sub = self.disk_card.findChild(QLabel, "metric_sub")

                if disk_label:
                    disk_label.setText(f"{disk_percent:.1f}%")
                if disk_progress:
                    disk_progress.setValue(int(disk_percent))
                if disk_sub:
                    used_gb = disk['used'] / (1024 ** 3)
                    total_gb = disk['total'] / (1024 ** 3)
                    disk_sub.setText(f"{disk['device']} {used_gb:.1f} / {total_gb:.1f} GB")

                self.disk_graph.update_data(disk_percent)

            # --- Процессы ---
            processes_label = self.processes_count.findChild(QLabel, "info_value")
            if processes_label:
                processes_label.setText(str(data['process_count']))

            # --- Время работы ---
            uptime_label = self.uptime_card.findChild(QLabel, "info_value")
            if uptime_label:
                uptime = self.format_uptime(data['boot_time'])
                uptime_label.setText(uptime)

            # --- Частота CPU ---
            freq_label = self.cpu_freq_card.findChild(QLabel, "info_value")
            if freq_label:
                freq = data['cpu_freq']
                if freq > 0:
                    freq_label.setText(f"{freq:.0f} MHz")
                else:
                    freq_label.setText("N/A")

            # --- Сеть ---
            network_label = self.network_card.findChild(QLabel, "info_value")
            if network_label:
                current_time = time.time()

                if self.prev_time > 0:
                    time_diff = current_time - self.prev_time
                    if time_diff > 0:
                        sent_speed = (data['net_sent'] - self.prev_net_sent) / time_diff
                        recv_speed = (data['net_recv'] - self.prev_net_recv) / time_diff

                        sent_text = self.format_speed(sent_speed)
                        recv_text = self.format_speed(recv_speed)
                        network_label.setText(f"⬆{sent_text} ⬇{recv_text}")

                self.prev_net_sent = data['net_sent']
                self.prev_net_recv = data['net_recv']
                self.prev_time = current_time

            # --- Статус ---
            self.status_text.setText(
                f"CPU: {cpu_percent:.1f}%  ·  Память: {memory_percent:.1f}%  ·  "
                f"{datetime.datetime.now().strftime('%H:%M:%S')}"
            )

        except Exception as e:
            self.status_text.setText(f"Ошибка: {str(e)}")

    def format_uptime(self, boot_time):
        uptime = datetime.datetime.now().timestamp() - boot_time
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)

        if days > 0:
            return f"{days}д {hours}ч"
        elif hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f}B/s"
        elif bytes_per_sec < 1024 ** 2:
            return f"{bytes_per_sec / 1024:.1f}K/s"
        elif bytes_per_sec < 1024 ** 3:
            return f"{bytes_per_sec / (1024 ** 2):.1f}M/s"
        else:
            return f"{bytes_per_sec / (1024 ** 3):.2f}G/s"

    def on_data_error(self, error):
        self.status_text.setText(f"Ошибка: {error}")

    def on_show(self):
        self.load_data()

    def closeEvent(self, event):
        self.update_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()
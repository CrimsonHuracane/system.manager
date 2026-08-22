"""
Базовый класс для выполнения тяжёлых задач в отдельном потоке
"""
from PySide6.QtCore import QThread, Signal


class WorkerThread(QThread):
    """Базовый класс для рабочих потоков"""

    # Сигналы для обновления интерфейса
    finished = Signal()
    error = Signal(str)
    progress = Signal(int)
    data_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        """Основная логика выполняется здесь"""
        try:
            self._run_impl()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _run_impl(self):
        """Переопределить в наследнике"""
        pass

    def stop(self):
        """Остановка потока"""
        self._is_running = False
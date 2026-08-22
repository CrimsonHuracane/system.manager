from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame


class BasePage(QWidget):
    """Общий каркас страницы """

    def __init__(self, title, subtitle=""):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(0)

        # --- ЗАГОЛОВОК ---
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 22)
        header_layout.setSpacing(6)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #e8edf3;
                font-size: 30px;
                font-weight: 300;
                letter-spacing: 0.4px;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        header_layout.addWidget(title_label)

        if self.subtitle:
            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet("""
                QLabel {
                    color: #6b7d95;
                    font-size: 13px;
                    font-weight: 400;
                    letter-spacing: 0.2px;
                    background: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            header_layout.addWidget(subtitle_label)


        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(74, 158, 255, 0.12),
                    stop: 0.35 rgba(48, 54, 61, 0.10),
                    stop: 1 rgba(48, 54, 61, 0)
                );
                border: none;
                margin-top: 12px;
            }
        """)
        header_layout.addWidget(separator)

        layout.addWidget(header)

        # --- КОНТЕНТ ---
        self.content_container = QWidget()
        self.content_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 18, 0, 0)
        self.content_layout.setSpacing(18)

        layout.addWidget(self.content_container, stretch=1)

    def on_show(self):
        pass

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
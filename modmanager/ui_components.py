from PyQt5.QtWidgets import QTableWidgetItem, QLabel, QSizePolicy, QScrollBar, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt5.QtGui import QFontMetrics, QPainter, QLinearGradient, QColor, QDesktopServices
import os

# --- Custom Table Widget Item for Sorting ---
class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            self_data = self.data(Qt.UserRole)
            other_data = other.data(Qt.UserRole)
            if self_data is not None and other_data is not None:
                return float(self_data) < float(other_data)
        except Exception:
            pass
        return super().__lt__(other)

# --- Dark Mode Style Setter ---
def setDarkMode(app):
    dark_style = """
    /* Base background */
    QWidget {
        background-color: #2b2b2b;
        color: #f0f0f0;
    }
    /* QTabWidget */
    QTabWidget::pane {
        border: 1px solid #444;
        background-color: #313438;
    }
    QTabBar::tab {
        background: #313438;
        border: 1px solid #444;
        padding: 5px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin: 1px;
    }
    QTabBar::tab:selected {
        background: #3c3f41;
        border-bottom: 2px solid #00aaff;
    }
    /* Buttons */
    QPushButton {
        background-color: #3c3f41;
        border: 1px solid #555;
        padding: 5px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #46494a;
    }
    QPushButton:pressed {
        background-color: #4d4f51;
    }
    /* QLineEdit */
    QLineEdit {
        background-color: #3c3f41;
        border: 1px solid #555;
        padding: 3px;
        border-radius: 4px;
    }
    /* QTableWidget */
    QTableWidget {
        background-color: #313438;
        alternate-background-color: #2b2b2b;
        gridline-color: #555;
    }
    QHeaderView::section {
        background-color: #3c3f41;
        padding: 4px;
        border: 1px solid #555;
    }
    /* ScrollBars */
    QScrollBar:vertical {
        background: #2b2b2b;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #555;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: none;
    }
    """
    app.setStyleSheet(dark_style)

# --- MarqueeLabel for Scrolling Text ---
class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._text = text
        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateOffset)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.hovered = False

    def enterEvent(self, event):
        self.hovered = True
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self._text)
        if text_width > self.width():
            self.timer.start(30)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.timer.stop()
        self.offset = 0
        self.update()
        super().leaveEvent(event)

    def updateOffset(self):
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self._text)
        if text_width <= self.width():
            self.timer.stop()
            self.offset = 0
            return
        self.offset += 2
        if self.offset > text_width:
            self.offset = -self.width()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self._text)
        if text_width <= self.width():
            super().paintEvent(event)
        else:
            painter.drawText(-self.offset, self.height() - fm.descent(), self._text)

# --- ClickableLabel with a Click Signal ---
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

# --- FadeOverlay for Scrollable Widgets ---
class FadeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        bg_color = self.parent().palette().color(self.parent().backgroundRole())
        gradient.setColorAt(0.0, QColor(bg_color.red(), bg_color.green(), bg_color.blue(), 0))
        gradient.setColorAt(1.0, bg_color)
        painter.fillRect(self.rect(), gradient)

# --- ScrollableDescriptionWidget for Long Text ---
class ScrollableDescriptionWidget(QWidget):
    def __init__(self, parent=None, max_lines=10):
        super().__init__(parent)
        from PyQt5.QtWidgets import QLabel, QScrollBar, QVBoxLayout
        self.max_lines = max_lines
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.label.setOpenExternalLinks(False)
        self.scrollBar = QScrollBar(Qt.Vertical, self)
        self.scrollBar.valueChanged.connect(self.onScroll)
        self.scrollBar.hide()
        self.fadeOverlay = FadeOverlay(self)
        fm = self.label.fontMetrics()
        self.line_height = fm.height()
        self.fixedHeight = self.line_height * self.max_lines
        self.setFixedHeight(self.fixedHeight)
        self.setMinimumWidth(100)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.scrollBar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scrollbar_width = 15
        self.scrollBar.setGeometry(self.width() - scrollbar_width, 0, scrollbar_width, self.height())
        available_width = self.width() - (scrollbar_width if self.scrollBar.isVisible() else 0)
        self.label.setFixedWidth(available_width)
        self.updateLabelPosition()
        fade_height = 20
        self.fadeOverlay.setGeometry(0, self.height() - fade_height, self.width(), fade_height)
        self.fadeOverlay.raise_()  # Bring the fade overlay to the front

    def setText(self, text):
        self.label.setText(text)
        self.label.adjustSize()
        content_height = self.label.height()
        if content_height > self.fixedHeight:
            self.scrollBar.setRange(0, content_height - self.fixedHeight)
            self.scrollBar.show()
        else:
            self.scrollBar.hide()
            self.scrollBar.setValue(0)
        self.updateLabelPosition()
        self.updateFadeVisibility()

    def onScroll(self, value):
        self.updateLabelPosition()
        self.updateFadeVisibility()

    def updateLabelPosition(self):
        offset = self.scrollBar.value() if self.scrollBar.isVisible() else 0
        self.label.move(0, -offset)

    def updateFadeVisibility(self):
        if self.scrollBar.isVisible():
            if self.scrollBar.value() >= self.scrollBar.maximum():
                self.fadeOverlay.hide()
            else:
                self.fadeOverlay.show()
        else:
            self.fadeOverlay.hide()

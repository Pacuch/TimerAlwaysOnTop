import sys
import config
import sqlite3
import datetime
import threading
from pynput import mouse
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

DB_FILE = config.DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            duration REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            x INTEGER,
            y INTEGER,
            button TEXT,
            window_title TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_active_window_title():
    if sys.platform == "darwin":
        try:
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            return active_app['NSApplicationName'] if active_app else "Unknown"
        except ImportError:
            return "Unknown (PyObjC required on macOS)"
        except Exception:
            return "Unknown"
    elif sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else "Unknown"
        except Exception:
            return "Unknown"
    else:
        return "Unknown (Unsupported OS)"

class ModernTimer(QWidget):
    def __init__(self):
        super().__init__()
        
        self.is_timing = False
        self.start_time = None
        self.mouse_listener = None
        
        self.init_ui()
        
        # Timer for UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_time_display)

    def init_ui(self):
        # Window settings
        # Frameless window, stays on top, tool window (no taskbar icon optionally)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Container widget for styling
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 5, 10, 15)  # Snug top and sides
        self.container_layout.setSpacing(0)  # Remove gap between top bar and timer
        self.layout.addWidget(self.container)
        
        # Top bar layout (for close button)
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(0, 0, 0, 0)
        
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.close)
        
        self.top_bar.addStretch()
        self.top_bar.addWidget(self.close_btn)
        
        self.container_layout.addLayout(self.top_bar)
        
        # Time Label
        self.time_label = QLabel("00:00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setObjectName("TimeLabel")
        self.container_layout.addWidget(self.time_label)
        
        # Action Button
        self.action_btn = QPushButton("START", self)
        self.action_btn.setObjectName("StartBtn")
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.clicked.connect(self.toggle_state)
        self.container_layout.addWidget(self.action_btn)
        
        self.apply_styles()
        self.position_window()

    def position_window(self):
        self.resize(220, 140)
        # Get primary screen resolution
        screen = QApplication.primaryScreen().geometry()
        # Top right corner with 30px margin
        x = screen.width() - self.width() - 30
        y = 30
        self.move(x, y)
        
    def apply_styles(self):
        self.setStyleSheet("""
            #Container {
                background-color: #1e1e2e;
                border-radius: 15px;
                border: 1px solid #313244;
            }
            #TimeLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 34px;
                font-weight: bold;
                margin-bottom: 5px;
                margin-top: 5px;
            }
            #StartBtn {
                background-color: #a6e3a1; /* Pastel Green */
                color: #11111b;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px;
                border: none;
            }
            #StartBtn:hover {
                background-color: #94cc90;
            }
            #StopBtn {
                background-color: #f38ba8; /* Pastel Red */
                color: #11111b;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px;
                border: none;
            }
            #StopBtn:hover {
                background-color: #da7d97;
            }
            #CloseBtn {
                background-color: transparent;
                color: #7f849c; /* Subtle, dimmer gray */
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 12px;
                border: none;
            }
            #CloseBtn:hover {
                color: #f38ba8; /* Turns red on hover */
            }
        """)

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_timing:
            timestamp = datetime.datetime.now().isoformat()
            
            def save_click():
                import time
                
                window_title = "Unknown"
                # Retry up to 5 times (over 0.5 seconds) to catch slow window transitions
                # like clicking an app on the taskbar to maximize it.
                for _ in range(5):
                    time.sleep(0.1)
                    current_title = get_active_window_title()
                    if current_title != "Unknown" and current_title.strip() != "":
                        window_title = current_title
                        break
                
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO clicks (timestamp, x, y, button, window_title) VALUES (?, ?, ?, ?, ?)",
                                   (timestamp, x, y, str(button), window_title))
                    conn.commit()
                    conn.close()
                    if config.DEBUG:
                        print(f"DEBUG [Click Telemetry]: time={timestamp}, button={button}, pos=({x},{y}), window='{window_title}'")
                except Exception as e:
                    print(f"Db error: {e}")
                    
            threading.Thread(target=save_click, daemon=True).start()

    def toggle_state(self):
        if not self.is_timing:
            # START
            self.start_time = datetime.datetime.now()
            self.is_timing = True
            
            # Start timer update frequently (every 100ms) to ensure smooth second updates
            self.update_timer.start(100)
            
            # Start telemetry implicitly
            if self.mouse_listener is None:
                self.mouse_listener = mouse.Listener(on_click=self.on_click)
                self.mouse_listener.start()
                
            # Update UI to red STOP button
            self.action_btn.setObjectName("StopBtn")
            self.action_btn.setText("STOP")
            self.setWindowOpacity(0.3)
            self.apply_styles()
        else:
            # STOP
            self.is_timing = False
            self.update_timer.stop()
            
            end_time = datetime.datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            
            # Stop telemetry implicitly
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
                
            # Save timer session to database
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO timers (start_time, end_time, duration) VALUES (?, ?, ?)",
                           (self.start_time.isoformat(), end_time.isoformat(), duration))
            conn.commit()
            conn.close()
            if config.DEBUG:
                print(f"DEBUG [Timer Session]: start={self.start_time.isoformat()}, end={end_time.isoformat()}, duration={duration:.2f}s")
            
            # Reset UI to green START button
            self.time_label.setText("00:00:00")
            self.action_btn.setObjectName("StartBtn")
            self.action_btn.setText("START")
            self.setWindowOpacity(1.0)
            self.apply_styles()

    def update_time_display(self):
        if self.is_timing:
            elapsed = datetime.datetime.now() - self.start_time
            total_seconds = int(elapsed.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
    # Enable dragging for frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'oldPos'):
            del self.oldPos

def main():
    init_db()
    app = QApplication(sys.argv)
    window = ModernTimer()
    window.show()
    
    # Ensure background telemetry hook is closed on app exit
    app.aboutToQuit.connect(lambda: window.mouse_listener.stop() if window.mouse_listener else None)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

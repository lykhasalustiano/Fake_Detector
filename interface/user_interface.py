from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

class SereniTruthApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("SereniTruth - Fake Article Detector")
        self.setFixedSize(1440, 900)  # Desktop size
        self.setStyleSheet("""
            QMainWindow {
                background-color: #E8FFE8;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)
        
        # Header
        self.create_header(main_layout)
        
        # Main container
        self.create_main_container(main_layout)
    
    def create_header(self, parent_layout):
        # Header layout
        header_layout = QHBoxLayout()
        
        # Logo and title
        logo_title_layout = QHBoxLayout()
        
        # Logo image
        logo_label = QLabel()
        pixmap = QPixmap("img/logo.png")

        if not pixmap.isNull():
            # Palakihin ng konti ang image (mas malaki sa container)
            pixmap = pixmap.scaled(180, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)

        # Fixed small height para hindi maapektuhan ang header/search bar
        logo_label.setFixedHeight(60)
        logo_label.setFixedWidth(190)   # para square container
        logo_label.setAlignment(Qt.AlignCenter)  # gitna ng container ang image
        logo_label.setStyleSheet("background: transparent; margin-right: 20px;")

        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addStretch()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search here...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 25px;
                padding: 12px 20px;
                font-size: 16px;
                min-width: 300px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        
        header_layout.addLayout(logo_title_layout)
        header_layout.addWidget(self.search_bar)
        
        parent_layout.addLayout(header_layout)
    
    def create_main_container(self, parent_layout):
        # Main container
        main_container = QFrame()
        main_container.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 86, 0, 76);
                border: 2px solid #0D5600;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        
        main_container_layout = QHBoxLayout(main_container)
        main_container_layout.setSpacing(20)
        
        # Left side containers
        self.create_left_containers(main_container_layout)
        
        # Right container
        self.create_right_container(main_container_layout)
        
        parent_layout.addWidget(main_container)
    
    def create_left_containers(self, parent_layout):
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        # Prediction section
        prediction_frame = QFrame()
        prediction_frame.setStyleSheet("""
            QFrame {
                background-color: #0D5600;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        prediction_layout = QVBoxLayout(prediction_frame)
        
        prediction_title = QLabel("PREDICTION")
        prediction_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
            }
        """)
        prediction_title.setAlignment(Qt.AlignCenter)
        prediction_layout.addWidget(prediction_title)
        
        # Buttons container
        left_container_1 = QFrame()
        left_container_1.setStyleSheet("""
            QFrame {
                background-color: #5CA74E;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        buttons_layout = QVBoxLayout(left_container_1)
        buttons_layout.setSpacing(10)
        
        # Fake Article Button
        self.fake_btn = QPushButton("FAKE ARTICLE")
        self.fake_btn.setStyleSheet("""
            QPushButton {
                background-color: #237914;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e6611;
            }
            QPushButton:pressed {
                background-color: #1a5a0f;
            }
        """)
        self.fake_btn.clicked.connect(self.on_fake_clicked)
        
        # Trusted Article Button
        self.trusted_btn = QPushButton("TRUSTED ARTICLE")
        self.trusted_btn.setStyleSheet("""
            QPushButton {
                background-color: #237914;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e6611;
            }
            QPushButton:pressed {
                background-color: #1a5a0f;
            }
        """)
        self.trusted_btn.clicked.connect(self.on_trusted_clicked)
        
        buttons_layout.addWidget(self.fake_btn)
        buttons_layout.addWidget(self.trusted_btn)
        
        # Status container
        left_container_2 = QFrame()
        left_container_2.setStyleSheet("""
            QFrame {
                background-color: #D5F5D4;
                border: 2px solid #0D5600;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        status_layout = QVBoxLayout(left_container_2)
        
        status_title = QLabel("STATUS")
        status_title.setStyleSheet("""
            QLabel {
                color: #000000;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border-bottom: 2px solid #0D5600;
                margin-bottom: 15px;
            }
        """)
        status_title.setAlignment(Qt.AlignCenter)
        
        self.status_text = QLabel("The article was safe\nand trusted.")
        self.status_text.setStyleSheet("""
            QLabel {
                color: #000000;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 20px;
                line-height: 1.4;
                border: 2px solid #0D5600;
                border-radius: 10px;
            }
        """)
        self.status_text.setAlignment(Qt.AlignCenter)
        
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_text)
        
        left_layout.addWidget(prediction_frame)
        left_layout.addWidget(left_container_1)
        left_layout.addWidget(left_container_2)
        left_layout.addStretch()
        
        parent_layout.addLayout(left_layout)
    
    def create_right_container(self, parent_layout):
        right_layout = QVBoxLayout()
        
        # Detection output header
        detection_header = QFrame()
        detection_header.setStyleSheet("""
            QFrame {
                background-color: #0D5600;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        detection_header_layout = QVBoxLayout(detection_header)
        
        detection_title = QLabel("DETECTION OUTPUT")
        detection_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
            }
        """)
        detection_title.setAlignment(Qt.AlignCenter)
        detection_header_layout.addWidget(detection_title)
        
        # Right container (article display area)
        right_container = QFrame()
        right_container.setStyleSheet("""
            QFrame {
                background-color: rgba(92, 167, 78, 0.3);
                border: none;
                padding: 10px;
                border-radius: 10px;
            }
        """)
        right_container.setFixedHeight(600)  # <-- Sakto ang height
        
        right_container_layout = QVBoxLayout(right_container)
        
        # Article display placeholder
        self.article_display = QLabel("ARTICLE WILL SHOW HERE...")
        self.article_display.setStyleSheet("""
            QLabel {
                color: rgba(13, 86, 0, 200);
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 10px;
            }
        """)
        self.article_display.setAlignment(Qt.AlignCenter)
        self.article_display.setWordWrap(True)

        right_container_layout.addWidget(self.article_display)
        
        right_layout.addWidget(detection_header)
        right_layout.addWidget(right_container)
        
        parent_layout.addLayout(right_layout, 2)
    
    def on_fake_clicked(self):
        self.status_text.setText("The article was detected\nas FAKE!")
        self.article_display.setText("FAKE ARTICLE DETECTED!\nArticle analysis will show here...")
    
    def on_trusted_clicked(self):
        self.status_text.setText("The article was safe\nand trusted.")
        self.article_display.setText("TRUSTED ARTICLE!\nArticle content will show here...")



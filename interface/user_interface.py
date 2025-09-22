from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QFrame, QTextEdit, QListWidget, 
                             QSplitter, QProgressBar, QMessageBox, QStackedWidget, QComboBox,
                             QListWidgetItem, QScrollArea, QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
import sys
import os
import tempfile
import shutil
from datetime import datetime
import threading
import concurrent.futures

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import fetch_page_content, enhanced_parse_articles
from data_handler import save_to_excel, load_excel_data

class ScrapingWorker(QThread):
    """Thread for performing scraping for a single source"""
    finished = pyqtSignal(dict, str)  # articles_data, source_name
    error = pyqtSignal(str, str)  # error_message, source_name
    progress = pyqtSignal(int, str, str)  # progress_percent, message, source_name
    
    def __init__(self, url, output_file, get_full_content=True):
        super().__init__()
        self.url = url
        self.output_file = output_file
        self.get_full_content = get_full_content
        # Determine source based on URL
        if "npr" in url:
            self.source = "npr"
        elif "kaggle" in url:
            self.source = "kaggle"
        else:
            self.source = "unknown"
    
    def run(self):
        try:
            self.progress.emit(10, f"Fetching {self.source} page...", self.source)
            
            if self.source == "kaggle":
                # For Kaggle, we don't need to fetch HTML content in the same way
                self.progress.emit(40, f"Parsing {self.source} dataset...", self.source)
                articles_data = enhanced_parse_articles(None, self.source, self.get_full_content, self.url)
            else:
                html_content = fetch_page_content(self.url)
                if not html_content:
                    self.error.emit(f"Failed to fetch page content from {self.source}", self.source)
                    return
                    
                self.progress.emit(40, f"Parsing {self.source} articles...", self.source)
                articles_data = enhanced_parse_articles(html_content, self.source, self.get_full_content)
            
            if articles_data:
                self.progress.emit(70, f"Saving {self.source} data to Excel...", self.source)
                # Create a temporary file first to avoid permission issues
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"temp_news_{self.source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                
                save_to_excel(articles_data, temp_file)
                
                # Try to move the temp file to the desired location
                try:
                    if os.path.exists(self.output_file):
                        # Backup the existing file
                        backup_file = self.output_file.replace('.xlsx', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
                        shutil.move(self.output_file, backup_file)
                    
                    shutil.move(temp_file, self.output_file)
                    self.finished.emit({"articles": articles_data, "file": self.output_file}, self.source)
                except PermissionError:
                    self.error.emit(f"Permission denied when trying to save to {self.output_file}. The file might be open in another program.", self.source)
                except Exception as e:
                    self.error.emit(f"Error saving file: {str(e)}", self.source)
            else:
                self.error.emit(f"No data was found from {self.source}", self.source)
                
        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {str(e)}", self.source)

class ScrapingManager(QThread):
    """Manager thread that coordinates multiple scraping workers"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # overall_progress, message
    source_progress = pyqtSignal(int, str, str)  # source_progress, message, source_name
    
    def __init__(self, urls, output_files, get_full_content=True):
        super().__init__()
        self.urls = urls
        self.output_files = output_files
        self.get_full_content = get_full_content
        self.workers = []
        self.results = {}
        self.lock = threading.Lock()
        
    def run(self):
        try:
            self.progress.emit(0, "Starting scraping process...")
            
            # Create worker threads for each source
            for url, output_file in zip(self.urls, self.output_files):
                worker = ScrapingWorker(url, output_file, self.get_full_content)
                worker.finished.connect(self.on_worker_finished)
                worker.error.connect(self.on_worker_error)
                worker.progress.connect(self.on_worker_progress)
                self.workers.append(worker)
            
            # Start all workers
            for worker in self.workers:
                worker.start()
            
            # Wait for all workers to finish
            for worker in self.workers:
                worker.wait()
                
            # Check if we have results from all sources
            if len(self.results) >= 1:  # At least one source succeeded
                all_articles = []
                for source, result in self.results.items():
                    all_articles.extend(result["articles"])
                
                if all_articles:
                    self.progress.emit(100, "Scraping completed!")
                    self.finished.emit(all_articles)
                else:
                    self.error.emit("No articles were found from any source")
            else:
                self.error.emit("All sources failed to complete scraping")
                
        except Exception as e:
            self.error.emit(f"An unexpected error occurred: {str(e)}")
    
    def on_worker_finished(self, result, source):
        with self.lock:
            self.results[source] = result
            completed = len(self.results)
            total = len(self.workers)
            progress = int((completed / total) * 100)
            self.progress.emit(progress, f"Completed {source} scraping")
    
    def on_worker_error(self, error_message, source):
        self.source_progress.emit(0, f"Error: {error_message}", source)
        # We don't emit the main error signal here to allow other sources to continue
    
    def on_worker_progress(self, progress, message, source):
        self.source_progress.emit(progress, message, source)

class ScrapingWindow(QMainWindow):
    """Separate window for scraping operations"""
    scraping_finished = pyqtSignal(list)  # Signal to send results back to main window
    
    def __init__(self, urls, excel_files):
        super().__init__()
        self.urls = urls
        self.excel_files = excel_files
        self.scraping_thread = None
        self.source_progress_bars = {}
        self.source_status_labels = {}
        
        self.setWindowTitle("SereniTruth - Scraping News Articles")
        self.setFixedSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #E8FFE8;
            }
        """)
        
        self.init_ui()
        self.start_scraping()  # Auto-start scraping when window opens
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Scraping News Articles...")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #0D5600;
                text-align: center;
                padding: 20px;
            }
        """)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #0D5600;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.overall_progress)
        
        self.overall_status = QLabel("Initializing...")
        self.overall_status.setStyleSheet("font-size: 14px; color: #666; text-align: center;")
        self.overall_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.overall_status)
        
        # Sources container
        sources_frame = QFrame()
        sources_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #0D5600;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        self.sources_layout = QVBoxLayout(sources_frame)
        layout.addWidget(sources_frame)
        
        # Create progress widgets for each source
        for url in self.urls:
            source = "NPR" if "npr" in url else "Kaggle Dataset"
            source_widget = self.create_source_progress_widget(source)
            self.sources_layout.addWidget(source_widget)
        
        layout.addStretch()
        
        # Close button (initially hidden)
        self.close_button = QPushButton("Close")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.close_button.clicked.connect(self.close)
        self.close_button.setVisible(False)
        layout.addWidget(self.close_button)
    
    def create_source_progress_widget(self, source_name):
        """Create progress widgets for a specific source"""
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        
        # Source name
        source_label = QLabel(f"{source_name}:")
        source_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        # Progress bar for this source
        progress_bar = QProgressBar()
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 4px;
            }
        """)
        
        # Status label for this source
        status_label = QLabel("Waiting to start...")
        status_label.setStyleSheet("color: #666; font-size: 12px;")
        
        source_layout.addWidget(source_label)
        source_layout.addWidget(progress_bar)
        source_layout.addWidget(status_label)
        
        # Store references
        self.source_progress_bars[source_name] = progress_bar
        self.source_status_labels[source_name] = status_label
        
        return source_widget
    
    def start_scraping(self):
        # Create and start scraping manager thread
        self.scraping_thread = ScrapingManager(self.urls, self.excel_files, True)
        self.scraping_thread.finished.connect(self.on_scraping_finished)
        self.scraping_thread.error.connect(self.on_scraping_error)
        self.scraping_thread.progress.connect(self.on_scraping_progress)
        self.scraping_thread.source_progress.connect(self.on_source_progress)
        self.scraping_thread.start()
        
    def on_scraping_progress(self, progress, message):
        self.overall_progress.setValue(progress)
        self.overall_status.setText(message)
        
    def on_source_progress(self, progress, message, source):
        source_key = "NPR" if source == "npr" else "Kaggle Dataset"
        if source_key in self.source_progress_bars:
            self.source_progress_bars[source_key].setValue(progress)
        if source_key in self.source_status_labels:
            self.source_status_labels[source_key].setText(message)
        
    def on_scraping_finished(self, articles_data):
        # Run fake news detection on the scraped articles
        try:
            from naive_bayes_classifier import detect_fake_news_with_nb
            articles_data = detect_fake_news_with_nb(articles_data)
        except Exception as e:
            print(f"Error running fake news detection: {e}")
            # Set default status for articles if detection fails
            for article in articles_data:
                article['Fake_News_Label'] = '❓ UNKNOWN'
        
        self.overall_status.setText(f"Completed! Found {len(articles_data)} articles.")
        self.close_button.setVisible(True)
        
        # Emit signal to main window
        self.scraping_finished.emit(articles_data)
        
        # Auto-close after 3 seconds
        QThread.msleep(3000)
        self.close()
                
    def on_scraping_error(self, error_message):
        self.overall_status.setText('Scraping failed')
        
        # Show error message
        QMessageBox.critical(self, 'Error', error_message)
        self.close_button.setVisible(True)

class ArticleDetailWindow(QMainWindow):
    def __init__(self, article_data, main_window):
        super().__init__()
        self.article_data = article_data
        self.main_window = main_window
        self.setWindowTitle("Article Details - SereniTruth")
        self.setGeometry(100, 50, 1300, 1000)  # Increased height for computation details
        self.setMinimumSize(1200, 900)
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Header with status
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #0D5600;
                border-radius: 15px;
                padding: 25px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Source and status row
        source_status_layout = QHBoxLayout()
        
        source_label = QLabel(f"📰 Source: {self.article_data.get('Source', 'Unknown')}")
        source_label.setStyleSheet("font-size: 16px; color: #0D5600; font-weight: bold; padding: 5px;")
        
        status_label = QLabel(f"🔍 {self.article_data.get('Fake_News_Label', '❓ UNKNOWN')}")
        status_color = "#d32f2f" if "FAKE" in self.article_data.get('Fake_News_Label', '') else "#2e7d32" if "REAL" in self.article_data.get('Fake_News_Label', '') or "TRUSTED" in self.article_data.get('Fake_News_Label', '') else "#ff9800"
        status_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {status_color}; padding: 5px; border: 2px solid {status_color}; border-radius: 8px; background-color: rgba(255,255,255,0.8);")
        
        source_status_layout.addWidget(source_label)
        source_status_layout.addStretch()
        source_status_layout.addWidget(status_label)
        
        # Title
        title_label = QLabel(self.article_data.get('Title', 'No title'))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            margin: 15px 0; 
            color: #1a1a1a; 
            line-height: 1.4;
            padding: 15px;
            min-height: 60px;
        """)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        
        header_layout.addLayout(source_status_layout)
        header_layout.addWidget(title_label)
        layout.addWidget(header_frame)
        
        # Computation Details Section
        computation_header = QLabel("🧮 Classification Details:")
        computation_header.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            margin: 15px 0 10px 0; 
            color: #0D5600;
            padding: 10px;
            border-bottom: 2px solid #0D5600;
        """)
        layout.addWidget(computation_header)
        
        # Computation details text area
        computation_text = QTextEdit()
        computation_text.setReadOnly(True)
        computation_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
                color: #2c3e50;
                font-family: 'Consolas', 'Monaco', monospace;
                max-height: 200px;
            }
        """)
        
        # Generate computation details
        computation_details = self.generate_computation_details()
        computation_text.setPlainText(computation_details)
        computation_text.setFixedHeight(150)
        layout.addWidget(computation_text)
        
        # Content section
        content_header = QLabel("📄 Article Content:")
        content_header.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            margin: 15px 0 10px 0; 
            color: #0D5600;
            padding: 10px;
            border-bottom: 2px solid #0D5600;
        """)
        layout.addWidget(content_header)
        
        # Content text area
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 25px;
                font-size: 16px;
                line-height: 1.8;
                color: #2c3e50;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Use full content if available, otherwise use teaser
        content = self.article_data.get('Full Content', '')
        if not content:
            content = self.article_data.get('Content Paragraphs', self.article_data.get('Teaser', 'No content available'))
        
        if content and content != 'No content available':
            paragraphs = content.split('\n')
            formatted_content = '\n\n'.join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
            content_text.setPlainText(formatted_content)
        else:
            content_text.setPlainText("No content available for this article.")
        
        layout.addWidget(content_text, 1)
        
        # Back button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        back_button = QPushButton("← Back to SereniTruth")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #0D5600;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1e6611;
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background-color: #0a4500;
            }
        """)
        back_button.clicked.connect(self.go_back)
        
        button_layout.addWidget(back_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def generate_computation_details(self):
        """Generate detailed computation breakdown for the classification"""
        details = []
        
        # Basic prediction info
        prediction = self.article_data.get('Prediction', 'Unknown')
        fake_prob = self.article_data.get('Fake_Probability', 0.5) * 100
        real_prob = self.article_data.get('Real_Probability', 0.5) * 100
        confidence = self.article_data.get('Confidence', 0.5) * 100
        
        details.append(f"PREDICTION: {prediction}")
        details.append(f"Confidence: {confidence:.1f}%")
        details.append("")
        details.append("PROBABILITY BREAKDOWN:")
        details.append(f"  Fake Probability: {fake_prob:.1f}%")
        details.append(f"  Real Probability: {real_prob:.1f}%")
        details.append("")
        
        # Add model info if available
        if 'Model_Used' in self.article_data:
            details.append(f"MODEL: {self.article_data['Model_Used']}")
        
        # Add feature info if available
        if 'Key_Features' in self.article_data:
            details.append("KEY FEATURES CONTRIBUTING:")
            for feature, weight in self.article_data['Key_Features'].items():
                details.append(f"  {feature}: {weight:.3f}")
        
        return "\n".join(details)
    
    def go_back(self):
        """Safely go back to main window"""
        try:
            if self.main_window and hasattr(self.main_window, 'isVisible'):
                if self.main_window.isMinimized():
                    self.main_window.showNormal()
                else:
                    self.main_window.show()
                
                self.main_window.raise_()
                self.main_window.activateWindow()
                self.close()
            else:
                self.close()
                QMessageBox.information(self, "Information", "Main window was closed. Please restart the application.")
        except RuntimeError as e:
            print(f"Error going back: {e}")
            self.close()
class SereniTruthApp(QMainWindow):
    def __init__(self, articles_data, urls, excel_files):
        super().__init__()
        self.articles_data = articles_data
        self.urls = urls
        self.excel_files = excel_files
        self.article_windows = []  # Track open article windows
        self.current_filter = "all"  # Track current filter: "all", "fake", "real"
        self.selected_article = None  # Track currently selected article
        
        self.setWindowTitle("SereniTruth - Fake Article Detector")
        self.setFixedSize(1440, 900)  # Desktop size
        self.setStyleSheet("""
            QMainWindow {
                background-color: #E8FFE8;
            }
        """)
        
        self.init_ui()
        self.display_articles()
        
    def init_ui(self):
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(20)
        
        # Create UI elements
        self.create_header()
        self.create_main_container()
        self.create_footer()
    
    def create_header(self):
        # Header layout
        header_layout = QHBoxLayout()
        
        # Logo and title
        logo_title_layout = QHBoxLayout()
        
        # Logo image
        logo_label = QLabel()
        # Use a placeholder if the image doesn't exist
        try:
            pixmap = QPixmap("img/logo.png")
            if not pixmap.isNull():
                pixmap = pixmap.scaled(180, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                logo_label.setText("LOGO")
        except:
            logo_label.setText("LOGO")

        # Fixed small height para hindi maapektuhan ang header/search bar
        logo_label.setFixedHeight(60)
        logo_label.setFixedWidth(190)   # para square container
        logo_label.setAlignment(Qt.AlignCenter)  # gitna ng container ang image
        logo_label.setStyleSheet("background: transparent; margin-right: 20px;")

        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addStretch()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search articles...")
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
        self.search_bar.textChanged.connect(self.filter_articles)
        
        # Refresh button
        self.refresh_btn = QPushButton('🔄 Scrape New Data')
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.refresh_btn.clicked.connect(self.start_scraping)
        
        header_layout.addLayout(logo_title_layout)
        header_layout.addWidget(self.search_bar)
        header_layout.addWidget(self.refresh_btn)
        
        self.main_layout.addLayout(header_layout)
    
    def create_main_container(self):
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
        
        # Right container - Articles list
        self.create_articles_list(main_container_layout)
        
        self.main_layout.addWidget(main_container)
    
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
        
        prediction_title = QLabel("FILTER ARTICLES")
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
        
        # Show All Articles Button
        self.all_btn = QPushButton("ALL ARTICLES")
        self.all_btn.setStyleSheet("""
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
        self.all_btn.clicked.connect(self.show_all_articles)
        
        # Fake Article Button
        self.fake_btn = QPushButton("FAKE ARTICLES")
        self.fake_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c62828;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.fake_btn.clicked.connect(self.show_fake_articles)
        
        # Trusted Article Button
        self.trusted_btn = QPushButton("TRUSTED ARTICLES")
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
        self.trusted_btn.clicked.connect(self.show_trusted_articles)
        
        buttons_layout.addWidget(self.all_btn)
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
        
        status_title = QLabel("SELECTED ARTICLE")
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
        
        self.status_text = QLabel("Click on an article to see its detection status and content preview.")
        self.status_text.setStyleSheet("""
            QLabel {
                color: #000000;
                font-size: 14px;
                text-align: center;
                padding: 15px;
                line-height: 1.4;
                border: 1px solid #0D5600;
                border-radius: 10px;
                background-color: white;
            }
        """)
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setWordWrap(True)
        
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_text)
        
        left_layout.addWidget(prediction_frame)
        left_layout.addWidget(left_container_1)
        left_layout.addWidget(left_container_2)
        left_layout.addStretch()
        
        parent_layout.addLayout(left_layout)
    
    def create_articles_list(self, parent_layout):
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
        
        self.articles_title = QLabel("ALL ARTICLES")
        self.articles_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
            }
        """)
        self.articles_title.setAlignment(Qt.AlignCenter)
        detection_header_layout.addWidget(self.articles_title)
        
        # Articles list
        self.articles_list = QListWidget()
        self.articles_list.itemClicked.connect(self.on_article_selected)  # Single click to select
        self.articles_list.itemDoubleClicked.connect(self.show_article_details)  # Double click to view details
        self.articles_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #E8F5E8;
                color: #0D5600;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #f0f8f0;
            }
        """)
        
        right_layout.addWidget(detection_header)
        right_layout.addWidget(self.articles_list)
        
        parent_layout.addLayout(right_layout, 2)
    
    def create_footer(self):
        # Footer
        footer_text = f'Data will be saved to: {", ".join([os.path.basename(f) for f in self.excel_files])}'
        footer_label = QLabel(footer_text)
        footer_label.setStyleSheet("color: #888; font-size: 10px;")
        self.main_layout.addWidget(footer_label)

    def display_articles(self):
        """Display articles based on current filter"""
        self.articles_list.clear()
        
        if not self.articles_data:
            self.articles_list.addItem("No articles available. Click 'Scrape New Data' to fetch articles.")
            return
        
        # Enhanced filtering: Filter articles based on current filter AND remove articles with invalid titles
        filtered_articles = []
        for article in self.articles_data:
            # Skip articles with no title or invalid titles
            title = article.get('Title', '')
            if (not title or 
                title == 'No title' or 
                title.strip() == '' or
                title == 'No title found' or
                title == 'Title not found' or
                title == 'Access Denied' or
                title == 'Error retrieving title'):
                continue
                
            if self.current_filter == "all":
                filtered_articles.append(article)
            elif self.current_filter == "fake":
                if 'FAKE' in article.get('Fake_News_Label', '').upper():
                    filtered_articles.append(article)
            elif self.current_filter == "real":
                if 'REAL' in article.get('Fake_News_Label', '').upper() or \
                'TRUSTED' in article.get('Fake_News_Label', '').upper():
                    filtered_articles.append(article)
        
        # Apply search filter if there's search text
        search_text = self.search_bar.text().lower()
        if search_text:
            filtered_articles = [article for article in filtered_articles 
                            if search_text in article.get('Title', '').lower() or 
                            search_text in article.get('Fake_News_Label', '').lower()]
        
        # Add filtered articles to the list
        for article in filtered_articles:
            status = article.get('Fake_News_Label', '❓ UNKNOWN')
            
            title = f"{article.get('Title', 'No Title')} - {status}"
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, article)
            self.articles_list.addItem(item)
        
        # Update status
        if filtered_articles:
            sources = set(article.get('Source', 'Unknown') for article in filtered_articles)
            filter_text = self.current_filter.upper() if self.current_filter != "all" else "ALL"
            self.articles_title.setText(f"{filter_text} ARTICLES ({len(filtered_articles)})")
        else:
            filter_text = self.current_filter.upper() if self.current_filter != "all" else "ALL"
            self.articles_title.setText(f"{filter_text} ARTICLES (0)")
        
    def on_article_selected(self, item):
        """Handle article selection to show details in status panel"""
        self.selected_article = item.data(Qt.UserRole)
        
        if self.selected_article:
            # Get article details
            title = self.selected_article.get('Title', 'No Title')
            status = self.selected_article.get('Fake_News_Label', '❓ UNKNOWN')
            source = self.selected_article.get('Source', 'Unknown')
            
            # Get content preview (first 200 characters)
            content = self.selected_article.get('Full Content', '')
            if not content:
                content = self.selected_article.get('Content Paragraphs', 
                         self.selected_article.get('Teaser', 'No content available'))
            
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            # Update status text with article details
            status_html = f"""
            <b>Title:</b> {title[:60]}{'...' if len(title) > 60 else ''}<br><br>
            <b>Source:</b> {source}<br><br>
            <b>Status:</b> {status}<br><br>
            <b>Preview:</b><br>
            {content_preview}<br><br>
            <i>Double-click to view full article</i>
            """
            
            self.status_text.setText(status_html)
    
    def show_article_details(self, item):
        """Show full article details in a separate window"""
        article_data = item.data(Qt.UserRole)
        
        # Create detail window with proper reference handling
        detail_window = ArticleDetailWindow(article_data, self)
        detail_window.show()
        self.article_windows.append(detail_window)
        
        # Keep main window visible - don't minimize it
    
    def show_all_articles(self):
        """Show all articles"""
        self.current_filter = "all"
        self.display_articles()
        self.status_text.setText("Showing all articles. Click on an article to see its details.")
    
    def show_fake_articles(self):
        """Show only fake articles"""
        self.current_filter = "fake"
        self.display_articles()
        self.status_text.setText("Showing fake articles only. Click on an article to see its details.")
    
    def show_trusted_articles(self):
        """Show only trusted/real articles"""
        self.current_filter = "real"
        self.display_articles()
        self.status_text.setText("Showing trusted articles only. Click on an article to see its details.")
    
    def filter_articles(self):
        """Filter articles based on search text"""
        self.display_articles()  # This will apply both current filter and search filter
        
    def start_scraping(self):
        """Open scraping window"""
        # Check if files are accessible before starting scraping
        inaccessible_files = []
        for file_path in self.excel_files:
            try:
                # Try to open the file to check permissions
                if os.path.exists(file_path):
                    with open(file_path, 'a') as f:
                        pass
            except PermissionError:
                inaccessible_files.append(file_path)
        
        if inaccessible_files:
            reply = QMessageBox.question(self, "File Access Issue",
                                        f"The following files are not accessible:\n{', '.join(inaccessible_files)}\n\n"
                                        "Would you like to choose a different location?",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                new_files = []
                for file_path in inaccessible_files:
                    new_path, _ = QFileDialog.getSaveFileName(
                        self, "Select New Location for News Data",
                        os.path.dirname(file_path), "Excel Files (*.xlsx)"
                    )
                    if new_path:
                        new_files.append(new_path)
                    else:
                        # User canceled, abort scraping
                        return
                
                # Replace inaccessible files with new locations
                for i, file_path in enumerate(inaccessible_files):
                    idx = self.excel_files.index(file_path)
                    self.excel_files[idx] = new_files[i]
            else:
                # User chose not to change location, abort scraping
                return
        
        # Create and show scraping window
        self.scraping_window = ScrapingWindow(self.urls, self.excel_files)
        self.scraping_window.scraping_finished.connect(self.on_new_articles_scraped)
        self.scraping_window.show()
        
        # Hide main window while scraping
        self.hide()
        
    def on_new_articles_scraped(self, new_articles_data):
        """Handle new articles from scraping window"""
        self.articles_data = new_articles_data
        self.current_filter = "all"  # Reset filter to show all new articles
        self.display_articles()
        
        # Show main window again
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Show success message
        sources = set(article.get('Source', 'Unknown') for article in self.articles_data)
        QMessageBox.information(self, 'Success', 
                            f'Successfully scraped {len(self.articles_data)} articles from {", ".join(sources)}!')
        
    def closeEvent(self, event):
        """Handle application close"""
        # Close all article windows first
        for window in self.article_windows:
            try:
                window.close()
            except:
                pass
            
        # Close scraping window if open
        if hasattr(self, 'scraping_window'):
            try:
                self.scraping_window.close()
            except:
                pass
            
        event.accept()
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
    
    def run(self):
        try:
            self.progress.emit(10, f"Fetching {self.source} page...", self.source)
            html_content = fetch_page_content(self.url)
            if not html_content:
                self.error.emit(f"Failed to fetch page content from {self.source}", self.source)
                return
                
            self.progress.emit(40, f"Parsing {self.source} articles...", self.source)
            articles_data = enhanced_parse_articles(html_content, self.source, self.get_full_content)
            
            if articles_data:
                self.progress.emit(70, f"Saving {self.source} articles to Excel...", self.source)
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
                self.error.emit(f"No articles were found from {self.source}", self.source)
                
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
            if len(self.results) == len(self.workers):
                all_articles = []
                for source, result in self.results.items():
                    all_articles.extend(result["articles"])
                
                if all_articles:
                    self.progress.emit(100, "Scraping completed!")
                    self.finished.emit(all_articles)
                else:
                    self.error.emit("No articles were found from any source")
            else:
                self.error.emit("Some sources failed to complete scraping")
                
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

class ArticleDetailWindow(QMainWindow):
    def __init__(self, article_data, main_window):
        super().__init__()
        self.article_data = article_data
        self.main_window = main_window  # Store reference to main window
        self.setWindowTitle("Article Details - SereniTruth")
        self.setGeometry(100, 100, 1000, 700)
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Source indicator
        source_label = QLabel(f"Source: {self.article_data.get('Source', 'Unknown')}")
        source_label.setStyleSheet("font-size: 14px; color: #666; margin: 5px;")
        layout.addWidget(source_label)
        
        # Title
        title_label = QLabel(self.article_data.get('Title', 'No title'))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # Metadata
        meta_frame = QFrame()
        meta_frame.setFrameStyle(QFrame.Box)
        meta_layout = QVBoxLayout(meta_frame)
        
        date_label = QLabel(f"Date: {self.article_data.get('Detailed Date', self.article_data.get('Published Date', 'N/A'))}")
        author_label = QLabel(f"Author: {self.article_data.get('Author', 'N/A')}")
        url_label = QLabel(f"URL: {self.article_data.get('Article URL', 'N/A')}")
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        for label in [date_label, author_label, url_label]:
            meta_layout.addWidget(label)
        
        layout.addWidget(meta_frame)
        
        # Content
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        
        # Use full content if available, otherwise use teaser
        content = self.article_data.get('Full Content', '')
        if not content:
            content = self.article_data.get('Content Paragraphs', self.article_data.get('Teaser', 'No content available'))
        
        content_text.setPlainText(content)
        layout.addWidget(content_text)
        
        # Back button
        back_button = QPushButton("Back to Main")
        back_button.clicked.connect(self.go_back)
        layout.addWidget(back_button)
        
    def go_back(self):
        """Safely go back to main window"""
        try:
            # Check if main window still exists
            if self.main_window and hasattr(self.main_window, 'isVisible'):
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
                self.close()
            else:
                # If main window was closed, create a new one
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
        self.scraping_thread = None
        self.source_progress_bars = {}
        self.source_status_labels = {}
        
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
        self.create_progress_elements()
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
    
    def create_progress_elements(self):
        # Main progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel('Ready to scrape new data')
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.main_layout.addWidget(self.status_label)
        
        # Container for source-specific progress
        self.sources_container = QWidget()
        self.sources_layout = QVBoxLayout(self.sources_container)
        self.sources_container.setVisible(False)
        self.main_layout.addWidget(self.sources_container)
    
    def create_source_progress_widget(self, source_name):
        """Create progress widgets for a specific source"""
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        
        # Source name
        source_label = QLabel(f"{source_name.upper()} Progress:")
        source_label.setStyleSheet("font-weight: bold;")
        
        # Progress bar for this source
        progress_bar = QProgressBar()
        
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
        
        detection_title = QLabel("ARTICLES LIST")
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
        
        # Articles list
        self.articles_list = QListWidget()
        self.articles_list.itemDoubleClicked.connect(self.show_article_details)
        self.articles_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #E8F5E8;
                color: #0D5600;
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
        self.articles_list.clear()
        if self.articles_data:
            for article in self.articles_data:
                # Get detection status (default to "Unknown" if not set)
                status = article.get('Fake_News_Label', '❓ UNKNOWN')
                
                # Add source and status to the title for better identification
                title = f"[{article.get('Source', 'Unknown')}] {article['Title']} - {status}"
                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, article)
                self.articles_list.addItem(item)
            
            sources = set(article.get('Source', 'Unknown') for article in self.articles_data)
            self.status_label.setText(f'Loaded {len(self.articles_data)} articles from {", ".join(sources)}')
        else:
            self.status_label.setText('No articles available. Click "Scrape New Data" to fetch articles.')
        
    def show_article_details(self, item):
        article_data = item.data(Qt.UserRole)
        
        # Create detail window with proper reference handling
        detail_window = ArticleDetailWindow(article_data, self)
        detail_window.show()
        self.article_windows.append(detail_window)
        
        # Optional: minimize main window
        self.showMinimized()
    
    def filter_articles(self):
        search_text = self.search_bar.text().lower()
        for i in range(self.articles_list.count()):
            item = self.articles_list.item(i)
            article_data = item.data(Qt.UserRole)
            
            # Check if search text matches title or status
            title_match = search_text in item.text().lower()
            status_match = search_text in article_data.get('Fake_News_Label', '').lower()
            
            item.setHidden(not (title_match or status_match))
        
    def start_scraping(self):
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
                
                # Update footer
                footer_text = f'Data will be saved to: {", ".join([os.path.basename(f) for f in self.excel_files])}'
                for i in reversed(range(self.main_layout.count())):
                    widget = self.main_layout.itemAt(i).widget()
                    if isinstance(widget, QLabel) and "Data will be saved to:" in widget.text():
                        widget.setText(footer_text)
                        break
            else:
                # User chose not to change location, abort scraping
                return
        
        # Set up UI for scraping
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText('Scraping in progress...')
        
        # Clear previous source progress widgets
        for i in reversed(range(self.sources_layout.count())):
            widget = self.sources_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Create progress widgets for each source
        self.source_progress_bars = {}
        self.source_status_labels = {}
        
        for url in self.urls:
            source = "npr" if "npr" in url else "kagglepost"
            source_widget = self.create_source_progress_widget(source)
            self.sources_layout.addWidget(source_widget)
        
        self.sources_container.setVisible(True)
        
        # Create and start scraping manager thread
        self.scraping_thread = ScrapingManager(self.urls, self.excel_files, True)
        self.scraping_thread.finished.connect(self.on_scraping_finished)
        self.scraping_thread.error.connect(self.on_scraping_error)
        self.scraping_thread.progress.connect(self.on_scraping_progress)
        self.scraping_thread.source_progress.connect(self.on_source_progress)
        self.scraping_thread.start()
        
    def on_scraping_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        
    def on_source_progress(self, progress, message, source):
        if source in self.source_progress_bars:
            self.source_progress_bars[source].setValue(progress)
        if source in self.source_status_labels:
            self.source_status_labels[source].setText(message)
        
    def on_scraping_finished(self, articles_data):
        # Run fake news detection on the scraped articles
        try:
            from naive_bayes_classifier import detect_fake_news_with_nb
            self.articles_data = detect_fake_news_with_nb(articles_data)
        except Exception as e:
            print(f"Error running fake news detection: {e}")
            self.articles_data = articles_data
            # Set default status for articles if detection fails
            for article in self.articles_data:
                article['Fake_News_Label'] = '❓ UNKNOWN'
        
        self.display_articles()
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.sources_container.setVisible(False)
        
        # Show success message
        sources = set(article.get('Source', 'Unknown') for article in self.articles_data)
        QMessageBox.information(self, 'Success', 
                            f'Successfully scraped {len(self.articles_data)} items from {", ".join(sources)}!')
                
    def on_scraping_error(self, error_message):
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.sources_container.setVisible(False)
        self.status_label.setText('Scraping failed')
        
        # Check if it's a timeout error
        if "timed out" in error_message.lower() or "timeout" in error_message.lower():
            error_message += "\n\nTip: The server is taking too long to respond. " \
                            "This could be due to network issues or the website being temporarily unavailable. " \
                            "Please try again later or check your internet connection."
        
        # Show error message
        QMessageBox.critical(self, 'Error', error_message)
            
    def on_fake_clicked(self):
        # Get the currently selected article
        current_item = self.articles_list.currentItem()
        if current_item:
            article_data = current_item.data(Qt.UserRole)
            
            # Mark as fake
            article_data['Fake_News_Label'] = '⚠️ FAKE'
            article_data['Prediction'] = 'Fake'
            
            # Update the status text to show the user's choice
            self.status_text.setText(f"Marked as FAKE:\n{article_data['Title'][:50]}...")
            
            # Refresh the display to show the updated status
            self.display_articles()
        else:
            self.status_text.setText("Please select an article first")

    def on_trusted_clicked(self):
        # Get the currently selected article
        current_item = self.articles_list.currentItem()
        if current_item:
            article_data = current_item.data(Qt.UserRole)
            
            # Mark as trusted
            article_data['Fake_News_Label'] = '✅ TRUSTED'
            article_data['Prediction'] = 'Real'
            
            # Update the status text to show the user's choice
            self.status_text.setText(f"Marked as TRUSTED:\n{article_data['Title'][:50]}...")
            
            # Refresh the display to show the updated status
            self.display_articles()
        else:
            self.status_text.setText("Please select an article first")
        
    def closeEvent(self, event):
        """Handle application close"""
        # Close all article windows first
        for window in self.article_windows:
            try:
                window.close()
            except:
                pass
            
        # Stop any running scraping threads
        if self.scraping_thread and self.scraping_thread.isRunning():
            self.scraping_thread.terminate()
            self.scraping_thread.wait()
            
        event.accept()
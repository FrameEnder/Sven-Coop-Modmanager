import os, glob, json, math, re, requests, shutil
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QScrollArea,
                             QGridLayout, QStackedWidget, QComboBox, QTextEdit, QDialog, QFrame)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap, QFont
from bs4 import BeautifulSoup
from modmanager.mod_data import DATA_DIR, CACHE_HTML_DIR, CACHE_THUMB_DIR, remove_from_download_cache_by_title, load_download_cache, save_download_cache, MODS_FOLDER
from modmanager.ui_components import MarqueeLabel, ClickableLabel
from PyQt5.QtWidgets import QApplication, QMessageBox

RESULTS_PER_PAGE = 60

class BrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_stack = QStackedWidget()
        self.init_results_view()
        self.init_detail_view()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.browser_stack)
        self.setLayout(main_layout)
        self.browser_map_index = []
        self.browser_search_results = []
        self.browser_current_page = 1
        self.cdn_list_path = os.path.join(DATA_DIR, "CDN_List.json")
        if not os.path.exists(self.cdn_list_path):
            self.populate_cdn_list()
        self.load_cdn_list()
        self.perform_browser_search()

    def init_results_view(self):
        self.browser_results_widget = QWidget()
        results_layout = QVBoxLayout(self.browser_results_widget)
        search_layout = QHBoxLayout()
        self.browser_search_input = QLineEdit()
        self.browser_search_input.setPlaceholderText("Search by title or tags...")
        self.browser_search_button = QPushButton("Search")
        search_layout.addWidget(self.browser_search_input)
        search_layout.addWidget(self.browser_search_button)
        results_layout.addLayout(search_layout)
        self.browser_search_button.clicked.connect(self.perform_browser_search)
        self.browser_search_input.returnPressed.connect(self.perform_browser_search)
        self.browser_loading_label = QLabel("Loading Content List...")
        self.browser_loading_label.setAlignment(Qt.AlignCenter)
        self.browser_loading_label.hide()
        results_layout.addWidget(self.browser_loading_label)
        self.browser_scroll_area = QScrollArea()
        self.browser_scroll_area.setWidgetResizable(True)
        self.browser_grid_container = QWidget()
        self.browser_grid_layout = QVBoxLayout(self.browser_grid_container)
        self.browser_scroll_area.setWidget(self.browser_grid_container)
        results_layout.addWidget(self.browser_scroll_area)
        self.browser_pagination_layout = QHBoxLayout()
        results_layout.addLayout(self.browser_pagination_layout)
        self.browser_stack.addWidget(self.browser_results_widget)

    def init_detail_view(self):
        self.browser_detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.browser_detail_widget)
        top_bar = QHBoxLayout()
        self.detail_title_label = QLabel("Map Title")
        self.detail_title_label.setFont(QFont("Arial", 16, QFont.Bold))
        top_bar.addWidget(self.detail_title_label)
        top_bar.addStretch()
        self.detail_back_button = QPushButton("⟵ Back")
        self.detail_back_button.clicked.connect(self.back_browser_detail)
        top_bar.addWidget(self.detail_back_button)
        detail_layout.addLayout(top_bar)
        self.detail_author_label = QLabel("Author: ")
        detail_layout.addWidget(self.detail_author_label)
        self.detail_screenshots_area = QScrollArea()
        self.detail_screenshots_area.setWidgetResizable(True)
        self.detail_screenshots_container = QWidget()
        self.detail_screenshots_layout = QHBoxLayout(self.detail_screenshots_container)
        self.detail_screenshots_area.setWidget(self.detail_screenshots_container)
        detail_layout.addWidget(self.detail_screenshots_area)
        meta_layout = QVBoxLayout()
        self.detail_release_label = QLabel("Original Release: ")
        self.detail_posted_label = QLabel("Posted Date: ")
        self.detail_bsp_label = QLabel("BSP Filename: ")
        meta_layout.addWidget(self.detail_release_label)
        meta_layout.addWidget(self.detail_posted_label)
        meta_layout.addWidget(self.detail_bsp_label)
        download_layout = QHBoxLayout()
        self.download_combo = QComboBox()
        self.detail_download_button = QPushButton("Download")
        self.detail_download_button.clicked.connect(self.download_selected_file)
        self.downloaded_indicator = QPushButton("✔")
        self.downloaded_indicator.setStyleSheet("""
            background-color: green;
            color: white;
            border-radius: 10px;
            font-weight: bold;
            font-size: 22pt;
        """)
        self.downloaded_indicator.setFixedSize(80, 20)
        self.downloaded_indicator.setEnabled(False)
        self.downloaded_indicator.hide()
        meta_layout.insertWidget(0, self.downloaded_indicator)
        download_layout.addWidget(QLabel("Download:"))
        download_layout.addWidget(self.download_combo)
        download_layout.addWidget(self.detail_download_button)
        meta_layout.addLayout(download_layout)
        detail_layout.addLayout(meta_layout)
        self.detail_desc_browser = QTextEdit()
        self.detail_desc_browser.setReadOnly(True)
        detail_layout.addWidget(QLabel("<h3>Description</h3>"))
        detail_layout.addWidget(self.detail_desc_browser)
        self.detail_info_browser = QTextEdit()
        self.detail_info_browser.setReadOnly(True)
        detail_layout.addWidget(QLabel("<h3>Additional Info</h3>"))
        detail_layout.addWidget(self.detail_info_browser)
        self.browser_stack.addWidget(self.browser_detail_widget)

    def populate_cdn_list(self):
        self.browser_loading_label.show()
        QApplication.processEvents()
        base_url = "http://scmapdb.wikidot.com"
        cached_pages = glob.glob(os.path.join(CACHE_HTML_DIR, "page*.html"))
        if cached_pages:
            total_pages = len(cached_pages)
        else:
            try:
                r = requests.get(base_url + "/tag:all/p/1", timeout=10)
                r.raise_for_status()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load initial page: {e}")
                self.browser_loading_label.hide()
                return
            soup = BeautifulSoup(r.text, "html.parser")
            page_info = soup.select_one("#page-content div.list-pages-box > p")
            total_pages = 1
            if page_info:
                text = page_info.get_text(strip=True)
                try:
                    total_pages = int(text.split()[-1])
                except:
                    total_pages = 1
        all_entries = {}
        for p in range(1, total_pages + 1):
            page_url = f"{base_url}/tag:all/p/{p}"
            cache_file = os.path.join(CACHE_HTML_DIR, f"page_{p}.html")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    page_html = f.read()
            else:
                try:
                    r = requests.get(page_url, timeout=10)
                    r.raise_for_status()
                    page_html = r.text
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(page_html)
                except Exception as e:
                    print(f"Failed to retrieve page {p}: {e}")
                    continue
            page_soup = BeautifulSoup(page_html, "html.parser")
            items = page_soup.find_all('div', class_='list-pages-item')
            for item in items:
                try:
                    title_tag = item.select_one("div.lister-item-title p a")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    page_href = title_tag.get("href", "")
                    if not page_href.startswith("http"):
                        page_href = base_url + page_href
                    tags_tag = item.select_one("div.lister-item-tags p")
                    tags_text = tags_tag.get_text(" ", strip=True) if tags_tag else ""
                    thumb_tag = item.select_one("div.lister-item-image a img")
                    thumb_local_path = ""
                    if thumb_tag:
                        src = thumb_tag.get("src", "")
                        if not src.startswith("http"):
                            src = base_url + src
                        safe_title = re.sub(r'[^A-Za-z0-9_-]', '_', title)
                        thumb_filename = f"{safe_title}_{p}.jpg"
                        thumb_local_path = os.path.join(CACHE_THUMB_DIR, thumb_filename)
                        if not os.path.exists(thumb_local_path):
                            try:
                                t = requests.get(src, timeout=10)
                                t.raise_for_status()
                                with open(thumb_local_path, "wb") as img_file:
                                    img_file.write(t.content)
                            except Exception as e:
                                print(f"Failed to download thumbnail for {title}: {e}")
                                thumb_local_path = ""
                    key = title
                    count = 1
                    while key in all_entries:
                        key = f"{title}_{count}"
                        count += 1
                    all_entries[key] = {
                        "Title": title,
                        "Page URL": page_href,
                        "Tags": tags_text,
                        "Thumbnail": thumb_local_path
                    }
                except Exception as e:
                    print(f"Error processing an item: {e}")
                    continue
        try:
            with open(self.cdn_list_path, "w", encoding="utf-8") as f:
                json.dump(all_entries, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to write CDN_List.json: {e}")
        self.browser_loading_label.hide()

    def load_cdn_list(self):
        try:
            with open(self.cdn_list_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.browser_map_index = list(data.values())[::-1]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load CDN_List.json: {e}")
            self.browser_map_index = []

    def perform_browser_search(self):
        query = self.browser_search_input.text().strip().lower()
        if query == "":
            results = self.browser_map_index[:]
        else:
            results = []
            terms = query.split()
            for entry in self.browser_map_index:
                title = entry.get("Title", "").lower()
                tags = entry.get("Tags", "").lower()
                if any(term in title or term in tags for term in terms):
                    results.append(entry)
        self.browser_search_results = results
        self.browser_current_page = 1
        self.update_browser_grid()
        self.update_pagination()

    def update_browser_grid(self):
        for i in reversed(range(self.browser_grid_layout.count())):
            widget = self.browser_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        start_index = (self.browser_current_page - 1) * RESULTS_PER_PAGE
        end_index = start_index + RESULTS_PER_PAGE
        page_entries = self.browser_search_results[start_index:end_index]
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        download_cache = load_download_cache()
        cols = 5
        for idx, entry in enumerate(page_entries):
            row = idx // cols
            col = idx % cols
            entry_widget = QWidget()
            entry_widget.setObjectName("entryWidget")
            entry_widget.setFixedSize(170, 230)
            entry_widget.setStyleSheet("""
                QWidget#entryWidget {
                    border: 2px solid transparent;
                    border-radius: 5px;
                    background-color: #313438;
                }
                QWidget#entryWidget:hover {
                    border: 2px solid lightblue;
                }
            """)
            entry_layout = QVBoxLayout(entry_widget)
            entry_layout.setContentsMargins(5, 5, 5, 5)
            entry_layout.setSpacing(5)
            entry_layout.setAlignment(Qt.AlignCenter)
            thumb_container = QWidget(entry_widget)
            thumb_container.setFixedSize(150, 150)
            thumb_container.setStyleSheet("background-color: #161616;")
            thumb_layout = QVBoxLayout(thumb_container)
            thumb_layout.setContentsMargins(0, 0, 0, 0)
            thumb_layout.setAlignment(Qt.AlignCenter)
            thumb_label = ClickableLabel(thumb_container)
            thumb_path = entry.get("Thumbnail", "")
            pixmap = QPixmap(thumb_path) if thumb_path and os.path.exists(thumb_path) else QPixmap()
            if not pixmap.isNull():
                pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb_label.setPixmap(pixmap)
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.clicked.connect(lambda entry=entry: self.open_browser_detail(entry))
            thumb_layout.addWidget(thumb_label)
            if entry.get("Page URL") in download_cache:
                overlay = QLabel("Downloaded", thumb_container)
                overlay.setStyleSheet("""
                    background-color: green;
                    color: white;
                    border-radius: 7px;
                    font-size: 11pt;
                    font-weight: bold;
                    padding: 2px;
                """)
                overlay.setFixedHeight(22)
                overlay.setFixedWidth(thumb_container.width())
                overlay.move(0, thumb_container.height() - overlay.height())
                overlay.setAlignment(Qt.AlignCenter)
                overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                overlay.show()
            entry_layout.addWidget(thumb_container, alignment=Qt.AlignCenter)
            title_container = QWidget(entry_widget)
            title_container.setFixedHeight(40)
            title_layout = QVBoxLayout(title_container)
            title_layout.setContentsMargins(0, 0, 0, 0)
            title_layout.setAlignment(Qt.AlignCenter)
            title_label = MarqueeLabel(entry.get("Title", ""), title_container)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size: 12pt; color: white;")
            title_layout.addWidget(title_label)
            entry_layout.addWidget(title_container)
            grid_layout.addWidget(entry_widget, row, col, alignment=Qt.AlignCenter)
        self.browser_grid_layout.addWidget(grid_widget)

    def update_pagination(self):
        for i in reversed(range(self.browser_pagination_layout.count())):
            item = self.browser_pagination_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        total_results = len(self.browser_search_results)
        total_pages = math.ceil(total_results / RESULTS_PER_PAGE) if total_results > 0 else 1
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.prev_browser_page)
        prev_btn.setEnabled(self.browser_current_page > 1)
        self.browser_pagination_layout.addWidget(prev_btn)
        page_label = QLabel(f"Page {self.browser_current_page} of {total_pages}")
        page_label.setAlignment(Qt.AlignCenter)
        self.browser_pagination_layout.addWidget(page_label)
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.next_browser_page)
        next_btn.setEnabled(self.browser_current_page < total_pages)
        self.browser_pagination_layout.addWidget(next_btn)

    def prev_browser_page(self):
        if self.browser_current_page > 1:
            self.browser_current_page -= 1
            self.update_browser_grid()
            self.update_pagination()

    def next_browser_page(self):
        total_pages = math.ceil(len(self.browser_search_results) / RESULTS_PER_PAGE)
        if self.browser_current_page < total_pages:
            self.browser_current_page += 1
            self.update_browser_grid()
            self.update_pagination()

    def back_browser_detail(self):
        self.update_browser_grid()
        self.browser_stack.setCurrentIndex(0)

    def open_browser_detail(self, entry):
        self.current_entry = entry
        content_path = os.path.join(DATA_DIR, "CDN_Content.json")
        content_data = {}
        if os.path.exists(content_path):
            try:
                with open(content_path, "r", encoding="utf-8") as f:
                    content_data = json.load(f)
            except:
                content_data = {}
        title = entry.get("Title", "")
        if title in content_data:
            detail = content_data[title]
        else:
            detail = self.scrape_map_detail(entry.get("Page URL", ""))
            content_data[title] = detail
            try:
                with open(content_path, "w", encoding="utf-8") as f:
                    json.dump(content_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error writing CDN_Content.json: {e}")
        self.detail_title_label.setText(detail.get("Title", title))
        self.detail_author_label.setText("Author: " + detail.get("Author", "Unknown"))
        self.detail_release_label.setText("Original Release: " + detail.get("Original Release", "Unknown"))
        self.detail_posted_label.setText("Posted Date: " + detail.get("Posted Date", "Unknown"))
        self.detail_bsp_label.setText("BSP Filename: " + detail.get("BSP Filename", "Unknown"))
        self.download_combo.clear()
        downloads = detail.get("Download List", [])
        for url in downloads:
            fname = url.split("/")[-1]
            self.download_combo.addItem(fname, userData=url)
        self.detail_desc_browser.setHtml(detail.get("Description", ""))
        self.detail_info_browser.setHtml(detail.get("Added Info", ""))
        for i in reversed(range(self.detail_screenshots_layout.count())):
            w = self.detail_screenshots_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        screenshots = detail.get("Screenshots", [])
        for img_url in screenshots:
            screenshot_label = ClickableLabel()
            try:
                r = requests.get(img_url, timeout=10)
                r.raise_for_status()
                img_data = r.content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                screenshot_label.setPixmap(pixmap)
            except Exception as e:
                print(f"Error loading screenshot: {e}")
            screenshot_label.clicked.connect(lambda url=img_url: self.enlarge_screenshot(url))
            self.detail_screenshots_layout.addWidget(screenshot_label)
        current_zip = self.download_combo.itemText(0) if self.download_combo.count() > 0 else ""
        zip_path = os.path.join(MODS_FOLDER, current_zip)
        if os.path.exists(zip_path):
            self.detail_download_button.setText("Delete")
            self.detail_download_button.setStyleSheet("background-color: red; color: white;")
            self.downloaded_indicator.show()
        else:
            self.detail_download_button.setText("Download")
            self.detail_download_button.setStyleSheet("")
            self.downloaded_indicator.hide()
        self.browser_stack.setCurrentIndex(1)

    def scrape_map_detail(self, url):
        detail = {}
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            title_elem = soup.select_one("#toc2 > span")
            detail["Title"] = title_elem.get_text(strip=True) if title_elem else ""
            author_elem = soup.select_one("#page-content div.actualcontent_wrap div.new_leftside table tr:nth-child(1) td:nth-child(2)")
            detail["Author"] = author_elem.get_text(strip=True) if author_elem else "Unknown"
            rel_elem = soup.select_one("#page-content div.actualcontent_wrap div.new_leftside table tr:nth-child(2) td:nth-child(1)")
            detail["Original Release"] = rel_elem.get_text(strip=True) if rel_elem else "Unknown"
            posted_elem = soup.select_one("#page-content div.actualcontent_wrap div.new_leftside table tr:nth-child(3) td:nth-child(2)")
            detail["Posted Date"] = posted_elem.get_text(strip=True) if posted_elem else "Unknown"
            bsp_elem = soup.select_one("#page-content div.actualcontent_wrap div.new_leftside table tr:nth-child(4) td:nth-child(2)")
            detail["BSP Filename"] = bsp_elem.get_text(strip=True) if bsp_elem else "Unknown"
            downloads = []
            dl_section = soup.select_one("#page-content div.dl div.collapsible-block-content")
            if dl_section:
                for a in dl_section.find_all("a", href=True):
                    href = a["href"]
                    if re.search(r"\.(zip|7z|rar)$", href, re.IGNORECASE):
                        downloads.append(href)
            detail["Download List"] = downloads
            desc_elem = soup.select_one("#toc3")
            description = ""
            if desc_elem:
                for sib in desc_elem.find_next_siblings():
                    if sib.name == 'h2' and 'toc4' in sib.get("id", ""):
                        break
                    description += str(sib)
            detail["Description"] = description.strip()
            screenshots = []
            gallery = soup.select_one(".gallery-box")
            if gallery:
                for a in gallery.find_all("a", href=True):
                    screenshots.append(a["href"])
            detail["Screenshots"] = screenshots
            added_info = ""
            info_elem = soup.select_one("#toc3")
            if info_elem:
                for sib in info_elem.find_next_siblings():
                    if sib.name in ("h2", "h3") and "toc6" in sib.get("id", ""):
                        break
                    added_info += str(sib)
            detail["Added Info"] = added_info.strip()
        except Exception as e:
            print(f"Error scraping detail from {url}: {e}")
        return detail

    def download_selected_file(self):
        if self.detail_download_button.text() == "Delete":
            reply = QMessageBox.question(self, "Confirm Deletion",
                                         "Are you sure you want to delete the downloaded mod?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            current_zip = self.download_combo.itemText(0) if self.download_combo.count() > 0 else ""
            target_path = os.path.join(MODS_FOLDER, current_zip)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                    QMessageBox.information(self, "Deletion Complete", f"{current_zip} has been deleted.")
                except Exception as e:
                    QMessageBox.warning(self, "Deletion Error", f"Failed to delete file: {e}")
            mod_title = self.detail_title_label.text()
            remove_from_download_cache_by_title(mod_title)
            self.detail_download_button.setText("Download")
            self.detail_download_button.setStyleSheet("")
            self.downloaded_indicator.hide()
            return
        url = self.download_combo.currentData()
        if not url:
            return
        target_folder = MODS_FOLDER
        os.makedirs(target_folder, exist_ok=True)
        local_filename = url.split("/")[-1]
        target_path = os.path.join(target_folder, local_filename)
        try:
            r = requests.get(url, stream=True, timeout=10)
            r.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            QMessageBox.information(self, "Download Complete", f"File downloaded to {target_path}")
            cache = load_download_cache()
            mod_url = self.current_entry.get("Page URL", url)
            cache[mod_url] = {
                "zipName": local_filename,
                "Title": self.detail_title_label.text(),
                "URL": url
            }
            save_download_cache(cache)
            mod_folder_name = os.path.splitext(local_filename)[0]
            data_pack_folder = os.path.join(os.path.dirname(MODS_FOLDER), "data-pack", mod_folder_name)
            os.makedirs(data_pack_folder, exist_ok=True)
            mod_title = self.detail_title_label.text()
            author_text = self.detail_author_label.text().replace("Author:", "").strip()
            description_text = self.detail_desc_browser.toPlainText()
            new_description = f"Author: {author_text}\n\n{description_text}"
            info_data = {
                "name": mod_title,
                "description": new_description
            }
            info_json_path = os.path.join(data_pack_folder, "info.json")
            with open(info_json_path, "w", encoding="utf-8") as f:
                json.dump(info_data, f, indent=4, ensure_ascii=False)
            cdn_list_path = os.path.join(os.path.dirname(MODS_FOLDER), "Data", "CDN_List.json")
            thumbnail_path = ""
            try:
                with open(cdn_list_path, "r", encoding="utf-8") as f:
                    cdn_data = json.load(f)
                for key, entry in cdn_data.items():
                    if entry.get("Title", "") == mod_title:
                        thumbnail_path = entry.get("Thumbnail", "")
                        break
            except Exception as e:
                print(f"Error loading CDN_List.json: {e}")
            if thumbnail_path and os.path.exists(thumbnail_path):
                dest_thumb_path = os.path.join(data_pack_folder, "thumbnail.jpg")
                try:
                    shutil.copyfile(thumbnail_path, dest_thumb_path)
                except Exception as e:
                    print(f"Error copying thumbnail: {e}")
            self.detail_download_button.setText("Delete")
            self.detail_download_button.setStyleSheet("background-color: red; color: white;")
            self.downloaded_indicator.show()
        except Exception as e:
            QMessageBox.warning(self, "Download Error", f"Failed to download file: {e}")
            mod_folder_name = os.path.splitext(local_filename)[0]
            data_pack_folder = os.path.join(os.path.dirname(MODS_FOLDER), "data-pack", mod_folder_name)
            os.makedirs(data_pack_folder, exist_ok=True)
            mod_title = self.detail_title_label.text()
            author_text = self.detail_author_label.text().replace("Author:", "").strip()
            description_text = self.detail_desc_browser.toPlainText()
            new_description = f"Author: {author_text}\n\n{description_text}"
            info_data = {
                "name": mod_title,
                "description": new_description
            }
            info_json_path = os.path.join(data_pack_folder, "info.json")
            with open(info_json_path, "w", encoding="utf-8") as f:
                json.dump(info_data, f, indent=4, ensure_ascii=False)
            cdn_list_path = os.path.join(os.path.dirname(MODS_FOLDER), "Data", "CDN_List.json")
            thumbnail_path = ""
            try:
                with open(cdn_list_path, "r", encoding="utf-8") as f:
                    cdn_data = json.load(f)
                for key, entry in cdn_data.items():
                    if entry.get("Title", "") == mod_title:
                        thumbnail_path = entry.get("Thumbnail", "")
                        break
            except Exception as e:
                print(f"Error loading CDN_List.json: {e}")
            if thumbnail_path and os.path.exists(thumbnail_path):
                dest_thumb_path = os.path.join(data_pack_folder, "thumbnail.jpg")
                try:
                    shutil.copyfile(thumbnail_path, dest_thumb_path)
                except Exception as e:
                    print(f"Error copying thumbnail: {e}")

    def enlarge_screenshot(self, img_url):
        try:
            r = requests.get(img_url, timeout=10)
            r.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(r.content)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load image: {e}")
            return
        max_width = int(self.width() * 0.5)
        max_height = int(self.height() * 0.5)
        scaled_pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dlg = QDialog(self, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        from PyQt5.QtWidgets import QGridLayout
        grid = QGridLayout(dlg)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        img_label = QLabel(dlg)
        img_label.setPixmap(scaled_pixmap)
        img_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(img_label, 0, 0)
        close_btn = QPushButton("X", dlg)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
        """)
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(dlg.accept)
        grid.addWidget(close_btn, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)
        dlg.setLayout(grid)
        dlg.adjustSize()
        center_point = self.geometry().center()
        dlg.move(center_point.x() - dlg.width() // 2, center_point.y() - dlg.height() // 2)
        dlg.exec_()

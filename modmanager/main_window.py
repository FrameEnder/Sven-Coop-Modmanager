import os, json, glob, shutil
from PyQt5.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QLabel, QHeaderView,
                             QFrame, QDialog, QLineEdit, QTextEdit, QMenu, QStyle)
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import Qt, QUrl
from modmanager.ui_components import SortableTableWidgetItem, ClickableLabel, ScrollableDescriptionWidget
from modmanager.mod_data import get_mod_list, human_file_size, enable_mod, enable_all_mods, disable_mod, delete_mod, \
    rename_mod, set_mod_description, set_mod_thumbnail, disable_all_mods
from modmanager.config import load_config, save_config
from modmanager.browser_page import BrowserTab


class ModManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sven Co-op [Mod Manager]")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(self.base_dir, "Sven_Map-Manager.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(1280, 920)
        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()
        self.mods_tab = QWidget()
        self.init_mods_tab()
        self.tabs.addTab(self.mods_tab, "Mods")
        self.browser_tab = BrowserTab()
        self.tabs.addTab(self.browser_tab, "Browser")
        self.settings_tab = QWidget()
        self.init_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")
        self.about_tab = QWidget()
        self.init_about_tab()
        self.tabs.addTab(self.about_tab, "About")
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def init_mods_tab(self):
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Status", "Mod Name", "Size"])
        self.table.setSelectionBehavior(self.table.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.load_mods_into_table()
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        top_layout.addWidget(self.table)
        action_panel = QVBoxLayout()
        self.btn_mod_folder = QPushButton("Mod Folder")
        self.btn_mod_folder.clicked.connect(self.open_mod_folder)
        action_panel.addWidget(self.btn_mod_folder)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_mods_into_table)
        action_panel.addWidget(self.btn_refresh)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        action_panel.addWidget(separator)
        self.btn_enable = QPushButton("Enable")
        self.btn_disable = QPushButton("Disable")
        self.btn_enable.clicked.connect(self.enable_selected_mods)
        self.btn_disable.clicked.connect(self.disable_selected_mod)
        action_panel.addWidget(self.btn_enable)
        action_panel.addWidget(self.btn_disable)
        self.btn_clear = QPushButton("Clear Mods")
        self.btn_clear.clicked.connect(self.clear_mods)
        action_panel.addWidget(self.btn_clear)
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        action_panel.addWidget(separator2)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("background-color: darkred; color: white;")
        self.btn_delete.clicked.connect(self.delete_selected_mod)
        action_panel.addWidget(self.btn_delete)
        action_panel.addStretch()
        top_layout.addLayout(action_panel)
        main_layout.addLayout(top_layout)
        self.details_panel = QWidget()
        details_layout = QHBoxLayout()
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setMaximumWidth(150)
        details_layout.addWidget(self.thumbnail_label)
        text_layout = QVBoxLayout()
        self.mod_name_label = QLabel("")
        self.description_widget = ScrollableDescriptionWidget()
        self.description_widget.label.linkActivated.connect(self.handle_link)
        text_layout.addWidget(self.mod_name_label)
        text_layout.addWidget(self.description_widget)
        details_layout.addLayout(text_layout)
        self.details_panel.setLayout(details_layout)
        main_layout.addWidget(self.details_panel)
        self.mods_tab.setLayout(main_layout)

    def init_settings_tab(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        self.btn_game_folder = QPushButton("Game Folder")
        self.btn_game_folder.clicked.connect(self.select_game_folder)
        self.lbl_game_folder = QLabel("Not set")
        layout.addWidget(self.btn_game_folder)
        layout.addWidget(self.lbl_game_folder)
        layout.addStretch()
        self.settings_tab.setLayout(layout)
        self.load_config_into_settings()

    def init_about_tab(self):
        layout = QVBoxLayout()
        about_label = QLabel()
        about_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        about_label.setOpenExternalLinks(False)
        about_label.linkActivated.connect(self.handle_link)
        about_text = """
        <p>Welcome to the Sven Co-op Map Manager,</p>
        <br>
        <p>This is an un-official FOSS map manager originally made for me, and my friend, so we can easily manage all the downloaded maps we've collected.</p>
        <p>It's rough, and I'm not the best programmer, but I think this is a good start, and I hope everyone enjoy's it just as much as I've enjoyed playing Sven Co-op... which is a lot.</p>
        <p>If you're curious how to start using this, just place your mods (still zipped up in .zip) in the mods folder in the same directory as this script. If it doesn't exist, you can create a mods directory there</p>
        <p>and click start.bat/start.sh depending on your OS Windows, or Linux. It'll download all the required pip modules, and start the App in a Virtual Environment.</p>
        <p>I recommend using Python 3.11. Oh, and this uses PyQT5 for its GUI – a little modern, I know, but anything more unique would be too hard for me to manage.</p>
        <p>Thank you to everyone in the Sven Co-op community, and keep up the good work!</p>
        <br>
        <p>~Sincerely, Proto Propski</p>
        <p>For Maps, and community feedback please visit the <a href="http://scmapdb.wikidot.com/">Sven Co-op Map Database</a></p>
        """
        about_label.setText(about_text)
        layout.addWidget(about_label)
        layout.addStretch()
        self.about_tab.setLayout(layout)

    def open_mod_folder(self):
        from PyQt5.QtGui import QDesktopServices
        mods_path = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "Mods")
        QDesktopServices.openUrl(QUrl.fromLocalFile(mods_path))

    def select_game_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Game Folder")
        if folder:
            addon_path = os.path.join(folder, "svencoop_addon")
            if os.path.isdir(addon_path):
                config = load_config()
                config["Game_Folder"] = folder
                save_config(config)
                self.lbl_game_folder.setText(folder)
            else:
                QMessageBox.warning(self, "Invalid Folder", "The selected folder does not contain 'svencoop_addon'.")

    def load_config_into_settings(self):
        config = load_config()
        game_folder = config.get("Game_Folder", "")
        self.lbl_game_folder.setText(game_folder if game_folder else "Not set")

    def load_mods_into_table(self):
        mods = get_mod_list()
        self.table.setRowCount(len(mods))
        for row, mod in enumerate(mods):
            status_item = SortableTableWidgetItem("")
            icon = self.style().standardIcon(QStyle.SP_DialogApplyButton) if mod[
                "enabled"] else self.style().standardIcon(QStyle.SP_DialogCancelButton)

            status_item.setIcon(icon)
            status_item.setData(Qt.UserRole, 0 if mod["enabled"] else 1)
            status_item.setFlags(Qt.ItemIsEnabled)
            name_item = QTableWidgetItem(mod["displayed_name"])
            name_item.setData(Qt.UserRole, mod["orig_mod_name"])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            size_text = human_file_size(mod["size_raw"])
            size_item = SortableTableWidgetItem(size_text)
            size_item.setData(Qt.UserRole, mod["size_raw"])
            size_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, status_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, size_item)
        self.table.resizeRowsToContents()

    def delete_selected_mod(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select mod(s) to delete.")
            return
        reply = QMessageBox.question(
            self,
            'Confirm Deletion',
            'Are you sure you want to delete the selected mod(s)?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
        for index in selected_rows:
            row = index.row()
            mod_item = self.table.item(row, 1)
            orig_mod_name = mod_item.data(Qt.UserRole) or mod_item.text()
            self.context_delete_mod(orig_mod_name)
        self.load_mods_into_table()
        self.clear_details_panel()

    def on_cell_double_clicked(self, row, column):
        # Only trigger if the status column (0) was double-clicked
        if column == 0:
            mod_item = self.table.item(row, 1)
            mod_name = mod_item.data(Qt.UserRole) or mod_item.text()

            # Retrieve the status from the status cell (column 0)
            status_item = self.table.item(row, 0)
            current_status = status_item.data(Qt.UserRole)  # 0 means enabled, 1 means disabled

            if current_status == 0:
                # Currently enabled: disable it
                self.context_disable_mod(mod_name)
            else:
                # Currently disabled: enable it
                self.context_enable_mod(mod_name)

    def open_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        mod_item = self.table.item(row, 1)
        orig_mod_name = mod_item.data(Qt.UserRole) or mod_item.text()
        menu = QMenu()
        action_enable = menu.addAction("Enable")
        action_disable = menu.addAction("Disable")
        menu.addSeparator()
        action_rename = menu.addAction("Rename")
        action_thumbnail = menu.addAction("Thumbnail")
        action_description = menu.addAction("Description")
        menu.addSeparator()
        action_delete = menu.addAction("Delete")
        action_enable.triggered.connect(self.enable_selected_mods)
        action_disable.triggered.connect(lambda: self.context_disable_mod(orig_mod_name))
        action_rename.triggered.connect(lambda: self.context_rename_mod(orig_mod_name))
        action_thumbnail.triggered.connect(lambda: self.context_thumbnail_mod(orig_mod_name))
        action_description.triggered.connect(lambda: self.context_description_mod(orig_mod_name))
        action_delete.triggered.connect(lambda: self.context_delete_mod(orig_mod_name))
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def on_table_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            mod_item = self.table.item(row, 1)
            orig_mod_name = mod_item.data(Qt.UserRole) or mod_item.text()
            self.update_details_panel(orig_mod_name)
        else:
            self.clear_details_panel()

    def context_enable_mod(self, mod_name):
        if enable_mod(mod_name, self):
            self.load_mods_into_table()
            self.update_details_panel(mod_name)

    def enable_selected_mods(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select mod(s) to enable.")
            return
        mods = []
        for index in selected_rows:
            row = index.row()
            mod_item = self.table.item(row, 1)
            mod_name = mod_item.data(Qt.UserRole) or mod_item.text()
            mod_archive = None
            for ext in [".zip", ".7z"]:
                path = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "Mods", mod_name + ext)
                if os.path.exists(path):
                    mod_archive = path
                    break
            if mod_archive:
                mods.append({"orig_mod_name": mod_name, "archive_path": mod_archive})
        if enable_all_mods(mods, self):
            self.load_mods_into_table()

    def context_disable_mod(self, mod_name):
        if disable_mod(mod_name, self):
            self.load_mods_into_table()
            self.update_details_panel(mod_name)

    def disable_selected_mod(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select a mod to disable.")
            return
        row = selected_rows[0].row()
        mod_item = self.table.item(row, 1)
        orig_mod_name = mod_item.data(Qt.UserRole) or mod_item.text()
        self.context_disable_mod(orig_mod_name)

    def context_delete_mod(self, mod_name):
        reply = QMessageBox.question(self, 'Confirm Deletion', 'Are you sure you want to delete the mod?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        if delete_mod(mod_name, self):
            self.load_mods_into_table()
            self.clear_details_panel()

    def context_rename_mod(self, mod_name):
        data_pack_dir = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "data-pack")
        os.makedirs(data_pack_dir, exist_ok=True)
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Alias")
        layout = QHBoxLayout()
        line_edit = QLineEdit()
        btn_set = QPushButton("Set Alias")
        layout.addWidget(line_edit)
        layout.addWidget(btn_set)
        dialog.setLayout(layout)
        btn_set.clicked.connect(
            lambda: [rename_mod(mod_name, line_edit.text(), self), dialog.accept(), self.load_mods_into_table(),
                     self.update_details_panel(mod_name)])
        dialog.exec_()

    def context_description_mod(self, mod_name):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Description")
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        btn_set = QPushButton("Set Description")
        layout.addWidget(text_edit)
        layout.addWidget(btn_set)
        dialog.setLayout(layout)
        btn_set.clicked.connect(lambda: [set_mod_description(mod_name, text_edit.toPlainText(), self), dialog.accept(),
                                         self.update_details_panel(mod_name)])
        dialog.exec_()

    def context_thumbnail_mod(self, mod_name):
        data_pack_dir = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "data-pack")
        os.makedirs(data_pack_dir, exist_ok=True)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Thumbnail Image", "",
                                                   "Images (*.png *.jpg *.jpeg *.webp)", options=options)
        if file_path:
            if set_mod_thumbnail(mod_name, file_path, self):
                self.update_details_panel(mod_name)

    def update_details_panel(self, mod_name):
        data_pack_dir = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "data-pack")
        mod_data_dir = os.path.join(data_pack_dir, mod_name)
        info_path = os.path.join(mod_data_dir, "info.json")
        alias = mod_name
        description = ""
        if os.path.exists(info_path):
            try:
                with open(info_path, "r") as f:
                    info = json.load(f)
                if "name" in info and info["name"]:
                    alias = info["name"]
                if "description" in info:
                    description = info["description"]
            except:
                pass
        self.mod_name_label.setText(alias)
        self.description_widget.setText(description)
        thumb_path = os.path.join(mod_data_dir, "thumbnail.jpg")
        if not os.path.exists(thumb_path):
            thumb_path = os.path.join(os.path.abspath(os.path.join(self.base_dir, "..")), "Thumbnail_Default.jpg")
        pixmap = QPixmap(thumb_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaledToWidth(150, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            self.thumbnail_label.clear()

    def clear_details_panel(self):
        self.mod_name_label.setText("")
        self.description_widget.setText("")
        self.thumbnail_label.clear()

    def clear_mods(self):
        if disable_all_mods(self):
            self.load_mods_into_table()
            self.clear_details_panel()

    def handle_link(self, url):
        message = f"You are about to open the following link:\n\n{url}\n\nDo you want to proceed?"
        reply = QMessageBox.question(self, "External Link", message, QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            from PyQt5.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(url))

    def on_tab_changed(self, index):
        if self.tabs.widget(index) == self.browser_tab:
            self.browser_tab.perform_browser_search()
        if self.tabs.widget(index) == self.mods_tab:
            self.load_mods_into_table()


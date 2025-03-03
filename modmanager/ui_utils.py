from PyQt5.QtWidgets import QMessageBox

def show_error(parent, message):
    dlg = QMessageBox(parent)
    dlg.setIcon(QMessageBox.Critical)
    dlg.setText(message)
    dlg.setWindowTitle("Error")
    dlg.exec_()

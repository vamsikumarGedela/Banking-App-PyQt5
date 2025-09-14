import sys
import os
import csv
import hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit,
    QLabel, QStackedWidget, QMessageBox, QTextEdit, QInputDialog,
    QSplashScreen
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation

# -------------------- Constants -------------------- #
USERS_FILE = "users.csv"
BALANCE_FILE = "balance.csv" 
HISTORY_FILE = "history.csv"
AVATAR_DIR = "Gbanking/avatars" 
SUSPICIOUS_LIMIT = 1000


# -------------------- Helpers -------------------- #
def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def load_balance(name):
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Name"] == name:
                    return float(row["Balance"])
    return 0.0


def save_balance(name, balance):
    records = []
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            records = list(csv.DictReader(f))

    updated = False
    for row in records:
        if row["Name"] == name:
            row["Balance"] = f"{balance:.2f}"
            updated = True
            break
    if not updated:
        records.append({"Name": name, "Balance": f"{balance:.2f}"})

    with open(BALANCE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Balance"])
        writer.writeheader()
        writer.writerows(records)


def log_transaction(name, trans_type, amount, balance):
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if os.stat(HISTORY_FILE).st_size == 0:
            writer.writerow(["Name", "Type", "Amount", "Balance", "Timestamp"])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([name, trans_type, f"{amount:.2f}", f"{balance:.2f}", timestamp])


def get_color_from_name(name):
    colors = ["#f44336", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#3F51B5", "#795548"]
    return colors[sum(ord(c) for c in name) % len(colors)]


def generate_avatar(name):
    if not os.path.exists(AVATAR_DIR):
        os.makedirs(AVATAR_DIR)

    initials = "".join([part[0] for part in name.split()]).upper()
    color = get_color_from_name(name)
    size = 100
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_circle = ImageDraw.Draw(circle)
    draw_circle.ellipse((0, 0, size, size), fill=color)

    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    draw_text = ImageDraw.Draw(circle)
    bbox = draw_text.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw_text.text(((size - text_w) / 2, (size - text_h) / 2), initials, font=font, fill="white")

    img.paste(circle, (0, 0), circle)

    path = os.path.join(AVATAR_DIR, f"{name.lower()}.png")
    img.save(path)
    return path


# -------------------- Main Application -------------------- #
class BankApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("\U0001F3E6 Bank System")
        self.stack = QStackedWidget(self)
        self.user = None
        self.balance = 0.0
        self._anim = None  # keep a reference for transitions
        self.init_ui()

    def init_ui(self):
        self.login_screen()
        self.register_screen()
        self.dashboard_screen()
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)
        self.stack.setCurrentWidget(self.login_widget)

    def animate_transition(self, target_widget):
        self._anim = QPropertyAnimation(self.stack, b"windowOpacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.1)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.stack.setCurrentWidget(target_widget)

    def login_screen(self):
        self.login_widget = QWidget()
        layout = QVBoxLayout()

        image_label = QLabel()
        pixmap = QPixmap("GbankingApp/Gbanking/bank.png")
        pixmap = pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        self.login_name = QLineEdit()
        self.login_name.setPlaceholderText("Enter Name")

        self.login_pin = QLineEdit()
        self.login_pin.setPlaceholderText("Enter 4-digit PIN")
        self.login_pin.setEchoMode(QLineEdit.Password)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login_user)

        switch_btn = QPushButton("New user? Register here")
        switch_btn.clicked.connect(lambda: self.animate_transition(self.register_widget))

        layout.addWidget(QLabel("Login"))
        layout.addWidget(self.login_name)
        layout.addWidget(self.login_pin)
        layout.addWidget(login_btn)
        layout.addWidget(switch_btn)

        self.login_widget.setLayout(layout)
        self.stack.addWidget(self.login_widget)

    def register_screen(self):
        self.register_widget = QWidget()
        layout = QVBoxLayout()

        image_label = QLabel()
        pixmap = QPixmap("GbankingApp\Gbanking\bank.png")
        pixmap = pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("Enter Name")

        self.reg_pin = QLineEdit()
        self.reg_pin.setPlaceholderText("Set 4-digit PIN")
        self.reg_pin.setEchoMode(QLineEdit.Password)

        reg_btn = QPushButton("Register")
        reg_btn.clicked.connect(self.register_user)

        switch_btn = QPushButton("Already have an account? Login")
        switch_btn.clicked.connect(lambda: self.animate_transition(self.login_widget))

        layout.addWidget(QLabel("Register"))
        layout.addWidget(self.reg_name)
        layout.addWidget(self.reg_pin)
        layout.addWidget(reg_btn)
        layout.addWidget(switch_btn)

        self.register_widget.setLayout(layout)
        self.stack.addWidget(self.register_widget)

    def dashboard_screen(self):
        self.dashboard_widget = QWidget()
        layout = QVBoxLayout()

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(100, 100)
        self.avatar_label.setAlignment(Qt.AlignCenter)

        self.welcome_label = QLabel()
        self.balance_label = QLabel()

        deposit_btn = QPushButton("Deposit")
        deposit_btn.clicked.connect(self.deposit)

        withdraw_btn = QPushButton("Withdraw")
        withdraw_btn.clicked.connect(self.withdraw)

        history_btn = QPushButton("Show Transaction History")
        history_btn.clicked.connect(self.show_history)

        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)

        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)

        layout.addWidget(self.avatar_label)
        layout.addWidget(self.welcome_label)
        layout.addWidget(self.balance_label)
        layout.addWidget(deposit_btn)
        layout.addWidget(withdraw_btn)
        layout.addWidget(history_btn)
        layout.addWidget(self.history_text)
        layout.addWidget(logout_btn)

        self.dashboard_widget.setLayout(layout)
        self.stack.addWidget(self.dashboard_widget)

    def login_user(self):
        name = self.login_name.text().strip().title()
        pin = self.login_pin.text().strip()
        if not name or not pin:
            QMessageBox.warning(self, "Error", "Fields cannot be empty.")
            return
        hashed = hash_pin(pin)

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Name"] == name and row["HashedPIN"] == hashed:
                        self.user = name
                        self.balance = load_balance(name)
                        self.update_dashboard()
                        self.animate_transition(self.dashboard_widget)
                        return
        QMessageBox.warning(self, "Error", "Invalid name or PIN.")

    def register_user(self):
        name = self.reg_name.text().strip().title()
        pin = self.reg_pin.text().strip()

        if not name.isalpha():
            QMessageBox.warning(self, "Error", "Name must contain only letters.")
            return
        if len(pin) != 4 or not pin.isdigit():
            QMessageBox.warning(self, "Error", "PIN must be exactly 4 digits.")
            return

        hashed = hash_pin(pin)

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Name"] == name:
                        QMessageBox.warning(self, "Error", "User already exists.")
                        return

        with open(USERS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if os.stat(USERS_FILE).st_size == 0:
                writer.writerow(["Name", "HashedPIN"])
            writer.writerow([name, hashed])

        generate_avatar(name)
        QMessageBox.information(self, "Success", "User registered successfully.")
        self.reg_name.clear()
        self.reg_pin.clear()

    def update_dashboard(self):
        self.welcome_label.setText(f"Welcome {self.user} \U0001F60A")
        self.balance_label.setText(f"Your Balance: ${self.balance:.2f}")
        self.history_text.clear()

        avatar_path = os.path.join(AVATAR_DIR, f"{self.user.lower()}.png")
        if os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pixmap)

    def deposit(self):
        amount, ok = QInputDialog.getDouble(self, "Deposit", "Enter amount to deposit:")
        if ok and amount > 0:
            if amount >= SUSPICIOUS_LIMIT:
                QMessageBox.warning(self, "Suspicious", "\u26A0\ufe0f Large deposit flagged as suspicious.")
            self.balance += amount
            log_transaction(self.user, "Deposit", amount, self.balance)
            self.update_dashboard()
            QMessageBox.information(self, "Success", f"${amount:.2f} was deposited successfully!")
        elif ok:
            QMessageBox.warning(self, "Error", "Deposit amount must be greater than 0.")

    def withdraw(self):
        # ✅ FIXED: use the correct static method name in one token
        amount, ok = QInputDialog.getDouble(self, "Withdraw", "Enter amount to withdraw:")
        if ok:
            if amount <= 0:
                QMessageBox.warning(self, "Error", "Amount must be positive.")
            elif amount > self.balance:
                QMessageBox.warning(self, "Error", "Insufficient balance.")
            else:
                if amount >= SUSPICIOUS_LIMIT:
                    QMessageBox.warning(self, "Suspicious", "\u26A0\ufe0f Large withdrawal flagged as suspicious.")
                self.balance -= amount
                log_transaction(self.user, "Withdrawal", amount, self.balance)
                self.update_dashboard()
                QMessageBox.information(self, "Success", f"${amount:.2f} was withdrawn successfully!")

    def show_history(self):
        self.history_text.clear()
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Name"] == self.user:
                        self.history_text.append(
                            f"{row['Timestamp']} | {row['Type']} | ${row['Amount']} | Balance: ${row['Balance']}")

    def logout(self):
        save_balance(self.user, self.balance)
        self.user = None
        self.login_name.clear()
        self.login_pin.clear()
        self.animate_transition(self.login_widget)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash_pix = QPixmap("GbankingApp/Gbanking/splash.png").scaled(500, 500, Qt.KeepAspectRatio)
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.show()
    QTimer.singleShot(2000, splash.close)

    window = BankApp()
    window.resize(420, 580)
    QTimer.singleShot(2000, window.show)

    sys.exit(app.exec_())

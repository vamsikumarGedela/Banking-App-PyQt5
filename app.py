import sys
import os
import csv
import hashlib
import secrets
from decimal import Decimal, ROUND_HALF_UP, getcontext
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QStackedWidget, QMessageBox, QInputDialog, QSplashScreen,
    QTableWidget, QTableWidgetItem, QFileDialog, QComboBox, QSpacerItem,
    QSizePolicy, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QPixmap, QIntValidator, QRegularExpressionValidator, QFont
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QObject, pyqtProperty,
    QRegularExpression, QEvent
)

# -------------------- Constants & Paths -------------------- #
APP_NAME = "🏦 GBanking"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Gbanking")
AVATAR_DIR = os.path.join(DATA_DIR, "avatars")

USERS_FILE = os.path.join(DATA_DIR, "users.csv")
BALANCE_FILE = os.path.join(DATA_DIR, "balance.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "history.csv")

SUSPICIOUS_LIMIT = Decimal("1000.00")
CURRENCY = "USD"
IDLE_LOCK_MS = 3 * 60 * 1000   # 3 minutes
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 5

# Security: pepper is static here; for production move to env/secret
PIN_PEPPER = "f6c6408a5b8a4680b7b8b7e7"

# Categories for transactions
CATEGORIES = ["General", "Salary", "Savings", "Rent", "Groceries", "Utilities", "Transfer", "ATM", "Entertainment", "Bills", "Other"]

# Money precision
getcontext().prec = 28


# -------------------- Helpers: Money, Files, Security -------------------- #
def to_money(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ensure_files():
    """Create data directory and CSVs with headers on first run."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(AVATAR_DIR, exist_ok=True)

    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Salt", "HashedPIN"])

    if not os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Balance"])

    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Type", "Amount", "Balance", "Timestamp", "Category", "Note"])


def hash_pin_legacy(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def hash_pin_salted(pin: str, salt_hex: str) -> str:
    material = (salt_hex + pin + PIN_PEPPER).encode()
    return hashlib.sha256(material).hexdigest()


def gen_salt() -> str:
    return secrets.token_hex(16)  # 32 hex chars


def load_balance(name: str) -> Decimal:
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name", "") == name:
                    try:
                        return to_money(row.get("Balance", "0"))
                    except Exception:
                        return Decimal("0.00")
    return Decimal("0.00")


def save_balance(name: str, balance: Decimal):
    # Read existing
    records = []
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r", newline="") as f:
            records = list(csv.DictReader(f))

    # Update or append
    updated = False
    for row in records:
        if row.get("Name", "") == name:
            row["Balance"] = f"{to_money(balance):.2f}"
            updated = True
            break
    if not updated:
        records.append({"Name": name, "Balance": f"{to_money(balance):.2f}"})

    # Write back
    with open(BALANCE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Balance"])
        writer.writeheader()
        writer.writerows(records)


def log_transaction(name: str, trans_type: str, amount: Decimal, balance: Decimal, category="General", note=""):
    new_file = not os.path.exists(HISTORY_FILE) or os.stat(HISTORY_FILE).st_size == 0
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["Name", "Type", "Amount", "Balance", "Timestamp", "Category", "Note"])
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([name, trans_type, f"{to_money(amount):.2f}", f"{to_money(balance):.2f}", ts, category, note])


def get_color_from_name(name):
    colors = ["#f44336", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#3F51B5", "#795548"]
    return colors[sum(ord(c) for c in name) % len(colors)]


def generate_avatar(name):
    initials = "".join([part[0] for part in name.split() if part]).upper() or "U"
    color = get_color_from_name(name)
    size = 120
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Base circle
    circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_circle = ImageDraw.Draw(circle)
    draw_circle.ellipse((0, 0, size, size), fill=color)

    # Outer glow ring
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse((4, 4, size - 4, size - 4), outline=(255, 255, 255, 60), width=6)

    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except Exception:
        font = ImageFont.load_default()

    draw_text = ImageDraw.Draw(circle)
    bbox = draw_text.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw_text.text(((size - text_w) / 2, (size - text_h) / 2 - 2), initials, font=font, fill="white")

    img.paste(circle, (0, 0), circle)
    img.alpha_composite(glow)

    path = os.path.join(AVATAR_DIR, f"{name.lower().replace(' ', '_')}.png")
    img.save(path)
    return path


# -------------------- Animated Number Helper -------------------- #
class NumberAnimator(QObject):
    def __init__(self, start: Decimal, end: Decimal, on_update):
        super().__init__()
        self._value = float(start)
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(450)
        self._anim.setStartValue(float(start))
        self._anim.setEndValue(float(end))
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.on_update = on_update
        self._anim.valueChanged.connect(lambda *_: self.on_update(Decimal(f"{self._value:.2f}")))

    def start(self):
        self._anim.start()

    def getValue(self):
        return self._value

    def setValue(self, v):
        self._value = v
        self.on_update(Decimal(f"{self._value:.2f}"))
    value = pyqtProperty(float, fget=getValue, fset=setValue)


# -------------------- Main Application -------------------- #
class BankApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.stack = QStackedWidget(self)
        self.user = None
        self.balance = Decimal("0.00")
        self._fade_anim = None
        self._balance_anim = None

        # security/session
        self.failed_attempts = {}      # {name: count}
        self.locked_until = {}         # {name: datetime}
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(IDLE_LOCK_MS)
        self.idle_timer.timeout.connect(self._auto_lock)
        self.installEventFilter(self)

        self._build_ui()
        self._apply_theme()

    # ---------- UI ---------- #
    def _build_ui(self):
        self._build_login()
        self._build_register()
        self._build_dashboard()

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.stack.setCurrentWidget(self.login_widget)

    def _apply_theme(self):
        self.setStyleSheet("""
          QWidget { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 14px; color: #EAECEF; }
          QWidget { background-color: #0B1020; }
          QLabel#title { font-size: 18px; font-weight: 700; color: #DDE9FF; margin: 6px 0 2px; }
          QLabel#balance { font-size: 28px; font-weight: 800; color: #8CC8FF; }
          QLabel#welcome { font-size: 16px; color: #BFD6FF; }
          QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #2D4B9A, stop:1 #5A8BFF);
            border: none; border-radius: 12px; padding: 10px 14px; font-weight: 600;
          }
          QPushButton#danger { background: #C62828; }
          QLineEdit, QComboBox {
            background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
            border-radius: 12px; padding: 10px; selection-background-color: #2D4B9A;
          }
          QTableWidget {
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.10);
            border-radius: 10px; gridline-color: rgba(255,255,255,0.15);
          }
          QHeaderView::section {
            background: rgba(255,255,255,0.08); border: none; padding: 6px; color: #EAECEF;
          }
        """)

    def _fade_to(self, target_widget):
        eff = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(eff)
        self.stack.setCurrentWidget(target_widget)

        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._fade_anim = anim  # keep ref

    # ---------- Screens ---------- #
    def _build_login(self):
        self.login_widget = QWidget()
        layout = QVBoxLayout()

        img = QLabel(alignment=Qt.AlignCenter)
        bank_img_path = os.path.join(BASE_DIR, "GbankingApp", "Gbanking", "bank.png")
        if os.path.exists(bank_img_path):
            pm = QPixmap(bank_img_path).scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img.setPixmap(pm)
        layout.addWidget(img)

        t = QLabel("Login", objectName="title", alignment=Qt.AlignCenter)
        layout.addWidget(t)

        self.login_name = QLineEdit(placeholderText="Enter Full Name")
        self.login_pin = QLineEdit(placeholderText="Enter 4-digit PIN")
        self.login_pin.setEchoMode(QLineEdit.Password)
        self.login_pin.setMaxLength(4)
        self.login_pin.setValidator(QIntValidator(0, 9999, self))

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login_user)

        switch_btn = QPushButton("New user? Register here")
        switch_btn.clicked.connect(lambda: self._fade_to(self.register_widget))

        layout.addWidget(self.login_name)
        layout.addWidget(self.login_pin)
        layout.addWidget(login_btn)
        layout.addWidget(switch_btn)
        layout.addStretch(1)

        self.login_widget.setLayout(layout)
        self.stack.addWidget(self.login_widget)

    def _build_register(self):
        self.register_widget = QWidget()
        layout = QVBoxLayout()

        img = QLabel(alignment=Qt.AlignCenter)
        bank_img_path = os.path.join(BASE_DIR, "GbankingApp", "Gbanking", "bank.png")
        if os.path.exists(bank_img_path):
            pm = QPixmap(bank_img_path).scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img.setPixmap(pm)
        layout.addWidget(img)

        t = QLabel("Register", objectName="title", alignment=Qt.AlignCenter)
        layout.addWidget(t)

        self.reg_name = QLineEdit(placeholderText="Enter Full Name")
        # allow letters, spaces, hyphen, apostrophe (first char must be a letter)
        self.reg_name.setValidator(QRegularExpressionValidator(QRegularExpression(r"[A-Za-z][A-Za-z\s\-']{1,48}"), self))

        self.reg_pin = QLineEdit(placeholderText="Set 4-digit PIN")
        self.reg_pin.setEchoMode(QLineEdit.Password)
        self.reg_pin.setMaxLength(4)
        self.reg_pin.setValidator(QIntValidator(0, 9999, self))

        reg_btn = QPushButton("Create Account")
        reg_btn.clicked.connect(self.register_user)

        switch_btn = QPushButton("Already have an account? Login")
        switch_btn.clicked.connect(lambda: self._fade_to(self.login_widget))

        layout.addWidget(self.reg_name)
        layout.addWidget(self.reg_pin)
        layout.addWidget(reg_btn)
        layout.addWidget(switch_btn)
        layout.addStretch(1)

        self.register_widget.setLayout(layout)
        self.stack.addWidget(self.register_widget)

    def _build_dashboard(self):
        self.dashboard_widget = QWidget()
        layout = QVBoxLayout()

        # Top: Avatar + Welcome
        top = QHBoxLayout()
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        top.addWidget(self.avatar_label)

        wl_box = QVBoxLayout()
        self.welcome_label = QLabel(objectName="welcome")
        self.balance_label = QLabel(objectName="balance")
        wl_box.addWidget(self.welcome_label)
        wl_box.addWidget(self.balance_label)
        top.addLayout(wl_box)
        top.addStretch(1)

        layout.addLayout(top)

        # Quick actions row
        actions = QHBoxLayout()
        deposit_btn = QPushButton("Deposit")
        withdraw_btn = QPushButton("Withdraw")
        export_btn = QPushButton("Export Statement")

        deposit_btn.clicked.connect(self.deposit)
        withdraw_btn.clicked.connect(self.withdraw)
        export_btn.clicked.connect(self.export_statement)

        actions.addWidget(deposit_btn)
        actions.addWidget(withdraw_btn)
        actions.addWidget(export_btn)
        actions.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(actions)

        # Filters row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:", alignment=Qt.AlignVCenter))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Deposit", "Withdrawal"])
        self.filter_combo.currentIndexChanged.connect(self.show_history)
        filter_row.addWidget(self.filter_combo)

        filter_row.addWidget(QLabel("Category:", alignment=Qt.AlignVCenter))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["All"] + CATEGORIES)
        self.category_combo.currentIndexChanged.connect(self.show_history)
        filter_row.addWidget(self.category_combo)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # History table
        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(["Timestamp", "Type", "Amount", "Balance", "Category", "Note"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(self.history_table.SelectRows)
        self.history_table.setEditTriggers(self.history_table.NoEditTriggers)
        layout.addWidget(self.history_table)

        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("danger")
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

        self.dashboard_widget.setLayout(layout)
        self.stack.addWidget(self.dashboard_widget)

    # ---------- Session / Events ---------- #
    def eventFilter(self, obj, event):
        # Reset idle timer on interaction
        et = event.type()
        if et in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.MouseMove):
            self.idle_timer.start()
        return super().eventFilter(obj, event)

    def _auto_lock(self):
        # Auto-logout to login screen if logged in
        if self.user:
            QMessageBox.information(self, "Session Locked", "No activity detected. You’ve been logged out for safety.")
            self.logout()

    # ---------- Auth ---------- #
    def _is_locked_out(self, name: str) -> bool:
        until = self.locked_until.get(name)
        if until and datetime.now() < until:
            remaining = (until - datetime.now()).seconds // 60 + 1
            QMessageBox.warning(self, "Locked", f"Too many failed attempts. Try again in ~{remaining} min.")
            return True
        return False

    def _record_failed_attempt(self, name: str):
        c = self.failed_attempts.get(name, 0) + 1
        self.failed_attempts[name] = c
        if c >= MAX_LOGIN_ATTEMPTS:
            self.locked_until[name] = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
            self.failed_attempts[name] = 0

    def login_user(self):
        name = self.login_name.text().strip().title()
        pin = self.login_pin.text().strip()

        if not name or len(pin) != 4 or not pin.isdigit():
            QMessageBox.warning(self, "Error", "Please enter a valid name and a 4-digit PIN.")
            return

        if self._is_locked_out(name):
            return

        ok = False
        found = False
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name", "") == name:
                        found = True
                        salt = row.get("Salt", "")  # may be empty for legacy
                        stored = row.get("HashedPIN", "")
                        if salt:
                            calc = hash_pin_salted(pin, salt)
                            ok = (calc == stored)
                        else:
                            calc = hash_pin_legacy(pin)
                            ok = (calc == stored)
                        break

        if not found:
            QMessageBox.warning(self, "Error", "User not found.")
            return

        if not ok:
            self._record_failed_attempt(name)
            QMessageBox.warning(self, "Error", "Invalid PIN.")
            return

        # success
        self.user = name
        self.balance = load_balance(name)
        self.update_dashboard(first=True)
        self._fade_to(self.dashboard_widget)
        self.idle_timer.start()
        self.login_pin.clear()

    def register_user(self):
        name = self.reg_name.text().strip().title()
        pin = self.reg_pin.text().strip()

        if not name or not pin.isdigit() or len(pin) != 4:
            QMessageBox.warning(self, "Error", "Provide a valid name and a 4-digit PIN.")
            return

        # Check exists
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name", "") == name:
                        QMessageBox.warning(self, "Error", "User already exists.")
                        return

        salt = gen_salt()
        hashed = hash_pin_salted(pin, salt)
        new_file = not os.path.exists(USERS_FILE) or os.stat(USERS_FILE).st_size == 0
        with open(USERS_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["Name", "Salt", "HashedPIN"])
            writer.writerow([name, salt, hashed])

        generate_avatar(name)
        QMessageBox.information(self, "Success", "User registered successfully.")
        self.reg_name.clear()
        self.reg_pin.clear()
        self._fade_to(self.login_widget)

    # ---------- Dashboard helpers ---------- #
    def update_dashboard(self, first=False):
        self.welcome_label.setText(f"Welcome, {self.user} 😊")

        def render_balance(val: Decimal):
            self.balance_label.setText(f"${val:.2f}")

        if first:
            render_balance(self.balance)
        else:
            try:
                current_text = self.balance_label.text().replace("$", "").strip() or "0.00"
                current_val = to_money(current_text)
            except Exception:
                current_val = self.balance
            self._balance_anim = NumberAnimator(current_val, self.balance, render_balance)
            self._balance_anim.start()

        avatar_path = os.path.join(AVATAR_DIR, f"{self.user.lower().replace(' ', '_')}.png")
        if os.path.exists(avatar_path):
            pm = QPixmap(avatar_path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pm)
        else:
            generate_avatar(self.user)
            if os.path.exists(avatar_path):
                pm = QPixmap(avatar_path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(pm)

        self.show_history()

    def _get_amount_category_note(self, title: str):
        dlg_amount, ok = QInputDialog.getDouble(self, title, f"Enter amount ({CURRENCY}):", 0.00, 0.01, 10_000_000.00, 2)
        if not ok:
            return None, None, None, False
        amount = to_money(dlg_amount)

        cat, ok = QInputDialog.getItem(self, title, "Category:", CATEGORIES, 0, False)
        if not ok:
            cat = "General"

        note, ok2 = QInputDialog.getText(self, title, "Note (optional):")
        if not ok2:
            note = ""

        return amount, cat, note, True

    def _confirm_large(self, title: str, amount: Decimal):
        if amount >= SUSPICIOUS_LIMIT:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Warning)
            m.setWindowTitle("Review Transaction")
            m.setText(f"⚠️ {title}\nLarge amount detected: ${amount:.2f}.\nDo you want to continue?")
            m.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            return m.exec_() == QMessageBox.Yes
        return True

    # ---------- Actions ---------- #
    def deposit(self):
        res = self._get_amount_category_note("Deposit")
        if not res[-1]:
            return
        amount, cat, note, _ = res

        if amount <= 0:
            QMessageBox.warning(self, "Error", "Deposit amount must be greater than 0.")
            return

        if not self._confirm_large("Deposit flagged as suspicious", amount):
            return

        self.balance = to_money(self.balance + amount)
        log_transaction(self.user, "Deposit", amount, self.balance, category=cat, note=note)
        self.update_dashboard()
        QMessageBox.information(self, "Success", f"${amount:.2f} was deposited successfully!")

    def withdraw(self):
        res = self._get_amount_category_note("Withdraw")
        if not res[-1]:
            return
        amount, cat, note, _ = res

        if amount <= 0:
            QMessageBox.warning(self, "Error", "Amount must be positive.")
            return
        if amount > self.balance:
            QMessageBox.warning(self, "Error", "Insufficient balance.")
            return

        if not self._confirm_large("Withdrawal flagged as suspicious", amount):
            return

        self.balance = to_money(self.balance - amount)
        log_transaction(self.user, "Withdrawal", amount, self.balance, category=cat, note=note)
        self.update_dashboard()
        QMessageBox.information(self, "Success", f"${amount:.2f} was withdrawn successfully!")

    def show_history(self):
        self.history_table.setRowCount(0)

        ftype = self.filter_combo.currentText()
        fcategory = self.category_combo.currentText()

        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", newline="") as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    if row.get("Name", "") == self.user:
                        if ftype != "All" and row.get("Type", "") != ftype:
                            continue
                        if fcategory != "All" and row.get("Category", "General") != fcategory:
                            continue
                        rows.append(row)

                def parse_ts(r):
                    try:
                        return datetime.strptime(r.get("Timestamp", ""), "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        return datetime.min

                rows.sort(key=parse_ts, reverse=True)

                for r in rows:
                    ts = r.get("Timestamp", "")
                    typ = r.get("Type", "")
                    amt = r.get("Amount", "0.00")
                    bal = r.get("Balance", "0.00")
                    cat = r.get("Category", "General")
                    note = r.get("Note", "")

                    ridx = self.history_table.rowCount()
                    self.history_table.insertRow(ridx)
                    self.history_table.setItem(ridx, 0, QTableWidgetItem(ts))
                    self.history_table.setItem(ridx, 1, QTableWidgetItem(typ))
                    self.history_table.setItem(ridx, 2, QTableWidgetItem(f"${amt}"))
                    self.history_table.setItem(ridx, 3, QTableWidgetItem(f"${bal}"))
                    self.history_table.setItem(ridx, 4, QTableWidgetItem(cat))
                    self.history_table.setItem(ridx, 5, QTableWidgetItem(note))

    def export_statement(self):
        if not self.user:
            QMessageBox.warning(self, "Error", "Please log in.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Statement", f"{self.user}_statement.csv", "CSV Files (*.csv)")
        if not path:
            return

        headers = ["Timestamp", "Type", "Amount", "Balance", "Category", "Note"]
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name"] + headers)
            for r in range(self.history_table.rowCount()):
                row = [self.user]
                for c in range(self.history_table.columnCount()):
                    item = self.history_table.item(r, c)
                    row.append(item.text() if item else "")
                writer.writerow(row)

        QMessageBox.information(self, "Exported", f"Statement saved to:\n{path}")

    def logout(self):
        if self.user is not None:
            save_balance(self.user, self.balance)
        self.user = None
        self.login_name.clear()
        self.login_pin.clear()
        self.idle_timer.stop()
        self._fade_to(self.login_widget)


# -------------------- Splash + Main -------------------- #
def find_splash_image():
    candidates = [
        os.path.join(BASE_DIR, "splash.png"),                               # next to script
        os.path.join(BASE_DIR, "GbankingApp", "Gbanking", "splash.png"),    # your old path
        os.path.join(DATA_DIR, "splash.png"),                               
        "/mnt/data/splash.png",                                             # attached image path
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


if __name__ == "__main__":
    ensure_files()
    app = QApplication(sys.argv)

    # Create splash (with progress % text)
    splash_path = find_splash_image()
    if splash_path:
        pix = QPixmap(splash_path).scaled(520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint)
    else:
        # Fallback: solid splash with text
        pix = QPixmap(520, 360)
        pix.fill(Qt.darkCyan)
        splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint)

    # Show initial message
    splash_font = QFont()
    splash_font.setPointSize(11)
    splash.setFont(splash_font)
    splash.show()
    splash.showMessage("Loading… 0%", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)
    app.processEvents()

    # Prepare main window but don't show yet
    window = BankApp()
    window.resize(520, 720)

    # Animate splash progress
    progress = {"val": 0}

    def tick():
        # You can perform light setup work here if needed
        progress["val"] += 4
        if progress["val"] > 100:
            progress["val"] = 100
        splash.showMessage(f"Loading… {progress['val']}%", Qt.AlignHCenter | Qt.AlignBottom, Qt.white)

        if progress["val"] >= 100:
            timer.stop()
            window.show()
            splash.finish(window)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(40)  # ~1 second to 100% (25 ticks)

    sys.exit(app.exec_())

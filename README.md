
# 🏦 GBanking (PyQt5 Desktop App)

A simple, modern-looking banking demo built with **PyQt5**. It supports user registration with salted+peppered PIN hashing, avatar generation, deposits, withdrawals, transaction history with filters, idle auto‑lock, and CSV export — all stored locally in CSV files. fileciteturn0file0

---

## ✨ Features
- **Register/Login** with 4‑digit PIN (salted + peppered SHA‑256)
- **Animated balance** updates and a polished **dark UI**
- **Deposits / Withdrawals** with category + note
- **Suspicious amount review** threshold (default: `$1000.00`)
- **Transaction history** with type/category filters, sorted by time
- **CSV export** of statement
- **Idle auto‑lock** (default: 3 minutes)
- **Avatar image** auto‑generated from initials

---

## 📦 Project Structure
```
.
├── app.py
├── Gbanking/
│   ├── users.csv           # Name, Salt, HashedPIN
│   ├── balance.csv         # Name, Balance
│   ├── history.csv         # Name, Type, Amount, Balance, Timestamp, Category, Note (autocreated)
│   └── avatars/            # Per-user avatar PNGs (autocreated)
├── splash.png              # optional (see below)
├── bank.png                # optional (see below)
└── README.md
```

> The `Gbanking/` folder and its CSVs/avatars are created automatically on first run if missing.

---

## 🖼️ Images (Optional but Nice)
- **Splash image**: the app looks for the first existing path in this order:
  1. `./splash.png` (next to `app.py`)
  2. `./GbankingApp/Gbanking/splash.png` (legacy)
  3. `./Gbanking/splash.png`
  4. `/mnt/data/splash.png`

- **Bank logo on login/register screen**: the app tries
  `./GbankingApp/Gbanking/bank.png`. Put your bank logo there or remove that line in code if not needed.

---

## 🛠️ Requirements
- Python 3.9+
- Packages: `PyQt5`, `Pillow`

Install:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install PyQt5 Pillow
```

---

## ▶️ Run
```bash
python app.py
```

If it’s your first run, the app will create `Gbanking/` with CSVs and the `avatars/` folder.

---

## 🚪 How to Use
1. **Register**: Enter your full name and a 4‑digit PIN.
2. **Login**: Use the same name + PIN (case-insensitive for name).  
3. **Dashboard**:
   - Click **Deposit** / **Withdraw** (choose category + note).
   - View **History** and filter by **Type** or **Category**.
   - **Export Statement** to CSV.
   - **Logout** to save your current balance.
4. **Auto‑Lock**: If you’re idle for a while (default: 3 minutes), the app returns to the login screen.

---

## ⚙️ Configuration (edit in `app.py`)
- `SUSPICIOUS_LIMIT = Decimal("1000.00")` – confirmation for large transactions
- `CURRENCY = "USD"` – currency label
- `IDLE_LOCK_MS = 3 * 60 * 1000` – idle auto‑lock time
- `CATEGORIES = [...]` – transaction categories
- Avatar/font: the app tries `arial.ttf` and falls back to a default

---

## 🧰 Data Model (CSV)
- **users.csv**: `Name, Salt, HashedPIN`
- **balance.csv**: `Name, Balance`
- **history.csv**: `Name, Type, Amount, Balance, Timestamp, Category, Note`

> Each user’s balance/history is keyed by the **Name** column.

---

## 🧪 Troubleshooting
- **Qt plugin errors on Windows**: Ensure `PyQt5` is installed in the **same** venv you’re running.
- **Font not found** for avatar initials: The app falls back if `arial.ttf` isn’t available.
- **Images not showing**: Confirm optional image file paths listed above.

---

## 📤 Uploading to GitHub
1. Put this `README.md` next to `app.py`.
2. (Optional) Create a `.gitignore` like:
   ```gitignore
   __pycache__/
   *.pyc
   .venv/
   venv/
   .env
   Gbanking/history.csv
   Gbanking/avatars/
   .DS_Store
   .idea/
   .vscode/
   ```
3. Initialize and push:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: GBanking PyQt5 app"
   git branch -M main
   git remote add origin (https://github.com/vamsikumarGedela/Banking-App-PyQt5)
   git push -u origin main
   ```

---

## 📄 License
Distributed under the MIT License. See LICENSE for details.

**## Author**
Vamsi Kumar - Initial development

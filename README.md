# SaveWise

**SaveWise** is a lightweight, responsive financial management and expense tracking web application. It helps users split and monitor spending between essential daily needs (**Daily**) and impulse or wasteful expenditures (**Faltu**).

---

## Technology Stack

- **Backend**: Python (Flask 3.1)
- **Database**: SQLite3 (with integer paise storage and strict `PRAGMA foreign_keys = ON` relational integrity)
- **Architecture**: Application factory pattern, isolated domain service layer, and uniform REST API under `/api/v1/`
- **Frontend**: Vanilla HTML5, modern CSS3 (responsive design system with dark/light themes), and modular ES6 JavaScript (zero external JS dependencies, XSS-safe DOM rendering)
- **Testing**: Python `unittest` suite covering services, business logic, multi-user isolation, and API endpoints

---

## Local Setup & Installation

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Set Up Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the sample environment file:
```bash
cp .env.example .env
```
Edit `.env` to configure your settings:
- `SECRET_KEY`: Random secret key for session/CSRF security (a random key will be generated dynamically if omitted).
- `DATABASE_PATH`: Path to SQLite database file (defaults to `savewise.db`).
- `FLASK_DEBUG`: Set to `True` for local development, `False` for production.

### 5. Verify Database & Seed Data
Run the verification check script:
```bash
python test_setup.py
```

---

## Running the Application

Start the local Flask development server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Running the Automated Tests

SaveWise includes a comprehensive test suite covering business logic and API integration:

```bash
# Run all unit and integration tests
python -m unittest discover -s tests -p "test_*.py" -v
```

- **`tests/test_services.py`**: Validates integer paise conversions, date parsing, zero-division error handling in balance/percentage calculations, and multi-user data isolation.
- **`tests/test_api.py`**: Validates REST endpoints, JSON error envelopes, HTTP status codes, input validations, CORS headers, and 404 handlers.

---

## REST API Endpoints (`/api/v1/`)

All API responses follow a uniform JSON structure:
- **Success**: `{"success": true, "data": <payload>, "message": "<string>"}`
- **Error**: `{"success": false, "error": "<description>"}`

### Dashboard
| Method | Endpoint | Query Params | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/dashboard/summary` | `month=YYYY-MM` | Computes monthly totals (income, daily, faltu, net balance, faltu percentages). |

### Incomes
| Method | Endpoint | Query Params / Payload | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/incomes` | `month=YYYY-MM` | Lists user incomes for the specified month (defaults to current month). |
| `POST` | `/api/v1/incomes` | `{ amount_inr, source, date, note? }` | Creates a new income record. |
| `GET` | `/api/v1/incomes/<id>` | — | Retrieves a single income record. |
| `PUT` | `/api/v1/incomes/<id>` | `{ amount_inr?, source?, date?, note? }` | Updates an existing income record. |
| `DELETE` | `/api/v1/incomes/<id>` | — | Deletes an income record. |

### Expenses
| Method | Endpoint | Query Params / Payload | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/expenses` | `month=YYYY-MM`, `type=daily\|faltu\|all` | Lists expenses with optional month and type filters. |
| `POST` | `/api/v1/expenses` | `{ amount_inr, type, sub_category, date, note? }` | Logs a new daily or faltu expense. |
| `GET` | `/api/v1/expenses/<id>` | — | Retrieves a single expense record. |
| `PUT` | `/api/v1/expenses/<id>` | `{ amount_inr?, type?, sub_category?, date?, note? }` | Updates an existing expense record. |
| `DELETE` | `/api/v1/expenses/<id>` | — | Deletes an expense record. |

---

## Project Roadmap

- [x] **Phase 1: Core Expense Tracker & Dashboard**
  - Income tracking and categorization.
  - Daily (essential) vs Faltu (discretionary) expense classification.
  - Monthly dashboard aggregations, balance, and faltu spending ratios.
  - Full CRUD operations with modal UI and filter tabs.
  - Clean modular architecture (service layer, integer paise math, SQLite foreign keys).

- [ ] **Phase 2: Smart Features & Budget Controls**
  - Monthly Faltu spending budget limit with alert warnings (`monthly_budgets` table ready).
  - Monthly savings targets (`savings_goals` table ready).
  - Visual analytics and spending breakdown charts.
  - One-tap quick presets for frequent expenses (`quick_presets` table ready).
  - 24-hour impulse control wishlist (`wishlist_items` table ready).
  - Udhar (lent/borrowed money) ledger (`udhar_records` table ready).

- [ ] **Phase 3: Multi-User, Intelligence & PWA**
  - Multi-user authentication (JWT / session login).
  - Savings simulator and what-if scenario planner.
  - Automated weekly financial summaries and actionable tips.
  - Progressive Web App (PWA) offline support.

---

## Notes on Legacy Files

Previous Node.js/MongoDB prototype files have been archived into [`old-node-version/`](old-node-version/) for reference.

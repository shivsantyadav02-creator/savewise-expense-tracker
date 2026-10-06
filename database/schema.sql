-- SaveWise SQLite Schema
-- Designed for Phase 1 (Core), Phase 2 (Smart Features), and Phase 3 (Auth & Intelligence)
-- Notice: user_id is in every table, enabling Phase 3 Multi-User without any schema changes!

-- 1. Users Table (Seeded with default_user id=1 for Phase 1)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Incomes Table (Phase 1)
-- All money stored as integers in paise (1 INR = 100 paise)
-- month is stored as 'YYYY-MM' (e.g. '2026-10') derived automatically from date
CREATE TABLE IF NOT EXISTS incomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    source TEXT NOT NULL,
    date DATE NOT NULL,
    month TEXT NOT NULL,
    note TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_incomes_user_month ON incomes(user_id, month);
CREATE INDEX IF NOT EXISTS idx_incomes_user_date ON incomes(user_id, date);

-- 3. Unified Expenses Table (Phase 1)
-- type is constrained to 'daily' or 'faltu'
-- wishlist_item_id is nullable (used when an expense is auto-created from a bought wishlist item in Phase 2)
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    type TEXT NOT NULL CHECK (type IN ('daily', 'faltu')),
    sub_category TEXT NOT NULL,
    date DATE NOT NULL,
    month TEXT NOT NULL,
    note TEXT,
    wishlist_item_id INTEGER DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (wishlist_item_id) REFERENCES wishlist_items (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month);
CREATE INDEX IF NOT EXISTS idx_expenses_user_type ON expenses(user_id, type);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);

-- 4. Monthly Budgets / Faltu Limit (Phase 2)
CREATE TABLE IF NOT EXISTS monthly_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    faltu_limit_paise INTEGER NOT NULL CHECK (faltu_limit_paise >= 0),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, month),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 5. Savings Goals (Phase 2)
CREATE TABLE IF NOT EXISTS savings_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    target_amount_paise INTEGER NOT NULL CHECK (target_amount_paise > 0),
    title TEXT NOT NULL DEFAULT 'Monthly Savings Target',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, month),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 6. Wishlist Items - 24-Hour Wait Rule (Phase 2)
CREATE TABLE IF NOT EXISTS wishlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    estimated_amount_paise INTEGER NOT NULL CHECK (estimated_amount_paise > 0),
    sub_category TEXT NOT NULL DEFAULT 'Shopping',
    status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'bought', 'dropped')),
    unlock_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_wishlist_user_status ON wishlist_items(user_id, status);

-- 7. Udhar Records - Money Lent / Borrowed (Phase 2)
CREATE TABLE IF NOT EXISTS udhar_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    person_name TEXT NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    type TEXT NOT NULL CHECK (type IN ('lent', 'borrowed')),
    due_date DATE,
    is_settled INTEGER NOT NULL DEFAULT 0 CHECK (is_settled IN (0, 1)),
    note TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_udhar_user_settled ON udhar_records(user_id, is_settled);

-- 8. Quick Presets for Fast Entry (Phase 2)
CREATE TABLE IF NOT EXISTS quick_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    type TEXT NOT NULL CHECK (type IN ('daily', 'faltu')),
    sub_category TEXT NOT NULL,
    icon TEXT DEFAULT '⚡',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Seed Initial Default User (user_id = 1 for Phase 1)
INSERT OR IGNORE INTO users (id, username, email, currency)
VALUES (1, 'default_user', 'user@savewise.local', 'INR');

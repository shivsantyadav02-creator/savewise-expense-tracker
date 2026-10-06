import sqlite3
from flask import Flask
from database.db import get_db, init_app
from utils.helpers import inr_to_paise, paise_to_inr, derive_month_from_date

def test_system():
    app = Flask(__name__)
    init_app(app)
    
    print("[1/3] Testing Currency & Date Helpers...")
    assert inr_to_paise(15.50) == 1550
    assert inr_to_paise("99.99") == 9999
    assert paise_to_inr(1550) == 15.50
    assert derive_month_from_date("2026-10-05") == "2026-10"
    print(" -> Helpers passed!")

    print("[2/3] Testing PRAGMA foreign_keys = ON & Row Factory...")
    with app.app_context():
        db = get_db()
        # Verify PRAGMA
        fk_status = db.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1, "Foreign keys are not enabled!"
        
        # Test FK violation rejection
        try:
            db.execute(
                "INSERT INTO expenses (user_id, amount_paise, type, sub_category, date, month) VALUES (?, ?, ?, ?, ?, ?)",
                (9999, 5000, 'daily', 'Food', '2026-10-05', '2026-10')
            )
            raise AssertionError("Foreign key violation was ignored!")
        except sqlite3.IntegrityError:
            print(" -> Foreign key constraint properly rejected invalid user_id!")

    print("[3/3] Testing Default User...")
    with app.app_context():
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = 1").fetchone()
        assert user is not None
        assert user["username"] == "default_user"
        print(f" -> Found seeded user: id={user['id']}, username={user['username']}")

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_system()

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

def inr_to_paise(amount_inr) -> int:
    """
    Safely converts amount in INR to integer paise.
    Uses Decimal to avoid floating-point binary precision issues.
    
    Example:
        inr_to_paise(19.99) -> 1999
        inr_to_paise("15.50") -> 1550
    """
    if amount_inr is None:
        raise ValueError("Amount cannot be None")
    try:
        dec = Decimal(str(amount_inr))
        if dec <= 0:
            raise ValueError("Amount must be greater than zero")
        paise = (dec * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(paise)
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid monetary value: {amount_inr}")

def paise_to_inr(paise: int) -> float:
    """
    Converts integer paise back to standard INR float.
    
    Example:
        paise_to_inr(1999) -> 19.99
    """
    if paise is None:
        return 0.0
    return round(float(paise) / 100.0, 2)

def derive_month_from_date(date_str: str) -> str:
    """
    Extracts 'YYYY-MM' from an ISO date string 'YYYY-MM-DD'.
    Guarantees consistent month indexing and prevents client tamper.
    
    Example:
        derive_month_from_date("2026-10-05") -> "2026-10"
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("A valid date string in 'YYYY-MM-DD' format is required.")
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except ValueError:
        raise ValueError(f"Invalid date '{date_str}'. Expected format is 'YYYY-MM-DD'.")

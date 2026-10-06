def get_current_user_id() -> int:
    """
    Returns the ID of the currently authenticated user.
    - Phase 1 & 2: Returns default seeded user ID (1).
    - Phase 3: Will be updated in this single location to read from 
      session cookie or JWT auth token.
    """
    return 1

def priority_to_threshold(priority: str) -> int:
    p = (priority or "").upper()
    if p == "HIGH":
        return 2
    if p == "MEDIUM":
        return 3
    if p == "LOW":
        return 4
    raise ValueError("invalid priority")

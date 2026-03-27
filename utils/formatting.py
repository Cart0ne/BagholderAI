"""
BagHolderAI - Shared formatting utilities.
"""


def fmt_price(price: float) -> str:
    """
    Format a price with appropriate decimals.
    - >= $1     → $1,234.56
    - >= $0.01  → $0.0123
    - >= $0.0001 → $0.000059
    - < $0.0001 → $0.00000059
    Handles micro-prices like BONK correctly (never shows $0.00).
    """
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:.4f}"
    if price >= 0.0001:
        return f"${price:.6f}"
    return f"${price:.8f}"

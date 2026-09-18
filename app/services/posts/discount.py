"""Discount calculations: D = F d t, P = F(1 - d t)."""

import re


class DiscountError(ValueError):
    """Raised when a discount request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise DiscountError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise DiscountError(f"{field} must be finite")
    if positive and number <= 0:
        raise DiscountError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise DiscountError(f"{field} cannot be negative")
    return number


def calculate_discount(data):
    """Solve D = F d t and P = F - D = F(1 - d t).

    solve_for: discount | present_value | discount_rate | time
    """
    solve_for = str(data.get("solve_for", "discount")).strip().lower()
    if solve_for not in {"discount", "present_value", "discount_rate", "time"}:
        raise DiscountError(
            "solve_for must be discount, present_value, discount_rate, or time"
        )

    if solve_for == "discount":
        F = _number(data, "future_value", positive=True)
        d = _number(data, "discount_rate") / 100.0
        t = _number(data, "t", positive=True)
        D = F * d * t
        P = F - D
    elif solve_for == "present_value":
        F = _number(data, "future_value", positive=True)
        d = _number(data, "discount_rate") / 100.0
        t = _number(data, "t", positive=True)
        D = F * d * t
        P = F - D
    elif solve_for == "discount_rate":
        F = _number(data, "future_value", positive=True)
        D = _number(data, "discount", positive=True)
        t = _number(data, "t", positive=True)
        d = D / (F * t)
        P = F - D
    else:  # time
        F = _number(data, "future_value", positive=True)
        D = _number(data, "discount", positive=True)
        d = _number(data, "discount_rate", positive=True) / 100.0
        t = D / (F * d)
        P = F - D

    result = {
        "formula": "D = F d t,  P = F - D",
        "solve_for": solve_for,
        "future_value": F,
        "present_value": P,
        "discount": D,
        "discount_rate": d * 100.0,
        "t": t,
    }
    if solve_for in {"discount", "present_value"}:
        result["steps"] = [
            f"1. Identify F = {_fmt(F)}, d = {_fmt(d * 100)}%, t = {_fmt(t)} year(s).",
            f"2. Compute D = F d t = {_fmt(F)} x {_fmt(d)} x {_fmt(t)}.",
            f"3. Discount amount D = {_fmt(D)}.",
            f"4. Present value P = F - D = {_fmt(P)}.",
        ]
    elif solve_for == "discount_rate":
        result["steps"] = [
            "1. Use d = D / (F t).",
            f"2. d = {_fmt(D)} / ({_fmt(F)} x {_fmt(t)}).",
            f"3. Discount rate d = {_fmt(d * 100)}%.",
        ]
    else:
        result["steps"] = [
            "1. Use t = D / (F d).",
            f"2. t = {_fmt(D)} / ({_fmt(F)} x {_fmt(d)}).",
            f"3. Time t = {_fmt(t)} year(s).",
        ]
    return result


def parse_discount_problem(text):
    """Parse a compact natural-language discount problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bdiscount\b", normalized, re.I):
        raise DiscountError("Please include a discount question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    future_match = re.search(
        rf"(?:future value|maturity value|face value|amount|worth)\s*(?:of|is|=)?\s*\$?{num}",
        normalized, re.I,
    )
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    time_match = re.search(rf"(?:for|in|after)\s+{num}\s*(year|years|yr|yrs|month|months|day|days)\b", normalized, re.I)
    present_match = re.search(rf"(?:present value|present worth|proceeds|discounted to)\s*(?:of|is|=)?\s*\$?{num}", normalized, re.I)

    if not future_match or not rate_match or not time_match:
        raise DiscountError("I need the future value, discount rate, and time")

    t = float(time_match.group(1))
    unit = time_match.group(2).lower()
    if unit.startswith("month"):
        t /= 12.0
    elif unit.startswith("day"):
        t /= 360.0

    return {
        "solve_for": "discount",
        "future_value": float(future_match.group(1)),
        "discount_rate": float(rate_match.group(1)),
        "t": t,
        "present_value": float(present_match.group(1)) if present_match else None,
    }


def solve_discount_problem(text):
    data = parse_discount_problem(text)
    result = calculate_discount(data)
    steps = [
        f"1. Identify F = {_fmt(result['future_value'])}, d = {_fmt(result['discount_rate'])}%, t = {_fmt(result['t'])} year(s).",
        f"2. Use D = F d t = {_fmt(result['future_value'])} x {_fmt(result['discount_rate']/100)} x {_fmt(result['t'])}.",
        f"3. Amount of discount D = {_fmt(result['discount'])}.",
        f"4. Present value P = F - D = {_fmt(result['present_value'])}.",
    ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
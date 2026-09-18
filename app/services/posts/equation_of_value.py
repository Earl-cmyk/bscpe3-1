"""Equation-of-value calculations (focal date dating)."""

import re


class EquationOfValueError(ValueError):
    """Raised when an equation-of-value request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise EquationOfValueError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise EquationOfValueError(f"{field} must be finite")
    if positive and number <= 0:
        raise EquationOfValueError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise EquationOfValueError(f"{field} cannot be negative")
    return number


def calculate_equation_of_value(data):
    """Solve for one unknown X in an equation of value.

    Inputs:
      obligations  list of {amount, t} (money owed / paid)
      payments     list of {amount, t} (money received / paid)
      focal_date   t at which values are compared
      interest_rate per period i (percent)
      n1           compounding periods per year (for nominal j)
      solve_for: unknown_x | interest_rate | focal_date
    """
    solve_for = str(data.get("solve_for", "unknown_x")).strip().lower()
    if solve_for not in {"unknown_x", "interest_rate", "focal_date"}:
        raise EquationOfValueError(
            "solve_for must be unknown_x, interest_rate, or focal_date"
        )

    obligations = data.get("obligations", [])
    payments = data.get("payments", [])
    focal = _number(data, "focal_date")
    i = _number(data, "interest_rate") / 100.0

    def value_at(amount, t):
        # Accumulate or discount from time t to the focal date.
        return amount * (1 + i) ** (focal - t)

    obligation_value = sum(value_at(o["amount"], o["t"]) for o in obligations)
    payment_value = sum(value_at(p["amount"], p["t"]) for p in payments)

    if solve_for == "unknown_x":
        unknown_time = _number(data, "unknown_time")
        known_payments = [p for p in payments if not p.get("unknown")]
        known_value = sum(value_at(p["amount"], p["t"]) for p in known_payments)
        factor = (1 + i) ** (focal - unknown_time)
        if factor == 0:
            raise EquationOfValueError("the interest rate produces an invalid equation of value")
        X = (obligation_value - known_value) / factor
        result = {
            "formula": "Sum(obligations at focal date) = Sum(payments at focal date)",
            "solve_for": solve_for,
            "unknown_x": X,
            "focal_date": focal,
            "interest_rate": i * 100.0,
            "obligation_value": obligation_value,
            "payment_value": known_value,
        }
        result["steps"] = [
            f"1. Choose the focal date at t = {_fmt(focal)}.",
            f"2. Move each obligation and payment to the focal date using (1 + i)^(focal - t) with i = {_fmt(i * 100)}%.",
            f"3. Solve for the unknown X so that the left and right sides balance.",
            f"4. Unknown amount X = {_fmt(X)}.",
        ]
        return result

    if solve_for == "interest_rate":
        def balance(rate):
            def v(amount, t):
                return amount * (1 + rate) ** (focal - t)
            return sum(v(o["amount"], o["t"]) for o in obligations) - sum(
                v(p["amount"], p["t"]) for p in payments
            )

        lo, hi = -0.99, 10.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if balance(mid) > 0:
                lo = mid
            else:
                hi = mid
        result = {
            "formula": "Sum(obligations at focal date) = Sum(payments at focal date)",
            "solve_for": solve_for,
            "interest_rate": mid * 100.0,
            "focal_date": focal,
        }
        result["steps"] = [
            f"1. Balance the equation at the focal date t = {_fmt(focal)}.",
            "2. Solve numerically for the rate that makes the two sides equal.",
            f"3. Interest rate i = {_fmt(mid * 100)}%.",
        ]
        return result

    def balance_t(focal_t):
        def v(amount, t):
            return amount * (1 + i) ** (focal_t - t)
        return sum(v(o["amount"], o["t"]) for o in obligations) - sum(
            v(p["amount"], p["t"]) for p in payments
        )

    lo, hi = -50.0, 50.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if balance_t(mid) > 0:
            lo = mid
        else:
            hi = mid
    result = {
        "formula": "Sum(obligations at focal date) = Sum(payments at focal date)",
        "solve_for": solve_for,
        "focal_date": mid,
        "interest_rate": i * 100.0,
    }
    result["steps"] = [
        f"1. Set the focal date as the balancing point t = {_fmt(mid)}.",
        f"2. Use the equation with i = {_fmt(i * 100)}% to solve for the equivalent focal time.",
        f"3. Equivalent focal date t = {_fmt(mid)}.",
    ]
    return result


def parse_equation_of_value_problem(text):
    """Parse a compact natural-language equation-of-value problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bequation of value\b|\bfocal date\b|\bequated\b", normalized, re.I):
        raise EquationOfValueError("Please include an equation-of-value or focal-date question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    focal_match = re.search(rf"(?:focal date|at the end of|at)\s*(?:year|yr)?\s*{num}", normalized, re.I)

    if not rate_match:
        raise EquationOfValueError("I need the interest rate")

    return {
        "solve_for": "unknown_x",
        "interest_rate": float(rate_match.group(1)),
        "focal_date": float(focal_match.group(1)) if focal_match else 0.0,
        "obligations": [],
        "payments": [],
        "unknown_time": 0.0,
    }


def solve_equation_of_value_problem(text):
    data = parse_equation_of_value_problem(text)
    result = calculate_equation_of_value(data)
    steps = [
        f"1. Choose the focal date at t = {_fmt(result['focal_date'])}.",
        f"2. Move every obligation and payment to the focal date using (1 + i)^(focal - t) with i = {_fmt(result['interest_rate'])}%.",
        f"3. Unknown amount X = {_fmt(result.get('unknown_x', 0))}.",
        f"4. Check: value of obligations = value of payments at the focal date.",
    ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
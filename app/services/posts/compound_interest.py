"""Compound-interest calculations (engineering economy)."""

from datetime import date
import re


class CompoundInterestError(ValueError):
    """Raised when a compound-interest request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise CompoundInterestError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise CompoundInterestError(f"{field} must be finite")
    if positive and number <= 0:
        raise CompoundInterestError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise CompoundInterestError(f"{field} cannot be negative")
    return number


def calculate_compound_interest(data):
    """Solve one unknown in F = P(1 + i)^n.

    Inputs use the legend:
      P  principal / present worth
      F  future worth
      i  interest rate per period (percent)
      n  number of interest periods
      n1 compounding periods per year (optional; used with t)
      t  time in years (optional; used with n1)

    solve_for: future_value | principal | interest_rate | periods
    """
    solve_for = str(data.get("solve_for", "future_value")).strip().lower()
    if solve_for not in {"future_value", "principal", "interest_rate", "periods"}:
        raise CompoundInterestError(
            "solve_for must be future_value, principal, interest_rate, or periods"
        )

    # Resolve n from n1 and t when n is not given directly.
    n = data.get("n")
    if n is None and data.get("n1") is not None and data.get("t") is not None:
        n1 = _number(data, "n1", positive=True)
        t = _number(data, "t", positive=True)
        n = n1 * t

    if solve_for == "future_value":
        P = _number(data, "principal", positive=True)
        i = _number(data, "interest_rate", allow_zero=True) / 100.0
        n = _number(data, "n", positive=True)
        F = P * (1 + i) ** n
    elif solve_for == "principal":
        F = _number(data, "future_value", positive=True)
        i = _number(data, "interest_rate", allow_zero=True) / 100.0
        n = _number(data, "n", positive=True)
        P = F / (1 + i) ** n
    elif solve_for == "interest_rate":
        P = _number(data, "principal", positive=True)
        F = _number(data, "future_value", positive=True)
        n = _number(data, "n", positive=True)
        if F <= P:
            raise CompoundInterestError("future_value must be greater than principal")
        i = ((F / P) ** (1 / n) - 1) * 100.0
    else:  # periods
        P = _number(data, "principal", positive=True)
        F = _number(data, "future_value", positive=True)
        i = _number(data, "interest_rate", positive=True) / 100.0
        if F <= P:
            raise CompoundInterestError("future_value must be greater than principal")
        n = __import__("math").log(F / P) / __import__("math").log(1 + i)

    result = {
        "formula": "F = P(1 + i)^n",
        "solve_for": solve_for,
        "principal": P,
        "future_value": F,
        "interest_rate": i * 100.0 if solve_for != "interest_rate" else i,
        "n": n,
        "interest": F - P,
    }
    if solve_for == "future_value":
        result["steps"] = [
            f"1. Use F = P(1 + i)^n with P = {_fmt(P)}, i = {_fmt(i * 100)}%, and n = {_fmt(n)}.",
            f"2. Compute (1 + i)^n = (1 + {_fmt(i)})^{_fmt(n)}.",
            f"3. Future worth F = {_fmt(F)}.",
            f"4. Interest earned I = F - P = {_fmt(F - P)}.",
        ]
    elif solve_for == "principal":
        result["steps"] = [
            f"1. Start from F = P(1 + i)^n and solve for P = F / (1 + i)^n.",
            f"2. Substitute P = {_fmt(F)} / (1 + {_fmt(i)})^{_fmt(n)}.",
            f"3. Present worth P = {_fmt(P)}.",
        ]
    elif solve_for == "interest_rate":
        result["steps"] = [
            f"1. Rearrange F = P(1 + i)^n to solve for i: i = (F/P)^(1/n) - 1.",
            f"2. Compute i = ({_fmt(F)} / {_fmt(P)})^(1/{_fmt(n)}) - 1.",
            f"3. Interest rate per period i = {_fmt(i * 100)}%.",
        ]
    else:
        result["steps"] = [
            "1. Begin with F = P(1 + i)^n.",
            f"2. Solve for n: n = ln(F/P) / ln(1 + i) = ln({_fmt(F)}/{_fmt(P)}) / ln(1 + {_fmt(i)}).",
            f"3. Number of periods n = {_fmt(n)}.",
        ]
    return result


def parse_compound_interest_problem(text):
    """Parse a compact natural-language compound-interest problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bcompound interest\b|\bcompounded\b", normalized, re.I):
        raise CompoundInterestError("Please include a compound-interest question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    principal_match = re.search(
        rf"(?:principal|invest|deposit(?:ed)?|borrow(?:ed)?)\s*(?:of|is|=)?\s*\$?{num}",
        normalized, re.I,
    )
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    periods_match = re.search(rf"{num}\s*(?:period|periods|quarter|quarters|month|months|year|years)\b", normalized, re.I)
    n1_match = re.search(r"(?:compounded|compounding)\s+(quarter|quarterly|month|monthly|semi-?annual|annually|annual|daily)", normalized, re.I)
    t_match = re.search(rf"(?:for|in|after)\s+{num}\s*(year|years|yr|yrs|month|months)\b", normalized, re.I)
    future_match = re.search(rf"(?:becomes|grows to|future value|amount|accumulate[sd]? to)\s*(?:of|is|=)?\s*\$?{num}", normalized, re.I)

    if not principal_match or not rate_match:
        raise CompoundInterestError("I need at least the principal and the interest rate")

    per_year = {"quarter": 4, "quarterly": 4, "month": 12, "monthly": 12,
                "semi-annual": 2, "annually": 1, "annual": 1, "daily": 365}
    n1 = per_year.get(n1_match.group(1).lower(), 1) if n1_match else 1

    t = 1.0
    if t_match:
        t = float(t_match.group(1))
        if t_match.group(2).lower().startswith("month"):
            t /= 12.0

    if periods_match and re.search(r"period", periods_match.group(0), re.I):
        n = float(periods_match.group(1))
    else:
        n = n1 * t

    return {
        "solve_for": "interest_rate" if re.search(r"(?:find|solve for|what is)\s+(?:the\s+)?(?:interest rate|rate)", normalized, re.I)
                     else "future_value",
        "principal": float(principal_match.group(1)),
        "interest_rate": float(rate_match.group(1)),
        "future_value": float(future_match.group(1)) if future_match else None,
        "n": n,
        "n1": n1,
        "t": t,
    }


def solve_compound_interest_problem(text):
    """Return a calculation and numbered explanation for a word problem."""
    data = parse_compound_interest_problem(text)
    result = calculate_compound_interest(data)

    if result["solve_for"] == "interest_rate":
        steps = [
            f"1. Use F = P(1 + i)^n with n = {_fmt(result['n'])} period(s).",
            f"2. Solve for i: i = (F/P)^(1/n) - 1 = ({_fmt(result['future_value'])} / {_fmt(result['principal'])})^(1/{_fmt(result['n'])}) - 1.",
            f"3. Rate per period: {_fmt(result['interest_rate'])}%.",
        ]
    elif result["solve_for"] == "periods":
        steps = [
            "1. Use F = P(1 + i)^n.",
            f"2. Solve for n: n = ln(F/P) / ln(1 + i) = ln({_fmt(result['future_value'])}/{_fmt(result['principal'])}) / ln(1 + {_fmt(result['interest_rate']/100)}).",
            f"3. Number of periods: {_fmt(result['n'])}.",
        ]
    else:
        steps = [
            f"1. Identify P = {_fmt(result['principal'])}, i = {_fmt(result['interest_rate'])}%, n = {_fmt(result['n'])}.",
            f"2. Use F = P(1 + i)^n = {_fmt(result['principal'])} x (1 + {_fmt(result['interest_rate']/100)})^{_fmt(result['n'])}.",
            f"3. Future worth F = {_fmt(result['future_value'])}.",
            f"4. Interest earned I = F - P = {_fmt(result['interest'])}.",
        ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
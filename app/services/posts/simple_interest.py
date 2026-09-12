"""Simple-interest calculations for the interactive feed and assistant."""

from datetime import date
import re


class SimpleInterestError(ValueError):
    """Raised when a simple-interest request cannot be calculated."""


def _date(value, field):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise SimpleInterestError(f"{field} must be a valid date") from error


def _number(data, field, *, positive=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise SimpleInterestError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise SimpleInterestError(f"{field} must be finite")
    if positive and number <= 0:
        raise SimpleInterestError(f"{field} must be greater than zero")
    return number


def ordinary_days(start, end):
    """Return elapsed days using the plain 30/360 convention."""
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (end.day - start.day)


def exact_days(start, end):
    """Return elapsed calendar days, excluding the start date."""
    return (end - start).days


def calculate_simple_interest(data):
    """Calculate one unknown from date-based simple-interest inputs.

    Rates are annual percentages in the input and output. Exact day count uses
    actual elapsed days with a 365-day denominator, including leap-year dates.
    """
    basis = str(data.get("basis", "ordinary")).strip().lower()
    if basis not in {"ordinary", "exact"}:
        raise SimpleInterestError("basis must be ordinary or exact")
    solve_for = str(data.get("solve_for", "future_value")).strip().lower()
    if solve_for not in {"future_value", "principal", "interest_rate"}:
        raise SimpleInterestError("solve_for must be future_value, principal, or interest_rate")

    start_value = data.get("start_date")
    end_value = data.get("end_date")
    if start_value is None and end_value is None and data.get("time_years") is not None:
        try:
            time_years = float(data["time_years"])
        except (TypeError, ValueError) as error:
            raise SimpleInterestError("time_years must be a number") from error
        if time_years <= 0:
            raise SimpleInterestError("time_years must be greater than zero")
        days = time_years * (360 if basis == "ordinary" else 365)
        start = end = None
    else:
        start = _date(start_value, "start_date")
        end = _date(end_value, "end_date")
        if end <= start:
            raise SimpleInterestError("end_date must be after start_date")
        days = ordinary_days(start, end) if basis == "ordinary" else exact_days(start, end)
        if days <= 0:
            raise SimpleInterestError("the selected dates must produce at least one day")
    time_fraction = days / (360 if basis == "ordinary" else 365)

    if solve_for == "future_value":
        principal = _number(data, "principal", positive=True)
        rate = _number(data, "interest_rate")
        future_value = principal * (1 + (rate / 100) * time_fraction)
    elif solve_for == "principal":
        future_value = _number(data, "future_value", positive=True)
        rate = _number(data, "interest_rate")
        factor = 1 + (rate / 100) * time_fraction
        if factor == 0:
            raise SimpleInterestError("the interest rate produces an invalid principal")
        principal = future_value / factor
    else:
        principal = _number(data, "principal", positive=True)
        future_value = _number(data, "future_value", positive=True)
        if future_value <= principal:
            raise SimpleInterestError("future_value must be greater than principal")
        rate = ((future_value / principal) - 1) / time_fraction * 100

    return {
        "basis": basis,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "days": days,
        "time_fraction": time_fraction,
        "principal": principal,
        "future_value": future_value,
        "interest_rate": rate,
        "interest": future_value - principal,
        "solve_for": solve_for,
    }


def parse_simple_interest_problem(text):
    """Parse a compact natural-language simple-interest problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bsimple interest\b|\binterest\b", normalized, re.I):
        raise SimpleInterestError("Please include a simple-interest question")

    numbers = r"([0-9]+(?:\.[0-9]+)?)"
    principal_match = re.search(rf"(?:principal|invest|deposit(?:ed)?|borrow(?:ed)?)\s*(?:of|is|=)?\s*\$?{numbers}", normalized, re.I)
    rate_match = re.search(rf"{numbers}\s*%", normalized, re.I)
    duration_match = re.search(rf"{numbers}\s*(year|years|yr|yrs|month|months|day|days)\b", normalized, re.I)
    future_value_match = re.search(rf"(?:becomes|grows to|future value|amount)\s*(?:of|is|=)?\s*\$?{numbers}", normalized, re.I)
    if not principal_match:
        principal_match = re.search(rf"\$?{numbers}\s*(?:at|@)", normalized, re.I)
    if not principal_match:
        principal_match = re.search(rf"\$?{numbers}\s+becomes\b", normalized, re.I)
    rate_requested = bool(re.search(r"(?:find|solve for|what is)\s+(?:the\s+)?(?:annual\s+)?(?:rate|interest rate)", normalized, re.I))
    if not principal_match or not duration_match or (not rate_match and not rate_requested) or (rate_requested and not future_value_match):
        raise SimpleInterestError("I need the principal, annual rate, and time period")

    principal = float(principal_match.group(1))
    rate = float(rate_match.group(1)) if rate_match else 0
    future_value = float(future_value_match.group(1)) if future_value_match else None
    duration = float(duration_match.group(1))
    unit = duration_match.group(2).lower()
    time_years = duration / (12 if unit.startswith("month") else 365 if unit.startswith("day") else 1)
    solve_for = "interest_rate" if rate_requested else "future_value"
    if re.search(r"(?:find|solve for|what is)\s+(?:the\s+)?interest\b", normalized, re.I):
        solve_for = "future_value"
    return {
        "basis": "ordinary",
        "solve_for": solve_for,
        "principal": principal,
        "interest_rate": rate,
        "future_value": future_value,
        "time_years": time_years,
    }


def solve_simple_interest_problem(text):
    """Return a calculation and numbered explanation for a word problem."""
    data = parse_simple_interest_problem(text)
    result = calculate_simple_interest(data)
    if result["solve_for"] == "interest_rate":
        steps = [
            "1. Convert the time to years: " + _format_number(result["time_fraction"]) + " year(s).",
            "2. Use r = ((A / P) - 1) / t = ((" + _format_number(result["future_value"]) + " / " + _format_number(result["principal"]) + ") - 1) / " + _format_number(result["time_fraction"]) + ".",
            "3. Annual interest rate: " + _format_number(result["interest_rate"]) + "%.",
        ]
        result["steps"] = steps
        return result
    steps = [
        "1. Convert the time to years: " + _format_number(result["time_fraction"]) + " year(s).",
        "2. Use I = P x r x t = " + _format_number(result["principal"]) + " x " + _format_number(result["interest_rate"] / 100) + " x " + _format_number(result["time_fraction"]) + ".",
        "3. Interest earned: " + _format_number(result["interest"]) + ".",
        "4. Future value A = P + I = " + _format_number(result["future_value"]) + ".",
    ]
    result["steps"] = steps
    return result


def _format_number(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")
"""Continuous-compounding calculations: F = P e^(j t)."""

import re
import math


class ContinuousCompoundingError(ValueError):
    """Raised when a continuous-compounding request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ContinuousCompoundingError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise ContinuousCompoundingError(f"{field} must be finite")
    if positive and number <= 0:
        raise ContinuousCompoundingError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise ContinuousCompoundingError(f"{field} cannot be negative")
    return number


def calculate_continuous_compounding(data):
    """Solve F = P e^(j t).

    solve_for: future_value | principal | nominal_rate | time
    """
    solve_for = str(data.get("solve_for", "future_value")).strip().lower()
    if solve_for not in {"future_value", "principal", "nominal_rate", "time"}:
        raise ContinuousCompoundingError(
            "solve_for must be future_value, principal, nominal_rate, or time"
        )

    if solve_for == "future_value":
        P = _number(data, "principal", positive=True)
        j = _number(data, "nominal_rate") / 100.0
        t = _number(data, "t", positive=True)
        F = P * math.exp(j * t)
        I = F - P
    elif solve_for == "principal":
        F = _number(data, "future_value", positive=True)
        j = _number(data, "nominal_rate") / 100.0
        t = _number(data, "t", positive=True)
        P = F / math.exp(j * t)
        I = F - P
    elif solve_for == "nominal_rate":
        P = _number(data, "principal", positive=True)
        F = _number(data, "future_value", positive=True)
        t = _number(data, "t", positive=True)
        if F <= P:
            raise ContinuousCompoundingError("future_value must be greater than principal")
        j = math.log(F / P) / t
        I = F - P
    else:  # time
        P = _number(data, "principal", positive=True)
        F = _number(data, "future_value", positive=True)
        j = _number(data, "nominal_rate", positive=True) / 100.0
        if F <= P:
            raise ContinuousCompoundingError("future_value must be greater than principal")
        t = math.log(F / P) / j
        I = F - P

    result = {
        "formula": "F = P e^(j t)",
        "solve_for": solve_for,
        "principal": P,
        "future_value": F,
        "nominal_rate": j * 100.0,
        "t": t,
        "interest": I,
    }
    if solve_for == "future_value":
        result["steps"] = [
            f"1. Identify P = {_fmt(P)}, j = {_fmt(j * 100)}%, t = {_fmt(t)} year(s).",
            f"2. Use F = P e^(j t) = {_fmt(P)} x e^({_fmt(j)} x {_fmt(t)}).",
            f"3. Future worth F = {_fmt(F)}.",
            f"4. Interest earned I = F - P = {_fmt(I)}.",
        ]
    elif solve_for == "principal":
        result["steps"] = [
            "1. Rearrange F = P e^(j t) to solve for P = F / e^(j t).",
            f"2. P = {_fmt(F)} / e^({_fmt(j)} x {_fmt(t)}).",
            f"3. Principal P = {_fmt(P)}.",
        ]
    elif solve_for == "nominal_rate":
        result["steps"] = [
            "1. Rearrange F = P e^(j t) to solve for j = ln(F/P) / t.",
            f"2. j = ln({_fmt(F)}/{_fmt(P)}) / {_fmt(t)}.",
            f"3. Nominal rate j = {_fmt(j * 100)}%.",
        ]
    else:
        result["steps"] = [
            "1. Rearrange F = P e^(j t) to solve for t = ln(F/P) / j.",
            f"2. t = ln({_fmt(F)}/{_fmt(P)}) / {_fmt(j)}.",
            f"3. Time t = {_fmt(t)} year(s).",
        ]
    return result


def parse_continuous_compounding_problem(text):
    """Parse a compact natural-language continuous-compounding problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bcontinu(?:ous|ously)\b|\bcompounded continuously\b", normalized, re.I):
        raise ContinuousCompoundingError("Please include a continuous-compounding question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    principal_match = re.search(
        rf"(?:principal|invest|deposit(?:ed)?|present value|present worth)\s*(?:of|is|=)?\s*\$?{num}",
        normalized, re.I,
    )
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    time_match = re.search(rf"(?:for|in|after)\s+{num}\s*(year|years|yr|yrs|month|months)\b", normalized, re.I)
    future_match = re.search(rf"(?:becomes|grows to|future value|amount|accumulate[sd]? to)\s*(?:of|is|=)?\s*\$?{num}", normalized, re.I)

    if not principal_match or not rate_match or not time_match:
        raise ContinuousCompoundingError("I need the principal, rate, and time")

    t = float(time_match.group(1))
    if time_match.group(2).lower().startswith("month"):
        t /= 12.0

    return {
        "solve_for": "future_value",
        "principal": float(principal_match.group(1)),
        "nominal_rate": float(rate_match.group(1)),
        "t": t,
        "future_value": float(future_match.group(1)) if future_match else None,
    }


def solve_continuous_compounding_problem(text):
    data = parse_continuous_compounding_problem(text)
    result = calculate_continuous_compounding(data)
    steps = [
        f"1. Identify P = {_fmt(result['principal'])}, j = {_fmt(result['nominal_rate'])}%, t = {_fmt(result['t'])} year(s).",
        f"2. Use F = P e^(j t) = {_fmt(result['principal'])} x e^({_fmt(result['nominal_rate']/100)} x {_fmt(result['t'])}).",
        f"3. Future worth F = {_fmt(result['future_value'])}.",
        f"4. Interest earned I = F - P = {_fmt(result['interest'])}.",
    ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
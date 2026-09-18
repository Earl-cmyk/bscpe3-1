"""Effective annual interest rate: i_e = (1 + j/n1)^n1 - 1."""

import re


class EffectiveRateError(ValueError):
    """Raised when an effective-rate request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise EffectiveRateError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise EffectiveRateError(f"{field} must be finite")
    if positive and number <= 0:
        raise EffectiveRateError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise EffectiveRateError(f"{field} cannot be negative")
    return number


def calculate_effective_rate(data):
    """Solve i_e = (1 + j/n1)^n1 - 1.

    solve_for: effective_rate | nominal_rate | periods_per_year
    """
    solve_for = str(data.get("solve_for", "effective_rate")).strip().lower()
    if solve_for not in {"effective_rate", "nominal_rate", "periods_per_year"}:
        raise EffectiveRateError(
            "solve_for must be effective_rate, nominal_rate, or periods_per_year"
        )

    if solve_for == "effective_rate":
        j = _number(data, "nominal_rate") / 100.0
        n1 = _number(data, "n1", positive=True)
        i_e = (1 + j / n1) ** n1 - 1
    elif solve_for == "nominal_rate":
        i_e = _number(data, "effective_rate") / 100.0
        n1 = _number(data, "n1", positive=True)
        j = n1 * ((1 + i_e) ** (1 / n1) - 1)
    else:
        j = _number(data, "nominal_rate", positive=True) / 100.0
        i_e = _number(data, "effective_rate", positive=True) / 100.0
        # Solve n1 numerically: (1 + j/n1)^n1 = 1 + i_e
        n1 = 1.0
        for _ in range(200):
            f = (1 + j / n1) ** n1 - (1 + i_e)
            df = (1 + j / n1) ** n1 * (
                __import__("math").log(1 + j / n1) - j / (n1 + j)
            )
            if abs(df) < 1e-15:
                break
            step = f / df
            n1 -= step
            if n1 <= 0:
                n1 = 0.5
            if abs(step) < 1e-12:
                break

    result = {
        "formula": "i_e = (1 + j/n1)^n1 - 1",
        "solve_for": solve_for,
        "nominal_rate": j * 100.0,
        "effective_rate": i_e * 100.0,
        "periods_per_year": n1,
    }
    if solve_for == "effective_rate":
        result["steps"] = [
            f"1. Identify j = {_fmt(j * 100)}% and n1 = {_fmt(n1)}.",
            f"2. Compute j / n1 = {_fmt(j * 100 / n1)}%.",
            f"3. Use i_e = (1 + j/n1)^n1 - 1 = (1 + {_fmt(j / n1)})^{_fmt(n1)} - 1.",
            f"4. Effective annual rate i_e = {_fmt(i_e * 100)}%.",
        ]
    elif solve_for == "nominal_rate":
        result["steps"] = [
            "1. Rearrange i_e = (1 + j/n1)^n1 - 1 to get j = n1((1 + i_e)^(1/n1) - 1).",
            f"2. j = {_fmt(n1)} x ((1 + {_fmt(i_e)})^(1/{_fmt(n1)}) - 1).",
            f"3. Nominal rate j = {_fmt(j * 100)}%.",
        ]
    else:
        result["steps"] = [
            "1. Solve (1 + j/n1)^n1 - 1 = i_e numerically for n1.",
            f"2. With j = {_fmt(j * 100)}% and i_e = {_fmt(i_e * 100)}%.",
            f"3. Compounding periods per year n1 = {_fmt(n1)}.",
        ]
    return result


def parse_effective_rate_problem(text):
    """Parse a compact natural-language effective-rate problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\beffective\b", normalized, re.I):
        raise EffectiveRateError("Please include an effective-rate question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    nominal_match = re.search(rf"(?:nominal|apr)\s*(?:rate|of|is|=)?\s*{num}\s*%", normalized, re.I)
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    n1_match = re.search(r"(?:compounded|compounding)\s+(quarter|quarterly|month|monthly|semi-?annual|annually|annual|daily)", normalized, re.I)

    per_year = {"quarter": 4, "quarterly": 4, "month": 12, "monthly": 12,
                "semi-annual": 2, "annually": 1, "annual": 1, "daily": 365}
    n1 = per_year.get(n1_match.group(1).lower(), 1) if n1_match else 1

    if not (nominal_match or rate_match):
        raise EffectiveRateError("I need the nominal rate")
    return {
        "solve_for": "effective_rate",
        "nominal_rate": float(nominal_match.group(1) if nominal_match else rate_match.group(1)),
        "n1": n1,
    }


def solve_effective_rate_problem(text):
    data = parse_effective_rate_problem(text)
    result = calculate_effective_rate(data)
    steps = [
        f"1. Identify nominal rate j = {_fmt(result['nominal_rate'])}% and n1 = {_fmt(result['periods_per_year'])}.",
        f"2. Compute j/n1 = {_fmt(result['nominal_rate'])}% / {_fmt(result['periods_per_year'])} = {_fmt(result['nominal_rate']/result['periods_per_year'])}%.",
        f"3. Use i_e = (1 + j/n1)^n1 - 1 = (1 + {_fmt(result['nominal_rate']/100/result['periods_per_year'])})^{_fmt(result['periods_per_year'])} - 1.",
        f"4. Effective annual rate i_e = {_fmt(result['effective_rate'])}%.",
    ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
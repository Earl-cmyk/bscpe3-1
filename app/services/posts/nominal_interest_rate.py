"""Nominal-interest-rate calculations: j = n1 * i."""

import re
import math


class NominalRateError(ValueError):
    """Raised when a nominal-rate request cannot be calculated."""


def _number(data, field, *, positive=False, allow_zero=False):
    value = data.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise NominalRateError(f"{field} must be a number") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise NominalRateError(f"{field} must be finite")
    if positive and number <= 0:
        raise NominalRateError(f"{field} must be greater than zero")
    if not allow_zero and not positive and number < 0:
        raise NominalRateError(f"{field} cannot be negative")
    return number


def calculate_nominal_rate(data):
    """Solve j = n1 * i.

    solve_for: nominal_rate | period_rate | periods_per_year
    Also supports deriving j from the effective annual rate:
        j = n1 * ((1 + i_e)^(1/n1) - 1)
    """
    solve_for = str(data.get("solve_for", "nominal_rate")).strip().lower()
    if solve_for not in {"nominal_rate", "period_rate", "periods_per_year"}:
        raise NominalRateError(
            "solve_for must be nominal_rate, period_rate, or periods_per_year"
        )

    if solve_for == "nominal_rate":
        if data.get("effective_rate") is not None:
            i_e = _number(data, "effective_rate") / 100.0
            n1 = _number(data, "n1", positive=True)
            i = (1 + i_e) ** (1 / n1) - 1
            j = n1 * i
            return {
                "formula": "j = n1[(1 + i_e)^(1/n1) - 1]",
                "solve_for": solve_for,
                "nominal_rate": j * 100.0,
                "period_rate": i * 100.0,
                "periods_per_year": n1,
                "effective_rate": i_e * 100.0,
            }
        i = _number(data, "period_rate") / 100.0
        n1 = _number(data, "n1", positive=True)
        j = n1 * i
    elif solve_for == "period_rate":
        j = _number(data, "nominal_rate") / 100.0
        n1 = _number(data, "n1", positive=True)
        i = j / n1
    else:
        j = _number(data, "nominal_rate") / 100.0
        i = _number(data, "period_rate", positive=True) / 100.0
        n1 = j / i

    result = {
        "formula": "j = n1 x i",
        "solve_for": solve_for,
        "nominal_rate": j * 100.0,
        "period_rate": i * 100.0,
        "periods_per_year": n1,
    }
    if solve_for == "nominal_rate":
        result["steps"] = [
            f"1. Identify period rate i = {_fmt(i * 100)}% and n1 = {_fmt(n1)}.",
            f"2. Use j = n1 x i = {_fmt(n1)} x {_fmt(i * 100)}%.",
            f"3. Nominal annual rate j = {_fmt(j * 100)}%.",
        ]
    elif solve_for == "period_rate":
        result["steps"] = [
            "1. Rearrange j = n1 x i to solve for i = j / n1.",
            f"2. i = {_fmt(j * 100)}% / {_fmt(n1)}.",
            f"3. Period rate i = {_fmt(i * 100)}%.",
        ]
    else:
        result["steps"] = [
            "1. Rearrange j = n1 x i to solve for n1 = j / i.",
            f"2. n1 = {_fmt(j * 100)}% / {_fmt(i * 100)}%.",
            f"3. Compounding periods per year n1 = {_fmt(n1)}.",
        ]
    return result


def parse_nominal_rate_problem(text):
    """Parse a compact natural-language nominal-rate problem."""
    normalized = " ".join(str(text or "").replace(",", "").split())
    if not re.search(r"\bnominal\b|\bapr\b|\bannual percentage rate\b", normalized, re.I):
        raise NominalRateError("Please include a nominal-rate question")

    num = r"([0-9]+(?:\.[0-9]+)?)"
    rate_match = re.search(rf"{num}\s*%", normalized, re.I)
    n1_match = re.search(r"(?:compounded|compounding)\s+(quarter|quarterly|month|monthly|semi-?annual|annually|annual|daily)", normalized, re.I)
    effective_match = re.search(rf"(?:effective|effective rate|effective annual)\s*(?:of|is|=)?\s*{num}\s*%", normalized, re.I)

    if not rate_match:
        raise NominalRateError("I need the interest rate")

    per_year = {"quarter": 4, "quarterly": 4, "month": 12, "monthly": 12,
                "semi-annual": 2, "annually": 1, "annual": 1, "daily": 365}
    n1 = per_year.get(n1_match.group(1).lower(), 1) if n1_match else 1

    if effective_match:
        return {
            "solve_for": "nominal_rate",
            "effective_rate": float(effective_match.group(1)),
            "n1": n1,
        }
    return {
        "solve_for": "nominal_rate",
        "period_rate": float(rate_match.group(1)),
        "n1": n1,
    }


def solve_nominal_rate_problem(text):
    data = parse_nominal_rate_problem(text)
    result = calculate_nominal_rate(data)

    if "effective_rate" in data:
        steps = [
            f"1. Convert the effective annual rate to a period rate: i = (1 + i_e)^(1/n1) - 1 = (1 + {_fmt(result['effective_rate']/100)})^(1/{_fmt(result['periods_per_year'])}) - 1.",
            f"2. Period rate i = {_fmt(result['period_rate'])}%.",
            f"3. Nominal rate j = n1 x i = {_fmt(result['periods_per_year'])} x {_fmt(result['period_rate'])}%.",
            f"4. Nominal annual rate j = {_fmt(result['nominal_rate'])}%.",
        ]
    else:
        steps = [
            f"1. Identify period rate i = {_fmt(result['period_rate'])}% and n1 = {_fmt(result['periods_per_year'])}.",
            f"2. Use j = n1 x i = {_fmt(result['periods_per_year'])} x {_fmt(result['period_rate'])}%.",
            f"3. Nominal annual rate j = {_fmt(result['nominal_rate'])}%.",
        ]
    result["steps"] = steps
    return result


def _fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")
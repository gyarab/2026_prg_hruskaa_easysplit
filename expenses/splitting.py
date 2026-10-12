"""Čistá logika dělení výdajů (bez závislosti na Djangu)."""
import math
from decimal import Decimal
from fractions import Fraction

CENT = Decimal("0.01")

EQUAL, EXACT, PERCENT, WEIGHT = "equal", "exact", "percent", "weight"


class SplitError(ValueError):
    """Chyba v zadání dělení (zobrazí se uživateli)."""


def allocate(total, weights):
    """Rozdělí `total` v poměru `weights` ({klíč: Decimal}) na celé haléře.
    Součet výsledku se vždy přesně rovná `total` (metoda největšího zbytku)."""
    total_cents = int(Decimal(total).quantize(CENT) * 100)
    exact = {k: Fraction(v) for k, v in weights.items()}
    weight_sum = sum(exact.values())
    if weight_sum <= 0:
        raise SplitError("Součet vah musí být větší než nula.")

    raw = {k: Fraction(total_cents) * w / weight_sum for k, w in exact.items()}
    cents = {k: math.floor(r) for k, r in raw.items()}
    leftover = total_cents - sum(cents.values())

    # největší zbytek dostane haléř navíc (při shodě rozhoduje pořadí)
    by_remainder = sorted(raw, key=lambda k: raw[k] - cents[k], reverse=True)
    for key in by_remainder[:leftover]:
        cents[key] += 1

    return {k: Decimal(c) * CENT for k, c in cents.items()}


def compute_shares(mode, total, values):
    """Vrátí {klíč: Decimal podíl}.
    `values` = {klíč účastníka: zadaná hodnota nebo None}."""
    if not values:
        raise SplitError("Vyberte alespoň jednoho účastníka.")
    total = Decimal(total).quantize(CENT)
    if total <= 0:
        raise SplitError("Částka musí být kladná.")

    if mode == EQUAL:
        return allocate(total, {k: Decimal(1) for k in values})

    if mode == WEIGHT:
        return allocate(total, values)

    if mode == PERCENT:
        percent_sum = sum(values.values())
        if percent_sum != Decimal(100):
            raise SplitError(f"Procenta se musí sečíst na 100 % (nyní {percent_sum} %).")
        return allocate(total, values)

    if mode == EXACT:
        parts = {k: v.quantize(CENT) for k, v in values.items()}
        diff = total - sum(parts.values())
        if diff != 0:
            raise SplitError(
                f"Součet částek se musí rovnat {total}. Chybí/přebývá: {diff}."
            )
        return parts

    raise SplitError("Neznámý způsob dělení.")
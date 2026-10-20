"""Template filter untuk tampilan Order System."""

from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def rupiah(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return "Rp0"
    return f"Rp{number:,.0f}".replace(",", ".")


@register.filter
def order_status_class(value):
    return {
        "pending": "waiting",
        "paid": "ready",
        "completed": "done",
        "expired": "done",
    }.get(value, "done")


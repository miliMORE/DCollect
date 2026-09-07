"""Assign the next list position so users never type sort order."""


def next_sort_order(queryset):
    last = queryset.order_by("-sort_order").values_list("sort_order", flat=True).first()
    try:
        return int(last or 0) + 10
    except (TypeError, ValueError):
        return 10

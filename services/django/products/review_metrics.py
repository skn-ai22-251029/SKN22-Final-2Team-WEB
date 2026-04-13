from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import Avg, Count

from .models import Review


def with_actual_review_metrics(queryset):
    return queryset.annotate(
        _actual_review_count=Count("reviews", distinct=True),
        _actual_review_score_avg=Avg("reviews__score"),
    )


def attach_actual_review_metrics(products):
    product_map = {}

    for product in products:
        if product is None:
            continue
        goods_id = getattr(product, "goods_id", None)
        if not goods_id:
            continue
        product._actual_review_count = int(getattr(product, "_actual_review_count", 0) or 0)
        if not hasattr(product, "_actual_review_score_avg"):
            product._actual_review_score_avg = None
        product_map[goods_id] = product

    if not product_map:
        return products

    aggregates = (
        Review.objects.filter(product_id__in=product_map.keys())
        .values("product_id")
        .annotate(
            _actual_review_count=Count("review_id"),
            _actual_review_score_avg=Avg("score"),
        )
    )

    for row in aggregates:
        product = product_map.get(row["product_id"])
        if product is None:
            continue
        product._actual_review_count = int(row["_actual_review_count"] or 0)
        product._actual_review_score_avg = row["_actual_review_score_avg"]

    return products


def normalize_review_count(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def normalize_rating_value(value):
    if value is None:
        return None

    try:
        numeric = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None

    if not numeric.is_finite():
        return None

    clamped = min(max(numeric, Decimal("0.0")), Decimal("5.0"))
    return float(clamped.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def normalize_rating_label(value):
    rating_value = normalize_rating_value(value)
    if rating_value is None or rating_value <= 0:
        return None
    return f"{rating_value:.1f}"


def get_actual_review_count(product):
    if product is None:
        return 0

    if not hasattr(product, "_actual_review_count"):
        attach_actual_review_metrics([product])

    return normalize_review_count(getattr(product, "_actual_review_count", 0))


def get_actual_rating_value(product):
    if product is None:
        return None

    if not hasattr(product, "_actual_review_score_avg"):
        attach_actual_review_metrics([product])

    avg_score = getattr(product, "_actual_review_score_avg", None)
    if avg_score is None:
        return None

    return normalize_rating_value(avg_score)


def get_actual_rating_label(product):
    return normalize_rating_label(get_actual_rating_value(product))

from datetime import timedelta

from django.utils import timezone

from ..services.chat_session_service import normalize_profile_context_type


def serialize_session(session):
    updated_at = timezone.localtime(session.updated_at)
    return {
        "session_id": str(session.session_id),
        "title": session.title,
        "target_pet_id": str(session.target_pet_id) if session.target_pet_id else None,
        "profile_context_type": normalize_profile_context_type(session.profile_context_type),
        "display_date": updated_at.strftime("%y/%m/%d"),
        "created_at": timezone.localtime(session.created_at).isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def serialize_message(message):
    recommended_products = []
    if hasattr(message, "recommended_products"):
        recommended_products = [
            {
                "goods_id": recommendation.product.goods_id,
                "product_name": recommendation.product.goods_name,
                "brand_name": recommendation.product.brand_name,
                "price": recommendation.product.price,
                "discount_price": recommendation.product.discount_price,
                "rating": float(recommendation.product.rating) if recommendation.product.rating is not None else None,
                "reviews": recommendation.product.review_count,
                "thumbnail_url": recommendation.product.thumbnail_url,
                "product_url": recommendation.product.product_url,
                "rank_order": recommendation.rank_order,
            }
            for recommendation in message.recommended_products.all()
        ]

    return {
        "message_id": str(message.message_id),
        "role": message.role,
        "content": message.content,
        "created_at": timezone.localtime(message.created_at).isoformat(),
        "recommended_products": recommended_products,
    }


def serialize_session_groups(sessions):
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    groups = []
    grouped = {}

    for session in sessions:
        session_date = timezone.localtime(session.updated_at).date()
        if session_date == today:
            key, label = "today", "오늘"
        elif session_date == yesterday:
            key, label = "yesterday", "어제"
        else:
            key = session_date.isoformat()
            label = timezone.localtime(session.updated_at).strftime("%y/%m/%d")

        if key not in grouped:
            grouped[key] = {"key": key, "label": label, "sessions": []}
            groups.append(grouped[key])
        grouped[key]["sessions"].append(serialize_session(session))

    return groups

from products.models import Product

from ..models import ChatMessageRecommendation


def persist_recommended_products(message, product_cards):
    if not product_cards:
        return

    goods_ids = [card.get("goods_id") for card in product_cards if card.get("goods_id")]
    if not goods_ids:
        return

    product_map = Product.objects.in_bulk(goods_ids, field_name="goods_id")
    recommendations = []
    for index, card in enumerate(product_cards):
        product = product_map.get(card.get("goods_id"))
        if product is None:
            continue
        recommendations.append(
            ChatMessageRecommendation(
                message=message,
                product=product,
                rank_order=index,
            )
        )

    if recommendations:
        ChatMessageRecommendation.objects.bulk_create(recommendations, ignore_conflicts=True)

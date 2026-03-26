from django.db import transaction
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.models import Product

from .models import Cart, CartItem, Order, OrderItem, UserInteraction, Wishlist, WishlistItem


AVAILABLE_MILEAGE = 3200
FREE_SHIPPING_THRESHOLD = 30000
BASE_SHIPPING_FEE = 3000
PAYMENT_METHODS = {
    "우리카드 1234 / 일시불",
    "카카오페이 / 일시불",
    "네이버페이 / 일시불",
}
COUPON_RULES = {
    "none": {"label": "적용된 쿠폰 없음", "discount": 0, "min_total": 0},
    "new-member": {"label": "신규회원 3,000원 할인", "discount": 3000, "min_total": 30000},
    "pet-care": {"label": "펫케어 5,000원 할인", "discount": 5000, "min_total": 60000},
}


def _display_product_name(brand_name, goods_name):
    if not goods_name:
        return ""

    normalized_brand = (brand_name or "").strip()
    normalized_name = goods_name.strip()

    if normalized_brand and normalized_name.lower().startswith(normalized_brand.lower()):
        trimmed = normalized_name[len(normalized_brand):].lstrip(" -_/|")
        if trimmed:
            return trimmed

    return normalized_name


def serialize_product_summary(product: Product) -> dict:
    price = product.price
    return {
        "product_id": product.goods_id,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "brand": product.brand_name,
        "price": price,
        "price_label": f"{price:,}원",
        "rating": float(product.rating) if product.rating is not None else None,
        "review_count": product.review_count,
        "thumbnail_url": product.thumbnail_url,
    }


def serialize_cart_item(item: CartItem) -> dict:
    product = item.product
    summary = serialize_product_summary(product)
    summary.update(
        {
            "cart_item_id": str(item.cart_item_id),
            "quantity": item.quantity,
            "line_total": summary["price"] * item.quantity,
            "line_total_label": f"{summary['price'] * item.quantity:,}원",
            "added_at": item.added_at.isoformat(),
        }
    )
    return summary


def serialize_wishlist_item(item: WishlistItem) -> dict:
    product = item.product
    summary = serialize_product_summary(product)
    summary.update(
        {
            "wishlist_item_id": str(item.wishlist_item_id),
            "added_at": item.added_at.isoformat(),
        }
    )
    return summary


def serialize_order_item(item: OrderItem) -> dict:
    product = item.product
    summary = serialize_product_summary(product)
    summary.update(
        {
            "quantity": item.quantity,
            "unit_price": item.price_at_order,
            "unit_price_label": f"{item.price_at_order:,}원",
            "line_total": item.price_at_order * item.quantity,
            "line_total_label": f"{item.price_at_order * item.quantity:,}원",
        }
    )
    return summary


def serialize_order(order: Order) -> dict:
    items = [serialize_order_item(item) for item in order.items.select_related("product").all()]
    return {
        "order_id": str(order.order_id),
        "status": order.status,
        "recipient_name": order.recipient_name,
        "recipient_phone": order.recipient_phone,
        "delivery_address": order.delivery_address,
        "delivery_message": order.delivery_message,
        "payment_method": order.payment_method,
        "applied_coupon_id": order.applied_coupon_id,
        "product_total": order.product_total,
        "product_total_label": f"{order.product_total:,}원",
        "coupon_discount": order.coupon_discount,
        "coupon_discount_label": f"{order.coupon_discount:,}원",
        "mileage_discount": order.mileage_discount,
        "mileage_discount_label": f"{order.mileage_discount:,}원",
        "shipping_fee": order.shipping_fee,
        "shipping_fee_label": f"{order.shipping_fee:,}원",
        "total_price": order.total_price,
        "total_price_label": f"{order.total_price:,}원",
        "item_count": len(items),
        "items": items,
        "created_at": order.created_at.isoformat(),
    }


def get_profile_value(user, field_name):
    try:
        profile = user.profile
    except Exception:
        return ""
    return getattr(profile, field_name, "") or ""


def normalize_delivery_address(data, user):
    delivery_address = (data.get("delivery_address") or "").strip()
    if delivery_address:
        return delivery_address

    address_main = (data.get("delivery_address_main") or "").strip()
    address_detail = (data.get("delivery_address_detail") or "").strip()
    if address_main:
        return " | ".join(part for part in [address_main, address_detail] if part)

    return get_profile_value(user, "address").strip()


def parse_positive_int(value, field_name):
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None, Response({"detail": f"{field_name} must be a number."}, status=status.HTTP_400_BAD_REQUEST)

    if parsed < 0:
        return None, Response({"detail": f"{field_name} must be at least 0."}, status=status.HTTP_400_BAD_REQUEST)

    return parsed, None


def get_coupon_or_400(coupon_id):
    normalized_coupon_id = (coupon_id or "none").strip() or "none"
    coupon = COUPON_RULES.get(normalized_coupon_id)
    if coupon is None:
        return None, None, Response({"detail": "invalid coupon_id."}, status=status.HTTP_400_BAD_REQUEST)
    return normalized_coupon_id, coupon, None


def validate_checkout_payload(request, cart_items):
    recipient_name = (request.data.get("recipient_name") or get_profile_value(request.user, "nickname")).strip()
    recipient_phone = (request.data.get("recipient_phone") or get_profile_value(request.user, "phone")).strip()
    delivery_address = normalize_delivery_address(request.data, request.user)
    delivery_message = (request.data.get("delivery_message") or "").strip()
    payment_method = (request.data.get("payment_method") or "").strip()

    if not recipient_name:
        return None, Response({"detail": "recipient_name is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not recipient_phone:
        return None, Response({"detail": "recipient_phone is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not delivery_address:
        return None, Response({"detail": "delivery_address is required."}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method not in PAYMENT_METHODS:
        return None, Response({"detail": "invalid payment_method."}, status=status.HTTP_400_BAD_REQUEST)

    product_total = sum(item.product.price * item.quantity for item in cart_items)
    shipping_fee = 0 if product_total >= FREE_SHIPPING_THRESHOLD else BASE_SHIPPING_FEE

    coupon_id, coupon, coupon_error = get_coupon_or_400(request.data.get("coupon_id"))
    if coupon_error:
        return None, coupon_error
    if product_total < coupon["min_total"]:
        return None, Response({"detail": "coupon is not available for current cart total."}, status=status.HTTP_400_BAD_REQUEST)

    mileage_amount, mileage_error = parse_positive_int(request.data.get("mileage_amount", 0), "mileage_amount")
    if mileage_error:
        return None, mileage_error
    if mileage_amount > AVAILABLE_MILEAGE:
        return None, Response({"detail": "mileage exceeds available balance."}, status=status.HTTP_400_BAD_REQUEST)

    coupon_discount = coupon["discount"]
    max_usable_mileage = max(product_total - coupon_discount, 0)
    if mileage_amount > max_usable_mileage:
        return None, Response({"detail": "mileage exceeds payable product total."}, status=status.HTTP_400_BAD_REQUEST)

    total_price = max(product_total - coupon_discount - mileage_amount, 0) + shipping_fee
    return {
        "recipient_name": recipient_name,
        "recipient_phone": recipient_phone,
        "delivery_address": delivery_address,
        "delivery_message": delivery_message,
        "payment_method": payment_method,
        "coupon_id": coupon_id,
        "coupon_discount": coupon_discount,
        "mileage_discount": mileage_amount,
        "product_total": product_total,
        "shipping_fee": shipping_fee,
        "total_price": total_price,
    }, None


def get_product_or_400(product_id):
    if not product_id:
        return None, Response({"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    product = Product.objects.filter(goods_id=product_id).first()
    if product is None:
        return None, Response({"detail": "product not found."}, status=status.HTTP_404_NOT_FOUND)

    return product, None


def get_cart_response(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    items = list(cart.items.select_related("product").order_by("-added_at"))
    serialized_items = [serialize_cart_item(item) for item in items]
    return Response(
        {
            "items": serialized_items,
            "item_count": len(serialized_items),
            "total_quantity": sum(item["quantity"] for item in serialized_items),
        }
    )


def get_wishlist_response(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    items = list(wishlist.items.select_related("product").order_by("-added_at"))
    serialized_items = [serialize_wishlist_item(item) for item in items]
    return Response(
        {
            "items": serialized_items,
            "item_count": len(serialized_items),
        }
    )


class OrderListView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "TODO"})

    @transaction.atomic
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = list(cart.items.select_related("product").order_by("-added_at"))
        if not cart_items:
            return Response({"detail": "cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        checkout_data, error_response = validate_checkout_payload(request, cart_items)
        if error_response:
            return error_response

        order = Order.objects.create(
            user=request.user,
            recipient_name=checkout_data["recipient_name"],
            recipient_phone=checkout_data["recipient_phone"],
            delivery_address=checkout_data["delivery_address"],
            delivery_message=checkout_data["delivery_message"],
            payment_method=checkout_data["payment_method"],
            applied_coupon_id=checkout_data["coupon_id"],
            product_total=checkout_data["product_total"],
            coupon_discount=checkout_data["coupon_discount"],
            mileage_discount=checkout_data["mileage_discount"],
            shipping_fee=checkout_data["shipping_fee"],
            total_price=checkout_data["total_price"],
            status="pending",
        )

        order_items = []
        interactions = []
        for cart_item in cart_items:
            order_items.append(
                OrderItem(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price_at_order=cart_item.product.price,
                )
            )
            interactions.append(
                UserInteraction(
                    user=request.user,
                    product=cart_item.product,
                    interaction_type="purchase",
                    weight=max(cart_item.quantity, 1),
                )
            )

        OrderItem.objects.bulk_create(order_items)
        UserInteraction.objects.bulk_create(interactions)
        cart.items.all().delete()

        order = Order.objects.prefetch_related("items__product").get(pk=order.pk)
        return Response({"order": serialize_order(order)}, status=status.HTTP_201_CREATED)


class CartView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return get_cart_response(request.user)

    @transaction.atomic
    def post(self, request):
        product, error_response = get_product_or_400(request.data.get("product_id"))
        if error_response:
            return error_response

        quantity = int(request.data.get("quantity", 1) or 1)
        if quantity < 1:
            return Response({"detail": "quantity must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])

        return Response(
            {"cart_item": serialize_cart_item(cart_item)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request):
        product, error_response = get_product_or_400(request.data.get("product_id"))
        if error_response:
            return error_response

        quantity = request.data.get("quantity")
        if quantity is None:
            return Response({"detail": "quantity is required."}, status=status.HTTP_400_BAD_REQUEST)

        quantity = int(quantity)
        if quantity < 1:
            return Response({"detail": "quantity must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item = CartItem.objects.filter(cart=cart, product=product).select_related("product").first()
        if cart_item is None:
            return Response({"detail": "cart item not found."}, status=status.HTTP_404_NOT_FOUND)

        cart_item.quantity = quantity
        cart_item.save(update_fields=["quantity"])
        return Response({"cart_item": serialize_cart_item(cart_item)})

    @transaction.atomic
    def delete(self, request):
        product, error_response = get_product_or_400(request.data.get("product_id"))
        if error_response:
            return error_response

        cart, _ = Cart.objects.get_or_create(user=request.user)
        deleted, _ = CartItem.objects.filter(cart=cart, product=product).delete()
        if not deleted:
            return Response({"detail": "cart item not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return get_wishlist_response(request.user)

    @transaction.atomic
    def post(self, request):
        product, error_response = get_product_or_400(request.data.get("product_id"))
        if error_response:
            return error_response

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        wishlist_item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        return Response(
            {"wishlist_item": serialize_wishlist_item(wishlist_item)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request):
        product, error_response = get_product_or_400(request.data.get("product_id"))
        if error_response:
            return error_response

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        deleted, _ = WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()
        if not deleted:
            return Response({"detail": "wishlist item not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)

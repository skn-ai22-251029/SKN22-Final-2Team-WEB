from django.db import transaction
from django.core.paginator import Paginator
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.models import Product
from users.quick_purchase import serialize_quick_purchase_profile

from ..models import Cart, CartItem, Order, OrderItem, UserInteraction, Wishlist, WishlistItem


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
ORDER_STATUS_META = {
    "pending": {
        "label": "주문 접수",
        "tone": "info",
        "can_reorder": True,
        "detail_hint": "상품 준비가 시작되면\n배송 상태가 업데이트됩니다",
        "cta_label": "다시 담기",
    },
    "shipping": {
        "label": "배송 중",
        "tone": "info",
        "can_reorder": True,
        "detail_hint": "상품이 배송 중입니다\n필요한 구성은 다시 주문할 수 있어요",
        "cta_label": "다시 담기",
    },
    "completed": {
        "label": "배송 완료",
        "tone": "success",
        "can_reorder": True,
        "detail_hint": "배송이 완료된 주문입니다\n필요한 상품은 다시 주문할 수 있어요",
        "cta_label": "다시 담기",
    },
    "cancelled": {
        "label": "주문 취소",
        "tone": "danger",
        "can_reorder": False,
        "detail_hint": "취소된 주문입니다\n결제와 배송 정보를 확인해 주세요",
        "cta_label": "주문 정보 확인",
    },
}
ORDER_LIST_ORDERING = {
    "latest": "-created_at",
    "oldest": "created_at",
}
DEFAULT_ORDER_PAGE_SIZE = 12


def error_response(detail, *, code, status_code, field=None, missing_fields=None, extra=None):
    payload = {
        "detail": detail,
        "code": code,
    }
    if field:
        payload["field"] = field
    if missing_fields:
        payload["missing_fields"] = missing_fields
    if extra:
        payload.update(extra)
    return Response(payload, status=status_code)


def _display_product_name(brand_name, goods_name):
    return (goods_name or "").strip()


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
        "product_url": product.product_url,
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
    total_quantity = sum(item["quantity"] for item in items)
    status_meta = ORDER_STATUS_META.get(
        order.status,
        {
            "label": order.status,
            "tone": "neutral",
            "can_reorder": False,
            "detail_hint": "",
            "cta_label": "주문 정보 확인",
        },
    )
    return {
        "order_id": str(order.order_id),
        "status": order.status,
        "status_label": status_meta["label"],
        "status_meta": {
            "code": order.status,
            "label": status_meta["label"],
            "tone": status_meta["tone"],
            "can_reorder": status_meta["can_reorder"],
            "detail_hint": status_meta["detail_hint"],
            "cta_label": status_meta["cta_label"],
        },
        "can_reorder": status_meta["can_reorder"],
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
        "item_count": total_quantity,
        "items": items,
        "created_at": order.created_at.isoformat(),
        "created_date": order.created_at.strftime("%Y.%m.%d"),
    }


def split_delivery_address(value):
    if not value:
        return "", ""

    parts = [part.strip() for part in value.split("|", 1)]
    base_address = parts[0] if parts else ""
    detail_address = parts[1] if len(parts) > 1 else ""
    return base_address, detail_address


def serialize_order_completion(order: Order) -> dict:
    serialized = serialize_order(order)
    delivery_base_address, delivery_detail_address = split_delivery_address(serialized["delivery_address"])
    return {
        "order_id": serialized["order_id"],
        "status": serialized["status"],
        "status_label": serialized["status_label"],
        "status_meta": serialized["status_meta"],
        "recipient_name": serialized["recipient_name"],
        "recipient_phone": serialized["recipient_phone"],
        "delivery_address": serialized["delivery_address"],
        "delivery_base_address": delivery_base_address,
        "delivery_detail_address": delivery_detail_address,
        "delivery_message": serialized["delivery_message"] or "배송 메시지 없음",
        "payment_method": serialized["payment_method"],
        "product_total": serialized["product_total"],
        "product_total_label": serialized["product_total_label"],
        "coupon_discount": serialized["coupon_discount"],
        "coupon_discount_label": serialized["coupon_discount_label"],
        "mileage_discount": serialized["mileage_discount"],
        "mileage_discount_label": serialized["mileage_discount_label"],
        "shipping_fee": serialized["shipping_fee"],
        "shipping_fee_label": "무료" if serialized["shipping_fee"] == 0 else serialized["shipping_fee_label"],
        "total_price": serialized["total_price"],
        "total_price_label": serialized["total_price_label"],
        "item_count": serialized["item_count"],
        "items": serialized["items"],
        "created_at": serialized["created_at"],
        "created_date": serialized["created_date"],
    }


def serialize_order_summary(order: Order) -> dict:
    serialized = serialize_order(order)
    items = serialized["items"]
    return {
        "order_id": serialized["order_id"],
        "status": serialized["status"],
        "status_label": serialized["status_label"],
        "status_meta": serialized["status_meta"],
        "can_reorder": serialized["can_reorder"],
        "recipient_name": serialized["recipient_name"],
        "delivery_message": serialized["delivery_message"],
        "payment_method": serialized["payment_method"],
        "total_price": serialized["total_price"],
        "total_price_label": serialized["total_price_label"],
        "item_count": serialized["item_count"],
        "created_at": serialized["created_at"],
        "created_date": serialized["created_date"],
        "items": items,
        "primary_item_name": items[0]["name"] if items else "",
    }


def parse_order_list_options(request):
    status_filter = (request.query_params.get("status") or "all").strip() or "all"
    if status_filter != "all" and status_filter not in ORDER_STATUS_META:
        return None, error_response(
            "invalid status filter.",
            code="invalid_status_filter",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="status",
        )

    ordering_key = (request.query_params.get("ordering") or "latest").strip() or "latest"
    ordering = ORDER_LIST_ORDERING.get(ordering_key)
    if ordering is None:
        return None, error_response(
            "invalid ordering.",
            code="invalid_ordering",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="ordering",
        )

    try:
        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = int(request.query_params.get("page_size", DEFAULT_ORDER_PAGE_SIZE) or DEFAULT_ORDER_PAGE_SIZE)
    except (TypeError, ValueError):
        return None, error_response(
            "page and page_size must be numbers.",
            code="invalid_pagination",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if page_size < 1 or page_size > 50:
        return None, error_response(
            "page_size must be between 1 and 50.",
            code="invalid_page_size",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="page_size",
        )

    return {
        "status_filter": status_filter,
        "ordering_key": ordering_key,
        "ordering": ordering,
        "page": page,
        "page_size": page_size,
    }, None


def get_profile_value(user, field_name):
    try:
        profile = user.profile
    except Exception:
        return ""
    return getattr(profile, field_name, "") or ""


def is_valid_payment_method(payment_method):
    normalized = str(payment_method or "").strip()
    if not normalized:
        return False
    if normalized in PAYMENT_METHODS:
        return True
    if " / " in normalized and "*" in normalized:
        return True
    if "페이" in normalized or "pay" in normalized.lower():
        return True
    return False


def normalize_delivery_address(data, user):
    delivery_address = (data.get("delivery_address") or "").strip()
    if delivery_address:
        return delivery_address

    address_main = (data.get("delivery_address_main") or "").strip()
    address_detail = (data.get("delivery_address_detail") or "").strip()
    if address_main:
        return " | ".join(part for part in [address_main, address_detail] if part)

    return get_profile_value(user, "address").strip()


def get_delivery_defaults(user):
    quick_purchase = serialize_quick_purchase_profile(user)
    return {
        "recipient_name": quick_purchase["recipient_name"].strip(),
        "recipient_phone": quick_purchase["recipient_phone"].strip(),
        "postal_code": quick_purchase["postal_code"].strip(),
        "address_main": quick_purchase["address_main"].strip(),
        "address_detail": quick_purchase["address_detail"].strip(),
    }


def parse_positive_int(value, field_name):
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None, error_response(
            f"{field_name} must be a number.",
            code="invalid_number",
            status_code=status.HTTP_400_BAD_REQUEST,
            field=field_name,
        )

    if parsed < 0:
        return None, error_response(
            f"{field_name} must be at least 0.",
            code="invalid_number",
            status_code=status.HTTP_400_BAD_REQUEST,
            field=field_name,
        )

    return parsed, None


def get_coupon_or_400(coupon_id):
    normalized_coupon_id = (coupon_id or "none").strip() or "none"
    coupon = COUPON_RULES.get(normalized_coupon_id)
    if coupon is None:
        return None, None, error_response(
            "invalid coupon_id.",
            code="invalid_coupon_id",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="coupon_id",
        )
    return normalized_coupon_id, coupon, None


def validate_checkout_payload(data, user, cart_items):
    delivery_defaults = get_delivery_defaults(user)
    recipient_name = (data.get("recipient_name") or delivery_defaults["recipient_name"] or get_profile_value(user, "nickname")).strip()
    recipient_phone = (data.get("recipient_phone") or delivery_defaults["recipient_phone"]).strip()
    postal_code = (data.get("postal_code") or delivery_defaults["postal_code"]).strip()
    address_main = (data.get("delivery_address_main") or delivery_defaults["address_main"]).strip()
    address_detail = (data.get("delivery_address_detail") or delivery_defaults["address_detail"]).strip()
    delivery_address = normalize_delivery_address(
        {
            **data,
            "delivery_address_main": address_main,
            "delivery_address_detail": address_detail,
        },
        user,
    )
    delivery_message = (data.get("delivery_message") or "").strip()
    payment_method = (data.get("payment_method") or get_profile_value(user, "payment_method")).strip()
    missing_fields = []

    if not recipient_name:
        missing_fields.append("recipient_name")
    if not recipient_phone:
        missing_fields.append("recipient_phone")
    if not postal_code:
        missing_fields.append("postal_code")
    if not address_main:
        missing_fields.append("delivery_address_main")
    if not address_detail:
        missing_fields.append("delivery_address_detail")
    if not payment_method:
        missing_fields.append("payment_method")

    if missing_fields:
        primary_field = missing_fields[0]
        return None, error_response(
            f"{primary_field} is required.",
            code="missing_required_fields",
            status_code=status.HTTP_400_BAD_REQUEST,
            field=primary_field,
            missing_fields=missing_fields,
        )

    normalized_phone = "".join(char for char in recipient_phone if char.isdigit())
    if len(normalized_phone) < 9:
        return None, error_response(
            "recipient_phone must be a valid phone number.",
            code="invalid_phone_number",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="recipient_phone",
        )

    if not is_valid_payment_method(payment_method):
        return None, error_response(
            "invalid payment_method.",
            code="invalid_payment_method",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="payment_method",
            extra={
                "available_payment_methods": sorted(PAYMENT_METHODS),
            },
        )

    product_total = sum(item.product.price * item.quantity for item in cart_items)
    shipping_fee = 0 if product_total >= FREE_SHIPPING_THRESHOLD else BASE_SHIPPING_FEE

    coupon_id, coupon, coupon_error = get_coupon_or_400(data.get("coupon_id"))
    if coupon_error:
        return None, coupon_error
    if product_total < coupon["min_total"]:
        return None, error_response(
            "coupon is not available for current cart total.",
            code="coupon_not_available",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="coupon_id",
        )

    mileage_amount, mileage_error = parse_positive_int(data.get("mileage_amount", 0), "mileage_amount")
    if mileage_error:
        return None, mileage_error
    if mileage_amount > AVAILABLE_MILEAGE:
        return None, error_response(
            "mileage exceeds available balance.",
            code="mileage_exceeds_balance",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="mileage_amount",
        )

    coupon_discount = coupon["discount"]
    max_usable_mileage = max(product_total - coupon_discount, 0)
    if mileage_amount > max_usable_mileage:
        return None, error_response(
            "mileage exceeds payable product total.",
            code="mileage_exceeds_payable_total",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="mileage_amount",
        )

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


def create_order_from_cart(user, checkout_data, cart_items):
    order = Order.objects.create(
        user=user,
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
                user=user,
                product=cart_item.product,
                interaction_type="purchase",
                weight=max(cart_item.quantity, 1),
            )
        )

    OrderItem.objects.bulk_create(order_items)
    UserInteraction.objects.bulk_create(interactions)
    Cart.objects.get(user=user).items.all().delete()
    return Order.objects.prefetch_related("items__product").get(pk=order.pk)


def get_product_or_400(product_id):
    if not product_id:
        return None, error_response(
            "product_id is required.",
            code="missing_product_id",
            status_code=status.HTTP_400_BAD_REQUEST,
            field="product_id",
        )

    product = Product.objects.filter(goods_id=product_id).first()
    if product is None:
        return None, error_response(
            "product not found.",
            code="product_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            field="product_id",
        )

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
        options, options_error_response = parse_order_list_options(request)
        if options_error_response:
            return options_error_response

        orders = Order.objects.filter(user=request.user).prefetch_related("items__product")
        if options["status_filter"] != "all":
            orders = orders.filter(status=options["status_filter"])
        orders = orders.order_by(options["ordering"])

        paginator = Paginator(orders, options["page_size"])
        page_obj = paginator.get_page(options["page"])
        serialized_orders = [serialize_order_summary(order) for order in page_obj.object_list]
        return Response(
            {
                "orders": serialized_orders,
                "count": paginator.count,
                "filters": {
                    "status": options["status_filter"],
                    "ordering": options["ordering_key"],
                    "available_statuses": [
                        {"code": "all", "label": "전체"}
                    ] + [
                        {"code": code, "label": meta["label"]}
                        for code, meta in ORDER_STATUS_META.items()
                    ],
                    "available_ordering": [
                        {"code": "latest", "label": "최신순"},
                        {"code": "oldest", "label": "오래된순"},
                    ],
                },
                "pagination": {
                    "page": page_obj.number,
                    "page_size": options["page_size"],
                    "total_pages": paginator.num_pages,
                    "total_count": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                },
                "reorder_policy": {
                    "mode": "add_to_cart",
                    "merge_behavior": "increase_quantity",
                },
            }
        )

    @transaction.atomic
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = list(cart.items.select_related("product").order_by("-added_at"))
        if not cart_items:
            return error_response(
                "cart is empty.",
                code="cart_empty",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        checkout_data, checkout_error_response = validate_checkout_payload(request.data, request.user, cart_items)
        if checkout_error_response:
            return checkout_error_response

        order = create_order_from_cart(request.user, checkout_data, cart_items)
        return Response(
            {
                "order": serialize_order(order),
                "completion": serialize_order_completion(order),
            },
            status=status.HTTP_201_CREATED,
        )


class QuickPurchaseView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = list(cart.items.select_related("product").order_by("-added_at"))
        if not cart_items:
            return error_response(
                "cart is empty.",
                code="cart_empty",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        quick_purchase = serialize_quick_purchase_profile(request.user)
        if not quick_purchase["has_delivery_info"] or not quick_purchase["has_payment_method"]:
            missing_requirements = []
            if not quick_purchase["has_delivery_info"]:
                missing_requirements.append("delivery_info")
            if not quick_purchase["has_payment_method"]:
                missing_requirements.append("payment_method")
            return error_response(
                "quick purchase requires saved delivery info and payment method.",
                code="quick_purchase_requirements_missing",
                status_code=status.HTTP_400_BAD_REQUEST,
                missing_fields=missing_requirements,
            )

        payload = {
            "recipient_name": quick_purchase["recipient_name"],
            "recipient_phone": quick_purchase["recipient_phone"],
            "delivery_address_main": quick_purchase["address_main"],
            "delivery_address_detail": quick_purchase["address_detail"],
            "delivery_message": request.data.get("delivery_message", ""),
            "payment_method": quick_purchase["payment_summary"],
            "coupon_id": request.data.get("coupon_id", "none"),
            "mileage_amount": request.data.get("mileage_amount", 0),
        }
        checkout_data, checkout_error_response = validate_checkout_payload(payload, request.user, cart_items)
        if checkout_error_response:
            return checkout_error_response

        order = create_order_from_cart(request.user, checkout_data, cart_items)
        return Response(
            {
                "order": serialize_order(order),
                "completion": serialize_order_completion(order),
                "quick_purchase": {
                    "has_delivery_info": True,
                    "has_payment_method": True,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = (
            Order.objects.filter(user=request.user, order_id=order_id)
            .prefetch_related("items__product")
            .first()
        )
        if order is None:
            return error_response(
                "order not found.",
                code="order_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return Response({"order": serialize_order(order)})


class CartView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return get_cart_response(request.user)

    @transaction.atomic
    def post(self, request):
        product, product_error_response = get_product_or_400(request.data.get("product_id"))
        if product_error_response:
            return product_error_response

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
        product, product_error_response = get_product_or_400(request.data.get("product_id"))
        if product_error_response:
            return product_error_response

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
        product, product_error_response = get_product_or_400(request.data.get("product_id"))
        if product_error_response:
            return product_error_response

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
        product, product_error_response = get_product_or_400(request.data.get("product_id"))
        if product_error_response:
            return product_error_response

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        wishlist_item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        return Response(
            {"wishlist_item": serialize_wishlist_item(wishlist_item)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request):
        product, product_error_response = get_product_or_400(request.data.get("product_id"))
        if product_error_response:
            return product_error_response

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        deleted, _ = WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()
        if not deleted:
            return Response({"detail": "wishlist item not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)

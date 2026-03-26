from django.db import transaction
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from products.models import Product

from .models import Cart, CartItem, Wishlist, WishlistItem


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
    def get(self, request):
        return Response({"message": "TODO"})


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

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Product
from users.models import User, UserProfile

from .models import Cart, CartItem, Order, OrderItem, UserInteraction, Wishlist, WishlistItem


class CartApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="cart@example.com", password="Password123!")
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            goods_id="GI1001",
            goods_name="장바구니 테스트 상품",
            brand_name="테스트 브랜드",
            price=12000,
            discount_price=9900,
            thumbnail_url="https://example.com/cart-thumb.png",
            product_url="https://example.com/cart-product",
            crawled_at=timezone.now(),
        )

    def test_get_cart_returns_empty_defaults(self):
        response = self.client.get("/api/orders/cart/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["item_count"], 0)
        self.assertEqual(response.data["total_quantity"], 0)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_post_cart_adds_item(self):
        response = self.client.post(
            "/api/orders/cart/",
            {"product_id": self.product.goods_id, "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cart_item"]["product_id"], self.product.goods_id)
        self.assertEqual(response.data["cart_item"]["quantity"], 2)
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())

    def test_post_cart_existing_item_increments_quantity(self):
        self.client.post("/api/orders/cart/", {"product_id": self.product.goods_id}, format="json")

        response = self.client.post(
            "/api/orders/cart/",
            {"product_id": self.product.goods_id, "quantity": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cart_item"]["quantity"], 4)

    def test_patch_cart_updates_quantity(self):
        self.client.post("/api/orders/cart/", {"product_id": self.product.goods_id}, format="json")

        response = self.client.patch(
            "/api/orders/cart/",
            {"product_id": self.product.goods_id, "quantity": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cart_item"]["quantity"], 5)

    def test_delete_cart_removes_item(self):
        self.client.post("/api/orders/cart/", {"product_id": self.product.goods_id}, format="json")

        response = self.client.delete(
            "/api/orders/cart/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())


class WishlistApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="wishlist@example.com", password="Password123!")
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            goods_id="GI2001",
            goods_name="관심상품 테스트 상품",
            brand_name="테스트 브랜드",
            price=18000,
            discount_price=14900,
            thumbnail_url="https://example.com/wishlist-thumb.png",
            product_url="https://example.com/wishlist-product",
            crawled_at=timezone.now(),
        )

    def test_get_wishlist_returns_empty_defaults(self):
        response = self.client.get("/api/orders/wishlist/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["item_count"], 0)
        self.assertTrue(Wishlist.objects.filter(user=self.user).exists())

    def test_post_wishlist_adds_item(self):
        response = self.client.post(
            "/api/orders/wishlist/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["wishlist_item"]["product_id"], self.product.goods_id)
        self.assertTrue(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).exists())

    def test_delete_wishlist_removes_item(self):
        self.client.post("/api/orders/wishlist/", {"product_id": self.product.goods_id}, format="json")

        response = self.client.delete(
            "/api/orders/wishlist/",
            {"product_id": self.product.goods_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).exists())


class OrderCreateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="order@example.com", password="Password123!")
        UserProfile.objects.create(
            user=self.user,
            nickname="주문자",
            address="서울 강동구 올림픽로 123 | 101동 1203호",
            phone="01012341234",
        )
        self.client.force_authenticate(self.user)

        self.product_a = Product.objects.create(
            goods_id="GI3001",
            goods_name="주문 생성 테스트 상품 A",
            brand_name="테스트 브랜드",
            price=18000,
            discount_price=15000,
            thumbnail_url="https://example.com/order-a.png",
            product_url="https://example.com/order-a",
            crawled_at=timezone.now(),
        )
        self.product_b = Product.objects.create(
            goods_id="GI3002",
            goods_name="주문 생성 테스트 상품 B",
            brand_name="테스트 브랜드",
            price=14000,
            discount_price=12000,
            thumbnail_url="https://example.com/order-b.png",
            product_url="https://example.com/order-b",
            crawled_at=timezone.now(),
        )

    def add_cart_items(self):
        self.client.post("/api/orders/cart/", {"product_id": self.product_a.goods_id, "quantity": 2}, format="json")
        self.client.post("/api/orders/cart/", {"product_id": self.product_b.goods_id, "quantity": 1}, format="json")

    def test_post_order_creates_order_and_clears_cart(self):
        self.add_cart_items()

        response = self.client.post(
            "/api/orders/",
            {
                "payment_method": "우리카드 1234 / 일시불",
                "delivery_message": "부재 시 문 앞에 놓아주세요",
                "coupon_id": "new-member",
                "mileage_amount": 1200,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(OrderItem.objects.filter(order__user=self.user).count(), 2)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)
        self.assertEqual(UserInteraction.objects.filter(user=self.user, interaction_type="purchase").count(), 2)

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.recipient_name, "주문자")
        self.assertEqual(order.payment_method, "우리카드 1234 / 일시불")
        self.assertEqual(order.product_total, 50000)
        self.assertEqual(order.coupon_discount, 3000)
        self.assertEqual(order.mileage_discount, 1200)
        self.assertEqual(order.shipping_fee, 0)
        self.assertEqual(order.total_price, 45800)
        self.assertEqual(response.data["order"]["total_price"], 45800)

    def test_post_order_rejects_empty_cart(self):
        response = self.client.post(
            "/api/orders/",
            {"payment_method": "우리카드 1234 / 일시불"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "cart is empty.")

    def test_post_order_rejects_invalid_coupon_for_cart_total(self):
        self.client.post("/api/orders/cart/", {"product_id": self.product_a.goods_id, "quantity": 1}, format="json")

        response = self.client.post(
            "/api/orders/",
            {
                "payment_method": "우리카드 1234 / 일시불",
                "coupon_id": "pet-care",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "coupon is not available for current cart total.")

    def test_post_order_rejects_mileage_above_available_balance(self):
        self.add_cart_items()

        response = self.client.post(
            "/api/orders/",
            {
                "payment_method": "우리카드 1234 / 일시불",
                "mileage_amount": 5000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "mileage exceeds available balance.")

    def test_post_order_requires_delivery_info_if_profile_missing(self):
        user = User.objects.create_user(email="missing@example.com", password="Password123!")
        self.client.force_authenticate(user)
        self.client.post("/api/orders/cart/", {"product_id": self.product_a.goods_id, "quantity": 1}, format="json")

        response = self.client.post(
            "/api/orders/",
            {"payment_method": "우리카드 1234 / 일시불"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "recipient_name is required.")

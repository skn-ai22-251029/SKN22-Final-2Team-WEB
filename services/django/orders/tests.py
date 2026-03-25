from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Product
from users.models import User

from .models import Cart, CartItem, Wishlist, WishlistItem


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

import uuid
from django.db import models
from users.models import User
from products.models import Product


class Cart(models.Model):
    cart_id    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart"


class CartItem(models.Model):
    cart_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart         = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product      = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="cart_items")
    quantity     = models.IntegerField(default=1)
    added_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cart_item"
        unique_together = [("cart", "product")]


class Wishlist(models.Model):
    wishlist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wishlist"


class WishlistItem(models.Model):
    wishlist_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="wishlist_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlist_item"
        unique_together = [("wishlist", "product")]


class Order(models.Model):
    STATUS_CHOICES = [("pending", "주문 접수"), ("completed", "배송 완료"), ("cancelled", "취소")]

    order_id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.RESTRICT, related_name="orders")
    recipient_name   = models.CharField(max_length=100)
    delivery_address = models.TextField()
    total_price      = models.IntegerField()
    status           = models.CharField(max_length=15, default="pending", choices=STATUS_CHOICES)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order"


class OrderItem(models.Model):
    order_item_id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product        = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="order_items")
    quantity       = models.IntegerField()
    price_at_order = models.IntegerField()

    class Meta:
        db_table = "order_item"


class UserInteraction(models.Model):
    INTERACTION_CHOICES = [("click", "클릭"), ("cart", "장바구니"), ("purchase", "구매"), ("reject", "거절")]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(User, on_delete=models.CASCADE)
    product          = models.ForeignKey(Product, on_delete=models.CASCADE)
    session_id       = models.UUIDField(null=True, blank=True)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_CHOICES)
    weight           = models.SmallIntegerField(default=1)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_interaction"

import uuid
from django.db import models
from users.models import User
from pets.models import Pet
from products.models import Product


class ChatSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_sessions")
    target_pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    title      = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"


class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "사용자"), ("assistant", "어시스턴트")]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session    = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"


class MessageProductCard(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="product_cards")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    reason  = models.TextField()

    class Meta:
        db_table = "message_product_card"

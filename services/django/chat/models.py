import uuid
from django.db import models
from users.models import User
from pets.models import Pet
from products.models import Product


class ChatSession(models.Model):
    PROFILE_CONTEXT_PET = "pet"
    PROFILE_CONTEXT_FUTURE = "future"
    PROFILE_CONTEXT_NONE = "none"
    PROFILE_CONTEXT_CHOICES = [
        (PROFILE_CONTEXT_PET, "반려동물"),
        (PROFILE_CONTEXT_FUTURE, "예비집사"),
        (PROFILE_CONTEXT_NONE, "선택 안 함"),
    ]

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    target_pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    profile_context_type = models.CharField(max_length=10, choices=PROFILE_CONTEXT_CHOICES, default=PROFILE_CONTEXT_NONE)
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


class ChatMessageRecommendation(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message    = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="recommended_products")
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="chat_message_recommendations")
    rank_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message_recommendation"
        unique_together = [("message", "product")]


class ChatSessionMemory(models.Model):
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name="memory", primary_key=True)
    summary_text = models.TextField(blank=True, default="")
    dialog_state = models.JSONField(default=dict, blank=True)
    last_compacted_message_id = models.UUIDField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session_memory"

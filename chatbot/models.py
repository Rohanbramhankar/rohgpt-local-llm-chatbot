from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    """RohGPT madhil prattek chat chi mahiti."""

    # unique=True kadhla: ek session madhe anek chats asu shaktat.
    session_key = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_conversations",
    )

    title = models.CharField(
        max_length=200,
        default="New Chat",
    )

    # PDF upload sathi
    pdf_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    pdf_text = models.TextField(
        blank=True,
        default="",
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    memory = models.TextField(
        blank=True,
        default="",
        max_length=2000,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    """Prattek chat madhle User ani AI che messages."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    conversation = models.ForeignKey(
        "chatbot.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class ChatImage(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="chat_images/%Y/%m")
    content_type = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
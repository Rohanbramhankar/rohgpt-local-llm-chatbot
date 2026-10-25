from django.db import models


class Conversation(models.Model):
    """RohGPT madhil prattek chat chi mahiti."""

    # unique=True kadhla: ek session madhe anek chats asu shaktat.
    session_key = models.CharField(
        max_length=100,
        db_index=True,
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
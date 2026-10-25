from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ChatImage


@receiver(post_delete, sender=ChatImage)
def delete_chat_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)

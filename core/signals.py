from django.db.models.signals import post_save
from django.dispatch import receiver

from django.conf import settings
from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is saved."""
    if created:
        role = (
            UserProfile.ROLE_OWNER if instance.is_superuser else UserProfile.ROLE_SALES
        )
        UserProfile.objects.get_or_create(user=instance, defaults={"role": role})

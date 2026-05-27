from django.conf import settings
from django.utils.translation import get_language

from .models import BusinessProfile, UserProfile


def gmi_context(request):
    """Inject business profile and current user role into every template."""
    profile = BusinessProfile.objects.filter(id=1).first()
    currency_code = profile.currency_code if profile else BusinessProfile.CURRENCY_UGX
    profile_logo_url = None
    if profile and profile.logo:
        try:
            if profile.logo.storage.exists(profile.logo.name):
                profile_logo_url = profile.logo.url
        except Exception:
            profile_logo_url = None
    user_role = None
    if request.user.is_authenticated:
        if request.user.is_superuser:
            user_role = UserProfile.ROLE_OWNER
        else:
            try:
                user_role = request.user.profile.role
            except Exception:
                user_role = None
    return {
        "profile": profile,
        "profile_logo_url": profile_logo_url,
        "user_role": user_role,
        "currency_code": currency_code,
        "currency_choices": BusinessProfile.CURRENCY_CHOICES,
        "current_language": get_language(),
        "language_choices": settings.LANGUAGES,
    }

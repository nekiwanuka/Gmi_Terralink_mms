from .models import BusinessProfile, UserProfile


def gmi_context(request):
    """Inject business profile and current user role into every template."""
    profile = BusinessProfile.objects.filter(id=1).first()
    currency_code = profile.currency_code if profile else BusinessProfile.CURRENCY_UGX
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
        "user_role": user_role,
        "currency_code": currency_code,
        "currency_choices": BusinessProfile.CURRENCY_CHOICES,
    }

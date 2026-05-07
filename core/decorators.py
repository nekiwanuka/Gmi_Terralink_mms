from functools import wraps

from django.shortcuts import redirect


def role_required(*allowed_roles):
    """Restrict a view to users whose UserProfile.role is in *allowed_roles*.

    Superusers always pass.  Unauthenticated users are sent to login.
    Users with an incompatible role see the access-denied page.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/login/?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                user_role = request.user.profile.role
            except AttributeError:
                return redirect("access_denied")
            if user_role in ("Admin", "General Manager"):
                return view_func(request, *args, **kwargs)
            effective_roles = {user_role}
            if user_role == "Warehouse Manager":
                effective_roles.add("Warehouse")
            if user_role == "Sales Attendant":
                effective_roles.add("Sales")
            if user_role == "Store Manager":
                effective_roles.update({"Sales", "Operations"})
            if not effective_roles.intersection(set(allowed_roles)):
                return redirect("access_denied")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator

from .models import UserPreference


def display_mode(request):
    if not request.user.is_authenticated:
        return {"display_mode": "light"}

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    return {"display_mode": preference.display_mode}

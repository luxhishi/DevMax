from .models import Notification, UserPreference


def display_mode(request):
    if not request.user.is_authenticated:
        return {
            "display_mode": "light",
            "header_notifications": [],
            "unread_notification_count": 0,
        }

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    notifications = list(
        Notification.objects.filter(user=request.user)
        .select_related("actor", "subthread", "post", "post__subthread", "comment")
        .order_by("-created_at")[:8]
    )
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return {
        "display_mode": preference.display_mode,
        "header_notifications": notifications,
        "unread_notification_count": unread_count,
        "header_avatar_url": preference.profile_photo.url if preference.profile_photo else "",
    }

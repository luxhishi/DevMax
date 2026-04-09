from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.templatetags.static import static

from .models import Comment, Post


AURA_PER_UPVOTE = 5
AURA_PER_RESPONSE = 10

ACHIEVEMENT_LEVELS = (
    {
        "level": "beginner",
        "name": "Baby Steps",
        "threshold": 5,
        "aura_bonus": 50,
        "image_path": "images/achievements/baby-steps.png",
        "fallback_label": "BS",
    },
    {
        "level": "intermediate",
        "name": "Adept",
        "threshold": 10,
        "aura_bonus": 80,
        "image_path": "images/achievements/adept.png",
        "fallback_label": "AD",
    },
    {
        "level": "advanced",
        "name": "To The Stars",
        "threshold": 15,
        "aura_bonus": 150,
        "image_path": "images/achievements/to-the-stars.png",
        "fallback_label": "TS",
    },
)


def _achievement_payload(level_config, upvotes=None, count=0):
    payload = {
        "level": level_config["level"],
        "name": level_config["name"],
        "threshold": level_config["threshold"],
        "aura_bonus": level_config["aura_bonus"],
        "aura_bonus_display": f"+{level_config['aura_bonus']} Aura",
        "image_url": static(level_config["image_path"]),
        "image_path": level_config["image_path"],
        "fallback_label": level_config["fallback_label"],
        "count": count,
        "count_label": "1 award" if count == 1 else f"{count} awards",
    }
    if upvotes is not None:
        payload["upvotes"] = upvotes
    return payload


def achievement_for_upvotes(upvotes):
    for level_config in reversed(ACHIEVEMENT_LEVELS):
        if upvotes >= level_config["threshold"]:
            return _achievement_payload(level_config, upvotes=upvotes, count=1)
    return None


def _count_awards_for_range(queryset, minimum, maximum=None):
    filtered = queryset.filter(upvotes__gte=minimum)
    if maximum is not None:
        filtered = filtered.filter(upvotes__lt=maximum)
    return filtered.count()


def build_user_reputation_summary(user, post_queryset=None, comment_queryset=None):
    post_queryset = post_queryset if post_queryset is not None else Post.objects.filter(author=user)
    comment_queryset = comment_queryset if comment_queryset is not None else Comment.objects.filter(author=user)

    total_post_upvotes = post_queryset.aggregate(total=Coalesce(Sum("upvotes"), 0))["total"] or 0
    total_comment_upvotes = comment_queryset.aggregate(total=Coalesce(Sum("upvotes"), 0))["total"] or 0
    upvote_total = total_post_upvotes + total_comment_upvotes

    achievement_rows = []
    total_achievement_count = 0
    badge_aura_total = 0
    for index, level_config in enumerate(ACHIEVEMENT_LEVELS):
        next_threshold = ACHIEVEMENT_LEVELS[index + 1]["threshold"] if index + 1 < len(ACHIEVEMENT_LEVELS) else None
        count = _count_awards_for_range(post_queryset, level_config["threshold"], next_threshold)
        count += _count_awards_for_range(comment_queryset, level_config["threshold"], next_threshold)
        total_achievement_count += count
        badge_aura_total += count * level_config["aura_bonus"]
        achievement_rows.append(_achievement_payload(level_config, count=count))

    post_response_total = Comment.objects.filter(post__author=user, parent__isnull=True).exclude(author=user).count()
    reply_response_total = Comment.objects.filter(parent__author=user).exclude(author=user).count()
    response_total = post_response_total + reply_response_total

    upvote_aura_total = upvote_total * AURA_PER_UPVOTE
    response_aura_total = response_total * AURA_PER_RESPONSE
    total_aura = upvote_aura_total + response_aura_total + badge_aura_total

    return {
        "total_aura": total_aura,
        "total_aura_display": f"{total_aura:,}",
        "achievement_total": total_achievement_count,
        "upvote_total": upvote_total,
        "upvote_total_display": f"{upvote_total:,}",
        "upvote_aura_total": upvote_aura_total,
        "response_total": response_total,
        "response_aura_total": response_aura_total,
        "badge_aura_total": badge_aura_total,
        "achievement_rows": achievement_rows,
        "earned_achievement_rows": [row for row in achievement_rows if row["count"]],
    }

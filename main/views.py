import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AdminAuditLog, Comment, Notification, Post, Subthread, SubthreadMembership, Tag, UserPreference, Vote
from .reputation import ACHIEVEMENT_LEVELS, achievement_for_upvotes, build_user_reputation_summary


PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PROFILE_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PROFILE_BIO_MAX_LENGTH = 280


def _build_post_detail_url(post_id, subthread_name, return_to_subthread=None, anchor=None, open_comment=False):
    url = reverse("main:post_detail", kwargs={"name": subthread_name, "post_id": post_id})
    query_params = {}
    if return_to_subthread:
        query_params["from_subthread"] = return_to_subthread
    if open_comment:
        query_params["open_comment"] = "1"
    if query_params:
        url = f"{url}?{urlencode(query_params)}"
    if anchor:
        url = f"{url}#{anchor}"
    return url


def _build_profile_url(username, tab=None):
    url = reverse("main:user_profile", kwargs={"username": username})
    if tab:
        url = f"{url}?{urlencode({'tab': tab})}"
    return url


def _profile_photo_url(preference):
    if preference and preference.profile_photo:
        return preference.profile_photo.url
    return ""


def _profile_bio_text(preference):
    if preference and preference.bio and preference.bio.strip():
        return preference.bio.strip()
    return "No bio yet"


def _build_search_url(query="", tab=None, scope_name=None):
    params = {}
    if query:
        params["q"] = query
    if tab:
        params["tab"] = tab
    if scope_name:
        params["scope"] = scope_name
    url = reverse("main:search")
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


def _build_questions_url(sort=None):
    url = reverse("main:questions")
    if sort:
        url = f"{url}?{urlencode({'sort': sort})}"
    return url


def _build_question_detail_url(post):
    return reverse("main:post_detail", kwargs={"name": post.subthread.name, "post_id": post.id})


def _normalize_tag_names(raw_tags):
    if not raw_tags:
        return []

    normalized_tags = []
    seen = set()
    for piece in re.split(r"[\r\n,]+", raw_tags):
        tag_name = re.sub(r"\s+", "-", piece.strip().lower())
        tag_name = re.sub(r"[^a-z0-9+#.\-]", "", tag_name).strip("-")
        if not tag_name or tag_name in seen:
            continue
        seen.add(tag_name)
        normalized_tags.append(tag_name)
        if len(normalized_tags) == 5:
            break

    return normalized_tags


def _normalize_profile_query(query):
    lowered = query.lower()
    if lowered.startswith("u/"):
        return query[2:].strip()
    return query


def _time_ago(value):
    local_value = timezone.localtime(value)
    now = timezone.localtime(timezone.now())
    delta = now - local_value

    if delta.total_seconds() < 60:
        return "just now"

    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit} ago"

    hours = int(delta.total_seconds() // 3600)
    if hours < 24:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"

    days = delta.days
    if days < 7:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit} ago"

    weeks = days // 7
    if weeks < 5:
        unit = "week" if weeks == 1 else "weeks"
        return f"{weeks} {unit} ago"

    months = days // 30
    if months < 12:
        unit = "month" if months == 1 else "months"
        return f"{months} {unit} ago"

    years = days // 365
    unit = "year" if years == 1 else "years"
    return f"{years} {unit} ago"


def _related_tags(subthread_name, title, content):
    haystack = f"{subthread_name} {title} {content}".lower()

    if "welcome to d/" in title.lower():
        return [subthread_name, "welcome", "introduction"]

    keyword_map = [
        ("tailwind", ["tailwind", "css", "plugins"]),
        ("react", ["react", "performance", "optimization"]),
        ("typescript", ["typescript", "generics", "typing"]),
        ("django", ["django", "backend", "community"]),
        ("python", ["python", "loops", "basics"]),
        ("webdev", ["webdev", "frontend", "tooling"]),
        ("performance", ["performance", "profiling", "optimization"]),
        ("plugin", ["plugins", "tooling", "workflow"]),
    ]

    for keyword, tags in keyword_map:
        if keyword in haystack:
            return tags

    return [subthread_name, "discussion", "tips"]


def _tag_names_for_post(post):
    prefetched_tags = getattr(post, "_prefetched_objects_cache", {}).get("tags")
    if prefetched_tags is not None:
        tag_names = [tag.name for tag in prefetched_tags]
    else:
        tag_names = list(post.tags.values_list("name", flat=True))

    if tag_names:
        return tag_names

    return _related_tags(post.subthread.name, post.title, post.content)


def _serialize_tag_names(tag_names, scope_name=None):
    return [
        {
            "name": tag_name,
            "url": _build_search_url(query=tag_name, tab="posts", scope_name=scope_name or None),
        }
        for tag_name in tag_names
    ]


def _serialize_post_tags(post, scope_name=None):
    return _serialize_tag_names(_tag_names_for_post(post), scope_name=scope_name)


def _assign_post_tags(post, raw_tags):
    tag_names = _normalize_tag_names(raw_tags)
    if not tag_names:
        tag_names = _related_tags(post.subthread.name, post.title, post.content)

    if _is_question_post(post):
        tag_names = ["question", *tag_names]

    ordered_tag_names = []
    seen = set()
    for tag_name in tag_names:
        if not tag_name or tag_name in seen:
            continue
        seen.add(tag_name)
        ordered_tag_names.append(tag_name)
        if len(ordered_tag_names) == 5:
            break

    tag_objects = [Tag.objects.get_or_create(name=tag_name)[0] for tag_name in ordered_tag_names]
    post.tags.set(tag_objects)


def _serialize_post(post, return_to_subthread=None, current_user_vote="", vote_return_url="", tag_scope_name=None):
    comment_total = getattr(post, "comment_total", None)
    if comment_total is None:
        comment_total = post.comments.count()

    return {
        "id": post.id,
        "title": post.title,
        "subthread": post.subthread.name,
        "upvotes": post.upvotes,
        "comments": comment_total,
        "timeAgo": _time_ago(post.created_at),
        "content": post.content,
        "tags": _serialize_post_tags(post, scope_name=tag_scope_name),
        "author": post.author.username,
        "achievement": achievement_for_upvotes(post.upvotes),
        "detail_url": _build_post_detail_url(post.id, post.subthread.name, return_to_subthread=return_to_subthread),
        "comments_url": _build_post_detail_url(
            post.id,
            post.subthread.name,
            return_to_subthread=return_to_subthread,
            anchor="comments",
        ),
        "current_user_vote": current_user_vote,
        "vote_return_url": vote_return_url,
    }


def _serialize_comment(comment):
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post.id,
        "post_title": comment.post.title,
        "subthread": comment.post.subthread.name,
        "timeAgo": _time_ago(comment.created_at),
        "achievement": achievement_for_upvotes(comment.upvotes),
        "detail_url": _build_post_detail_url(comment.post.id, comment.post.subthread.name, anchor="comments"),
    }


def _fake_posts():
    return [
        {
            "id": 1,
            "title": "How to optimize React performance?",
            "subthread": "react",
            "upvotes": 1234,
            "comments": 89,
            "timeAgo": "2 hours ago",
            "content": "I'm working on a large React app...",
            "tags": _serialize_tag_names(
                _related_tags("react", "How to optimize React performance?", "I'm working on a large React app...")
            ),
            "author": "user1",
            "detail_url": _build_post_detail_url(1, "react"),
            "comments_url": _build_post_detail_url(1, "react", anchor="comments"),
        },
        {
            "id": 2,
            "title": "Understanding TypeScript Generics",
            "subthread": "typescript",
            "upvotes": 987,
            "comments": 54,
            "timeAgo": "4 hours ago",
            "content": "Generics can be confusing...",
            "tags": _serialize_tag_names(
                _related_tags("typescript", "Understanding TypeScript Generics", "Generics can be confusing...")
            ),
            "author": "user2",
            "detail_url": _build_post_detail_url(2, "typescript"),
            "comments_url": _build_post_detail_url(2, "typescript", anchor="comments"),
        },
    ]


def _is_question_post(post):
    if getattr(post, "is_question", False):
        return True

    title = post.title.strip().lower()
    content = post.content.strip().lower()
    question_prefixes = (
        "how ",
        "what ",
        "why ",
        "when ",
        "where ",
        "who ",
        "which ",
        "can ",
        "could ",
        "should ",
        "would ",
        "does ",
        "do ",
        "did ",
        "is ",
        "are ",
        "will ",
    )
    return "?" in title or "?" in content or title.startswith(question_prefixes)


def _sync_subthread_members(subthread):
    member_total = SubthreadMembership.objects.filter(subthread=subthread).count()
    if subthread.members != member_total:
        subthread.members = member_total
        subthread.save(update_fields=["members"])
    return member_total


def _user_joined_subthread_ids(user):
    if not user.is_authenticated:
        return []

    return list(
        SubthreadMembership.objects.filter(user=user).values_list("subthread_id", flat=True)
    )


def _user_can_manage_post(user, post):
    return user.is_authenticated and (user == post.author or user.is_superuser)


def _user_can_manage_comment(user, comment):
    return user.is_authenticated and (user == comment.author or user.is_superuser)


def _user_can_manage_subthread(user, subthread):
    return user.is_authenticated and (user == subthread.created_by or user.is_superuser)


def _log_admin_action(actor, action_type, target_type, target_display, detail="", target_url=""):
    if not actor.is_authenticated:
        return

    AdminAuditLog.objects.create(
        actor=actor,
        action_type=action_type,
        target_type=target_type,
        target_display=target_display,
        target_url=target_url,
        detail=detail,
    )


def _sidebar_context(request, exclude_subthread_id=None):
    if not request.user.is_authenticated:
        return {
            "joined_subthreads": [],
            "suggested_subthreads": [],
            "joined_subthread_names": [],
        }

    memberships = list(
        SubthreadMembership.objects.filter(user=request.user)
        .select_related("subthread")
        .order_by("-created_at")
    )
    joined_subthreads = [membership.subthread for membership in memberships[:3]]
    joined_subthread_names = [membership.subthread.name for membership in memberships]
    joined_subthread_ids = [membership.subthread_id for membership in memberships]
    suggested_subthreads = Subthread.objects.order_by("name")
    if joined_subthread_ids:
        suggested_subthreads = suggested_subthreads.exclude(id__in=joined_subthread_ids)
    if exclude_subthread_id is not None:
        suggested_subthreads = suggested_subthreads.exclude(id=exclude_subthread_id)

    return {
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": list(suggested_subthreads[:2]),
        "joined_subthread_names": joined_subthread_names,
    }


def _ensure_welcome_post(subthread):
    post, created = Post.objects.get_or_create(
        subthread=subthread,
        author=subthread.created_by,
        title=f"Welcome to d/{subthread.name}!",
        defaults={
            "content": f"First post in d/{subthread.name}.",
        },
    )
    if created or not post.tags.exists():
        _assign_post_tags(post, "")
    return post


def _post_detail_redirect(post_id, return_to_subthread=None):
    post = get_object_or_404(Post.objects.select_related("subthread"), id=post_id)
    return redirect(_build_post_detail_url(post_id, post.subthread.name, return_to_subthread=return_to_subthread))


def _vote_queryset(target):
    if isinstance(target, Post):
        return Vote.objects.filter(post=target, comment__isnull=True)
    return Vote.objects.filter(comment=target, post__isnull=True)


def _sync_vote_totals(target):
    vote_qs = _vote_queryset(target)
    target.upvotes = vote_qs.filter(vote_type="up").count() + getattr(target, "manual_upvotes", 0)
    target.downvotes = vote_qs.filter(vote_type="down").count() + getattr(target, "manual_downvotes", 0)
    target.save(update_fields=["upvotes", "downvotes"])
    _award_achievement_notifications(target)


def _achievement_notification_type(level):
    notification_type_map = {
        "beginner": Notification.TYPE_ACHIEVEMENT_BEGINNER,
        "intermediate": Notification.TYPE_ACHIEVEMENT_INTERMEDIATE,
        "advanced": Notification.TYPE_ACHIEVEMENT_ADVANCED,
    }
    return notification_type_map[level]


def _award_achievement_notifications(target):
    if getattr(target, "upvotes", 0) < ACHIEVEMENT_LEVELS[0]["threshold"]:
        return

    target_kwargs = {
        "user_id": target.author_id,
        "notification_type": "",
        "subthread_id": target.post.subthread_id if isinstance(target, Comment) else target.subthread_id,
        "post_id": target.post_id if isinstance(target, Comment) else target.id,
        "comment_id": target.id if isinstance(target, Comment) else None,
    }

    for level_config in ACHIEVEMENT_LEVELS:
        if target.upvotes < level_config["threshold"]:
            continue

        notification_type = _achievement_notification_type(level_config["level"])
        existing_notification = Notification.objects.filter(
            user_id=target.author_id,
            notification_type=notification_type,
            post_id=target_kwargs["post_id"],
            comment_id=target_kwargs["comment_id"],
        ).exists()
        if existing_notification:
            continue

        Notification.objects.create(
            user_id=target_kwargs["user_id"],
            notification_type=notification_type,
            subthread_id=target_kwargs["subthread_id"],
            post_id=target_kwargs["post_id"],
            comment_id=target_kwargs["comment_id"],
        )


def _build_comment_tree(post, user):
    comments = list(
        Comment.objects.filter(post=post)
        .select_related("author", "parent")
        .order_by("created_at")
    )
    vote_map = {}
    if user.is_authenticated and comments:
        vote_map = dict(
            Vote.objects.filter(
                user=user,
                comment_id__in=[comment.id for comment in comments],
                post__isnull=True,
            ).values_list("comment_id", "vote_type")
        )

    comment_lookup = {}
    roots = []
    for comment in comments:
        comment.children = []
        comment.current_user_vote = vote_map.get(comment.id, "")
        comment.time_ago = _time_ago(comment.created_at)
        comment.reply_count = 0
        comment.reply_count_label = "0 replies"
        comment.can_manage = _user_can_manage_comment(user, comment)
        comment.can_boost_votes = user.is_authenticated and user.is_superuser
        comment.achievement = achievement_for_upvotes(comment.upvotes)
        comment_lookup[comment.id] = comment

    for comment in comments:
        parent = comment_lookup.get(comment.parent_id)
        if parent is None:
            roots.append(comment)
        else:
            parent.children.append(comment)

    def annotate_reply_counts(node):
        descendant_count = 0
        for child in node.children:
            descendant_count += 1 + annotate_reply_counts(child)
        node.reply_count = descendant_count
        node.reply_count_label = "1 reply" if descendant_count == 1 else f"{descendant_count} replies"
        return descendant_count

    for root in roots:
        annotate_reply_counts(root)

    return roots, len(comments)


def _user_post_vote_map(user, posts):
    if not user.is_authenticated or not posts:
        return {}

    return dict(
        Vote.objects.filter(
            user=user,
            post_id__in=[post.id for post in posts],
            comment__isnull=True,
        ).values_list("post_id", "vote_type")
    )


def index(request):
    base_post_qs = (
        Post.objects.all()
        .select_related("subthread", "author")
        .prefetch_related("tags")
        .order_by("-upvotes", "-created_at")
    )
    personalized_home_feed = request.user.is_authenticated and not request.user.is_superuser
    feed_empty_title = "No posts yet."
    feed_empty_hint = ""

    if personalized_home_feed:
        joined_subthread_ids = _user_joined_subthread_ids(request.user)
        post_qs = base_post_qs.filter(subthread_id__in=joined_subthread_ids)
        if not joined_subthread_ids:
            feed_empty_title = "Join a subthread to build your home feed."
            feed_empty_hint = "Posts from subthreads you join will show up here."
        else:
            feed_empty_title = "No posts from your joined subthreads yet."
            feed_empty_hint = "When new posts land in communities you joined, they will show up here."
    else:
        post_qs = base_post_qs

    post_list = list(post_qs)
    if post_list:
        vote_map = _user_post_vote_map(request.user, post_list)
        index_url = reverse("main:index")
        posts = [
            _serialize_post(
                post,
                current_user_vote=vote_map.get(post.id, ""),
                vote_return_url=index_url,
                tag_scope_name="",
            )
            for post in post_list
        ]
    else:
        posts = _fake_posts() if not personalized_home_feed and not base_post_qs.exists() else []

    context = {
        "posts": posts,
        "personalized_home_feed": personalized_home_feed,
        "feed_empty_title": feed_empty_title,
        "feed_empty_hint": feed_empty_hint,
        "current_nav": "home",
        **_sidebar_context(request),
    }
    return render(request, "index.html", context)


def trending(request):
    return redirect("main:index")


def questions(request):
    requested_sort = request.GET.get("sort", "newest").strip().lower()
    sort_options = {
        "newest": "Newest",
        "discussed": "Most Discussed",
        "upvoted": "Most Upvoted",
        "unanswered": "Unanswered",
    }
    active_sort = requested_sort if requested_sort in sort_options else "newest"

    question_posts = list(
        Post.objects.all().select_related("subthread", "author").prefetch_related("tags")
    )
    question_posts = [post for post in question_posts if _is_question_post(post)]

    for post in question_posts:
        post.comment_total = post.comments.count()

    if active_sort == "discussed":
        question_posts.sort(key=lambda post: (post.comment_total, post.created_at), reverse=True)
    elif active_sort == "upvoted":
        question_posts.sort(key=lambda post: (post.upvotes, post.created_at), reverse=True)
    elif active_sort == "unanswered":
        question_posts = [post for post in question_posts if post.comment_total == 0]
        question_posts.sort(key=lambda post: post.created_at, reverse=True)
    else:
        question_posts.sort(key=lambda post: post.created_at, reverse=True)

    vote_map = _user_post_vote_map(request.user, question_posts)
    questions_url = request.get_full_path()
    serialized_questions = [
            _serialize_post(
                post,
                current_user_vote=vote_map.get(post.id, ""),
                vote_return_url=questions_url,
                tag_scope_name="",
            )
            for post in question_posts
    ]

    question_sort_tabs = [
        {
            "id": sort_id,
            "label": label,
            "url": _build_questions_url(sort=sort_id),
            "active": active_sort == sort_id,
        }
        for sort_id, label in sort_options.items()
    ]

    context = {
        "questions": serialized_questions,
        "question_total": len(question_posts),
        "active_question_sort": active_sort,
        "question_sort_tabs": question_sort_tabs,
        "available_subthreads": list(Subthread.objects.order_by("name")) if request.user.is_authenticated else [],
        "current_nav": "questions",
        **_sidebar_context(request),
    }
    return render(request, "questions.html", context)


@login_required
def superuser_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser access required.")

    recent_posts = list(
        Post.objects.select_related("subthread", "author")
        .prefetch_related("tags")
        .order_by("-created_at")[:6]
    )
    recent_comments = list(
        Comment.objects.select_related("author", "post", "post__subthread")
        .order_by("-created_at")[:6]
    )
    recent_subthreads = list(
        Subthread.objects.select_related("created_by").order_by("-created_at")[:6]
    )
    recent_users = list(User.objects.order_by("-date_joined")[:6])
    audit_logs = list(
        AdminAuditLog.objects.select_related("actor").order_by("-created_at")[:10]
    )

    vote_map = _user_post_vote_map(request.user, recent_posts)
    dashboard_url = reverse("main:superuser_dashboard")

    context = {
        "dashboard_posts": [
            _serialize_post(
                post,
                current_user_vote=vote_map.get(post.id, ""),
                vote_return_url=dashboard_url,
                tag_scope_name="",
            )
            for post in recent_posts
        ],
        "dashboard_comments": [
            {
                "id": comment.id,
                "content": comment.content,
                "author": comment.author.username,
                "post_title": comment.post.title,
                "subthread_name": comment.post.subthread.name,
                "created_at": comment.created_at,
                "time_ago": _time_ago(comment.created_at),
                "detail_url": _build_post_detail_url(comment.post_id, comment.post.subthread.name, anchor="comments"),
            }
            for comment in recent_comments
        ],
        "dashboard_subthreads": recent_subthreads,
        "dashboard_users": recent_users,
        "audit_logs": audit_logs,
        "stats": {
            "users": User.objects.count(),
            "subthreads": Subthread.objects.count(),
            "posts": Post.objects.count(),
            "comments": Comment.objects.count(),
            "questions": Post.objects.filter(is_question=True).count(),
            "moderation_actions": AdminAuditLog.objects.count(),
        },
        "current_nav": "superuser_dashboard",
        **_sidebar_context(request),
    }
    return render(request, "superuser_dashboard.html", context)


@login_required
@require_POST
def ask_question(request):
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    raw_tags = request.POST.get("tags", "")
    subthread_id = request.POST.get("subthread_id", "").strip()

    if not (title and content and subthread_id):
        return redirect("main:questions")

    subthread = get_object_or_404(Subthread, id=subthread_id)
    post = Post.objects.create(
        title=title,
        content=content,
        subthread=subthread,
        author=request.user,
        is_question=True,
    )
    _assign_post_tags(post, raw_tags)
    return redirect(_build_question_detail_url(post))


def search(request):
    query = request.GET.get("q", "").strip()
    scope_name = request.GET.get("scope", "").strip().lower()
    requested_tab = request.GET.get("tab", "").strip().lower()
    scope_subthread = Subthread.objects.filter(name=scope_name).first() if scope_name else None
    search_scope_name = scope_subthread.name if scope_subthread else ""
    profile_query = _normalize_profile_query(query)

    if scope_subthread:
        search_tabs_config = [("posts", "Posts")]
        default_search_tab = "posts"
    else:
        search_tabs_config = [
            ("all", "All"),
            ("posts", "Posts"),
            ("subthreads", "Subthreads"),
            ("users", "Users"),
        ]
        default_search_tab = "all"

    valid_tabs = {tab_id for tab_id, _ in search_tabs_config}
    active_search_tab = requested_tab if requested_tab in valid_tabs else default_search_tab

    post_results = []
    subthread_results = []
    profile_results = []
    post_total = 0
    subthread_total = 0
    profile_total = 0

    if query:
        if scope_subthread:
            post_qs = (
                Post.objects.filter(subthread=scope_subthread)
                .select_related("subthread", "author")
                .prefetch_related("tags")
                .filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(tags__name__icontains=query))
                .distinct()
                .order_by("-upvotes", "-created_at")
            )
        else:
            post_qs = (
                Post.objects.select_related("subthread", "author")
                .prefetch_related("tags")
                .filter(
                    Q(title__icontains=query)
                    | Q(content__icontains=query)
                    | Q(subthread__name__icontains=query)
                    | Q(tags__name__icontains=query)
                )
                .distinct()
                .order_by("-upvotes", "-created_at")
            )
            subthread_results = list(
                Subthread.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).order_by("name")
            )
            subthread_total = len(subthread_results)
            if profile_query:
                profile_results = list(
                    User.objects.filter(username__icontains=profile_query).order_by("username")
                )
                profile_total = len(profile_results)

        post_list = list(post_qs)
        post_total = len(post_list)
        vote_map = _user_post_vote_map(request.user, post_list)
        search_return_url = request.get_full_path()
        post_results = [
            _serialize_post(
                post,
                return_to_subthread=search_scope_name or None,
                current_user_vote=vote_map.get(post.id, ""),
                vote_return_url=search_return_url,
                tag_scope_name=search_scope_name,
            )
            for post in post_list
        ]

    tab_counts = {
        "all": profile_total + subthread_total + post_total,
        "posts": post_total,
        "subthreads": subthread_total,
        "users": profile_total,
    }
    search_tabs = []
    if query:
        search_tabs = [
            {
                "id": tab_id,
                "label": label,
                "count": tab_counts.get(tab_id, 0),
                "url": _build_search_url(query=query, tab=tab_id, scope_name=search_scope_name or None),
                "active": active_search_tab == tab_id,
            }
            for tab_id, label in search_tabs_config
        ]

    show_profile_results = bool(query) and not search_scope_name and active_search_tab in {"all", "users"}
    show_subthread_results = bool(query) and not search_scope_name and active_search_tab in {"all", "subthreads"}
    show_post_results = (not query) or active_search_tab in {"all", "posts"}

    context = {
        "query": query,
        "search_query": query,
        "search_scope_name": search_scope_name,
        "search_tabs": search_tabs,
        "active_search_tab": active_search_tab,
        "default_search_tab": default_search_tab,
        "post_results": post_results,
        "subthread_results": subthread_results,
        "profile_results": profile_results,
        "post_total": post_total,
        "subthread_total": subthread_total,
        "profile_total": profile_total,
        "show_profile_results": show_profile_results,
        "show_subthread_results": show_subthread_results,
        "show_post_results": show_post_results,
        **_sidebar_context(request),
    }
    return render(request, "search_results.html", context)


def post_detail(request, name, post_id):
    return_to_subthread = request.GET.get("from_subthread", "").strip()
    open_comment_modal = request.user.is_authenticated and request.GET.get("open_comment") == "1"
    if return_to_subthread and Subthread.objects.filter(name=return_to_subthread).exists():
        back_url = reverse("main:subthread_detail", kwargs={"name": return_to_subthread})
    else:
        return_to_subthread = ""
        back_url = reverse("main:index")

    try:
        post = Post.objects.select_related("subthread", "author").prefetch_related("tags").get(id=post_id)
        if post.subthread.name != name:
            return redirect(_build_post_detail_url(post.id, post.subthread.name, return_to_subthread=return_to_subthread))
        current_user_vote = ""
        if request.user.is_authenticated:
            current_user_vote = (
                Vote.objects.filter(user=request.user, post=post, comment__isnull=True)
                .values_list("vote_type", flat=True)
                .first()
                or ""
            )
        comments, total_comment_count = _build_comment_tree(post, request.user)

        post_data = {
            "id": post.id,
            "title": post.title,
            "subthread": post.subthread.name,
            "author": post.author.username,
            "upvotes": post.upvotes,
            "downvotes": post.downvotes,
            "comments": total_comment_count,
            "timeAgo": _time_ago(post.created_at),
            "content": post.content,
            "tags": _serialize_post_tags(post, scope_name=post.subthread.name),
            "achievement": achievement_for_upvotes(post.upvotes),
        }
        return render(
            request,
            "post_detail.html",
            {
                "post": post_data,
                "comments": comments,
                "back_url": back_url,
                "current_user_vote": current_user_vote,
                "return_to_subthread": return_to_subthread,
                "open_comment_modal": open_comment_modal,
                "can_manage_post": _user_can_manage_post(request.user, post),
                "can_boost_votes": request.user.is_authenticated and request.user.is_superuser,
                "search_query": request.GET.get("q", "").strip(),
            },
        )
    except Post.DoesNotExist:
        fallback_posts = {
            1: {
                "id": 1,
                "title": "How to optimize React performance?",
                "subthread": "react",
                "author": "user1",
                "timeAgo": "2 hours ago",
                "content": "Full post content here...",
                "tags": _serialize_tag_names(["react", "performance"]),
                "upvotes": 1234,
                "downvotes": 10,
                "comments": 89,
            },
            2: {
                "id": 2,
                "title": "Understanding TypeScript Generics",
                "subthread": "typescript",
                "author": "user2",
                "timeAgo": "4 hours ago",
                "content": "Full post content here...",
                "tags": _serialize_tag_names(["typescript"]),
                "upvotes": 987,
                "downvotes": 5,
                "comments": 54,
            },
        }
        post = fallback_posts.get(int(post_id))
        if post is None:
            from django.http import Http404

            raise Http404("Post not found")
        return render(
            request,
            "post_detail.html",
            {
                "post": post,
                "comments": [],
                "back_url": back_url,
                "current_user_vote": "",
                "return_to_subthread": return_to_subthread,
                "open_comment_modal": open_comment_modal,
                "can_manage_post": False,
                "can_boost_votes": False,
                "search_query": request.GET.get("q", "").strip(),
            },
        )


@login_required
@require_POST
def post_comment(request, name, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get("content")
    parent_id = request.POST.get("parent_id")
    return_to_subthread = request.POST.get("return_to_subthread", "").strip()
    if content:
        parent = get_object_or_404(Comment, id=parent_id) if parent_id else None
        Comment.objects.create(post=post, author=request.user, content=content, parent=parent)
    return _post_detail_redirect(post_id, return_to_subthread=return_to_subthread)


@login_required
@require_POST
def delete_post(request, name, post_id):
    post = get_object_or_404(Post.objects.select_related("subthread", "author"), id=post_id)
    if post.subthread.name != name:
        return redirect("main:delete_post", name=post.subthread.name, post_id=post.id)

    if not _user_can_manage_post(request.user, post):
        return HttpResponseForbidden("You can only delete your own posts.")

    next_url = request.POST.get("next", "").strip()
    return_to_subthread = request.POST.get("return_to_subthread", "").strip()

    fallback_url = reverse("main:subthread_detail", kwargs={"name": post.subthread.name})
    if return_to_subthread and Subthread.objects.filter(name=return_to_subthread).exists():
        fallback_url = reverse("main:subthread_detail", kwargs={"name": return_to_subthread})

    post_display = post.title
    post_detail_url = _build_post_detail_url(post.id, post.subthread.name, return_to_subthread=return_to_subthread or None)
    action_detail = f"d/{post.subthread.name} by u/{post.author.username}"
    post.delete()
    _log_admin_action(
        actor=request.user,
        action_type=AdminAuditLog.ACTION_POST_DELETE,
        target_type="post",
        target_display=post_display,
        target_url=post_detail_url,
        detail=action_detail,
    )

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(fallback_url)


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("post", "post__subthread", "author"), id=comment_id)
    if not _user_can_manage_comment(request.user, comment):
        return HttpResponseForbidden("You can only delete comments you manage.")

    next_url = request.POST.get("next", "").strip()
    fallback_url = _build_post_detail_url(comment.post_id, comment.post.subthread.name, anchor="comments")
    comment_display = comment.content[:80] or f"Comment {comment.id}"
    comment_detail = f"On {comment.post.title} in d/{comment.post.subthread.name} by u/{comment.author.username}"
    comment.delete()
    _log_admin_action(
        actor=request.user,
        action_type=AdminAuditLog.ACTION_COMMENT_DELETE,
        target_type="comment",
        target_display=comment_display,
        target_url=fallback_url,
        detail=comment_detail,
    )

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(fallback_url)


@login_required
@require_POST
def delete_subthread(request, name):
    subthread = get_object_or_404(Subthread.objects.select_related("created_by"), name=name)
    if not _user_can_manage_subthread(request.user, subthread):
        return HttpResponseForbidden("You can only delete subthreads you manage.")

    next_url = request.POST.get("next", "").strip()
    subthread_display = f"d/{subthread.name}"
    subthread_detail = f"Created by u/{subthread.created_by.username} with {subthread.members} members"
    subthread.delete()
    _log_admin_action(
        actor=request.user,
        action_type=AdminAuditLog.ACTION_SUBTHREAD_DELETE,
        target_type="subthread",
        target_display=subthread_display,
        detail=subthread_detail,
    )

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("main:index")


@login_required
@require_POST
def adjust_post_votes(request, post_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser access required.")

    post = get_object_or_404(Post, id=post_id)
    vote_type = request.POST.get("vote_type", "").strip()
    next_url = request.POST.get("next", "").strip()

    if vote_type == "up":
        post.manual_upvotes += 1
        post.save(update_fields=["manual_upvotes"])
    elif vote_type == "down":
        post.manual_downvotes += 1
        post.save(update_fields=["manual_downvotes"])
    else:
        return HttpResponseForbidden("Invalid vote adjustment.")

    _sync_vote_totals(post)
    _log_admin_action(
        actor=request.user,
        action_type=AdminAuditLog.ACTION_POST_VOTE_BOOST,
        target_type="post",
        target_display=post.title,
        target_url=_build_post_detail_url(post.id, post.subthread.name),
        detail=f"+1 {vote_type}vote on d/{post.subthread.name}",
    )

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(_build_post_detail_url(post.id, post.subthread.name))


@login_required
@require_POST
def adjust_comment_votes(request, comment_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser access required.")

    comment = get_object_or_404(Comment.objects.select_related("post", "post__subthread"), id=comment_id)
    vote_type = request.POST.get("vote_type", "").strip()
    next_url = request.POST.get("next", "").strip()

    if vote_type == "up":
        comment.manual_upvotes += 1
        comment.save(update_fields=["manual_upvotes"])
    elif vote_type == "down":
        comment.manual_downvotes += 1
        comment.save(update_fields=["manual_downvotes"])
    else:
        return HttpResponseForbidden("Invalid vote adjustment.")

    _sync_vote_totals(comment)
    _log_admin_action(
        actor=request.user,
        action_type=AdminAuditLog.ACTION_COMMENT_VOTE_BOOST,
        target_type="comment",
        target_display=comment.content[:80] or f"Comment {comment.id}",
        target_url=_build_post_detail_url(comment.post_id, comment.post.subthread.name, anchor="comments"),
        detail=f"+1 {vote_type}vote on comment in d/{comment.post.subthread.name}",
    )

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(_build_post_detail_url(comment.post_id, comment.post.subthread.name, anchor="comments"))


@login_required
@require_POST
def vote(request, post_id=None, comment_id=None):
    if post_id:
        obj = get_object_or_404(Post, id=post_id)
    elif comment_id:
        obj = get_object_or_404(Comment, id=comment_id)
    else:
        return JsonResponse({"error": "Invalid vote target"}, status=400)

    vote_type = request.POST.get("vote_type")
    return_to_subthread = request.POST.get("return_to_subthread", "").strip()
    next_url = request.POST.get("next", "").strip()
    if vote_type not in ["up", "down"]:
        return JsonResponse({"error": "Invalid vote type"}, status=400)

    existing_votes = list(_vote_queryset(obj).filter(user=request.user).order_by("-id"))
    vote_obj = existing_votes[0] if existing_votes else None

    if len(existing_votes) > 1:
        Vote.objects.filter(id__in=[vote.id for vote in existing_votes[1:]]).delete()

    if vote_obj:
        if vote_obj.vote_type == vote_type:
            vote_obj.delete()
        else:
            vote_obj.vote_type = vote_type
            vote_obj.save(update_fields=["vote_type"])
    else:
        Vote.objects.create(
            user=request.user,
            post=obj if isinstance(obj, Post) else None,
            comment=obj if isinstance(obj, Comment) else None,
            vote_type=vote_type,
        )

    _sync_vote_totals(obj)
    target_post_id = post_id if post_id else obj.post.id
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return _post_detail_redirect(target_post_id, return_to_subthread=return_to_subthread)


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("main:index")
        return render(request, "registration/login.html", {"error": "Invalid username or password."})
    return render(request, "registration/login.html")


def signup_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        username = request.POST["username"]
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]
        if password1 == password2:
            try:
                User.objects.create_user(username=username, email=email, password=password1)
                return render(
                    request,
                    "registration/signup.html",
                    {"success": f"Account created for {username}! Please log in."},
                )
            except IntegrityError:
                return render(request, "registration/signup.html", {"error": "Username already exists."})
        return render(request, "registration/signup.html", {"error": "Passwords do not match."})
    return render(request, "registration/signup.html")


@login_required
def profile_redirect(request):
    return redirect(_build_profile_url(request.user.username, tab=request.GET.get("tab", "").strip() or None))


def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    active_tab = request.GET.get("tab", "overview").strip().lower()
    if active_tab not in {"overview", "posts", "comments"}:
        active_tab = "overview"
    profile_preference = UserPreference.objects.filter(user=profile_user).first()

    user_posts_qs = (
        Post.objects.filter(author=profile_user)
        .select_related("subthread", "author")
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    user_comments_qs = (
        Comment.objects.filter(author=profile_user)
        .select_related("post", "post__subthread")
        .order_by("-created_at")
    )
    owned_subthreads_qs = Subthread.objects.filter(created_by=profile_user).order_by("-created_at")

    user_posts = list(user_posts_qs)
    post_vote_map = _user_post_vote_map(request.user, user_posts)
    profile_overview_url = _build_profile_url(profile_user.username, tab="overview")
    profile_posts_url = _build_profile_url(profile_user.username, tab="posts")
    profile_reputation = build_user_reputation_summary(
        profile_user,
        post_queryset=user_posts_qs,
        comment_queryset=user_comments_qs,
    )

    recent_posts = [
        _serialize_post(
            post,
            current_user_vote=post_vote_map.get(post.id, ""),
            vote_return_url=profile_overview_url,
            tag_scope_name="",
        )
        for post in user_posts[:5]
    ]
    recent_comments = [_serialize_comment(comment) for comment in user_comments_qs[:5]]
    top_posts = [
        _serialize_post(
            post,
            current_user_vote=post_vote_map.get(post.id, ""),
            vote_return_url=profile_overview_url,
            tag_scope_name="",
        )
        for post in user_posts_qs.order_by("-upvotes", "-created_at")[:3]
    ]
    all_posts = [
        _serialize_post(
            post,
            current_user_vote=post_vote_map.get(post.id, ""),
            vote_return_url=profile_posts_url,
            tag_scope_name="",
        )
        for post in user_posts
    ]
    all_comments = [_serialize_comment(comment) for comment in user_comments_qs]

    overview_items = sorted(
        [
            {
                "kind": "post",
                "created_at": post.created_at,
                "data": _serialize_post(
                    post,
                    current_user_vote=post_vote_map.get(post.id, ""),
                    vote_return_url=profile_overview_url,
                    tag_scope_name="",
                ),
            }
            for post in user_posts
        ]
        + [
            {
                "kind": "comment",
                "created_at": comment.created_at,
                "data": _serialize_comment(comment),
            }
            for comment in user_comments_qs
        ],
        key=lambda item: item["created_at"],
        reverse=True,
    )

    context = {
        "profile_user": profile_user,
        "recent_posts": recent_posts,
        "recent_comments": recent_comments,
        "top_posts": top_posts,
        "overview_items": overview_items,
        "profile_posts": all_posts,
        "profile_comments": all_comments,
        "active_tab": active_tab,
        "post_count": user_posts_qs.count(),
        "comment_count": user_comments_qs.count(),
        "subthread_count": owned_subthreads_qs.count(),
        "is_own_profile": request.user.is_authenticated and request.user == profile_user,
        "profile_photo_url": _profile_photo_url(profile_preference),
        "profile_bio": _profile_bio_text(profile_preference),
        "profile_bio_is_empty": not (profile_preference and profile_preference.bio and profile_preference.bio.strip()),
        "profile_reputation": profile_reputation,
        "owned_subthreads": list(owned_subthreads_qs.values("name", "description", "members")[:4]),
        **_sidebar_context(request),
    }
    return render(request, "profile.html", context)


def user_hover_card(request, username):
    hover_user = get_object_or_404(User, username=username)
    hover_preference = UserPreference.objects.filter(user=hover_user).first()
    hover_reputation = build_user_reputation_summary(hover_user)
    context = {
        "hover_user": hover_user,
        "hover_profile_photo_url": _profile_photo_url(hover_preference),
        "hover_profile_bio": _profile_bio_text(hover_preference),
        "hover_profile_url": _build_profile_url(hover_user.username),
        "hover_reputation": hover_reputation,
    }
    return render(request, "components/user_hover_card.html", context)


@login_required
@require_POST
def update_profile_photo(request):
    profile_photo = request.FILES.get("profile_photo")
    redirect_url = _build_profile_url(request.user.username)

    if not profile_photo:
        messages.error(request, "Choose an image before saving your profile photo.")
        return redirect(redirect_url)

    lowered_name = profile_photo.name.lower()
    valid_extension = any(lowered_name.endswith(extension) for extension in PROFILE_PHOTO_EXTENSIONS)
    if not valid_extension:
        messages.error(request, "Use a JPG, PNG, GIF, or WebP image for your profile photo.")
        return redirect(redirect_url)

    if profile_photo.size > PROFILE_PHOTO_MAX_BYTES:
        messages.error(request, "Profile photos must be 5 MB or smaller.")
        return redirect(redirect_url)

    if profile_photo.content_type and not profile_photo.content_type.startswith("image/"):
        messages.error(request, "That file does not look like an image.")
        return redirect(redirect_url)

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    previous_photo_name = preference.profile_photo.name if preference.profile_photo else ""
    preference.profile_photo = profile_photo
    preference.save(update_fields=["profile_photo"])

    if previous_photo_name and previous_photo_name != preference.profile_photo.name:
        preference.profile_photo.storage.delete(previous_photo_name)

    messages.success(request, "Profile photo updated.")
    return redirect(redirect_url)


@login_required
@require_POST
def update_profile_bio(request):
    bio = request.POST.get("bio", "").strip()
    redirect_url = _build_profile_url(request.user.username)

    if len(bio) > PROFILE_BIO_MAX_LENGTH:
        messages.error(request, f"Bio must be {PROFILE_BIO_MAX_LENGTH} characters or fewer.")
        return redirect(redirect_url)

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    preference.bio = bio
    preference.save(update_fields=["bio"])

    if bio:
        messages.success(request, "Bio updated.")
    else:
        messages.success(request, "Bio cleared. Showing \"No bio yet\" now.")
    return redirect(redirect_url)


@login_required
@require_POST
def update_display_mode(request):
    display_mode = request.POST.get("display_mode")
    if display_mode not in {"light", "dark"}:
        return JsonResponse({"error": "Invalid display mode."}, status=400)

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    preference.display_mode = display_mode
    preference.save(update_fields=["display_mode"])
    return JsonResponse({"display_mode": display_mode})


@login_required
@require_POST
def mark_notifications_read(request):
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
    updated_count = unread_notifications.update(is_read=True)
    return JsonResponse({"marked_read": updated_count})


@login_required
def logout_view(request):
    logout(request)
    return redirect("main:index")


@login_required
def create_subthread(request):
    if request.method != "POST":
        return redirect("main:index")

    name = request.POST.get("name", "").strip().lower()
    description = request.POST.get("description", "").strip()

    if not name:
        context = {"posts": [], "error": "Name is required.", **_sidebar_context(request)}
        return render(request, "index.html", context)

    subthread, created = Subthread.objects.get_or_create(
        name=name,
        defaults={"description": description, "created_by": request.user},
    )
    if created:
        _sync_subthread_members(subthread)
        _ensure_welcome_post(subthread)
        return redirect("main:subthread_detail", name=subthread.name)

    context = {
        "posts": [],
        "error": f"Subthread d/{name} already exists.",
        **_sidebar_context(request),
    }
    return render(request, "index.html", context)


def subthread_detail(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    _ensure_welcome_post(subthread)
    post_qs = Post.objects.filter(subthread=subthread).select_related("author").prefetch_related("tags")
    post_list = list(post_qs)
    vote_map = _user_post_vote_map(request.user, post_list)
    subthread_url = reverse("main:subthread_detail", kwargs={"name": subthread.name})
    posts = [
        _serialize_post(
            post,
            return_to_subthread=subthread.name,
            current_user_vote=vote_map.get(post.id, ""),
            vote_return_url=subthread_url,
            tag_scope_name=subthread.name,
        )
        for post in post_list
    ]

    sidebar_context = _sidebar_context(request, exclude_subthread_id=subthread.id)
    context = {
        "subthread": subthread,
        "posts": posts,
        "subthread_is_joined": request.user.is_authenticated and subthread.name in sidebar_context["joined_subthread_names"],
        "can_manage_subthread": _user_can_manage_subthread(request.user, subthread),
        "search_scope_name": subthread.name,
        **sidebar_context,
    }
    return render(request, "subthread_detail.html", context)


@login_required
@require_POST
def join_subthread(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    SubthreadMembership.objects.get_or_create(user=request.user, subthread=subthread)
    _sync_subthread_members(subthread)

    next_url = request.POST.get("next", "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)

    return redirect("main:subthread_detail", name=subthread.name)


@login_required
@require_POST
def leave_subthread(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    SubthreadMembership.objects.filter(user=request.user, subthread=subthread).delete()
    _sync_subthread_members(subthread)

    next_url = request.POST.get("next", "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)

    return redirect("main:subthread_detail", name=subthread.name)


@login_required
@require_POST
def create_post(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    raw_tags = request.POST.get("tags", "")

    if title and content:
        post = Post.objects.create(
            title=title,
            content=content,
            subthread=subthread,
            author=request.user,
        )
        _assign_post_tags(post, raw_tags)

    return redirect("main:subthread_detail", name=subthread.name)

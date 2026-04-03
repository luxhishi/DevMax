from urllib.parse import urlencode

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Comment, Post, Subthread, UserPreference, Vote


def _build_post_detail_url(post_id, subthread_name, return_to_subthread=None, anchor=None):
    url = reverse("main:post_detail", kwargs={"name": subthread_name, "post_id": post_id})
    if return_to_subthread:
        url = f"{url}?{urlencode({'from_subthread': return_to_subthread})}"
    if anchor:
        url = f"{url}#{anchor}"
    return url


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


def _serialize_post(post, return_to_subthread=None):
    return {
        "id": post.id,
        "title": post.title,
        "subthread": post.subthread.name,
        "upvotes": post.upvotes,
        "comments": post.comments.count(),
        "timeAgo": _time_ago(post.created_at),
        "content": post.content,
        "tags": _related_tags(post.subthread.name, post.title, post.content),
        "author": post.author.username,
        "detail_url": _build_post_detail_url(post.id, post.subthread.name, return_to_subthread=return_to_subthread),
        "comments_url": _build_post_detail_url(post.id, post.subthread.name, return_to_subthread=return_to_subthread, anchor="comments"),
    }


def _serialize_comment(comment):
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post.id,
        "post_title": comment.post.title,
        "subthread": comment.post.subthread.name,
        "timeAgo": _time_ago(comment.created_at),
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
            "tags": _related_tags("react", "How to optimize React performance?", "I'm working on a large React app..."),
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
            "tags": _related_tags("typescript", "Understanding TypeScript Generics", "Generics can be confusing..."),
            "author": "user2",
            "detail_url": _build_post_detail_url(2, "typescript"),
            "comments_url": _build_post_detail_url(2, "typescript", anchor="comments"),
        },
    ]


def _sidebar_context(request):
    if not request.user.is_authenticated:
        return {
            "joined_subthreads": [],
            "suggested_subthreads": [],
        }

    return {
        "joined_subthreads": list(
            Subthread.objects.filter(created_by=request.user).values("name", "description", "members")[:3]
        ),
        "suggested_subthreads": list(
            Subthread.objects.exclude(created_by=request.user).values("name", "description", "members")[:2]
        ),
    }


def _post_detail_redirect(post_id, return_to_subthread=None):
    post = get_object_or_404(Post.objects.select_related("subthread"), id=post_id)
    return redirect(_build_post_detail_url(post_id, post.subthread.name, return_to_subthread=return_to_subthread))


def _vote_queryset(target):
    if isinstance(target, Post):
        return Vote.objects.filter(post=target, comment__isnull=True)
    return Vote.objects.filter(comment=target, post__isnull=True)


def _sync_vote_totals(target):
    vote_qs = _vote_queryset(target)
    target.upvotes = vote_qs.filter(vote_type="up").count()
    target.downvotes = vote_qs.filter(vote_type="down").count()
    target.save(update_fields=["upvotes", "downvotes"])


def index(request):
    post_qs = Post.objects.all().select_related("subthread", "author").order_by("-upvotes", "-created_at")
    if post_qs.exists():
        posts = [_serialize_post(post) for post in post_qs]
    else:
        posts = _fake_posts()

    context = {"posts": posts, **_sidebar_context(request)}
    return render(request, "index.html", context)


def trending(request):
    return redirect("main:index")


def post_detail(request, name, post_id):
    return_to_subthread = request.GET.get("from_subthread", "").strip()
    if return_to_subthread and Subthread.objects.filter(name=return_to_subthread).exists():
        back_url = reverse("main:subthread_detail", kwargs={"name": return_to_subthread})
    else:
        return_to_subthread = ""
        back_url = reverse("main:index")

    try:
        post = Post.objects.select_related("subthread", "author").get(id=post_id)
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
        comments = list(
            Comment.objects.filter(post=post, parent=None)
            .select_related("author")
            .prefetch_related("replies__author")
        )
        comment_vote_map = {}
        if request.user.is_authenticated and comments:
            comment_ids = [comment.id for comment in comments]
            reply_ids = [reply.id for comment in comments for reply in comment.replies.all()]
            tracked_comment_ids = comment_ids + reply_ids
            if tracked_comment_ids:
                comment_vote_map = dict(
                    Vote.objects.filter(
                        user=request.user,
                        comment_id__in=tracked_comment_ids,
                        post__isnull=True,
                    ).values_list("comment_id", "vote_type")
                )

        for comment in comments:
            comment.current_user_vote = comment_vote_map.get(comment.id, "")
            comment.time_ago = _time_ago(comment.created_at)
            for reply in comment.replies.all():
                reply.current_user_vote = comment_vote_map.get(reply.id, "")
                reply.time_ago = _time_ago(reply.created_at)

        post_data = {
            "id": post.id,
            "title": post.title,
            "subthread": post.subthread.name,
            "author": post.author.username,
            "upvotes": post.upvotes,
            "downvotes": post.downvotes,
            "comments": len(comments) + sum(comment.replies.count() for comment in comments),
            "timeAgo": _time_ago(post.created_at),
            "content": post.content,
            "tags": _related_tags(post.subthread.name, post.title, post.content),
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
                "tags": ["react", "performance"],
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
                "tags": ["typescript"],
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
def vote(request, post_id=None, comment_id=None):
    if post_id:
        obj = get_object_or_404(Post, id=post_id)
    elif comment_id:
        obj = get_object_or_404(Comment, id=comment_id)
    else:
        return JsonResponse({"error": "Invalid vote target"}, status=400)

    vote_type = request.POST.get("vote_type")
    return_to_subthread = request.POST.get("return_to_subthread", "").strip()
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
def profile_view(request):
    user_posts_qs = (
        Post.objects.filter(author=request.user)
        .select_related("subthread", "author")
        .order_by("-created_at")
    )
    user_comments_qs = (
        Comment.objects.filter(author=request.user)
        .select_related("post", "post__subthread")
        .order_by("-created_at")
    )
    owned_subthreads_qs = Subthread.objects.filter(created_by=request.user).order_by("-created_at")

    recent_posts = [_serialize_post(post) for post in user_posts_qs[:5]]
    recent_comments = [_serialize_comment(comment) for comment in user_comments_qs[:5]]
    top_posts = [
        _serialize_post(post)
        for post in user_posts_qs.order_by("-upvotes", "-created_at")[:3]
    ]

    context = {
        "profile_user": request.user,
        "recent_posts": recent_posts,
        "recent_comments": recent_comments,
        "top_posts": top_posts,
        "post_count": user_posts_qs.count(),
        "comment_count": user_comments_qs.count(),
        "subthread_count": owned_subthreads_qs.count(),
        "owned_subthreads": list(owned_subthreads_qs.values("name", "description", "members")[:4]),
        **_sidebar_context(request),
    }
    return render(request, "profile.html", context)


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
        return redirect("main:subthread_detail", name=subthread.name)

    context = {
        "posts": [],
        "error": f"Subthread d/{name} already exists.",
        **_sidebar_context(request),
    }
    return render(request, "index.html", context)


def subthread_detail(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    post_qs = Post.objects.filter(subthread=subthread).select_related("author")
    posts = [_serialize_post(post, return_to_subthread=subthread.name) for post in post_qs]

    context = {
        "subthread": subthread,
        "posts": posts,
        **_sidebar_context(request),
    }
    return render(request, "subthread_detail.html", context)


@login_required
@require_POST
def create_post(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()

    if title and content:
        Post.objects.create(
            title=title,
            content=content,
            subthread=subthread,
            author=request.user,
        )

    return redirect("main:subthread_detail", name=subthread.name)

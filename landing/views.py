from django.http import Http404
from django.shortcuts import render

POSTS = [
    {
        "id": 1,
        "subthread": "python",
        "timeAgo": "2h ago",
        "title": "How to loop in Python?",
        "content": "I am struggling with for loops...",
        "tags": ["python", "loops"],
        "upvotes": 10,
        "comments": 2,
    },
    {
        "id": 2,
        "subthread": "webdev",
        "timeAgo": "5h ago",
        "title": "Best Tailwind plugins?",
        "content": "Looking for Tailwind UI plugins...",
        "tags": ["tailwind", "css"],
        "upvotes": 7,
        "comments": 1,
    },
]


def index(request):
    joined_subthreads = [
        {"name": "python", "description": "All about Python", "members": 1200},
        {"name": "webdev", "description": "Frontend & Backend", "members": 850}
    ]

    suggested_subthreads = [
        {"name": "django", "description": "Django framework", "members": 600},
        {"name": "tailwind", "description": "Tailwind CSS tips", "members": 400}
    ]

    context = {
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": suggested_subthreads,
        "posts": POSTS,
    }

    return render(request, "index.html", context)


def post_detail(request, post_id):
    try:
        post = next(p for p in POSTS if p["id"] == post_id)
    except StopIteration:
        raise Http404("Post not found")

    return render(request, "post_detail.html", {"post": post})
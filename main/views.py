from django.shortcuts import render

def index(request):
    posts = [
        {
            "title": "How to optimize React performance?",
            "subthread": "react",
            "upvotes": 1234,
            "comments": 89,
            "timeAgo": "2 hours ago",
            "content": "I'm working on a large React app...",
            "tags": ["react", "performance", "optimization"],
        },
        {
            "title": "Understanding TypeScript Generics",
            "subthread": "typescript",
            "upvotes": 987,
            "comments": 54,
            "timeAgo": "4 hours ago",
            "content": "Generics can be confusing...",
            "tags": ["typescript", "tutorial"],
        },
    ]

    joined_subthreads = [
        {"name": "react"},
        {"name": "typescript"},
        {"name": "python"},
    ]

    suggested_subthreads = [
        {"name": "rust", "description": "Rust discussions"},
        {"name": "golang", "description": "Go tips"},
    ]

    return render(request, "index.html", {
        "posts": posts,
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": suggested_subthreads,
    })

from django.shortcuts import render

def index(request):
    joined_subthreads = [
        {"name": "python", "description": "All about Python", "members": 1200},
        {"name": "webdev", "description": "Frontend & Backend", "members": 850}
    ]

    suggested_subthreads = [
        {"name": "django", "description": "Django framework", "members": 600},
        {"name": "tailwind", "description": "Tailwind CSS tips", "members": 400}
    ]

    posts = [
        {"subthread": "python", "timeAgo": "2h ago", "title": "How to loop in Python?", 
         "content": "I am struggling with for loops...", "tags": ["python", "loops"], "upvotes": 10, "comments": 2},
        {"subthread": "webdev", "timeAgo": "5h ago", "title": "Best Tailwind plugins?", 
         "content": "Looking for Tailwind UI plugins...", "tags": ["tailwind", "css"], "upvotes": 7, "comments": 1}
    ]

    context = {
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": suggested_subthreads,
        "posts": posts
    }

    return render(request, "index.html", context)
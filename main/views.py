from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError

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

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')  # Redirect to home index
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid username or password.'})
    return render(request, 'registration/login.html')

def signup_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        if password1 == password2:
            try:
                user = User.objects.create_user(username=username, email=email, password=password1)
                return render(request, 'registration/signup.html', {'success': f'Account created for {username}! Please log in.'})
            except IntegrityError:
                return render(request, 'registration/signup.html', {'error': 'Username already exists.'})
        else:
            return render(request, 'registration/signup.html', {'error': 'Passwords do not match.'})
    return render(request, 'registration/signup.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('/')

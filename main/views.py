from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import Subthread

def index(request):
    posts = [
        {
            "id": 1,
            "title": "How to optimize React performance?",
            "subthread": "react",
            "upvotes": 1234,
            "comments": 89,
            "timeAgo": "2 hours ago",
            "content": "I'm working on a large React app...",
            "tags": ["react", "performance", "optimization"],
        },
        {
            "id": 2,
            "title": "Understanding TypeScript Generics",
            "subthread": "typescript",
            "upvotes": 987,
            "comments": 54,
            "timeAgo": "4 hours ago",
            "content": "Generics can be confusing...",
            "tags": ["typescript", "tutorial"],
        },
    ]

    if request.user.is_authenticated:
        joined_subthreads = list(Subthread.objects.filter(created_by=request.user).values('name', 'description', 'members')[:3])
        suggested_subthreads = list(Subthread.objects.exclude(created_by=request.user).values('name', 'description', 'members')[:2])
    else:
        joined_subthreads = []
        suggested_subthreads = []

    return render(request, "index.html", {
        "posts": posts,
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": suggested_subthreads,
    })

def post_detail(request, post_id):
    # Fake post detail for demo
    posts = {
        1: {
            "title": "How to optimize React performance?",
            "subthread": "react",
            "timeAgo": "2 hours ago",
            "content": "Full post content here...",
            "tags": ["react", "performance"],
            "upvotes": 1234,
            "comments": 89
        },
        2: {
            "title": "Understanding TypeScript Generics",
            "subthread": "typescript",
            "timeAgo": "4 hours ago",
            "content": "Full post content here...",
            "tags": ["typescript"],
            "upvotes": 987,
            "comments": 54
        }
    }
    post = posts.get(post_id, None)
    if post is None:
        from django.http import Http404
        raise Http404("Post not found")
    return render(request, "post_detail.html", {"post": post})

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

@login_required
def create_subthread(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            subthread, created = Subthread.objects.get_or_create(
                name=name.lower(),
                defaults={'description': description, 'created_by': request.user}
            )
            if created:
                return redirect('subthread_detail', name=name.lower())
            else:
                return render(request, 'index.html', {
                    'posts': [], 'joined_subthreads': [], 'suggested_subthreads': [],
                    'error': f'Subthread d/{name} already exists.'
                })
        else:
            return render(request, 'index.html', {
                'posts': [], 'joined_subthreads': [], 'suggested_subthreads': [],
                'error': 'Name is required.'
            })
    return redirect('index')

def subthread_detail(request, name):
    try:
        subthread = Subthread.objects.get(name=name)
    except Subthread.DoesNotExist:
        from django.http import Http404
        raise Http404("Subthread not found")
    
    # Fake posts for this subthread for demo
    posts = [
        {
            "id": 3,
            "title": f"Welcome to d/{name}!",
            "subthread": name,
            "upvotes": 5,
            "comments": 1,
            "timeAgo": "just now",
            "content": f"First post in d/{name}.",
            "tags": [name],
        }
    ]
    
    joined_subthreads = list(Subthread.objects.filter(created_by=request.user).values('name', 'description', 'members')[:3]) if request.user.is_authenticated else []
    suggested_subthreads = list(Subthread.objects.exclude(created_by=request.user).values('name', 'description', 'members')[:2]) if request.user.is_authenticated else []
    return render(request, "subthread_detail.html", {
        "subthread": subthread,
        "posts": posts,
        "joined_subthreads": joined_subthreads,
        "suggested_subthreads": suggested_subthreads
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Subthread, Post, Comment, Vote

def index(request):
    posts = Post.objects.all().select_related('subthread', 'author')
    if not posts:
        # Fallback to fake data if no posts in DB
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
                "author": "user1",
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
                "author": "user2",
            },
        ]
    else:
        # Convert to dict format for template compatibility
        posts = [
            {
                "id": post.id,
                "title": post.title,
                "subthread": post.subthread.name,
                "upvotes": post.upvotes,
                "comments": post.comments.count(),
                "timeAgo": post.created_at.strftime("%H hours ago"),  # Simple time ago
                "content": post.content,
                "tags": [],  # No tags yet
                "author": post.author.username,
            }
            for post in posts
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
    try:
        post = Post.objects.select_related('subthread', 'author').get(id=post_id)
        comments = Comment.objects.filter(post=post, parent=None).select_related('author').prefetch_related('replies__author')
        post_data = {
            "id": post.id,
            "title": post.title,
            "subthread": post.subthread.name,
            "upvotes": post.upvotes,
            "downvotes": post.downvotes,
            "comments": comments.count() + sum(reply.replies.count() for comment in comments for reply in comment.replies.all()),
            "timeAgo": post.created_at.strftime("%H hours ago"),
            "content": post.content,
            "tags": [],  # No tags yet
        }
        return render(request, "post_detail.html", {"post": post_data, "comments": comments})
    except Post.DoesNotExist:
        # Fallback to fake data
        posts = {
            1: {
                "title": "How to optimize React performance?",
                "subthread": "react",
                "timeAgo": "2 hours ago",
                "content": "Full post content here...",
                "tags": ["react", "performance"],
                "upvotes": 1234,
                "downvotes": 10,
                "comments": 89
            },
            2: {
                "title": "Understanding TypeScript Generics",
                "subthread": "typescript",
                "timeAgo": "4 hours ago",
                "content": "Full post content here...",
                "tags": ["typescript"],
                "upvotes": 987,
                "downvotes": 5,
                "comments": 54
            }
        }
        post = posts.get(int(post_id), None)
        if post is None:
            from django.http import Http404
            raise Http404("Post not found")
        return render(request, "post_detail.html", {"post": post, "comments": []})
@login_required
@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content')
    parent_id = request.POST.get('parent_id')
    if content:
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id)
        Comment.objects.create(post=post, author=request.user, content=content, parent=parent)
    return redirect('post_detail', post_id=post_id)

@login_required
@require_POST
def vote(request, post_id=None, comment_id=None):
    if post_id:
        obj = get_object_or_404(Post, id=post_id)
        vote_type = request.POST.get('vote_type')
    elif comment_id:
        obj = get_object_or_404(Comment, id=comment_id)
        vote_type = request.POST.get('vote_type')
    else:
        return JsonResponse({'error': 'Invalid vote target'}, status=400)

    if vote_type not in ['up', 'down']:
        return JsonResponse({'error': 'Invalid vote type'}, status=400)

    vote_obj, created = Vote.objects.get_or_create(
        user=request.user,
        post=obj if isinstance(obj, Post) else None,
        comment=obj if isinstance(obj, Comment) else None,
        defaults={'vote_type': vote_type}
    )
    if not created:
        if vote_obj.vote_type == vote_type:
            # Remove vote if same
            vote_obj.delete()
            if isinstance(obj, Post):
                if vote_type == 'up':
                    obj.upvotes -= 1
                else:
                    obj.downvotes -= 1
            else:
                if vote_type == 'up':
                    obj.upvotes -= 1
                else:
                    obj.downvotes -= 1
        else:
            # Change vote
            if isinstance(obj, Post):
                if vote_type == 'up':
                    obj.upvotes += 1
                    obj.downvotes -= 1
                else:
                    obj.downvotes += 1
                    obj.upvotes -= 1
            else:
                if vote_type == 'up':
                    obj.upvotes += 1
                    obj.downvotes -= 1
                else:
                    obj.downvotes += 1
                    obj.upvotes -= 1
            vote_obj.vote_type = vote_type
            vote_obj.save()
    else:
        if isinstance(obj, Post):
            if vote_type == 'up':
                obj.upvotes += 1
            else:
                obj.downvotes += 1
        else:
            if vote_type == 'up':
                obj.upvotes += 1
            else:
                obj.downvotes += 1
    obj.save()
    if post_id:
        return redirect('post_detail', post_id=post_id)
    else:
        return redirect('post_detail', post_id=obj.post.id)

def logout_view(request):
    logout(request)
    return redirect('index')

def subthread_detail(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    posts = Post.objects.filter(subthread=subthread).select_related('author')
    return render(request, 'subthread_detail.html', {'subthread': subthread, 'posts': posts})

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
def create_subthread(request):
    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST.get('description', '')
        Subthread.objects.create(name=name, description=description, created_by=request.user)
        return redirect('index')
    return render(request, 'create_subthread.html')

def subthread_detail(request, name):
    subthread = get_object_or_404(Subthread, name=name)
    posts = Post.objects.filter(subthread=subthread).select_related('author')
    return render(request, 'subthread_detail.html', {'subthread': subthread, 'posts': posts})

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

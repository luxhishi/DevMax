from django.db import models
from django.contrib.auth.models import User

class Subthread(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"d/{self.name}"

    class Meta:
        ordering = ['-created_at']

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    subthread = models.ForeignKey(Subthread, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

    class Meta:
        ordering = ['created_at']

class Vote(models.Model):
    VOTE_CHOICES = (
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=4, choices=VOTE_CHOICES)

    class Meta:
        unique_together = ('user', 'post', 'comment')


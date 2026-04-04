from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.urls import reverse


class UserPreference(models.Model):
    DISPLAY_MODE_CHOICES = (
        ("light", "Light"),
        ("dark", "Dark"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preference")
    display_mode = models.CharField(max_length=5, choices=DISPLAY_MODE_CHOICES, default="light")

    def __str__(self):
        return f"Preferences for {self.user.username}"


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


class SubthreadMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subthread_memberships")
    subthread = models.ForeignKey(Subthread, on_delete=models.CASCADE, related_name="memberships")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "subthread"],
                name="unique_subthread_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} in d/{self.subthread.name}"


class Tag(models.Model):
    name = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    subthread = models.ForeignKey(Subthread, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_question = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    manual_upvotes = models.IntegerField(default=0)
    manual_downvotes = models.IntegerField(default=0)
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
    manual_upvotes = models.IntegerField(default=0)
    manual_downvotes = models.IntegerField(default=0)
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
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(post__isnull=False) & Q(comment__isnull=True))
                    | (Q(post__isnull=True) & Q(comment__isnull=False))
                ),
                name="vote_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "post"],
                condition=Q(post__isnull=False, comment__isnull=True),
                name="unique_post_vote_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "comment"],
                condition=Q(comment__isnull=False, post__isnull=True),
                name="unique_comment_vote_per_user",
            ),
        ]


class Notification(models.Model):
    TYPE_SUBTHREAD_POST = "subthread_post"
    TYPE_POST_COMMENT = "post_comment"
    TYPE_COMMENT_REPLY = "comment_reply"

    TYPE_CHOICES = (
        (TYPE_SUBTHREAD_POST, "New subthread post"),
        (TYPE_POST_COMMENT, "Comment on your post"),
        (TYPE_COMMENT_REPLY, "Reply to your comment"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="sent_notifications")
    notification_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    subthread = models.ForeignKey(Subthread, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"

    @property
    def target_url(self):
        if self.post_id:
            url = reverse("main:post_detail", kwargs={"name": self.post.subthread.name, "post_id": self.post_id})
            if self.notification_type in {self.TYPE_POST_COMMENT, self.TYPE_COMMENT_REPLY}:
                return f"{url}#comments"
            return url
        if self.subthread_id:
            return reverse("main:subthread_detail", kwargs={"name": self.subthread.name})
        return reverse("main:index")

    @property
    def message(self):
        actor_name = self.actor.username if self.actor_id else "Someone"
        if self.notification_type == self.TYPE_SUBTHREAD_POST and self.subthread_id:
            return f"{actor_name} posted in d/{self.subthread.name}"
        if self.notification_type == self.TYPE_POST_COMMENT:
            return f"{actor_name} commented on your post"
        if self.notification_type == self.TYPE_COMMENT_REPLY:
            return f"{actor_name} replied to your comment"
        return f"{actor_name} sent you a notification"

    @property
    def detail(self):
        if self.notification_type == self.TYPE_SUBTHREAD_POST and self.post_id:
            return self.post.title
        if self.comment_id:
            return self.comment.content
        if self.post_id:
            return self.post.title
        return ""


class AdminAuditLog(models.Model):
    ACTION_POST_DELETE = "post_delete"
    ACTION_COMMENT_DELETE = "comment_delete"
    ACTION_SUBTHREAD_DELETE = "subthread_delete"
    ACTION_POST_VOTE_BOOST = "post_vote_boost"
    ACTION_COMMENT_VOTE_BOOST = "comment_vote_boost"

    ACTION_CHOICES = (
        (ACTION_POST_DELETE, "Post deleted"),
        (ACTION_COMMENT_DELETE, "Comment deleted"),
        (ACTION_SUBTHREAD_DELETE, "Subthread deleted"),
        (ACTION_POST_VOTE_BOOST, "Post vote boosted"),
        (ACTION_COMMENT_VOTE_BOOST, "Comment vote boosted"),
    )

    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_audit_logs")
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=32)
    target_display = models.CharField(max_length=255)
    target_url = models.CharField(max_length=255, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_type_display()} by {self.actor.username}"


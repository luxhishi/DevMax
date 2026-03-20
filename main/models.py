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


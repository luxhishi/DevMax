from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0009_manual_vote_boosts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(choices=[("post_delete", "Post deleted"), ("comment_delete", "Comment deleted"), ("subthread_delete", "Subthread deleted"), ("post_vote_boost", "Post vote boosted"), ("comment_vote_boost", "Comment vote boosted")], max_length=32)),
                ("target_type", models.CharField(max_length=32)),
                ("target_display", models.CharField(max_length=255)),
                ("target_url", models.CharField(blank=True, max_length=255)),
                ("detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admin_audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]

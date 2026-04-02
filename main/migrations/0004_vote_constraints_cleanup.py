from django.db import migrations, models
from django.db.models import Q


def dedupe_votes_and_sync_totals(apps, schema_editor):
    Vote = apps.get_model("main", "Vote")
    Post = apps.get_model("main", "Post")
    Comment = apps.get_model("main", "Comment")

    invalid_votes = Vote.objects.filter(
        (Q(post__isnull=True) & Q(comment__isnull=True))
        | (Q(post__isnull=False) & Q(comment__isnull=False))
    )
    invalid_votes.delete()

    seen_keys = set()
    duplicate_ids = []
    for vote in Vote.objects.order_by("-id"):
        if vote.post_id is not None:
            key = ("post", vote.user_id, vote.post_id)
        elif vote.comment_id is not None:
            key = ("comment", vote.user_id, vote.comment_id)
        else:
            duplicate_ids.append(vote.id)
            continue

        if key in seen_keys:
            duplicate_ids.append(vote.id)
        else:
            seen_keys.add(key)

    if duplicate_ids:
        Vote.objects.filter(id__in=duplicate_ids).delete()

    for post in Post.objects.all():
        post_votes = Vote.objects.filter(post_id=post.id, comment__isnull=True)
        post.upvotes = post_votes.filter(vote_type="up").count()
        post.downvotes = post_votes.filter(vote_type="down").count()
        post.save(update_fields=["upvotes", "downvotes"])

    for comment in Comment.objects.all():
        comment_votes = Vote.objects.filter(comment_id=comment.id, post__isnull=True)
        comment.upvotes = comment_votes.filter(vote_type="up").count()
        comment.downvotes = comment_votes.filter(vote_type="down").count()
        comment.save(update_fields=["upvotes", "downvotes"])


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_userpreference"),
    ]

    operations = [
        migrations.RunPython(dedupe_votes_and_sync_totals, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="vote",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.CheckConstraint(
                condition=((Q(post__isnull=False) & Q(comment__isnull=True)) | (Q(post__isnull=True) & Q(comment__isnull=False))),
                name="vote_exactly_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.UniqueConstraint(
                condition=Q(comment__isnull=True, post__isnull=False),
                fields=("user", "post"),
                name="unique_post_vote_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.UniqueConstraint(
                condition=Q(comment__isnull=False, post__isnull=True),
                fields=("user", "comment"),
                name="unique_comment_vote_per_user",
            ),
        ),
    ]

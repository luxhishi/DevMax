from django.db import migrations


QUESTION_PREFIXES = (
    "how ",
    "what ",
    "why ",
    "when ",
    "where ",
    "who ",
    "which ",
    "can ",
    "could ",
    "should ",
    "would ",
    "does ",
    "do ",
    "did ",
    "is ",
    "are ",
    "will ",
)


def _looks_like_question(post):
    if getattr(post, "is_question", False):
        return True

    title = (post.title or "").strip().lower()
    content = (post.content or "").strip().lower()
    return "?" in title or "?" in content or title.startswith(QUESTION_PREFIXES)


def add_question_tag_to_question_posts(apps, schema_editor):
    Post = apps.get_model("main", "Post")
    Tag = apps.get_model("main", "Tag")

    question_tag, _ = Tag.objects.get_or_create(name="question")

    for post in Post.objects.all().iterator():
        if _looks_like_question(post):
            post.tags.add(question_tag)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0010_admin_audit_log"),
    ]

    operations = [
        migrations.RunPython(add_question_tag_to_question_posts, migrations.RunPython.noop),
    ]

from django.db import migrations, models


def infer_tags(post):
    subthread_name = post.subthread.name.lower()
    title = post.title.lower()
    content = post.content.lower()
    haystack = f"{subthread_name} {title} {content}"

    if "welcome to d/" in title:
        return [subthread_name, "welcome", "introduction"]

    keyword_map = [
        ("tailwind", ["tailwind", "css", "plugins"]),
        ("react", ["react", "performance", "optimization"]),
        ("typescript", ["typescript", "generics", "typing"]),
        ("django", ["django", "backend", "community"]),
        ("python", ["python", "loops", "basics"]),
        ("webdev", ["webdev", "frontend", "tooling"]),
        ("performance", ["performance", "profiling", "optimization"]),
        ("plugin", ["plugins", "tooling", "workflow"]),
    ]

    for keyword, tags in keyword_map:
        if keyword in haystack:
            return tags

    return [subthread_name, "discussion", "tips"]


def backfill_post_tags(apps, schema_editor):
    Post = apps.get_model("main", "Post")
    Tag = apps.get_model("main", "Tag")
    tag_cache = {}

    for post in Post.objects.select_related("subthread").all():
        tag_objects = []
        for tag_name in infer_tags(post):
            tag = tag_cache.get(tag_name)
            if tag is None:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                tag_cache[tag_name] = tag
            tag_objects.append(tag)
        post.tags.set(tag_objects)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_post_is_question"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=32, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name="post",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="posts", to="main.tag"),
        ),
        migrations.RunPython(backfill_post_tags, migrations.RunPython.noop),
    ]

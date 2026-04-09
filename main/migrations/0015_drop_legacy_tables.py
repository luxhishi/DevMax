from django.db import migrations


LEGACY_TABLES = [
    "badges",
    "comment_votes",
    "comments",
    "communities",
    "community_members",
    "follows",
    "moderation_reports",
    "notifications",
    "post_tags",
    "post_votes",
    "posts",
    "profiles",
    "saved_posts",
    "tags",
    "user_badges",
    "users",
]


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0014_post_accepted_comment"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f'DROP TABLE IF EXISTS "{table_name}" CASCADE;',
            reverse_sql=migrations.RunSQL.noop,
        )
        for table_name in LEGACY_TABLES
    ]

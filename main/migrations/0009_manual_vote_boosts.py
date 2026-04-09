from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_tag_and_post_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="manual_downvotes",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="comment",
            name="manual_upvotes",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="post",
            name="manual_downvotes",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="post",
            name="manual_upvotes",
            field=models.IntegerField(default=0),
        ),
    ]

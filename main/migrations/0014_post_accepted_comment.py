from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0013_userpreference_bio"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="accepted_comment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="accepted_for_posts",
                to="main.comment",
            ),
        ),
    ]

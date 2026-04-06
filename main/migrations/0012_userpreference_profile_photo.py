from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0011_question_tag_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreference",
            name="profile_photo",
            field=models.FileField(blank=True, upload_to="profile_photos/"),
        ),
    ]

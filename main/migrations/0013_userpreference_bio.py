from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0012_userpreference_profile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreference",
            name="bio",
            field=models.TextField(blank=True),
        ),
    ]

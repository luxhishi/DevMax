import mimetypes

from django.db import migrations, models


def backfill_profile_photos_into_database(apps, schema_editor):
    UserPreference = apps.get_model("main", "UserPreference")
    content_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    for preference in UserPreference.objects.exclude(profile_photo="").iterator():
        if preference.profile_photo_blob:
            continue

        profile_photo = preference.profile_photo
        if not profile_photo:
            continue

        try:
            with profile_photo.open("rb") as photo_file:
                photo_bytes = photo_file.read()
        except OSError:
            continue

        if not photo_bytes:
            continue

        lowered_name = profile_photo.name.lower()
        extension = f".{lowered_name.rsplit('.', 1)[-1]}" if "." in lowered_name else ""
        content_type = content_type_map.get(extension) or mimetypes.guess_type(profile_photo.name)[0] or "application/octet-stream"
        UserPreference.objects.filter(pk=preference.pk).update(
            profile_photo_blob=photo_bytes,
            profile_photo_content_type=content_type,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0015_drop_legacy_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreference",
            name="profile_photo_blob",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userpreference",
            name="profile_photo_content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(backfill_profile_photos_into_database, migrations.RunPython.noop),
    ]

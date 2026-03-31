from django.db import migrations, models


def set_existing_profile_context(apps, schema_editor):
    ChatSession = apps.get_model("chat", "ChatSession")
    ChatSession.objects.filter(target_pet__isnull=False).update(profile_context_type="pet")
    ChatSession.objects.filter(target_pet__isnull=True).update(profile_context_type="none")


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_chatmessagerecommendation"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="profile_context_type",
            field=models.CharField(
                choices=[("pet", "반려동물"), ("future", "예비집사"), ("none", "선택 안 함")],
                default="none",
                max_length=10,
            ),
        ),
        migrations.RunPython(set_existing_profile_context, migrations.RunPython.noop),
    ]

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0003_chatsession_profile_context_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatSessionMemory",
            fields=[
                (
                    "session",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="memory",
                        serialize=False,
                        to="chat.chatsession",
                    ),
                ),
                ("summary_text", models.TextField(blank=True, default="")),
                ("dialog_state", models.JSONField(blank=True, default=dict)),
                ("last_compacted_message_id", models.UUIDField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "chat_session_memory",
            },
        ),
    ]

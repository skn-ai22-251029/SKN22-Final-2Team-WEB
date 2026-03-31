from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pets", "0003_future_pet_profile_and_food_choices"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'pet' AND column_name = 'age_unknown'
                        ) THEN
                            ALTER TABLE pet ADD COLUMN age_unknown boolean NOT NULL DEFAULT FALSE;
                        END IF;
                    END
                    $$;
                    """,
                    reverse_sql="""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'pet' AND column_name = 'age_unknown'
                        ) THEN
                            ALTER TABLE pet DROP COLUMN age_unknown;
                        END IF;
                    END
                    $$;
                    """,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="pet",
                    name="age_unknown",
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]

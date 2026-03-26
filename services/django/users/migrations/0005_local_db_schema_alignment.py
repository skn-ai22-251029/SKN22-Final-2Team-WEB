from django.db import migrations, models


LOCAL_DB_ALIGNMENT_SQL = """
ALTER TABLE public.user_profile
    DROP CONSTRAINT IF EXISTS user_profile_nickname_9cd44794_uniq;
DROP INDEX IF EXISTS public.user_profile_nickname_9cd44794_like;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'user_social_auth_uid_required'
          AND conrelid = 'public.social_auth_usersocialauth'::regclass
    ) THEN
        ALTER TABLE public.social_auth_usersocialauth
            ADD CONSTRAINT user_social_auth_uid_required
            CHECK (NOT (uid::text = ''::text));
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("social_django", "0016_alter_usersocialauth_extra_data"),
        ("users", "0004_userprofile_nickname_unique"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(LOCAL_DB_ALIGNMENT_SQL, migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="userprofile",
                    name="nickname",
                    field=models.CharField(max_length=100),
                ),
            ],
        ),
    ]

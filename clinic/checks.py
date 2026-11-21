from django.conf import settings
from django.core.checks import Error, Tags, register
from django.db import DatabaseError, connection


@register(Tags.security, deploy=True)
def check_runtime_database_role(app_configs, **kwargs):
    if not getattr(settings, "REQUIRE_RESTRICTED_DB_ROLE", False):
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb
                       OR rolreplication
                       OR has_schema_privilege(current_user, 'public', 'CREATE')
                       OR EXISTS (
                           SELECT 1 FROM pg_class t
                           JOIN pg_namespace n ON n.oid = t.relnamespace
                           WHERE n.nspname = 'public'
                             AND t.relname IN (
                                 'clinic_doctor', 'clinic_patient', 'clinic_appointment'
                             )
                             AND pg_has_role(t.relowner, 'MEMBER')
                       )
                FROM pg_roles WHERE rolname = current_user
                """
            )
            unrestricted = cursor.fetchone()[0]
    except DatabaseError:
        return [Error("Не удалось проверить роль PostgreSQL.", id="clinic.E001")]

    if unrestricted:
        return [
            Error(
                "Роль Django имеет лишние полномочия PostgreSQL.",
                hint="Выполните настройку отдельной роли из docs/security.md.",
                id="clinic.E002",
            )
        ]
    return []

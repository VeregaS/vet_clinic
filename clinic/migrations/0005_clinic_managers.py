from django.db import migrations


def create_clinic_managers(apps, schema_editor):
    database = schema_editor.connection.alias
    content_types = apps.get_model("contenttypes", "ContentType").objects.using(
        database
    )
    permissions = apps.get_model("auth", "Permission").objects.using(database)
    groups = apps.get_model("auth", "Group").objects.using(database)
    doctor, _ = content_types.get_or_create(app_label="clinic", model="doctor")
    permission, _ = permissions.get_or_create(
        content_type=doctor,
        codename="manage_clinic",
        defaults={"name": "Управление клиникой"},
    )
    group, _ = groups.get_or_create(name="Администраторы клиники")
    group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("clinic", "0004_staff_history_slots"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [
        migrations.RunPython(create_clinic_managers, migrations.RunPython.noop)
    ]

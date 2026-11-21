import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("clinic", "0005_clinic_managers")]

    operations = [
        migrations.CreateModel(
            name="RequestBudget",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("client_key", models.CharField(max_length=64)),
                ("window_start", models.BigIntegerField(db_index=True)),
                ("attempts", models.PositiveIntegerField()),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("client_key", "window_start"),
                        name="clinic_budget_key_window",
                    ),
                ],
            },
        ),
        migrations.AlterField(
            model_name="appointment",
            name="complaint",
            field=models.TextField(
                blank=True,
                validators=[django.core.validators.MaxLengthValidator(2000)],
                verbose_name="Жалоба",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="diagnosis",
            field=models.TextField(
                blank=True,
                default="",
                validators=[django.core.validators.MaxLengthValidator(4000)],
                verbose_name="Диагноз",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="prescription",
            field=models.TextField(
                blank=True,
                default="",
                validators=[django.core.validators.MaxLengthValidator(4000)],
                verbose_name="Назначения / Рецепт",
            ),
        ),
    ]

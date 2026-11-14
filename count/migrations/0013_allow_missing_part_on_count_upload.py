import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("count", "0012_rename_accepted_count_countloadbatch_error_count_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tempcountloaddetail",
            name="part",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="cycles.partmaster",
            ),
        ),
    ]

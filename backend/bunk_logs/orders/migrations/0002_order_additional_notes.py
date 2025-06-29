from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='additional_notes',
            field=models.TextField(blank=True, null=True, help_text='Additional notes for this order'),
        ),
    ]

# Generated by Django 5.2.3 on 2025-07-08 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='in_progress', help_text="The current status of the order (e.g., 'in_progress', 'completed', 'cancelled').", max_length=50),
        ),
    ]

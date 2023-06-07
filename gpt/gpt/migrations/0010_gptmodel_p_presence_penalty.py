# Generated by Django 4.2.1 on 2023-06-07 13:26

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gpt', '0009_alter_gptmodel_p_temperature'),
    ]

    operations = [
        migrations.AddField(
            model_name='gptmodel',
            name='p_presence_penalty',
            field=models.FloatField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)], verbose_name='Presence penalty'),
        ),
    ]

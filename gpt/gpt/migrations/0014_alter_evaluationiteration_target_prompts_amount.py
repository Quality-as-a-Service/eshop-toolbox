# Generated by Django 4.2.1 on 2023-06-14 18:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gpt', '0013_evaluationiteration_target_prompts_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evaluationiteration',
            name='target_prompts_amount',
            field=models.BigIntegerField(default=None, null=True),
        ),
    ]
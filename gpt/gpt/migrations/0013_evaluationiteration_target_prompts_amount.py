# Generated by Django 4.2.1 on 2023-06-14 18:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gpt', '0012_alter_completition_completition_text_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluationiteration',
            name='target_prompts_amount',
            field=models.BigIntegerField(default=0),
        ),
    ]

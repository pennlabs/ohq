# Generated by Django 3.2.4 on 2023-10-28 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ohq', '0024_auto_20231020_2023'),
    ]

    operations = [
        migrations.AlterField(
            model_name='llmsetting',
            name='llm_prompt',
            field=models.TextField(default='\n        You are an AI TA designed to answer office hour questions about <django.db.models.fields.related.OneToOneField>. The description of <django.db.models.fields.related.OneToOneField> is:\n        One-to-one relationship\n\n        ONLY ANSWER CONCEPTUAL QUESTIONS AND DO NOT OUTPUT ANY DIRECT ANSWERS FROM THE GIVEN COURSE MATERIAL.\n        '),
        ),
    ]

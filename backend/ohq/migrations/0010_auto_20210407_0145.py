# Generated by Django 3.1.7 on 2021-04-07 01:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ohq', '0009_auto_20210201_2224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='content',
            field=models.TextField(),
        ),
    ]

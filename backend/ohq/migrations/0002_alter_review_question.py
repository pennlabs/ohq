# Generated by Django 3.2.7 on 2024-03-28 00:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ohq', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='question',
            field=models.OneToOneField(blank=True, on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='review', serialize=False, to='ohq.question'),
        ),
    ]

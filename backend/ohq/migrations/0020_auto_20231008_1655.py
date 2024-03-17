# Generated by Django 3.2.4 on 2023-10-08 16:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ohq', '0019_auto_20211114_1800'),
    ]

    operations = [
        migrations.CreateModel(
            name='VectorDB',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('time_updated', models.DateTimeField(auto_now=True)),
                ('top_k', models.IntegerField(blank=True, null=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ohq.course')),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('vector_db', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ohq.vectordb')),
            ],
        ),
        migrations.AddConstraint(
            model_name='vectordb',
            constraint=models.UniqueConstraint(fields=('name', 'course'), name='unique_VectorDB'),
        ),
        migrations.AddConstraint(
            model_name='document',
            constraint=models.UniqueConstraint(fields=('name',), name='unique_document'),
        ),
    ]

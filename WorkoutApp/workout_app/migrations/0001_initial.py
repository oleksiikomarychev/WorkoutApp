# Generated by Django 4.2.16 on 2025-02-09 13:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MuscleGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Progression',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.FloatField()),
                ('sets', models.IntegerField()),
                ('intensity', models.FloatField()),
                ('volume', models.IntegerField()),
                ('effort', models.CharField(choices=[('RPE', 'RPE'), ('RIR', 'RIR')], max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='ProgressionTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('weeks', models.IntegerField()),
                ('sessions_per_week', models.IntegerField()),
                ('progressions', models.ManyToManyField(related_name='templates', to='workout_app.progression')),
            ],
        ),
        migrations.CreateModel(
            name='Workout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('progression_template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='workout_app.progressiontemplate')),
            ],
        ),
        migrations.CreateModel(
            name='ExercisePool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('video_url', models.URLField(blank=True, null=True)),
                ('equipment_needed', models.CharField(blank=True, max_length=255, null=True)),
                ('muscle_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercises', to='workout_app.musclegroup')),
            ],
        ),
        migrations.CreateModel(
            name='Exercise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('sets', models.IntegerField()),
                ('reps', models.IntegerField()),
                ('weight', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('workout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercises', to='workout_app.workout')),
            ],
        ),
    ]

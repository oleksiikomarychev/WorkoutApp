from django.db import models

class Workout(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    progression_template = models.ForeignKey('ProgressionTemplate', on_delete=models.SET_NULL, null=True, blank=True)



class Exercise(models.Model):
    workout = models.ForeignKey(Workout, related_name='exercises', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sets = models.IntegerField()
    reps = models.IntegerField()
    weight = models.FloatField(blank=True, null=True)


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)


class ExercisePool(models.Model):
    muscle_group = models.ForeignKey(MuscleGroup, related_name='exercises', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    equipment_needed = models.CharField(max_length=255, blank=True, null=True)


class Progression(models.Model):
    weight = models.FloatField()  # Вес штанги
    sets = models.IntegerField()  # Количество подходов
    intensity = models.FloatField()  # % от ПМ (1RM)
    volume = models.IntegerField()  # КПШ (объем) или QBL
    effort = models.CharField(max_length=10, choices=[("RPE", "RPE"), ("RIR", "RIR")])  # Усилие

    def __str__(self):
        return f"{self.weight} кг, {self.sets}x, Int: {self.intensity}%"

class ProgressionTemplate(models.Model):
    name = models.CharField(max_length=255)
    weeks = models.IntegerField()  # Количество недель
    sessions_per_week = models.IntegerField()  # Тренировок в неделю
    progressions = models.ManyToManyField(Progression, related_name="templates")

    def __str__(self):
        return self.name
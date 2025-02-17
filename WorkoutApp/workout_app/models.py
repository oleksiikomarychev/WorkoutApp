import enum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class ExerciseList(models.Model):
    workout = models.ForeignKey('Workout', on_delete=models.CASCADE, related_name='exercise_list')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    muscle_group = models.CharField(max_length=100, blank=True, null=True)
    equipment = models.CharField(max_length=255, blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class UserMax(models.Model):
    exercise = models.ForeignKey(ExerciseList, on_delete=models.CASCADE, related_name='user_maxes')
    max_weight = models.FloatField()
    rep_max = models.IntegerField(choices=[(i, f'{i}ПМ') for i in range(1, 11)])

    def __str__(self):
        return f"{self.exercise.name}: {self.max_weight} кг на {self.rep_max}ПМ"

class EffortType(enum.Enum):
    RPE = "RPE"
    RIR = "RIR"

    @classmethod
    def choices(cls):
        return [(tag.value, tag.name) for tag in cls]

class Progression(models.Model):
    weight = models.FloatField()
    sets = models.IntegerField()
    intensity = models.FloatField()
    volume = models.IntegerField()
    effort = models.CharField(max_length=10, choices=[("RPE", "RPE"), ("RIR", "RIR")])

    def __str__(self):
        return f"{self.weight} кг, {self.sets}x, Int: {self.intensity}%"

class ProgressionTemplate(models.Model):
    user_max = models.ForeignKey(UserMax, on_delete=models.CASCADE, related_name="progression_templates")
    sets = models.PositiveIntegerField()
    intensity = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    effort = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(10)])

    def __str__(self):
        return f"{self.user_max.exercise.name} - {self.intensity}% | {self.sets}x | RPE {self.effort}"

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

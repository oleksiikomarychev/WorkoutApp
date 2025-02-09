from django.db import models

from WorkoutApp.Workout.views import ProgressionTemplate


class Workout(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    progression_template = models.ForeignKey(ProgressionTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_progression_schedule(self):
        if self.progression_template:
            return self.progression_template.generate_progression()
        return []



class Exercise(models.Model):
    workout = models.ForeignKey(Workout, related_name='exercises', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sets = models.IntegerField()
    reps = models.IntegerField()
    weight = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)


class ExercisePool(models.Model):
    muscle_group = models.ForeignKey(MuscleGroup, related_name='exercises', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    equipment_needed = models.CharField(max_length=255, blank=True, null=True)
import enum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class Workout(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    progression_template = models.ForeignKey('Progressions', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

class ExerciseList(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    muscle_group = models.CharField(max_length=100, blank=True, null=True)
    equipment = models.CharField(max_length=255, blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Exercise(models.Model):
    name = models.CharField(max_length=255)
    sets = models.IntegerField()
    reps = models.IntegerField()
    weight = models.FloatField(blank=True, null=True)

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

class Progressions(models.Model):
    user_max = models.ForeignKey(UserMax, on_delete=models.CASCADE, related_name="progressions")
    sets = models.PositiveIntegerField()
    intensity = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    effort = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    volume = models.PositiveIntegerField(editable=False)

    def __str__(self):
        return f"{self.user_max.exercise.name} - {self.intensity}% | {self.sets}x | RPE {self.effort} | Volume {self.volume} КПШ"

    def save(self, *args, **kwargs):
        self.update_volume()
        super().save(*args, **kwargs)

    def update_volume(self):
        reps = self.get_reps()
        if isinstance(reps, str):
            self.volume = 0
        else:
            self.volume = self.sets * reps

    def adjust_effort(self, new_effort):
        self.effort = new_effort
        if new_effort < self.effort:
            self.volume = int(self.volume * (new_effort / self.effort))
        self.save()

    def adjust_intensity(self, new_intensity):
        self.intensity = new_intensity
        if new_intensity < self.intensity:
            self.volume = int(self.volume * (self.intensity / new_intensity))
        self.save()

    def get_reps(self):
        rpe_table = {
            100: {10: 1},
            95: {10: 2, 9.5: "1-2", 9: 1},
            90: {10: 3, 9.5: "2-3", 9: 2, 8.5: "1-2", 8: 1},
            85: {10: 5, 9.5: "4-5", 9: 4, 8.5: "3-4", 8: 3, 7.5: "2-3", 7: 2},
            80: {10: 7, 9.5: "6-7", 9: 6, 8.5: "5-6", 8: 5, 7.5: "4-5", 7: 4, 6.5: "3-4", 6: 3},
            75: {10: 10, 9.5: "9-10", 9: 9, 8.5: "8-9", 8: 8, 7.5: "7-8", 7: 7, 6.5: "6-7", 6: 6},
            70: {10: "12+", 9.5: "11-12", 9: 11, 8.5: "10-11", 8: 10, 7.5: "9-10", 7: 9, 6.5: "8-9", 6: 8},
            65: {10: "15+", 9.5: "13-15", 9: "13-14", 8.5: "12-13", 8: 12, 7.5: "11-12", 7: 11, 6.5: "10-11", 6: 10},
            60: {10: "20+", 9.5: "18-20", 9: "17-18", 8.5: "16-17", 8: "15-16", 7.5: "14-15", 7: "13-14", 6.5: "12-13", 6: 12}
        }
        intensity_rounded = min(rpe_table.keys(), key=lambda x: abs(x - self.intensity))

        closest_effort = min(rpe_table[intensity_rounded].keys(), key=lambda x: abs(x - self.effort))
        reps = rpe_table[intensity_rounded].get(closest_effort, None)

        if reps is None:
            print(f"WARNING: No reps found for intensity {self.intensity}, effort {self.effort}")

        return reps

    def get_calculated_weight(self):
        if not self.user_max or not self.user_max.max_weight:
            return None
        return round(self.user_max.max_weight * (self.intensity / 100), 2)

class ProgressionTemplate(models.Model):
    user_max = models.ForeignKey(UserMax, on_delete=models.CASCADE, related_name="progression_templates")
    sets = models.PositiveIntegerField()
    intensity = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    volume = models.PositiveIntegerField(editable=False)
    effort = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])

    def __str__(self):
        return f"{self.user_max} кг, {self.sets}x, Int: {self.intensity}%"

    def save(self, *args, **kwargs):
        self.update_volume()
        super().save(*args, **kwargs)

    def update_volume(self):
        reps = self.get_reps()
        self.volume = self.sets * reps if isinstance(reps, int) else 0

    def get_reps(self):
        rpe_table = {
            100: {10: 1},
            95: {10: 2, 9.5: "1-2", 9: 1},
            90: {10: 3, 9.5: "2-3", 9: 2, 8.5: "1-2", 8: 1},
            85: {10: 5, 9.5: "4-5", 9: 4, 8.5: "3-4", 8: 3, 7.5: "2-3", 7: 2},
            80: {10: 7, 9.5: "6-7", 9: 6, 8.5: "5-6", 8: 5, 7.5: "4-5", 7: 4, 6.5: "3-4", 6: 3},
            75: {10: 10, 9.5: "9-10", 9: 9, 8.5: "8-9", 8: 8, 7.5: "7-8", 7: 7, 6.5: "6-7", 6: 6},
            70: {10: "12+", 9.5: "11-12", 9: 11, 8.5: "10-11", 8: 10, 7.5: "9-10", 7: 9, 6.5: "8-9", 6: 8},
            65: {10: "15+", 9.5: "13-15", 9: "13-14", 8.5: "12-13", 8: 12, 7.5: "11-12", 7: 11, 6.5: "10-11", 6: 10},
            60: {10: "20+", 9.5: "18-20", 9: "17-18", 8.5: "16-17", 8: "15-16", 7.5: "14-15", 7: "13-14", 6.5: "12-13", 6: 12}
        }

        intensity_rounded = min(rpe_table.keys(), key=lambda x: abs(x - self.intensity))
        return rpe_table.get(intensity_rounded, {}).get(self.effort, "—")

class MuscleGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

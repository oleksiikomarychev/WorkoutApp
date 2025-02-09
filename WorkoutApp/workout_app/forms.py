from django import forms
from WorkoutApp.workout_app.models import Workout, Exercise

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['name', 'description']

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['name', 'sets', 'reps', 'weight']

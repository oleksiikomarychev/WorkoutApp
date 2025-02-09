from rest_framework import serializers
from WorkoutApp.workout_app.models import Workout, Exercise
from .models import Progression, ProgressionTemplate


class ExerciseSerializer(serializers.ModelSerializer):
    workout_id = serializers.PrimaryKeyRelatedField(
        queryset=Workout.objects.all(), source="workout", write_only=True  # ✅
    )

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'sets', 'reps', 'weight', 'workout_id']  # ✅ `workout_id` в JSON

class WorkoutSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = Workout
        fields = ['id', 'name', 'description', 'exercises']


class ProgressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Progression
        fields = ["weight", "sets", "intensity", "volume", "effort"]

class ProgressionTemplateSerializer(serializers.ModelSerializer):
    progressions = ProgressionSerializer(many=True)  # Вложенные прогрессии

    class Meta:
        model = ProgressionTemplate
        fields = ["name", "weeks", "sessions_per_week", "progressions"]

    def create(self, validated_data):
        progressions_data = validated_data.pop("progressions")
        template = ProgressionTemplate.objects.create(**validated_data)

        for progression_data in progressions_data:
            Progression.objects.create(template=template, **progression_data)

        return template

from rest_framework import serializers
from WorkoutApp.workout_app.models import Workout, Exercise, ExerciseList
from .models import Progression, ProgressionTemplate, UserMax

class ExerciseSerializer(serializers.ModelSerializer):
    workout_id = serializers.PrimaryKeyRelatedField(
        queryset=Workout.objects.all(), source="workout", write_only=True
    )

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'sets', 'reps', 'weight', 'workout_id']

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
    user_max = serializers.PrimaryKeyRelatedField(queryset=UserMax.objects.all(), write_only=True)
    user_max_display = serializers.SerializerMethodField()

    class Meta:
        model = ProgressionTemplate
        fields = ["id", "user_max", "user_max_display", "sets", "intensity", "effort"]

    def get_user_max_display(self, obj):
        return f"{obj.user_max.exercise.name}: {obj.user_max.max_weight} кг на {obj.user_max.rep_max}ПМ"


    def create(self, validated_data):
        progressions_data = validated_data.pop("progressions", [])  # Указываем [] как значение по умолчанию
        template = ProgressionTemplate.objects.create(**validated_data)

        if progressions_data:  # Проверяем, что список не пуст
            for progression_data in progressions_data:
                Progression.objects.create(template=template, **progression_data)

        return template

class UserMaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMax
        fields = ['id', 'exercise', 'max_weight', 'rep_max']

class ExerciseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseList
        fields = ['id', 'workout', 'name', 'description', 'muscle_group', 'equipment', 'video_url']


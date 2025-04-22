from rest_framework import serializers
from WorkoutApp.workout_app.models import Workout, Exercise, ExerciseList, ProgressionTemplate
from .models import Progressions, UserMax

class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = ['id', 'name', 'description', 'progression_template']

class ExerciseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseList
        fields = ['id', 'name', 'description', 'muscle_group', 'equipment', 'video_url']

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ['id', 'name', 'sets', 'reps', 'weight']

class ProgressionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressionTemplate
        fields = ['id', 'user_max', 'sets', 'intensity', 'volume', 'effort']

    def create(self, validated_data):
        template = ProgressionTemplate(**validated_data)
        template.save()
        return template

    def update(self, instance, validated_data):
        instance.sets = validated_data.get('sets', instance.sets)
        instance.intensity = validated_data.get('intensity', instance.intensity)
        instance.effort = validated_data.get('effort', instance.effort)
        instance.save()
        return instance

class ProgressionsSerializer(serializers.ModelSerializer):
    user_max = serializers.PrimaryKeyRelatedField(queryset=UserMax.objects.all(), write_only=True)
    user_max_display = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField(read_only=True)
    calculated_weight = serializers.SerializerMethodField()

    class Meta:
        model = Progressions
        fields = ["id", "user_max", "user_max_display", "sets", "intensity", "effort", "reps", "volume", "calculated_weight"]

    def get_user_max_display(self, obj):
        if isinstance(obj.user_max, UserMax):
            return f"{obj.user_max.exercise.name}: {obj.user_max.max_weight} кг на {obj.user_max.rep_max} ПМ"
        return "Нет данных"

    def get_reps(self, obj):
        reps = obj.get_reps()
        return reps if reps is not None else "N/A"

    def get_calculated_weight(self, obj):
        weight = obj.get_calculated_weight()
        return weight if weight is not None else "N/A"

    def create(self, validated_data):
        progressions_data = validated_data.pop("progressions", [])
        template = Progressions.objects.create(**validated_data)

        if progressions_data:
            for progression_data in progressions_data:
                Progressions.objects.create(template=template, **progression_data)

        return template

class UserMaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMax
        fields = '__all__'


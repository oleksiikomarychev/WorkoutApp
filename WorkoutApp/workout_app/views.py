from .models import Progression, ProgressionTemplate
from .serializers import ProgressionSerializer, ProgressionTemplateSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from WorkoutApp.workout_app.models import Workout, Exercise
from WorkoutApp.workout_app.serializers import WorkoutSerializer, ExerciseSerializer
from rest_framework import status

class WorkoutViewSet(viewsets.ModelViewSet):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer

    @action(detail=True, methods=['post'])
    def add_exercise(self, request, pk=None):
        workout = self.get_object()
        serializer = ExerciseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workout=workout)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer

    def create(self, request, *args, **kwargs):
        workout_id = request.data.get("workout_id")  # ✅ Проверяем, передан ли workout_id
        if not workout_id:
            return Response({"error": "workout_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            workout = Workout.objects.get(id=workout_id)
        except Workout.DoesNotExist:
            return Response({"error": "Workout not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workout=workout)  # ✅ Указываем workout перед сохранением
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ProgressionViewSet(viewsets.ModelViewSet):
    queryset = Progression.objects.all()
    serializer_class = ProgressionSerializer

class ProgressionTemplateViewSet(viewsets.ModelViewSet):
    queryset = ProgressionTemplate.objects.all()
    serializer_class = ProgressionTemplateSerializer




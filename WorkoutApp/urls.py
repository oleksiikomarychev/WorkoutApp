from rest_framework.routers import DefaultRouter
from django.urls import path, include
from WorkoutApp.Workout.views import WorkoutViewSet, ExerciseViewSet

router = DefaultRouter()
router.register(r'workouts', WorkoutViewSet)
router.register(r'exercises', ExerciseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

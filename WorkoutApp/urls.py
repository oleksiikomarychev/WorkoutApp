from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from WorkoutApp.workout_app.views import WorkoutViewSet, ExerciseViewSet, ProgressionViewSet, ProgressionTemplateViewSet

schema_view = get_schema_view(
   openapi.Info(
      title="WorkoutApp API",
      default_version='v1',
      description="API для работы с тренировками и упражнениями",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@workoutapp.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r'workouts', WorkoutViewSet)
router.register(r'exercises', ExerciseViewSet)
router.register(r'progressions', ProgressionViewSet)
router.register(r'progression-templates', ProgressionTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

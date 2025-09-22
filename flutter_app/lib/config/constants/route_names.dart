/// App route names
/// 
/// This file contains all the route names used in the app.
/// It's recommended to use these constants instead of hardcoding route names.
class RouteNames {
  // Main app routes
  static const String home = '/home';
  static const String dashboard = '/dashboard';
  static const String debug = '/debug';
  static const String profile = '/profile';
  
  // Workout routes
  static const String workouts = '/workouts';
  static const String workoutDetail = '/workouts/:id';
  static const String createWorkout = '/workouts/create';
  static const String editWorkout = '/workouts/:id/edit';
  
  // Exercise routes
  static const String exercises = '/exercises';
  static const String exerciseDetail = '/exercises/:id';
  static const String createExercise = '/exercises/create';
  static const String editExercise = '/exercises/:id/edit';
  
  // User max routes
  static const String userMaxes = '/user-maxes';
  static const String userMaxDetail = '/user-maxes/:id';
  static const String createUserMax = '/user-maxes/create';
  static const String editUserMax = '/user-maxes/:id/edit';
  
  // Progression template routes
  static const String progressions = '/progressions';
  static const String progressionDetail = '/progressions/:id';
  static const String createProgression = '/progressions/create';
  static const String editProgression = '/progressions/:id/edit';
  
  // Calendar plan routes
  static const String calendarPlans = '/calendar-plans';
  static const String calendarPlanDetail = '/calendar-plans/:id';
  static const String createCalendarPlan = '/calendar-plans/create';
  static const String editCalendarPlan = '/calendar-plans/:id/edit';
  
  // Applied calendar plan routes
  static const String appliedCalendarPlans = '/applied-calendar-plans';
  static const String appliedCalendarPlanDetail = '/applied-calendar-plans/:id';
  
  // Settings routes
  static const String settings = '/settings';
  static const String notifications = '/notifications';
  static const String about = '/about';
  
  // Utility routes
  static const String notFound = '/not-found';
  static const String maintenance = '/maintenance';
  static const String error = '/error';
  
  /// Helper method to generate route with parameters
  static String generateRouteWithParams(String route, Map<String, dynamic> params) {
    String generatedRoute = route;
    
    params.forEach((key, value) {
      generatedRoute = generatedRoute.replaceAll(':$key', value.toString());
    });
    
    return generatedRoute;
  }
}

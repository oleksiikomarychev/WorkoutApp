



class RouteNames {

  static const String home = '/home';
  static const String dashboard = '/dashboard';
  static const String debug = '/debug';
  static const String profile = '/profile';


  static const String workouts = '/workouts';
  static const String workoutDetail = '/workouts/:id';
  static const String createWorkout = '/workouts/create';
  static const String editWorkout = '/workouts/:id/edit';


  static const String exercises = '/exercises';
  static const String exerciseDetail = '/exercises/:id';
  static const String createExercise = '/exercises/create';
  static const String editExercise = '/exercises/:id/edit';


  static const String userMaxes = '/user-maxes';
  static const String userMaxDetail = '/user-maxes/:id';
  static const String createUserMax = '/user-maxes/create';
  static const String editUserMax = '/user-maxes/:id/edit';


  static const String progressions = '/progressions';
  static const String progressionDetail = '/progressions/:id';
  static const String createProgression = '/progressions/create';
  static const String editProgression = '/progressions/:id/edit';


  static const String calendarPlans = '/calendar-plans';
  static const String calendarPlanDetail = '/calendar-plans/:id';
  static const String createCalendarPlan = '/calendar-plans/create';
  static const String editCalendarPlan = '/calendar-plans/:id/edit';


  static const String appliedCalendarPlans = '/applied-calendar-plans';
  static const String appliedCalendarPlanDetail = '/applied-calendar-plans/:id';


  static const String settings = '/settings';
  static const String notifications = '/notifications';
  static const String about = '/about';


  static const String coachDashboard = '/coach/dashboard';
  static const String coachAthletes = '/coach/athletes';
  static const String coachAthleteDetail = '/coach/athletes/detail';
  static const String coachRelationships = '/coach/relationships';
  static const String coachChat = '/coach/chat';
  static const String myCoaches = '/coaching/my-coaches';


  static const String socialFeed = '/social/feed';


  static const String notFound = '/not-found';
  static const String maintenance = '/maintenance';
  static const String error = '/error';


  static String generateRouteWithParams(String route, Map<String, dynamic> params) {
    String generatedRoute = route;

    params.forEach((key, value) {
      generatedRoute = generatedRoute.replaceAll(':$key', value.toString());
    });

    return generatedRoute;
  }
}

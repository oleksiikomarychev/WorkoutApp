import 'package:flutter/material.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../models/calendar_plan.dart';
import '../models/exercise_definition.dart';
import '../models/macro.dart';
import '../models/microcycle.dart';
import '../models/plan_schedule.dart';
import '../models/workout_session.dart';
import 'active_plan_screen.dart';
import 'analytics_screen.dart';
import 'calendar_plan_create.dart';
import 'calendar_plan_detail.dart';
import 'calendar_plans_screen.dart';
import 'chat_screen.dart';
import 'exercise_form_screen.dart';
import 'exercise_list_screen.dart';
import 'exercise_selection_screen.dart';
import 'exercises_screen.dart';
import 'home_screen_new.dart';
import 'macros/macro_editor_screen.dart';
import 'macros/macros_list_screen.dart';
import 'macros/macros_preview_screen.dart';
import 'plan_editor_screen.dart';
import 'plan_microcycle_editor.dart';
import 'progression_detail_screen.dart';
import 'session_history_screen.dart';
import 'session_log_screen.dart';
import 'splash_screen_new.dart';
import 'user_max_screen.dart';
import 'user_profile_screen.dart';
import 'all_users_screen.dart';
import 'workout_detail_screen.dart';
import 'workout_list_screen.dart';
import 'workout_session_history_screen.dart';
import 'workouts_screen.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/coach/coach_athletes_screen.dart';

class DebugScreen extends StatelessWidget {
  const DebugScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final Map<String, WidgetBuilder> screens = {
      'Active Plan': (context) => const ActivePlanScreen(),
      'Analytics': (context) => const AnalyticsScreen(),
      'Calendar Plan Create': (context) => const CalendarPlanCreate(),
      'Calendar Plan Detail (stub)': (context) => CalendarPlanDetail(plan: _stubCalendarPlan()),
      'Calendar Plans': (context) => const CalendarPlansScreen(),
      'Chat Screen (embedded)': (context) => const ChatScreen(embedded: true),
      'Exercise Selection': (context) => ExerciseSelectionScreen(),
      'Exercise Form (stub)': (context) => ExerciseFormScreen(exercise: _stubExerciseDefinition(), workoutId: 0),
      'Workout Detail': (context) => WorkoutDetailScreen(workoutId: 2000),
      'Workouts': (context) => WorkoutsScreen(),
      'Workout List': (context) => WorkoutListScreen(progressionId: 1),
      'Exercise List': (context) => ExerciseListScreen(),
      'Exercises Screen': (context) => const ExercisesScreen(),
      'Home Screen': (context) => const HomeScreenNew(),
      'Macro Editor': (context) => MacroEditorScreen(initial: _stubPlanMacro(), calendarPlanId: 1),
      'Macros List': (context) => const MacrosListScreen(calendarPlanId: 1),
      'Macros Preview': (context) => const MacrosPreviewScreen(appliedPlanId: 1),
      'Plan Editor (stub)': (context) => PlanEditorScreen(plan: _stubCalendarPlan()),
      'Plan Microcycle Editor (stub)': (context) => PlanMicrocycleEditor(microcycle: _stubMicrocycle()),
      'Progression Detail (stub)': (context) => const ProgressionDetailScreen(templateId: 1),
      'User Maxes': (context) => const UserMaxScreen(),
      'Session History': (context) => const SessionHistoryScreen(),
      'Session Log': (context) => SessionLogScreen(session: _stubWorkoutSession()),
      'Splash Screen': (context) => const SplashScreenNew(),
      'User Profile': (context) => const UserProfileScreen(),
      'All Users (list)': (context) => const AllUsersScreen(),
      'Workout Session History': (context) => const WorkoutSessionHistoryScreen(workoutId: 1),
      'Coach Dashboard (CRM)': (context) => const CoachDashboardScreen(),
      'Coach Athletes (CRM)': (context) => const CoachAthletesScreen(),
    };

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Debug Screen',
            onTitleTap: openChat,
          ),
          body: ListView(
        children: [
          ListTile(
            title: const Text('Reset app state'),
            onTap: () {},
          ),
          ListTile(
            title: const Text('Clear cache'),
            onTap: () {},
          ),
          ...screens.entries.map((entry) {
            return ListTile(
              title: Text(entry.key),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: entry.value)),
            );
          }),
        ],
      ),
    );
      },
    );
  }

CalendarPlan _stubCalendarPlan() {
  return CalendarPlan(
    id: 0,
    name: 'Sample Plan',
    schedule: const {},
    durationWeeks: 0,
    mesocycles: const [],
  );
}

ExerciseDefinition _stubExerciseDefinition() {
  return const ExerciseDefinition(
    id: 0,
    name: 'Sample Exercise',
    muscleGroup: 'Chest',
    equipment: 'Barbell',
  );
}

PlanMacro _stubPlanMacro() {
  return PlanMacro(
    calendarPlanId: 1,
    name: 'Sample Macro',
    isActive: true,
    priority: 100,
    rule: MacroRule.empty(),
  );
}

Microcycle _stubMicrocycle() {
  return const Microcycle(
    id: 0,
    mesocycleId: 0,
    name: 'Sample Microcycle',
    orderIndex: 0,
    schedule: <String, List<ExerciseScheduleItemDto>>{},
    daysCount: 7,
  );
}

WorkoutSession _stubWorkoutSession() {
  final now = DateTime.now();
  return WorkoutSession(
    id: 0,
    workoutId: 0,
    startedAt: now,
    finishedAt: now,
    status: 'completed',
    durationSeconds: 0,
    progress: const {},
  );
}
}

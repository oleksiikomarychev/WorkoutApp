import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/floating_header_bar.dart';
import 'package:workout_app/services/chat_service.dart';

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
import 'coach_athlete_plan_screen.dart';
import 'coaching/my_coaches_screen.dart';
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
import 'public_user_profile_screen.dart';
import 'session_history_screen.dart';
import 'session_log_screen.dart';
import 'social/social_feed_screen.dart';
import 'splash_screen_new.dart';
import 'user_max_screen.dart';
import 'user_profile_screen.dart';
import 'all_users_screen.dart';
import 'workout_detail_screen.dart';
import 'workout_list_screen.dart';
import 'workout_session_history_screen.dart';
import 'workouts_screen.dart';
import 'nutrition_plan_active.dart';
import 'nutrition_plans_list.dart';
import 'nutrition_plan_detail.dart';
import 'nutrition_plan_create.dart';
import 'package:workout_app/screens/coach/athlete_detail_screen.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/coach/coach_athletes_screen.dart';
import 'package:workout_app/screens/coach/coach_relationships_screen.dart';

class DebugScreen extends StatelessWidget {
  const DebugScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final Map<String, WidgetBuilder> screens = {
      'Active Plan': (context) => const ActivePlanScreen(),
      'Analytics': (context) => const AnalyticsScreen(),
      'Calendar Plan Create': (context) => const CalendarPlanCreate(),
      'Calendar Plan Detail (stub)': (context) =>
          CalendarPlanDetail(plan: _stubCalendarPlan()),
      'Calendar Plans': (context) => const CalendarPlansScreen(),
      'Chat Screen (embedded)': (context) => const ChatScreen(embedded: true),
      'Exercise Selection': (context) => ExerciseSelectionScreen(),
      'Exercise Form (stub)': (context) =>
          ExerciseFormScreen(exercise: _stubExerciseDefinition(), workoutId: 0),
      'Workout Detail': (context) => WorkoutDetailScreen(workoutId: 2000),
      'Workouts': (context) => WorkoutsScreen(),
      'Workout List': (context) => WorkoutListScreen(progressionId: 1),
      'Exercise List': (context) => ExerciseListScreen(),
      'Exercises Screen': (context) => const ExercisesScreen(),
      'Home Screen': (context) => const HomeScreenNew(),
      'Macro Editor': (context) =>
          MacroEditorScreen(initial: _stubPlanMacro(), calendarPlanId: 1),
      'Macros List': (context) => const MacrosListScreen(calendarPlanId: 1),
      'Macros Preview': (context) =>
          const MacrosPreviewScreen(appliedPlanId: 1),
      'Plan Editor (stub)': (context) =>
          PlanEditorScreen(plan: _stubCalendarPlan()),
      'Plan Microcycle Editor (stub)': (context) =>
          PlanMicrocycleEditor(microcycle: _stubMicrocycle()),
      'Progression Detail (stub)': (context) =>
          const ProgressionDetailScreen(templateId: 1),
      'User Maxes': (context) => const UserMaxScreen(),
      'Session History': (context) => const SessionHistoryScreen(),
      'Session Log': (context) =>
          SessionLogScreen(session: _stubWorkoutSession()),
      'Splash Screen': (context) => const SplashScreenNew(),
      'User Profile': (context) => const UserProfileScreen(),
      'All Users (list)': (context) => const AllUsersScreen(),
      'Workout Session History': (context) =>
          const WorkoutSessionHistoryScreen(workoutId: 1),
      'Coach Dashboard (CRM)': (context) => const CoachDashboardScreen(),
      'Coach Athletes (CRM)': (context) => const CoachAthletesScreen(),
      'Nutrition Plan Active': (context) => const NutritionPlanActive(),
      'Nutrition Plans List': (context) => const NutritionPlansList(),
      'Nutrition Plan Detail': (context) =>
          const NutritionPlanDetail(sessionData: {}),
      'Nutrition Plan Create': (context) => const NutritionPlanCreate(),
      ..._coachAndSocialScreens(),
    };

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          body: SafeArea(
            child: Stack(
              children: [
                ListView(
                  padding: const EdgeInsets.fromLTRB(16, 104, 16, 16),
                  children: [
                    ListTile(
                      title: const Text('Reset app state'),
                      onTap: () {},
                    ),
                    ListTile(title: const Text('Clear cache'), onTap: () {}),
                    const Divider(),
                    ...screens.entries.map((entry) {
                      return ListTile(
                        title: Text(entry.key),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: entry.value),
                        ),
                      );
                    }),
                  ],
                ),
                Align(
                  alignment: Alignment.topCenter,
                  child: FloatingHeaderBar(
                    title: 'Debug Screen',
                    onTitleTap: openChat,
                    actions: [_buildOverflowMenu(context)],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildOverflowMenu(BuildContext context) {
    return PopupMenuButton<String>(
      icon: const Icon(Icons.more_vert),
      onSelected: (value) {
        if (value == 'logout') {
          _handleLogout(context);
        }
      },
      itemBuilder: (context) => const [
        PopupMenuItem(value: 'logout', child: Text('Log out')),
      ],
    );
  }

  Future<void> _handleLogout(BuildContext context) async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Выйти из аккаунта?'),
        content: const Text('Вы уверены, что хотите выйти?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Выйти'),
          ),
        ],
      ),
    );

    if (shouldLogout != true || !context.mounted) return;

    try {
      try {
        final chat = pv.Provider.of<ChatService>(context, listen: false);
        await chat.disconnect();
      } catch (_) {}
      await FirebaseAuth.instance.signOut();
      try {
        await GoogleSignIn(
          clientId:
              '282810209663-u4upa0psrlsd24ls422na68n1gcmlllb.apps.googleusercontent.com',
        ).signOut();
      } catch (_) {}
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Ошибка при выходе: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Map<String, WidgetBuilder> _coachAndSocialScreens() {
    return {
      'Coach Chat (stub)': (context) => CoachChatScreen(
        args: CoachChatScreenArgs(
          channelId: 'debug-channel',
          title: 'Debug Coach Chat',
        ),
      ),
      'Coach Relationships': (context) => const CoachRelationshipsScreen(),
      'Coach Athlete Detail (stub)': (context) =>
          const AthleteDetailScreen(athleteId: 'debug-athlete'),
      'Coach Athlete Plan (stub)': (context) => const CoachAthletePlanScreen(
        athleteId: 'debug-athlete',
        athleteName: 'Debug Athlete',
      ),
      'My Coaches': (context) => const MyCoachesScreen(),
      'Social Feed': (context) => const SocialFeedScreen(),
      'Public User Profile (stub)': (context) => const PublicUserProfileScreen(
        userId: 'debug-user',
        initialName: 'Debug User',
      ),
    };
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

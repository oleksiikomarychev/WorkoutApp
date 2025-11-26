import 'package:intl/intl.dart';

import '../constants/profile_constants.dart';
import '../models/workout_session.dart';

class DayActivity {
  final int sessionCount;
  final double volume;

  const DayActivity({required this.sessionCount, required this.volume});
}

class UserStats {
  final int totalWorkouts;
  final double totalVolume;
  final int activeDays;
  final Map<DateTime, DayActivity> activityMap;
  final List<WorkoutSession> completedSessions;
  final double maxDayVolume;
  final int weeks;

  const UserStats({
    required this.totalWorkouts,
    required this.totalVolume,
    required this.activeDays,
    required this.activityMap,
    required this.completedSessions,
    required this.maxDayVolume,
    required this.weeks,
  });

  factory UserStats.fromAggregates(
    Map<String, dynamic> data, {
    int weeks = kProfileActivityWeeks,
    int sessionLimit = kProfileCompletedSessionsLimit,
  }) {
    final totalWorkouts = (data['total_workouts'] ?? 0) as int;
    final totalVolume = (data['total_volume'] ?? 0).toDouble();
    final activeDays = (data['active_days'] ?? 0) as int;
    final maxDayVolume = (data['max_day_volume'] ?? 0).toDouble();
    final weeksValue = (data['weeks'] ?? weeks) as int;

    final activityRaw = data['activity_map'] as Map<String, dynamic>? ?? const {};
    final activityMap = <DateTime, DayActivity>{};
    activityRaw.forEach((key, value) {
      if (value is Map) {
        try {
          final dt = DateTime.parse(key);
          final day = DateTime(dt.year, dt.month, dt.day);
          final sc = (value['session_count'] ?? 0) as int;
          final vol = (value['volume'] ?? 0).toDouble();
          activityMap[day] = DayActivity(sessionCount: sc, volume: vol);
        } catch (_) {}
      }
    });

    final sessionsRaw = data['completed_sessions'] as List<dynamic>? ?? const [];
    final completedSessions = <WorkoutSession>[];
    for (final item in sessionsRaw.take(sessionLimit)) {
      if (item is Map<String, dynamic>) {
        try {
          completedSessions.add(WorkoutSession.fromJson(item));
        } catch (_) {}
      }
    }

    return UserStats(
      totalWorkouts: totalWorkouts,
      totalVolume: totalVolume,
      activeDays: activeDays,
      activityMap: activityMap,
      completedSessions: completedSessions,
      maxDayVolume: maxDayVolume,
      weeks: weeksValue,
    );
  }
}

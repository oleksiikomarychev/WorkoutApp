import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/workout_session.dart';
import '../services/service_locator.dart' as sl;

final publicCompletedSessionsProvider = FutureProvider.family<List<WorkoutSession>, String>((ref, userId) async {
  final svc = ref.watch(sl.analyticsServiceProvider);
  final data = await svc.getProfileAggregates(userId: userId);
  final sessionsRaw = data['completed_sessions'] as List<dynamic>? ?? const [];
  final sessions = <WorkoutSession>[];
  for (final item in sessionsRaw) {
    if (item is Map<String, dynamic>) {
      try {
        sessions.add(WorkoutSession.fromJson(item));
      } catch (_) {}
    }
  }
  sessions.sort((a, b) => b.startedAt.compareTo(a.startedAt));
  return sessions.take(20).toList();
});

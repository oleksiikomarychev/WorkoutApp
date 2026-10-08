import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/models/user_profile.dart';
import 'package:workout_app/models/user_summary.dart';
import 'package:workout_app/models/coach_review.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/providers/app_locale_provider.dart';
import 'package:workout_app/services/workout_session_service.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/models/user_stats.dart';
import 'package:workout_app/constants/profile_constants.dart';


final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});


final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutSessionService(apiClient);
});

final sessionsHistorySWRProvider = StreamProvider.family<List<WorkoutSession>, int>((ref, workoutId) {
  final svc = ref.watch(workoutSessionServiceProvider);
  return svc.listSessionsSWR(workoutId);
});

final allSessionsHistorySWRProvider = StreamProvider<List<WorkoutSession>>((ref) {
  final svc = ref.watch(workoutSessionServiceProvider);
  return svc.listAllSessionsSWR();
});

final completedSessionsProviderFamily = FutureProvider.family<List<WorkoutSession>, int?>((ref, workoutId) async {
  final svc = ref.watch(workoutSessionServiceProvider);
  final items = workoutId != null
      ? await svc.listSessions(workoutId)
      : await svc.listAllSessions();
  final completed = items
      .where((s) => s.status.toLowerCase() == 'completed' || s.finishedAt != null)
      .toList();
  completed.sort((a, b) => b.startedAt.compareTo(a.startedAt));
  return completed.take(20).toList();
});

final completedSessionsProvider = FutureProvider<List<WorkoutSession>>((ref) async {
  return ref.watch(completedSessionsProviderFamily(null).future);
});

final userProfileProvider = FutureProvider<UserProfile>((ref) async {
  final svc = ref.watch(sl.profileServiceProvider);
  final profile = await svc.fetchProfile();
  await ref.read(appLocaleProvider.notifier).setFromProfileIfUnset(profile.settings.locale);
  return profile;
});

final allUsersProvider = FutureProvider.family<List<UserSummary>, bool>((ref, coach) async {
  final svc = ref.watch(sl.usersServiceProvider);
  return svc.fetchAll(limit: 500, coach: coach);
});

class UserFilters {
  final bool? coach;
  final List<String>? specializations;
  final List<String>? languages;
  final int? minRate;
  final int? maxRate;
  final String? sortBy;

  const UserFilters({
    this.coach,
    this.specializations,
    this.languages,
    this.minRate,
    this.maxRate,
    this.sortBy,
  });

  UserFilters copyWith({
    bool? coach,
    List<String>? specializations,
    List<String>? languages,
    int? minRate,
    int? maxRate,
    String? sortBy,
  }) {
    return UserFilters(
      coach: coach ?? this.coach,
      specializations: specializations ?? this.specializations,
      languages: languages ?? this.languages,
      minRate: minRate ?? this.minRate,
      maxRate: maxRate ?? this.maxRate,
      sortBy: sortBy ?? this.sortBy,
    );
  }

  bool get isNotEmpty =>
      coach != null ||
      specializations != null ||
      languages != null ||
      minRate != null ||
      maxRate != null ||
      sortBy != null;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is UserFilters &&
          runtimeType == other.runtimeType &&
          coach == other.coach &&
          _listEquals(specializations, other.specializations) &&
          _listEquals(languages, other.languages) &&
          minRate == other.minRate &&
          maxRate == other.maxRate &&
          sortBy == other.sortBy;

  @override
  int get hashCode =>
      coach.hashCode ^
      specializations.hashCode ^
      languages.hashCode ^
      minRate.hashCode ^
      maxRate.hashCode ^
      sortBy.hashCode;

  bool _listEquals(List<dynamic>? a, List<dynamic>? b) {
    if (a == null && b == null) return true;
    if (a == null || b == null) return false;
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}

final filteredUsersProvider = FutureProvider.family<List<UserSummary>, UserFilters>((ref, filters) async {
  final svc = ref.watch(sl.usersServiceProvider);
  return svc.fetchAll(
    limit: 500,
    coach: filters.coach ?? false,
    specializations: filters.specializations,
    languages: filters.languages,
    minRate: filters.minRate,
    maxRate: filters.maxRate,
    sortBy: filters.sortBy,
  );
});

final publicUserProfileProvider = FutureProvider.family<UserProfile, String>((ref, userId) async {
  final svc = ref.watch(sl.profileServiceProvider);
  return svc.fetchProfileById(userId);
});

final publicProfileAggregatesProvider = FutureProvider.family<UserStats, String>((ref, userId) async {
  final analytics = ref.watch(sl.analyticsServiceProvider);
  final data = await analytics.getProfileAggregates(
    weeks: kProfileActivityWeeks,
    limit: kProfileCompletedSessionsLimit,
    userId: userId,
  );
  return UserStats.fromAggregates(
    data,
    weeks: kProfileActivityWeeks,
    sessionLimit: kProfileCompletedSessionsLimit,
  );
});

final coachReviewsProvider = FutureProvider.family<CoachReviewListResponse, String>((ref, coachId) async {
  final svc = ref.watch(sl.crmReviewsServiceProvider);
  return svc.getCoachReviews(coachId: coachId, limit: 100, offset: 0);
});

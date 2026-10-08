import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kShowActivityChartKey = 'profile_show_activity_chart';
const _kShowWorkoutHistoryKey = 'profile_show_workout_history';
const _kShowWorkoutAnalyticsKey = 'profile_show_workout_analytics';
const _kWorkoutAnalyticsShowAllTimeKey = 'profile_workout_analytics_show_all_time';
const _kWorkoutAnalyticsUseHorizontalScrollKey =
    'profile_workout_analytics_use_horizontal_scroll';

class ProfileScreenSectionsState {
  final bool showActivityChart;
  final bool showWorkoutHistory;
  final bool showWorkoutAnalytics;
  final bool workoutAnalyticsShowAllTime;
  final bool workoutAnalyticsUseHorizontalScroll;

  const ProfileScreenSectionsState({
    required this.showActivityChart,
    required this.showWorkoutHistory,
    required this.showWorkoutAnalytics,
    required this.workoutAnalyticsShowAllTime,
    required this.workoutAnalyticsUseHorizontalScroll,
  });

  ProfileScreenSectionsState copyWith({
    bool? showActivityChart,
    bool? showWorkoutHistory,
    bool? showWorkoutAnalytics,
    bool? workoutAnalyticsShowAllTime,
    bool? workoutAnalyticsUseHorizontalScroll,
  }) {
    return ProfileScreenSectionsState(
      showActivityChart: showActivityChart ?? this.showActivityChart,
      showWorkoutHistory: showWorkoutHistory ?? this.showWorkoutHistory,
      showWorkoutAnalytics: showWorkoutAnalytics ?? this.showWorkoutAnalytics,
      workoutAnalyticsShowAllTime:
          workoutAnalyticsShowAllTime ?? this.workoutAnalyticsShowAllTime,
      workoutAnalyticsUseHorizontalScroll: workoutAnalyticsUseHorizontalScroll ??
          this.workoutAnalyticsUseHorizontalScroll,
    );
  }
}

final profileScreenSectionsProvider =
    StateNotifierProvider<ProfileScreenSectionsController, ProfileScreenSectionsState>((ref) {
  return ProfileScreenSectionsController();
});

class ProfileScreenSectionsController extends StateNotifier<ProfileScreenSectionsState> {
  bool _loaded = false;
  ProfileScreenSectionsState? _pending;

  ProfileScreenSectionsController()
      : super(const ProfileScreenSectionsState(
          showActivityChart: true,
          showWorkoutHistory: true,
          showWorkoutAnalytics: true,
          workoutAnalyticsShowAllTime: true,
          workoutAnalyticsUseHorizontalScroll: true,
        )) {
    unawaited(_load());
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final showActivity = prefs.getBool(_kShowActivityChartKey) ?? true;
    final showHistory = prefs.getBool(_kShowWorkoutHistoryKey) ?? true;
    final showAnalytics = prefs.getBool(_kShowWorkoutAnalyticsKey) ?? true;
    final showAllTime = prefs.getBool(_kWorkoutAnalyticsShowAllTimeKey) ?? true;
    final useHScroll = prefs.getBool(_kWorkoutAnalyticsUseHorizontalScrollKey) ?? true;
    state = ProfileScreenSectionsState(
      showActivityChart: showActivity,
      showWorkoutHistory: showHistory,
      showWorkoutAnalytics: showAnalytics,
      workoutAnalyticsShowAllTime: showAllTime,
      workoutAnalyticsUseHorizontalScroll: useHScroll,
    );
    _loaded = true;

    final pending = _pending;
    if (pending != null) {
      _pending = null;
      await setShowActivityChart(pending.showActivityChart);
      await setShowWorkoutHistory(pending.showWorkoutHistory);
      await setShowWorkoutAnalytics(pending.showWorkoutAnalytics);
      await setWorkoutAnalyticsShowAllTime(pending.workoutAnalyticsShowAllTime);
      await setWorkoutAnalyticsUseHorizontalScroll(
          pending.workoutAnalyticsUseHorizontalScroll);
    }
  }

  Future<void> setShowActivityChart(bool value) async {
    if (!_loaded) {
      _pending = ( _pending ?? state).copyWith(showActivityChart: value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kShowActivityChartKey, value);
    state = state.copyWith(showActivityChart: value);
  }

  Future<void> setShowWorkoutHistory(bool value) async {
    if (!_loaded) {
      _pending = ( _pending ?? state).copyWith(showWorkoutHistory: value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kShowWorkoutHistoryKey, value);
    state = state.copyWith(showWorkoutHistory: value);
  }

  Future<void> setShowWorkoutAnalytics(bool value) async {
    if (!_loaded) {
      _pending = (_pending ?? state).copyWith(showWorkoutAnalytics: value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kShowWorkoutAnalyticsKey, value);
    state = state.copyWith(showWorkoutAnalytics: value);
  }

  Future<void> setWorkoutAnalyticsShowAllTime(bool value) async {
    if (!_loaded) {
      _pending = (_pending ?? state).copyWith(workoutAnalyticsShowAllTime: value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kWorkoutAnalyticsShowAllTimeKey, value);
    state = state.copyWith(workoutAnalyticsShowAllTime: value);
  }

  Future<void> setWorkoutAnalyticsUseHorizontalScroll(bool value) async {
    if (!_loaded) {
      _pending = (_pending ?? state).copyWith(workoutAnalyticsUseHorizontalScroll: value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kWorkoutAnalyticsUseHorizontalScrollKey, value);
    state = state.copyWith(workoutAnalyticsUseHorizontalScroll: value);
  }
}

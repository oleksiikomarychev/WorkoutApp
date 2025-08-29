import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/user_max.dart';

class CalendarPlanSummary {
  final int id;
  final String name;

  CalendarPlanSummary({required this.id, required this.name});

  factory CalendarPlanSummary.fromJson(Map<String, dynamic> json) {
    return CalendarPlanSummary(
      id: json['id'] as int,
      name: json['name'] as String,
    );
  }
}

class AppliedCalendarPlanSummary {
  final int id;
  final bool isActive;
  final DateTime? startDate;
  final DateTime endDate;
  final CalendarPlanSummary calendarPlan;
  final NextWorkoutSummary? nextWorkout;

  AppliedCalendarPlanSummary({
    required this.id,
    required this.isActive,
    required this.startDate,
    required this.endDate,
    required this.calendarPlan,
    this.nextWorkout,
  });

  factory AppliedCalendarPlanSummary.fromJson(Map<String, dynamic> json) {
    return AppliedCalendarPlanSummary(
      id: json['id'] as int,
      isActive: json['is_active'] as bool,
      startDate: json['start_date'] != null ? DateTime.parse(json['start_date'] as String) : null,
      endDate: DateTime.parse(json['end_date'] as String),
      calendarPlan: CalendarPlanSummary.fromJson(json['calendar_plan'] as Map<String, dynamic>),
      nextWorkout: json['next_workout'] != null
          ? NextWorkoutSummary.fromJson(Map<String, dynamic>.from(json['next_workout'] as Map))
          : null,
    );
  }
}

class NextWorkoutSummary {
  final int id;
  final String name;
  final DateTime? scheduledFor;
  final int? planOrderIndex;

  NextWorkoutSummary({
    required this.id,
    required this.name,
    this.scheduledFor,
    this.planOrderIndex,
  });

  factory NextWorkoutSummary.fromJson(Map<String, dynamic> json) {
    return NextWorkoutSummary(
      id: json['id'] as int,
      name: (json['name'] ?? '') as String,
      scheduledFor: json['scheduled_for'] != null
          ? DateTime.parse(json['scheduled_for'] as String)
          : null,
      planOrderIndex: json['plan_order_index'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'scheduled_for': scheduledFor?.toIso8601String(),
      'plan_order_index': planOrderIndex,
    };
  }
}

class AppliedCalendarPlan {
  final int id;
  final int calendarPlanId;
  final bool isActive;
  final DateTime? startDate;
  final DateTime endDate;
  final CalendarPlan calendarPlan;
  final List<UserMax> userMaxes;
  final NextWorkoutSummary? nextWorkout;

  AppliedCalendarPlan({
    required this.id,
    required this.calendarPlanId,
    required this.isActive,
    required this.startDate,
    required this.endDate,
    required this.calendarPlan,
    required this.userMaxes,
    required this.nextWorkout,
  });

  factory AppliedCalendarPlan.fromJson(Map<String, dynamic> json) {
    return AppliedCalendarPlan(
      id: json['id'] as int,
      calendarPlanId: json['calendar_plan_id'] as int,
      isActive: json['is_active'] as bool? ?? false,
      startDate: json['start_date'] != null
          ? DateTime.parse(json['start_date'] as String)
          : null,
      endDate: DateTime.parse(json['end_date'] as String),
      calendarPlan: json['calendar_plan'] != null
          ? CalendarPlan.fromJson(
              Map<String, dynamic>.from(json['calendar_plan'] as Map),
            )
          : CalendarPlan(
              id: json['calendar_plan_id'] as int,
              name: 'Unknown Plan',
              schedule: {},
              durationWeeks: 0,
              isActive: false,
            ),
      userMaxes: json['user_maxes'] != null
          ? (json['user_maxes'] as List<dynamic>)
              .whereType<Map<String, dynamic>>()
              .map(UserMax.fromJson)
              .toList()
          : json['user_max_ids'] != null
              ? (json['user_max_ids'] as List<dynamic>)
                  .map((id) => UserMax(
                        id: id as int,
                        exerciseId: 0,
                        maxWeight: 0,
                        repMax: 0,
                      ))
                  .toList()
              : [],
      nextWorkout: json['next_workout'] != null
          ? NextWorkoutSummary.fromJson(
              Map<String, dynamic>.from(json['next_workout'] as Map),
            )
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'calendar_plan_id': calendarPlanId,
      'is_active': isActive,
      'start_date': startDate?.toIso8601String(),
      'end_date': endDate.toIso8601String(),
      'calendar_plan': calendarPlan.toJson(),
      'user_maxes': userMaxes.map((e) => e.toJson()).toList(),
      'next_workout': nextWorkout?.toJson(),
    };
  }
}

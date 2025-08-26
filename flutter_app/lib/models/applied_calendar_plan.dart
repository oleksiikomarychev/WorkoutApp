import 'calendar_plan.dart';
import 'user_max.dart';

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
      calendarPlan: CalendarPlan.fromJson(
        Map<String, dynamic>.from(json['calendar_plan'] as Map),
      ),
      userMaxes: (json['user_maxes'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map(UserMax.fromJson)
          .toList(),
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

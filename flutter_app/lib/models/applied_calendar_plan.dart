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
  final String? status;
  final int? plannedSessionsTotal;
  final int? actualSessionsCompleted;
  final double? adherencePct;
  final String? notes;
  final String? dropoutReason;
  final DateTime? droppedAt;

  AppliedCalendarPlanSummary({
    required this.id,
    required this.isActive,
    required this.startDate,
    required this.endDate,
    required this.calendarPlan,
    this.nextWorkout,
    this.status,
    this.plannedSessionsTotal,
    this.actualSessionsCompleted,
    this.adherencePct,
    this.notes,
    this.dropoutReason,
    this.droppedAt,
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
      status: json['status'] as String?,
      plannedSessionsTotal: json['planned_sessions_total'] as int?,
      actualSessionsCompleted: json['actual_sessions_completed'] as int?,
      adherencePct: (json['adherence_pct'] as num?)?.toDouble(),
      notes: json['notes'] as String?,
      dropoutReason: json['dropout_reason'] as String?,
      droppedAt: json['dropped_at'] != null
          ? DateTime.parse(json['dropped_at'] as String)
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
   // Progress and dropout
  final String? status;
  final int? plannedSessionsTotal;
  final int? actualSessionsCompleted;
  final double? adherencePct;
  final String? notes;
  final String? dropoutReason;
  final DateTime? droppedAt;

  AppliedCalendarPlan({
    required this.id,
    required this.calendarPlanId,
    required this.isActive,
    required this.startDate,
    required this.endDate,
    required this.calendarPlan,
    required this.userMaxes,
    required this.nextWorkout,
    this.status,
    this.plannedSessionsTotal,
    this.actualSessionsCompleted,
    this.adherencePct,
    this.notes,
    this.dropoutReason,
    this.droppedAt,
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
              .map((umJson) => UserMax.fromJson(umJson))
              .toList()
          : json['user_max_ids'] != null
              ? (json['user_max_ids'] as List<dynamic>)
                  .map((id) => UserMax(
                        id: id as int,
                        name: 'Unknown',
                        exerciseId: 0,
                        exerciseName: 'Unknown',
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
      status: json['status'] as String?,
      plannedSessionsTotal: json['planned_sessions_total'] as int?,
      actualSessionsCompleted: json['actual_sessions_completed'] as int?,
      adherencePct: (json['adherence_pct'] as num?)?.toDouble(),
      notes: json['notes'] as String?,
      dropoutReason: json['dropout_reason'] as String?,
      droppedAt: json['dropped_at'] != null
          ? DateTime.parse(json['dropped_at'] as String)
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
      'status': status,
      'planned_sessions_total': plannedSessionsTotal,
      'actual_sessions_completed': actualSessionsCompleted,
      'adherence_pct': adherencePct,
      'notes': notes,
      'dropout_reason': dropoutReason,
      'dropped_at': droppedAt?.toIso8601String(),
    };
  }
}

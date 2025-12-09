import 'mesocycle.dart';

class CalendarPlan {
  final int id;
  final String name;

  final Map<String, dynamic> schedule;
  final int durationWeeks;
  final bool isActive;
  final int? rootPlanId;
  final bool isOriginal;
  final bool isPublic;
  final DateTime? startDate;
  final DateTime? endDate;

  final List<Mesocycle> mesocycles;

  final String? primaryGoal;
  final String? intendedExperienceLevel;
  final int? intendedFrequencyPerWeek;
  final int? sessionDurationTargetMin;
  final List<int>? primaryFocusLifts;
  final List<String>? requiredEquipment;
  final String? notes;

  CalendarPlan({
    required this.id,
    required this.name,
    required this.schedule,
    required this.durationWeeks,
    this.isActive = false,
    this.rootPlanId,
    this.isOriginal = true,
    this.isPublic = false,
    this.startDate,
    this.endDate,
    this.mesocycles = const [],
    this.primaryGoal,
    this.intendedExperienceLevel,
    this.intendedFrequencyPerWeek,
    this.sessionDurationTargetMin,
    this.primaryFocusLifts,
    this.requiredEquipment,
    this.notes,
  });

  factory CalendarPlan.fromJson(Map<String, dynamic> json) {
    return CalendarPlan(
      id: (json['id'] as int?) ?? 0,
      name: json['name'] ?? '',
      schedule: Map<String, dynamic>.from(json['schedule'] ?? {}),
      durationWeeks: (json['duration_weeks'] as int?) ?? 0,
      isActive: json['is_active'] ?? false,
      rootPlanId: json['root_plan_id'] as int?,
      isOriginal: (json['is_original'] as bool?) ?? (json['root_plan_id'] == null || json['root_plan_id'] == json['id']),
      isPublic: json['is_public'] as bool? ?? false,
      startDate: json['start_date'] != null ? DateTime.parse(json['start_date']) : null,
      endDate: json['end_date'] != null ? DateTime.parse(json['end_date']) : null,
      mesocycles: (json['mesocycles'] as List<dynamic>? ?? [])
          .map((e) => e != null ? Mesocycle.fromJson(e as Map<String, dynamic>) : Mesocycle(id: 0, name: '', orderIndex: 0))
          .toList(),
      primaryGoal: json['primary_goal'] as String?,
      intendedExperienceLevel: json['intended_experience_level'] as String?,
      intendedFrequencyPerWeek: json['intended_frequency_per_week'] as int?,
      sessionDurationTargetMin: json['session_duration_target_min'] as int?,
      primaryFocusLifts: (json['primary_focus_lifts'] as List<dynamic>?)
          ?.map((e) => (e as num).toInt())
          .toList(),
      requiredEquipment: (json['required_equipment'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
      notes: json['notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'schedule': schedule,
      'duration_weeks': durationWeeks,
      'is_active': isActive,
      'root_plan_id': rootPlanId,
      'is_original': isOriginal,
      'is_public': isPublic,
      'start_date': startDate?.toIso8601String(),
      'end_date': endDate?.toIso8601String(),
      'mesocycles': mesocycles.map((e) => e.toJson()).toList(),
      'primary_goal': primaryGoal,
      'intended_experience_level': intendedExperienceLevel,
      'intended_frequency_per_week': intendedFrequencyPerWeek,
      'session_duration_target_min': sessionDurationTargetMin,
      'primary_focus_lifts': primaryFocusLifts,
      'required_equipment': requiredEquipment,
      'notes': notes,
    };
  }
}

class CalendarPlanSummary {
  final int id;
  final String name;
  final int durationWeeks;
  final bool isActive;
  final int rootPlanId;
  final bool isOriginal;
  final String? primaryGoal;
  final String? intendedExperienceLevel;
  final int? intendedFrequencyPerWeek;
  final int? sessionDurationTargetMin;

  CalendarPlanSummary({
    required this.id,
    required this.name,
    required this.durationWeeks,
    required this.isActive,
    required this.rootPlanId,
    required this.isOriginal,
    this.primaryGoal,
    this.intendedExperienceLevel,
    this.intendedFrequencyPerWeek,
    this.sessionDurationTargetMin,
  });

  factory CalendarPlanSummary.fromJson(Map<String, dynamic> json) {
    return CalendarPlanSummary(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      durationWeeks: json['duration_weeks'] as int? ?? 0,
      isActive: json['is_active'] as bool? ?? true,
      rootPlanId: json['root_plan_id'] as int? ?? json['id'] as int,
      isOriginal: json['is_original'] as bool? ?? (json['root_plan_id'] == null || json['root_plan_id'] == json['id']),
      primaryGoal: json['primary_goal'] as String?,
      intendedExperienceLevel: json['intended_experience_level'] as String?,
      intendedFrequencyPerWeek: json['intended_frequency_per_week'] as int?,
      sessionDurationTargetMin: json['session_duration_target_min'] as int?,
    );
  }
}

class CalendarPlanSummary {
  final int id;
  final String name;
  final int durationWeeks;
  final bool isActive;
  final int rootPlanId;
  final bool isOriginal;

  CalendarPlanSummary({
    required this.id,
    required this.name,
    required this.durationWeeks,
    required this.isActive,
    required this.rootPlanId,
    required this.isOriginal,
  });

  factory CalendarPlanSummary.fromJson(Map<String, dynamic> json) {
    return CalendarPlanSummary(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      durationWeeks: json['duration_weeks'] as int? ?? 0,
      isActive: json['is_active'] as bool? ?? true,
      rootPlanId: json['root_plan_id'] as int? ?? json['id'] as int,
      isOriginal: json['is_original'] as bool? ?? (json['root_plan_id'] == null || json['root_plan_id'] == json['id']),
    );
  }
}

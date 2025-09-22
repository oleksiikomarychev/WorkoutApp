import 'mesocycle.dart';

class CalendarPlan {
  final int id;
  final String name;
  // Legacy top-level schedule (kept for backward compatibility)
  final Map<String, dynamic> schedule;
  final int durationWeeks;
  final bool isActive;
  final DateTime? startDate;
  final DateTime? endDate;
  // New nested structure
  final List<Mesocycle> mesocycles;

  CalendarPlan({
    required this.id,
    required this.name,
    required this.schedule,
    required this.durationWeeks,
    this.isActive = false,
    this.startDate,
    this.endDate,
    this.mesocycles = const [],
  });

  factory CalendarPlan.fromJson(Map<String, dynamic> json) {
    return CalendarPlan(
      id: (json['id'] as int?) ?? 0,
      name: json['name'] ?? '',
      schedule: Map<String, dynamic>.from(json['schedule'] ?? {}),
      durationWeeks: (json['duration_weeks'] as int?) ?? 0,
      isActive: json['is_active'] ?? false,
      startDate: json['start_date'] != null ? DateTime.parse(json['start_date']) : null,
      endDate: json['end_date'] != null ? DateTime.parse(json['end_date']) : null,
      mesocycles: (json['mesocycles'] as List<dynamic>? ?? [])
          .map((e) => e != null ? Mesocycle.fromJson(e as Map<String, dynamic>) : Mesocycle(id: 0, name: '', orderIndex: 0))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'schedule': schedule,
      'duration_weeks': durationWeeks,
      'is_active': isActive,
      'start_date': startDate?.toIso8601String(),
      'end_date': endDate?.toIso8601String(),
      'mesocycles': mesocycles.map((e) => e.toJson()).toList(),
    };
  }
}

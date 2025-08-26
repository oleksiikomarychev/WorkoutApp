import 'plan_schedule.dart';

class Microcycle {
  final int id;
  final int mesocycleId;
  final String name;
  final String? notes;
  final int orderIndex;
  final Map<String, List<ExerciseScheduleItemDto>> schedule;
  final int? daysCount;
  final double? normalizationValue;
  final String? normalizationUnit; // 'kg' or '%'

  const Microcycle({
    required this.id,
    required this.mesocycleId,
    required this.name,
    this.notes,
    required this.orderIndex,
    required this.schedule,
    this.daysCount,
    this.normalizationValue,
    this.normalizationUnit,
  });

  factory Microcycle.fromJson(Map<String, dynamic> json) {
    final raw = Map<String, dynamic>.from(json['schedule'] ?? {});
    final sched = <String, List<ExerciseScheduleItemDto>>{};
    raw.forEach((key, value) {
      final list = (value as List<dynamic>? ?? [])
          .map((e) => ExerciseScheduleItemDto.fromJson(e as Map<String, dynamic>))
          .toList();
      sched[key] = list;
    });

    return Microcycle(
      id: json['id'] as int,
      mesocycleId: json['mesocycle_id'] as int,
      name: json['name'] ?? '',
      notes: json['notes'],
      orderIndex: (json['order_index'] ?? 0) as int,
      schedule: sched,
      daysCount: json['days_count'] as int?,
      normalizationValue: (json['normalization_value'] as num?)?.toDouble(),
      normalizationUnit: json['normalization_unit'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'mesocycle_id': mesocycleId,
        'name': name,
        'notes': notes,
        'order_index': orderIndex,
        'schedule': schedule.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
        if (daysCount != null) 'days_count': daysCount,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
      };
}

class MicrocycleUpdateDto {
  final String? name;
  final String? notes;
  final int? orderIndex;
  final Map<String, List<ExerciseScheduleItemDto>>? schedule;
  final int? daysCount;
  final double? normalizationValue;
  final String? normalizationUnit; // 'kg' or '%'

  const MicrocycleUpdateDto({
    this.name,
    this.notes,
    this.orderIndex,
    this.schedule,
    this.daysCount,
    this.normalizationValue,
    this.normalizationUnit,
  });

  Map<String, dynamic> toJson() => {
        if (name != null) 'name': name,
        if (notes != null) 'notes': notes,
        if (orderIndex != null) 'order_index': orderIndex,
        if (schedule != null) 'schedule': schedule?.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
        if (daysCount != null) 'days_count': daysCount,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
      };
}

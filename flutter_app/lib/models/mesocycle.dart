import 'microcycle.dart';

class Mesocycle {
  final int id;
  final String name;
  final String? notes;
  final int orderIndex;
  final double? normalizationValue;
  final String? normalizationUnit;
  final int? weeksCount;
  final int? microcycleLengthDays;
  final List<Microcycle> microcycles;

  const Mesocycle({
    required this.id,
    required this.name,
    this.notes,
    required this.orderIndex,
    this.normalizationValue,
    this.normalizationUnit,
    this.weeksCount,
    this.microcycleLengthDays,
    this.microcycles = const [],
  });

  factory Mesocycle.fromJson(Map<String, dynamic> json) => Mesocycle(
        id: (json['id'] as int?) ?? 0,
        name: json['name'] ?? '',
        notes: json['notes'],
        orderIndex: (json['order_index'] as int?) ?? 0,
        normalizationValue: (json['normalization_value'] as num?)?.toDouble(),
        normalizationUnit: json['normalization_unit'] as String?,
        weeksCount: json['weeks_count'] as int?,
        microcycleLengthDays: json['microcycle_length_days'] as int?,
        microcycles: (json['microcycles'] as List<dynamic>? ?? [])
            .map((e) => e != null ? Microcycle.fromJson(e as Map<String, dynamic>) : Microcycle(id: 0, mesocycleId: 0, name: '', orderIndex: 0, schedule: {}))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'notes': notes,
        'order_index': orderIndex,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
        if (weeksCount != null) 'weeks_count': weeksCount,
        if (microcycleLengthDays != null) 'microcycle_length_days': microcycleLengthDays,
        'microcycles': microcycles.map((e) => e.toJson()).toList(),
      };
}

class MesocycleUpdateDto {
  final String? name;
  final String? notes;
  final int? orderIndex;
  final double? normalizationValue;
  final String? normalizationUnit;
  final int? weeksCount;
  final int? microcycleLengthDays;

  const MesocycleUpdateDto({
    this.name,
    this.notes,
    this.orderIndex,
    this.normalizationValue,
    this.normalizationUnit,
    this.weeksCount,
    this.microcycleLengthDays,
  });

  Map<String, dynamic> toJson() => {
        if (name != null) 'name': name,
        if (notes != null) 'notes': notes,
        if (orderIndex != null) 'order_index': orderIndex,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
        if (weeksCount != null) 'weeks_count': weeksCount,
        if (microcycleLengthDays != null) 'microcycle_length_days': microcycleLengthDays,
      };
}

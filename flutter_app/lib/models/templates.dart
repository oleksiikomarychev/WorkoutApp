class MicrocycleTemplateDto {
  final int? id;
  final String name;
  final String? notes;
  final int orderIndex;
  final int? daysCount;
  final Map<String, dynamic>? schedule;

  MicrocycleTemplateDto({this.id, required this.name, this.notes, this.orderIndex = 0, this.daysCount, this.schedule});

  factory MicrocycleTemplateDto.fromJson(Map<String, dynamic> json) {
    return MicrocycleTemplateDto(
      id: json['id'] as int?,
      name: (json['name'] ?? '').toString(),
      notes: json['notes']?.toString(),
      orderIndex: (json['order_index'] as int?) ?? 0,
      daysCount: json['days_count'] as int?,
      schedule: (json['schedule'] as Map?)?.cast<String, dynamic>(),
    );
  }
}

class MesocycleTemplateResponse {
  final int id;
  final String userId;
  final String name;
  final String? notes;
  final int? weeksCount;
  final int? microcycleLengthDays;
  final double? normalizationValue;
  final String? normalizationUnit;
  final bool isPublic;
  final List<MicrocycleTemplateDto> microcycles;

  MesocycleTemplateResponse({
    required this.id,
    required this.userId,
    required this.name,
    this.notes,
    this.weeksCount,
    this.microcycleLengthDays,
    this.normalizationValue,
    this.normalizationUnit,
    required this.isPublic,
    required this.microcycles,
  });

  factory MesocycleTemplateResponse.fromJson(Map<String, dynamic> json) {
    return MesocycleTemplateResponse(
      id: json['id'] as int,
      userId: (json['user_id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      notes: json['notes']?.toString(),
      weeksCount: json['weeks_count'] as int?,
      microcycleLengthDays: json['microcycle_length_days'] as int?,
      normalizationValue: (json['normalization_value'] as num?)?.toDouble(),
      normalizationUnit: json['normalization_unit']?.toString(),
      isPublic: (json['is_public'] as bool?) ?? false,
      microcycles: (json['microcycles'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .map((e) => MicrocycleTemplateDto.fromJson(e))
          .toList(),
    );
  }
}

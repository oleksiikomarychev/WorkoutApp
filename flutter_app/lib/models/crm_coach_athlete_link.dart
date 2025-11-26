class CoachAthleteLink {
  final int id;
  final String coachId;
  final String athleteId;
  final String status;
  final String? channelId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? note;
  final DateTime? endedAt;
  final String? endedReason;

  const CoachAthleteLink({
    required this.id,
    required this.coachId,
    required this.athleteId,
    required this.status,
    this.channelId,
    required this.createdAt,
    required this.updatedAt,
    this.note,
    this.endedAt,
    this.endedReason,
  });

  factory CoachAthleteLink.fromJson(Map<String, dynamic> json) {
    return CoachAthleteLink(
      id: json['id'] as int,
      coachId: json['coach_id']?.toString() ?? '',
      athleteId: json['athlete_id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'pending',
      channelId: json['channel_id']?.toString(),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ?? DateTime.now(),
      note: json['note'] as String?,
      endedAt: json['ended_at'] != null ? DateTime.parse(json['ended_at'] as String) : null,
      endedReason: json['ended_reason'] as String?,
    );
  }
}

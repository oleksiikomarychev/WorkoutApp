class Invitation {
  final String id;
  final String coachUserId;
  final String emailOrUserId;
  final String code;
  final String status;
  final DateTime? expiresAt;
  final DateTime createdAt;

  Invitation({
    required this.id,
    required this.coachUserId,
    required this.emailOrUserId,
    required this.code,
    required this.status,
    this.expiresAt,
    required this.createdAt,
  });

  factory Invitation.fromJson(Map<String, dynamic> json) {
    return Invitation(
      id: json['id'] as String,
      coachUserId: json['coach_user_id'] as String,
      emailOrUserId: json['email_or_user_id'] as String,
      code: json['code'] as String,
      status: json['status'] as String,
      expiresAt: json['expires_at'] != null ? DateTime.parse(json['expires_at'] as String) : null,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class InvitationCreatePayload {
  final String emailOrUserId;
  final int? ttlHours;

  InvitationCreatePayload({required this.emailOrUserId, this.ttlHours});

  Map<String, dynamic> toJson() => {
        'email_or_user_id': emailOrUserId,
        if (ttlHours != null) 'ttl_hours': ttlHours,
      };
}

class UserSummary {
  final String userId;
  final String? displayName;
  final String? photoUrl;
  final bool isPublic;
  final DateTime createdAt;
  final DateTime? lastActiveAt;

  const UserSummary({
    required this.userId,
    required this.displayName,
    required this.photoUrl,
    required this.isPublic,
    required this.createdAt,
    required this.lastActiveAt,
  });

  factory UserSummary.fromJson(Map<String, dynamic> json) {
    return UserSummary(
      userId: json['user_id']?.toString() ?? '',
      displayName: json['display_name'] as String?,
      photoUrl: json['photo_url'] as String?,
      isPublic: json['is_public'] as bool? ?? false,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.fromMillisecondsSinceEpoch(0),
      lastActiveAt: json['last_active_at'] != null
          ? DateTime.tryParse(json['last_active_at'].toString())
          : null,
    );
  }
}

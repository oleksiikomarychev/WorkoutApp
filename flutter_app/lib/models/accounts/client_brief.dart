class ClientBrief {
  final String id;
  final String? displayName;
  final String? avatarUrl;
  final String status;

  ClientBrief({
    required this.id,
    this.displayName,
    this.avatarUrl,
    required this.status,
  });

  factory ClientBrief.fromJson(Map<String, dynamic> json) {
    return ClientBrief(
      id: json['id'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      status: json['status'] as String? ?? 'active',
    );
  }
}

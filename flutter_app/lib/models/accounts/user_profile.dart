class UserProfile {
  final String id;
  final String firebaseUid;
  final String? email;
  final String? displayName;
  final String? avatarUrl;
  final String? locale;
  final String? timezone;
  final String? country;
  final bool marketingOptIn;

  UserProfile({
    required this.id,
    required this.firebaseUid,
    this.email,
    this.displayName,
    this.avatarUrl,
    this.locale,
    this.timezone,
    this.country,
    this.marketingOptIn = false,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as String,
      firebaseUid: json['firebase_uid'] as String,
      email: json['email'] as String?,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      locale: json['locale'] as String?,
      timezone: json['timezone'] as String?,
      country: json['country'] as String?,
      marketingOptIn: (json['marketing_opt_in'] as bool?) ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'firebase_uid': firebaseUid,
      if (email != null) 'email': email,
      if (displayName != null) 'display_name': displayName,
      if (avatarUrl != null) 'avatar_url': avatarUrl,
      if (locale != null) 'locale': locale,
      if (timezone != null) 'timezone': timezone,
      if (country != null) 'country': country,
      'marketing_opt_in': marketingOptIn,
    };
  }
}

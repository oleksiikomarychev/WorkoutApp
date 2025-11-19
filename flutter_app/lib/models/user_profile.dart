class UserSettings {
  final String unitSystem;
  final String locale;
  final String? timezone;
  final bool notificationsEnabled;

  const UserSettings({
    required this.unitSystem,
    required this.locale,
    required this.timezone,
    required this.notificationsEnabled,
  });

  factory UserSettings.fromJson(Map<String, dynamic> json) {
    return UserSettings(
      unitSystem: json['unit_system']?.toString() ?? 'metric',
      locale: json['locale']?.toString() ?? 'en',
      timezone: json['timezone'] as String?,
      notificationsEnabled: json['notifications_enabled'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
        'unit_system': unitSystem,
        'locale': locale,
        'timezone': timezone,
        'notifications_enabled': notificationsEnabled,
      };

  UserSettings copyWith({
    String? unitSystem,
    String? locale,
    String? timezone,
    bool? notificationsEnabled,
  }) {
    return UserSettings(
      unitSystem: unitSystem ?? this.unitSystem,
      locale: locale ?? this.locale,
      timezone: timezone ?? this.timezone,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
    );
  }
}

class UserProfile {
  final String userId;
  final String? displayName;
  final String? bio;
  final String? photoUrl;
  final bool isPublic;
  final DateTime createdAt;
  final DateTime updatedAt;
  final UserSettings settings;
  final double? bodyweightKg;
  final double? heightCm;
  final int? age;
  final String? sex;
  final double? trainingExperienceYears;
  final String? trainingExperienceLevel;
  final String? primaryDefaultGoal;
  final String? trainingEnvironment;
  final double? weeklyGainCoef;
  final DateTime? lastActiveAt;

  const UserProfile({
    required this.userId,
    required this.displayName,
    required this.bio,
    required this.photoUrl,
    required this.isPublic,
    required this.createdAt,
    required this.updatedAt,
    required this.settings,
    this.bodyweightKg,
    this.heightCm,
    this.age,
    this.sex,
    this.trainingExperienceYears,
    this.trainingExperienceLevel,
    this.primaryDefaultGoal,
    this.trainingEnvironment,
    this.weeklyGainCoef,
    this.lastActiveAt,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      userId: json['user_id']?.toString() ?? '',
      displayName: json['display_name'] as String?,
      bio: json['bio'] as String?,
      photoUrl: json['photo_url'] as String?,
      isPublic: json['is_public'] as bool? ?? false,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.fromMillisecondsSinceEpoch(0),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ?? DateTime.fromMillisecondsSinceEpoch(0),
      settings: UserSettings.fromJson((json['settings'] as Map<String, dynamic>? ?? const {})),
      bodyweightKg: (json['bodyweight_kg'] as num?)?.toDouble(),
      heightCm: (json['height_cm'] as num?)?.toDouble(),
      age: json['age'] as int?,
      sex: json['sex'] as String?,
      trainingExperienceYears: (json['training_experience_years'] as num?)?.toDouble(),
      trainingExperienceLevel: json['training_experience_level'] as String?,
      primaryDefaultGoal: json['primary_default_goal'] as String?,
      trainingEnvironment: json['training_environment'] as String?,
      weeklyGainCoef: (json['weekly_gain_coef'] as num?)?.toDouble(),
      lastActiveAt: json['last_active_at'] != null
          ? DateTime.tryParse(json['last_active_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'user_id': userId,
        'display_name': displayName,
        'bio': bio,
        'photo_url': photoUrl,
        'is_public': isPublic,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
        'settings': settings.toJson(),
        'bodyweight_kg': bodyweightKg,
        'height_cm': heightCm,
        'age': age,
        'sex': sex,
        'training_experience_years': trainingExperienceYears,
        'training_experience_level': trainingExperienceLevel,
        'primary_default_goal': primaryDefaultGoal,
        'training_environment': trainingEnvironment,
        'weekly_gain_coef': weeklyGainCoef,
        'last_active_at': lastActiveAt?.toIso8601String(),
      };

  UserProfile copyWith({
    String? displayName,
    String? bio,
    String? photoUrl,
    bool? isPublic,
    DateTime? updatedAt,
    UserSettings? settings,
    double? bodyweightKg,
    double? heightCm,
    int? age,
    String? sex,
    double? trainingExperienceYears,
    String? trainingExperienceLevel,
    String? primaryDefaultGoal,
    String? trainingEnvironment,
    double? weeklyGainCoef,
    DateTime? lastActiveAt,
  }) {
    return UserProfile(
      userId: userId,
      displayName: displayName ?? this.displayName,
      bio: bio ?? this.bio,
      photoUrl: photoUrl ?? this.photoUrl,
      isPublic: isPublic ?? this.isPublic,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      settings: settings ?? this.settings,
      bodyweightKg: bodyweightKg ?? this.bodyweightKg,
      heightCm: heightCm ?? this.heightCm,
      age: age ?? this.age,
      sex: sex ?? this.sex,
      trainingExperienceYears:
          trainingExperienceYears ?? this.trainingExperienceYears,
      trainingExperienceLevel:
          trainingExperienceLevel ?? this.trainingExperienceLevel,
      primaryDefaultGoal: primaryDefaultGoal ?? this.primaryDefaultGoal,
      trainingEnvironment: trainingEnvironment ?? this.trainingEnvironment,
      weeklyGainCoef: weeklyGainCoef ?? this.weeklyGainCoef,
      lastActiveAt: lastActiveAt ?? this.lastActiveAt,
    );
  }
}

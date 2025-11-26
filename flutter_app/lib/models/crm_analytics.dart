class AthleteTrainingSummaryModel {
  final String athleteId;
  final DateTime? lastWorkoutAt;
  final int sessionsCount;
  final double? totalVolume;
  final int? activePlanId;
  final String? activePlanName;
  final int? daysSinceLastWorkout;
  final double? sessionsPerWeek;
  final double? planAdherence;
  final double? avgIntensity;
  final double? avgEffort;
  final Map<String, double>? rpeDistribution;
  final String? segment;

  AthleteTrainingSummaryModel({
    required this.athleteId,
    required this.lastWorkoutAt,
    required this.sessionsCount,
    required this.totalVolume,
    required this.activePlanId,
    required this.activePlanName,
    required this.daysSinceLastWorkout,
    required this.sessionsPerWeek,
    required this.planAdherence,
    required this.avgIntensity,
    required this.avgEffort,
    required this.rpeDistribution,
    required this.segment,
  });

  factory AthleteTrainingSummaryModel.fromJson(Map<String, dynamic> json) {
    return AthleteTrainingSummaryModel(
      athleteId: json['athlete_id'] as String,
      lastWorkoutAt: json['last_workout_at'] != null
          ? DateTime.parse(json['last_workout_at'] as String)
          : null,
      sessionsCount: json['sessions_count'] as int,
      totalVolume: (json['total_volume'] != null)
          ? (json['total_volume'] as num).toDouble()
          : null,
      activePlanId: json['active_plan_id'] as int?,
      activePlanName: json['active_plan_name'] as String?,
      daysSinceLastWorkout: json['days_since_last_workout'] as int?,
      sessionsPerWeek: (json['sessions_per_week'] as num?)?.toDouble(),
      planAdherence: (json['plan_adherence'] as num?)?.toDouble(),
      avgIntensity: (json['avg_intensity'] as num?)?.toDouble(),
      avgEffort: (json['avg_effort'] as num?)?.toDouble(),
      rpeDistribution: (json['rpe_distribution'] as Map<String, dynamic>?)
          ?.map((key, value) => MapEntry(key, (value as num).toDouble())),
      segment: json['segment'] as String?,
    );
  }
}

class CoachAthletesAnalyticsModel {
  final String coachId;
  final DateTime generatedAt;
  final int weeks;
  final int totalAthletes;
  final int activeLinks;
  final List<AthleteTrainingSummaryModel> athletes;

  CoachAthletesAnalyticsModel({
    required this.coachId,
    required this.generatedAt,
    required this.weeks,
    required this.totalAthletes,
    required this.activeLinks,
    required this.athletes,
  });

  factory CoachAthletesAnalyticsModel.fromJson(Map<String, dynamic> json) {
    final athletesJson = json['athletes'] as List<dynamic>? ?? const [];
    return CoachAthletesAnalyticsModel(
      coachId: json['coach_id'] as String,
      generatedAt: DateTime.parse(json['generated_at'] as String),
      weeks: json['weeks'] as int,
      totalAthletes: json['total_athletes'] as int,
      activeLinks: json['active_links'] as int,
      athletes: athletesJson
          .whereType<Map<String, dynamic>>()
          .map(AthleteTrainingSummaryModel.fromJson)
          .toList(),
    );
  }
}

class CoachSummaryAnalyticsModel {
  final String coachId;
  final DateTime generatedAt;
  final int weeks;
  final int totalAthletes;
  final int activeLinks;
  final double avgSessionsPerWeek;
  final int inactiveAthletesCount;
  final double avgPlanAdherence;
  final double avgIntensity;
  final double avgEffort;
  final Map<String, int> segmentCounts;

  CoachSummaryAnalyticsModel({
    required this.coachId,
    required this.generatedAt,
    required this.weeks,
    required this.totalAthletes,
    required this.activeLinks,
    required this.avgSessionsPerWeek,
    required this.inactiveAthletesCount,
    required this.avgPlanAdherence,
    required this.avgIntensity,
    required this.avgEffort,
    required this.segmentCounts,
  });

  factory CoachSummaryAnalyticsModel.fromJson(Map<String, dynamic> json) {
    return CoachSummaryAnalyticsModel(
      coachId: json['coach_id'] as String,
      generatedAt: DateTime.parse(json['generated_at'] as String),
      weeks: json['weeks'] as int,
      totalAthletes: json['total_athletes'] as int,
      activeLinks: json['active_links'] as int,
      avgSessionsPerWeek: (json['avg_sessions_per_week'] as num).toDouble(),
      inactiveAthletesCount: json['inactive_athletes_count'] as int,
      avgPlanAdherence: (json['avg_plan_adherence'] as num).toDouble(),
      avgIntensity: (json['avg_intensity'] as num).toDouble(),
      avgEffort: (json['avg_effort'] as num).toDouble(),
      segmentCounts: (json['segment_counts'] as Map<String, dynamic>?)
              ?.map((key, value) => MapEntry(key, value as int)) ??
          const {},
    );
  }
}

class AthleteTrendPointModel {
  final DateTime periodStart;
  final int sessionsCount;
  final double totalVolume;

  AthleteTrendPointModel({
    required this.periodStart,
    required this.sessionsCount,
    required this.totalVolume,
  });

  factory AthleteTrendPointModel.fromJson(Map<String, dynamic> json) {
    return AthleteTrendPointModel(
      periodStart: DateTime.parse(json['period_start'] as String),
      sessionsCount: json['sessions_count'] as int,
      totalVolume: (json['total_volume'] as num).toDouble(),
    );
  }
}

class AthleteDetailedAnalyticsModel {
  final String athleteId;
  final DateTime generatedAt;
  final int weeks;
  final int sessionsCount;
  final double? totalVolume;
  final int? activePlanId;
  final String? activePlanName;
  final DateTime? lastWorkoutAt;
  final int? daysSinceLastWorkout;
  final List<AthleteTrendPointModel> trend;
  final double? sessionsPerWeek;
  final double? planAdherence;
  final double? avgIntensity;
  final double? avgEffort;
  final Map<String, double>? rpeDistribution;

  AthleteDetailedAnalyticsModel({
    required this.athleteId,
    required this.generatedAt,
    required this.weeks,
    required this.sessionsCount,
    required this.totalVolume,
    required this.activePlanId,
    required this.activePlanName,
    required this.lastWorkoutAt,
    required this.daysSinceLastWorkout,
    required this.trend,
    required this.sessionsPerWeek,
    required this.planAdherence,
    required this.avgIntensity,
    required this.avgEffort,
    required this.rpeDistribution,
  });

  factory AthleteDetailedAnalyticsModel.fromJson(Map<String, dynamic> json) {
    final trendJson = json['trend'] as List<dynamic>? ?? const [];
    return AthleteDetailedAnalyticsModel(
      athleteId: json['athlete_id'] as String,
      generatedAt: DateTime.parse(json['generated_at'] as String),
      weeks: json['weeks'] as int,
      sessionsCount: json['sessions_count'] as int,
      totalVolume: json['total_volume'] != null
          ? (json['total_volume'] as num).toDouble()
          : null,
      activePlanId: json['active_plan_id'] as int?,
      activePlanName: json['active_plan_name'] as String?,
      lastWorkoutAt: json['last_workout_at'] != null
          ? DateTime.parse(json['last_workout_at'] as String)
          : null,
      daysSinceLastWorkout: json['days_since_last_workout'] as int?,
      trend: trendJson
          .whereType<Map<String, dynamic>>()
          .map(AthleteTrendPointModel.fromJson)
          .toList(),
      sessionsPerWeek: (json['sessions_per_week'] as num?)?.toDouble(),
      planAdherence: (json['plan_adherence'] as num?)?.toDouble(),
      avgIntensity: (json['avg_intensity'] as num?)?.toDouble(),
      avgEffort: (json['avg_effort'] as num?)?.toDouble(),
      rpeDistribution: (json['rpe_distribution'] as Map<String, dynamic>?)
          ?.map((key, value) => MapEntry(key, (value as num).toDouble())),
    );
  }
}

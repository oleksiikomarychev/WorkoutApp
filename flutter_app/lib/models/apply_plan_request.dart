class ComputeSettings {
  final bool computeWeights;
  final double roundingStep;
  final String roundingMode; // 'nearest' | 'floor' | 'ceil'
  final bool generateWorkouts;
  final DateTime? startDate;

  const ComputeSettings({
    this.computeWeights = true,
    this.roundingStep = 2.5,
    this.roundingMode = 'nearest',
    this.generateWorkouts = true,
    this.startDate,
  });

  Map<String, dynamic> toJson() {
    return {
      'compute_weights': computeWeights,
      'rounding_step': roundingStep,
      'rounding_mode': roundingMode,
      'generate_workouts': generateWorkouts,
      'start_date': startDate?.toIso8601String(),
    };
  }
}

class ApplyPlanRequest {
  final List<int> userMaxIds;
  final ComputeSettings compute;

  const ApplyPlanRequest({
    required this.userMaxIds,
    this.compute = const ComputeSettings(),
  });

  Map<String, dynamic> toJson() {
    return {
      'user_max_ids': userMaxIds,
      'compute': compute.toJson(),
    };
  }
}

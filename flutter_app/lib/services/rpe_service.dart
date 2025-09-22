import 'package:workout_app/config/rpe_table.dart' as rpe_table;

class RpeService {
  /// ⚡ ULTRA-FAST: Calculate RPE from intensity and reps using optimized local lookup
  /// No HTTP calls - instant results
  Future<double?> calculateRpe(double intensity, int reps) async {
    final intensityInt = intensity.round();
    final result = rpe_table.RpeTable.getRpe(intensityInt, reps);
    print('calculateRpe (LOCAL): intensity=$intensityInt, reps=$reps -> rpe=$result');
    return result?.toDouble();
  }

  /// ⚡ ULTRA-FAST: Calculate reps from intensity and RPE using optimized local lookup
  /// No HTTP calls - instant results
  Future<int?> calculateReps(double intensity, double rpe) async {
    final intensityInt = intensity.round();
    final rpeInt = rpe.round();
    final result = rpe_table.RpeTable.getReps(intensityInt, rpeInt);
    print('calculateReps (LOCAL): intensity=$intensityInt, rpe=$rpeInt -> reps=$result');
    return result;
  }

  /// ⚡ ULTRA-FAST: Calculate intensity from reps and RPE using optimized local lookup
  /// No HTTP calls - instant results
  Future<double?> calculateIntensity(int reps, double rpe) async {
    final rpeInt = rpe.round();
    final result = rpe_table.RpeTable.getIntensity(reps, rpeInt);
    print('calculateIntensity (LOCAL): reps=$reps, rpe=$rpeInt -> intensity=$result');
    return result?.toDouble();
  }

  /// Calculate one rep max using the optimized local table
  double calculateOneRepMax(double rpe, int reps, double weight) {
    final rpeInt = rpe.round();
    final intensity = rpe_table.RpeTable.getIntensity(reps, rpeInt);
    if (intensity == null) return 0.0;
    return weight / (intensity / 100.0);
  }

  /// Get all available intensities
  List<int> getAvailableIntensities() {
    return rpe_table.RpeTable.getAvailableIntensities();
  }

  /// Get all available RPE values for a given intensity
  List<double> getAvailableRpes(int intensity) {
    final rpes = rpe_table.RpeTable.getAvailableRpes(intensity);
    return rpes?.map((rpe) => rpe.toDouble()).toList() ?? [];
  }

  /// Validate intensity value
  bool isValidIntensity(int intensity) {
    return rpe_table.RpeTable.isValidIntensity(intensity);
  }

  /// Validate RPE value
  bool isValidRpe(double rpe) {
    return rpe_table.RpeTable.isValidRpe(rpe.round());
  }
}

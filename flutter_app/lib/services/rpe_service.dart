import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/config/rpe_table.dart' as rpe_table;

class RpeService {
  final ApiClient _apiClient;

  RpeService(this._apiClient);



  Future<double?> calculateRpe(double intensity, int reps) async {
    final intensityInt = intensity.round();
    final result = rpe_table.RpeTable.getRpe(intensityInt, reps);
    print('calculateRpe (LOCAL): intensity=$intensityInt, reps=$reps -> rpe=$result');
    return result?.toDouble();
  }



  Future<int?> calculateReps(double intensity, double rpe) async {
    final intensityInt = intensity.round();
    final rpeInt = rpe.round();
    final result = rpe_table.RpeTable.getReps(intensityInt, rpeInt);
    print('calculateReps (LOCAL): intensity=$intensityInt, rpe=$rpeInt -> reps=$result');
    return result;
  }



  Future<double?> calculateIntensity(int reps, double rpe) async {
    final rpeInt = rpe.round();
    final result = rpe_table.RpeTable.getIntensity(reps, rpeInt);
    print('calculateIntensity (LOCAL): reps=$reps, rpe=$rpeInt -> intensity=$result');
    return result?.toDouble();
  }


  double calculateOneRepMax(double rpe, int reps, double weight) {
    final rpeInt = rpe.round();
    final intensity = rpe_table.RpeTable.getIntensity(reps, rpeInt);
    if (intensity == null) return 0.0;
    return weight / (intensity / 100.0);
  }


  List<int> getAvailableIntensities() {
    return rpe_table.RpeTable.getAvailableIntensities();
  }


  List<double> getAvailableRpes(int intensity) {
    final rpes = rpe_table.RpeTable.getAvailableRpes(intensity);
    return rpes?.map((rpe) => rpe.toDouble()).toList() ?? [];
  }


  bool isValidIntensity(int intensity) {
    return rpe_table.RpeTable.isValidIntensity(intensity);
  }


  bool isValidRpe(double rpe) {
    return rpe_table.RpeTable.isValidRpe(rpe.round());
  }
}

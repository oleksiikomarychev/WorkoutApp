import 'api_client.dart';

class RpeService {
  final ApiClient _client;
  RpeService(this._client);

  Future<Map<String, dynamic>> compute({
    int? intensity,
    double? effort,
    int? volume,
    int? userMaxId,
    double? maxWeight,
    double roundingStep = 2.5,
    String roundingMode = 'nearest',
  }) async {
    final payload = <String, dynamic>{
      if (intensity != null) 'intensity': intensity,
      if (effort != null) 'effort': effort,
      if (volume != null) 'volume': volume,
      if (userMaxId != null) 'user_max_id': userMaxId,
      if (maxWeight != null) 'max_weight': maxWeight,
      'rounding_step': roundingStep,
      'rounding_mode': roundingMode,
    };
    final resp = await _client.post('/rpe/compute', payload, context: 'RpeService.compute');
    return (resp as Map).cast<String, dynamic>();
  }
}

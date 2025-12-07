import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class MesocycleService extends BaseApiService {
  @override
  final ApiClient apiClient;

  @override
  MesocycleService({required this.apiClient}) : super(apiClient);


  Future<List<Mesocycle>> listMesocycles(int planId) async {
    return await getList<Mesocycle>(
      ApiConfig.listMesocyclesEndpoint(planId.toString()),
      (json) => Mesocycle.fromJson(json),
    );
  }

  Future<Mesocycle> createMesocycle(int planId, MesocycleUpdateDto data) async {
    return await post<Mesocycle>(
      ApiConfig.createMesocycleEndpoint(planId.toString()),
      data.toJson(),
      (json) => Mesocycle.fromJson(json),
    );
  }

  Future<Microcycle> updateMicrocycle(int microcycleId, MicrocycleUpdateDto data) async {
    return await put<Microcycle>(
      ApiConfig.updateMicrocycleEndpoint(microcycleId.toString()),
      data.toJson(),
      (json) => Microcycle.fromJson(json),
    );
  }

  Future<List<int>> validateMicrocycles(List<int> microcycleIds) async {
    final res = await post<Map<String, dynamic>>(
      ApiConfig.validateMicrocyclesEndpoint(),
      microcycleIds,
      (json) => json,
    );
    final ids = (res['valid_ids'] as List<dynamic>? ?? const []).map((e) => (e as num).toInt()).toList();
    return ids;
  }

  Future<void> deleteMesocycle(int mesocycleId) async {
    await delete(ApiConfig.deleteMesocycleEndpoint(mesocycleId.toString()));
  }

  Future<void> deleteMicrocycle(int microcycleId) async {
    await delete(ApiConfig.deleteMicrocycleEndpoint(microcycleId.toString()));
  }
}

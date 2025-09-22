import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class MesocycleService extends BaseApiService {
  @override
  final ApiClient apiClient;

  @override
  MesocycleService({required this.apiClient}) : super(apiClient);

  // Mesocycles
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
}

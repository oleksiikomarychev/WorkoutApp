import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/services/base_api_service.dart';

class MesocycleService extends BaseApiService {
  MesocycleService(super.apiClient);

  // Mesocycles
  Future<List<Mesocycle>> listMesocycles(int planId) async {
    return await getList<Mesocycle>(
      ApiConfig.calendarPlanMesocyclesEndpoint(planId.toString()),
      (json) => Mesocycle.fromJson(json),
    );
  }

  Future<Mesocycle> createMesocycle(int planId, MesocycleUpdateDto data) async {
    return await post<Mesocycle>(
      ApiConfig.calendarPlanMesocyclesEndpoint(planId.toString()),
      data.toJson(),
      (json) => Mesocycle.fromJson(json),
    );
  }

  Future<Mesocycle> updateMesocycle(int mesocycleId, MesocycleUpdateDto data) async {
    return await put<Mesocycle>(
      ApiConfig.mesocycleByIdEndpoint(mesocycleId.toString()),
      data.toJson(),
      (json) => Mesocycle.fromJson(json),
    );
  }

  Future<bool> deleteMesocycle(int mesocycleId) async {
    return await delete(
      ApiConfig.mesocycleByIdEndpoint(mesocycleId.toString()),
    );
  }

  // Microcycles
  Future<List<Microcycle>> listMicrocycles(int mesocycleId) async {
    return await getList<Microcycle>(
      ApiConfig.mesocycleMicrocyclesEndpoint(mesocycleId.toString()),
      (json) => Microcycle.fromJson(json),
    );
  }

  Future<Microcycle> createMicrocycle(int mesocycleId, MicrocycleUpdateDto data) async {
    return await post<Microcycle>(
      ApiConfig.mesocycleMicrocyclesEndpoint(mesocycleId.toString()),
      data.toJson(),
      (json) => Microcycle.fromJson(json),
    );
  }

  Future<Microcycle> updateMicrocycle(int microcycleId, MicrocycleUpdateDto data) async {
    return await put<Microcycle>(
      ApiConfig.microcycleByIdEndpoint(microcycleId.toString()),
      data.toJson(),
      (json) => Microcycle.fromJson(json),
    );
  }

  Future<bool> deleteMicrocycle(int microcycleId) async {
    return await delete(
      ApiConfig.microcycleByIdEndpoint(microcycleId.toString()),
    );
  }
}

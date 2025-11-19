import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/macro.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class MacroService extends BaseApiService {
  @override
  final ApiClient apiClient;
  final _log = LoggerService('MacroService');

  MacroService({required this.apiClient}) : super(apiClient);

  Future<List<PlanMacro>> listMacros(int calendarPlanId) async {
    final res = await apiClient.get(
      ApiConfig.listMacrosEndpoint(calendarPlanId.toString()),
      context: 'MacroService.listMacros',
    );
    if (res is List) {
      return res
          .whereType<Map<String, dynamic>>()
          .map((j) => PlanMacro.fromJson(j))
          .toList();
    }
    if (res is Map) {
      Map<String, dynamic> m;
      try {
        m = Map<String, dynamic>.from(res);
      } catch (_) {
        return [];
      }
      List<dynamic>? pickList(Map<String, dynamic> src) {
        for (final k in const ['results', 'items', 'data', 'macros']) {
          final v = src[k];
          if (v is List) return v;
          if (v is Map && v['items'] is List) return v['items'] as List;
        }
        return null;
      }
      final list = pickList(m);
      if (list != null) {
        return list
            .whereType<Map>()
            .map((j) => PlanMacro.fromJson(Map<String, dynamic>.from(j as Map)))
            .toList();
      }
      if (m.containsKey('id')) {
        return [PlanMacro.fromJson(m)];
      }
    }
    return [];
  }

  Future<PlanMacro> createMacro({
    required int calendarPlanId,
    required String name,
    bool isActive = true,
    int priority = 100,
    required MacroRule rule,
  }) async {
    final payload = {
      'name': name,
      'is_active': isActive,
      'priority': priority,
      'rule': rule.toJson(),
    };
    final res = await apiClient.post(
      ApiConfig.createMacroEndpoint(calendarPlanId.toString()),
      payload,
      context: 'MacroService.createMacro',
    );
    return PlanMacro.fromJson(res as Map<String, dynamic>);
  }

  Future<PlanMacro> updateMacro({
    required int calendarPlanId,
    required int macroId,
    String? name,
    bool? isActive,
    int? priority,
    MacroRule? rule,
  }) async {
    final payload = <String, dynamic>{
      if (name != null) 'name': name,
      if (isActive != null) 'is_active': isActive,
      if (priority != null) 'priority': priority,
      if (rule != null) 'rule': rule.toJson(),
    };
    final res = await apiClient.put(
      ApiConfig.updateMacroEndpoint(calendarPlanId.toString(), macroId.toString()),
      payload,
      context: 'MacroService.updateMacro',
    );
    return PlanMacro.fromJson(res as Map<String, dynamic>);
  }

  Future<void> deleteMacro({required int calendarPlanId, required int macroId}) async {
    await apiClient.delete(
      ApiConfig.deleteMacroEndpoint(calendarPlanId.toString(), macroId.toString()),
      context: 'MacroService.deleteMacro',
    );
  }

  Future<Map<String, dynamic>> runPreview({required int appliedPlanId}) async {
    final res = await apiClient.post(
      ApiConfig.runMacrosEndpoint(appliedPlanId.toString()),
      <String, dynamic>{},
      context: 'MacroService.runPreview',
    );
    return (res as Map).cast<String, dynamic>();
  }

  Future<Map<String, dynamic>> applyMacros({required int appliedPlanId}) async {
    final res = await apiClient.post(
      ApiConfig.applyMacrosEndpoint(appliedPlanId.toString()),
      <String, dynamic>{},
      context: 'MacroService.applyMacros',
    );
    return (res as Map).cast<String, dynamic>();
  }
}

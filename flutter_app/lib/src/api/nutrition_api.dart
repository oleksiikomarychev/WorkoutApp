import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';

class NutritionApi {
  static final ApiClient _apiClient = ApiClient();

  static Future<Map<String, dynamic>> createFood({
    required String name,
    required String unit,
    required double dosage,
    double calories = 0,
    double proteins = 0,
    double fats = 0,
    double carbs = 0,
    required double weightG,
  }) async {
    final endpoint = ApiConfig.createFoodEndpoint();
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
      'calories': calories,
      'proteins': proteins,
      'fats': fats,
      'carbs': carbs,
      'weight_g': weightG,
    };
    final data = await _apiClient.post(
      endpoint,
      payload,
      context: 'createFood',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

  static Future<Map<String, dynamic>?> getFood(int foodId) async {
    final endpoint = ApiConfig.getFoodEndpoint(foodId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getFood',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<List<Map<String, dynamic>>> getAllFood() async {
    final endpoint = ApiConfig.getAllFoodEndpoint();
    final data = await _apiClient.get(
      endpoint,
      context: 'getAllFood',
    );
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  static Future<Map<String, dynamic>?> updateFood(
    int foodId, {
    required String name,
    required String unit,
    required double dosage,
    double calories = 0,
    double proteins = 0,
    double fats = 0,
    double carbs = 0,
    required double weightG,
  }) async {
    final endpoint = ApiConfig.updateFoodEndpoint(foodId);
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
      'calories': calories,
      'proteins': proteins,
      'fats': fats,
      'carbs': carbs,
      'weight_g': weightG,
    };
    final data = await _apiClient.put(
      endpoint,
      payload,
      context: 'updateFood',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<bool> deleteFood(int foodId) async {
    final endpoint = ApiConfig.deleteFoodEndpoint(foodId);
    final data = await _apiClient.delete(
      endpoint,
      context: 'deleteFood',
    );
    if (data is Map<String, dynamic> && data['deleted'] == true) {
      return true;
    }
    return false;
  }

  static Future<Map<String, dynamic>> createSupplement({
    required String name,
    required String unit,
    required double dosage,
  }) async {
    final endpoint = ApiConfig.createSupplementEndpoint();
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
    };
    final data = await _apiClient.post(
      endpoint,
      payload,
      context: 'createSupplement',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

  static Future<Map<String, dynamic>?> getSupplement(int supplementId) async {
    final endpoint = ApiConfig.getSupplementEndpoint(supplementId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSupplement',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<List<Map<String, dynamic>>> getAllSupplements() async {
    final endpoint = ApiConfig.getAllSupplementsEndpoint();
    final data = await _apiClient.get(
      endpoint,
      context: 'getAllSupplements',
    );
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  static Future<Map<String, dynamic>?> updateSupplement(
    int supplementId, {
    required String name,
    required String unit,
    required double dosage,
  }) async {
    final endpoint = ApiConfig.updateSupplementEndpoint(supplementId);
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
    };
    final data = await _apiClient.put(
      endpoint,
      payload,
      context: 'updateSupplement',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<bool> deleteSupplement(int supplementId) async {
    final endpoint = ApiConfig.deleteSupplementEndpoint(supplementId);
    final data = await _apiClient.delete(
      endpoint,
      context: 'deleteSupplement',
    );
    if (data is Map<String, dynamic> && data['deleted'] == true) {
      return true;
    }
    return false;
  }

  static Future<Map<String, dynamic>> createMedication({
    required String name,
    required String unit,
    required double dosage,
    double? halfLifeHours,
    double? concentration,
  }) async {
    final endpoint = ApiConfig.createMedicationEndpoint();
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
      if (halfLifeHours != null) 'half_life_hours': halfLifeHours,
      if (concentration != null) 'concentration': concentration,
    };
    final data = await _apiClient.post(
      endpoint,
      payload,
      context: 'createMedication',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

  static Future<Map<String, dynamic>?> getMedication(int medicationId) async {
    final endpoint = ApiConfig.getMedicationEndpoint(medicationId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getMedication',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<List<Map<String, dynamic>>> getAllMedications() async {
    final endpoint = ApiConfig.getAllMedicationsEndpoint();
    final data = await _apiClient.get(
      endpoint,
      context: 'getAllMedications',
    );
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  static Future<Map<String, dynamic>?> updateMedication(
    int medicationId, {
    required String name,
    required String unit,
    required double dosage,
    double? halfLifeHours,
    double? concentration,
  }) async {
    final endpoint = ApiConfig.updateMedicationEndpoint(medicationId);
    final payload = {
      'name': name,
      'unit': unit,
      'dosage': dosage,
      if (halfLifeHours != null) 'half_life_hours': halfLifeHours,
      if (concentration != null) 'concentration': concentration,
    };
    final data = await _apiClient.put(
      endpoint,
      payload,
      context: 'updateMedication',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<bool> deleteMedication(int medicationId) async {
    final endpoint = ApiConfig.deleteMedicationEndpoint(medicationId);
    final data = await _apiClient.delete(
      endpoint,
      context: 'deleteMedication',
    );
    if (data is Map<String, dynamic> && data['deleted'] == true) {
      return true;
    }
    return false;
  }

  static Future<Map<String, dynamic>> createSession({
    required int userId,
    required String sessionId,
    required List<Map<String, dynamic>> entries,
    int? workoutId,
    int? appliedPlanWorkoutId,
    required String date,
  }) async {
    final endpoint = ApiConfig.createSessionEndpoint();
    final payload = {
      'user_id': userId,
      'session_id': sessionId,
      'entries': entries,
      if (workoutId != null) 'workout_id': workoutId,
      if (appliedPlanWorkoutId != null) 'applied_plan_workout_id': appliedPlanWorkoutId,
      'date': date,
    };
    final data = await _apiClient.post(
      endpoint,
      payload,
      context: 'createSession',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

  static Future<Map<String, dynamic>?> getSession(String sessionId) async {
    final endpoint = ApiConfig.getSessionEndpoint(sessionId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSession',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<Map<String, dynamic>?> getSessionByUserId(int userId) async {
    final endpoint = ApiConfig.getSessionByUserIdEndpoint(userId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSessionByUserId',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<Map<String, dynamic>?> getSessionByWorkoutId(int workoutId) async {
    final endpoint = ApiConfig.getSessionByWorkoutIdEndpoint(workoutId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSessionByWorkoutId',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<Map<String, dynamic>?> getSessionByAppliedPlanWorkoutId(int appliedPlanWorkoutId) async {
    final endpoint = ApiConfig.getSessionByAppliedPlanWorkoutIdEndpoint(appliedPlanWorkoutId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSessionByAppliedPlanWorkoutId',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<List<Map<String, dynamic>>> getAllSessions() async {
    final endpoint = ApiConfig.getAllSessionsEndpoint();
    final data = await _apiClient.get(
      endpoint,
      context: 'getAllSessions',
    );
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  static Future<List<Map<String, dynamic>>> getSessionsByUserId(int userId) async {
    final endpoint = ApiConfig.getSessionByUserIdEndpoint(userId);
    final data = await _apiClient.get(
      endpoint,
      context: 'getSessionsByUserId',
    );
    if (data is List) {
      return data.cast<Map<String, dynamic>>();
    }
    return [];
  }

  static Future<Map<String, dynamic>?> updateSession(
    String sessionId, {
    required int userId,
    required List<Map<String, dynamic>> entries,
    int? workoutId,
    int? appliedPlanWorkoutId,
    required String date,
  }) async {
    final endpoint = ApiConfig.updateSessionEndpoint(sessionId);
    final payload = {
      'user_id': userId,
      'session_id': sessionId,
      'entries': entries,
      if (workoutId != null) 'workout_id': workoutId,
      if (appliedPlanWorkoutId != null) 'applied_plan_workout_id': appliedPlanWorkoutId,
      'date': date,
    };
    final data = await _apiClient.put(
      endpoint,
      payload,
      context: 'updateSession',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  static Future<bool> deleteSession(String sessionId) async {
    final endpoint = ApiConfig.deleteSessionEndpoint(sessionId);
    final data = await _apiClient.delete(
      endpoint,
      context: 'deleteSession',
    );
    if (data is Map<String, dynamic> && data['deleted'] == true) {
      return true;
    }
    return false;
  }
}

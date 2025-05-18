class ApiConfig {
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000';
  
  static const String localBaseUrl = 'http://127.0.0.1:8000';
  
  static const String productionBaseUrl = 'https://yourproductionapi.com';
  
  static const int connectionTimeout = 30;
  static const int receiveTimeout = 30;
  
  static const String apiPrefix = '';
  
  static String getBaseUrl() {
    return localBaseUrl;
  }
  
  static const String healthEndpoint = '/health';
  static const String workoutsEndpoint = '/workouts';
  static const String exercisesEndpoint = '/exercises';
  static const String progressionsEndpoint = '/progressions';
  static const String userMaxEndpoint = '/user-max';
}

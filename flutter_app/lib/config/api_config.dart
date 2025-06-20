class ApiConfig {
  // Base URLs
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000';
  static const String localBaseUrl = 'http://127.0.0.1:8000';
  static const String productionBaseUrl = 'https://yourproductionapi.com';
  
  // Timeouts
  static const int connectionTimeout = 30;
  static const int receiveTimeout = 30;
  
  // API Prefix - should match the FastAPI app's prefix
  static const String apiPrefix = '';
  
  /// Returns the base URL for API requests
  /// 
  /// By default, uses local development server.
  /// For Android emulator, use [androidEmulatorBaseUrl]
  /// For production, use [productionBaseUrl]
  static String getBaseUrl() {
    // Check if running on Android emulator
    // if (Platform.isAndroid) {
    //   return androidEmulatorBaseUrl;
    // }
    return localBaseUrl;
  }
  
  /// Builds a full API endpoint URL
  static String buildEndpoint(String path) {
    if (path.startsWith('/')) {
      return '${getBaseUrl()}$path';
    }
    return '${getBaseUrl()}/$path';
  }
  
  // API Endpoints - these should match your FastAPI router prefixes
  static const String healthEndpoint = '/api/health';
  static const String workoutsEndpoint = '/api/v1/workouts';
  static const String exercisesEndpoint = '/api/v1/exercises';
  static const String exerciseListEndpoint = '/api/v1/exercises/list';
  static const String progressionsEndpoint = '/api/v1/progressions';
  static const String userMaxEndpoint = '/api/v1/user-maxes';
}

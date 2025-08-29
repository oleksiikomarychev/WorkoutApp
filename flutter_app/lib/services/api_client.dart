import 'dart:convert';
import 'dart:developer' as developer;
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../config/api_config.dart';
import 'logger_service.dart';
import 'base_api_service.dart';

class ApiClient {
  final http.Client _httpClient;
  final Map<String, String> _defaultHeaders;
  final LoggerService _logger = LoggerService('ApiClient');
  
  ApiClient({
    http.Client? httpClient,
    Map<String, String>? defaultHeaders,
  }) : 
    _httpClient = httpClient ?? http.Client(),
    _defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...?defaultHeaders,
    };
  factory ApiClient.create() {
    return ApiClient();
  }
  Future<dynamic> patch(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);
    
    _logRequest('PATCH', uri, body: data, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _authHeaders(),
      };
      final response = await _httpClient.patch(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));
      
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('PATCH', uri, e, context: context);
      rethrow;
    }
  }
  Future<Map<String, String>> _authHeaders() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return const {};
      final token = await user.getIdToken();
      // Provide both Authorization for gateway verification and X-User-Id as a fallback
      return {
        'Authorization': 'Bearer $token',
        'X-User-Id': user.uid,
      };
    } catch (e) {
      // If anything goes wrong obtaining token, send no auth headers
      return const {};
    }
  }

  Future<dynamic> get(String endpoint, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);
    
    _logRequest('GET', uri, context: context);
    try {
      print('Making GET request to: ${uri.toString()}');
      final headers = {
        ..._defaultHeaders,
        ...await _authHeaders(),
      };
      final response = await _httpClient.get(
        uri,
        headers: headers,
      ).timeout(const Duration(seconds: 10));
      
      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');
      
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      print('Error in GET request to $uri: $e');
      _logError('GET', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> post(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);
    
    _logRequest('POST', uri, body: data, context: context);
    try {
      print('POST request to: ${uri.toString()}');
      print('Request body: ${json.encode(data)}');
      final headers = {
        ..._defaultHeaders,
        ...await _authHeaders(),
      };
      print('Headers: $headers');
      
      final response = await _httpClient.post(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));
      
      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');
      
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      print('Error in POST request to $uri: $e');
      _logError('POST', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> put(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);
    
    _logRequest('PUT', uri, body: data, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _authHeaders(),
      };
      final response = await _httpClient.put(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));
      
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('PUT', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> delete(String endpoint, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);
    
    _logRequest('DELETE', uri, context: context);
    try {
      print('Sending DELETE request to: ${uri.toString()}');
      final headers = {
        ..._defaultHeaders,
        ...await _authHeaders(),
      };
      print('Headers: $headers');
      
      final response = await _httpClient.delete(
        uri,
        headers: headers,
      ).timeout(const Duration(seconds: 10));
      
      print('DELETE response status: ${response.statusCode}');
      print('Response body: ${response.body}');
      
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e, stackTrace) {
      print('Error in DELETE request to $uri: $e');
      print('Stack trace: $stackTrace');
      _logError('DELETE', uri, e, context: context);
      rethrow;
    }
  }
  // Helper method to handle the API response
  dynamic _handleResponse(http.Response response) {
    final statusCode = response.statusCode;
    final responseBody = response.body;
    
    _logger.d('Response status: $statusCode');
    _logger.d('Response body: $responseBody');
    
    if (statusCode >= 200 && statusCode < 300) {
      if (responseBody.isEmpty) {
        return null;
      }
      try {
        return json.decode(responseBody);
      } catch (e) {
        _logger.e('Failed to parse response body: $e');
        return responseBody;
      }
    } else {
      String errorMessage;
      try {
        final errorJson = json.decode(responseBody) as Map<String, dynamic>;
        errorMessage = errorJson['detail'] ?? errorJson['message'] ?? 'Unknown error';
      } catch (e) {
        errorMessage = 'Request failed with status: $statusCode';
      }
      throw ApiException(
        errorMessage,
        statusCode: statusCode,
        rawResponse: responseBody,
      );
    }
  }

  void _logRequest(String method, Uri uri, {dynamic body, String? context}) {
    if (kDebugMode) {
      developer.log(
        '→ $method ${uri.toString()}${body != null ? ' | Body: ${json.encode(body)}' : ''}',
        name: 'ApiClient${context != null ? '/$context' : ''}',
      );
    }
  }
  void _logResponse(http.Response response, {String? context}) {
    if (kDebugMode) {
      developer.log(
        '← ${response.statusCode} ${response.reasonPhrase} | URL: ${response.request?.url} | Body: ${response.body}',
        name: 'ApiClient${context != null ? '/$context' : ''}',
      );
    }
  }
  void _logError(String method, Uri uri, dynamic error, {String? context}) {
    if (kDebugMode) {
      developer.log(
        '✖ $method ${uri.toString()} | Error: $error',
        name: 'ApiClient${context != null ? '/$context' : ''}',
        error: error,
      );
    }
  }

  // Dispose method to close the HTTP client
  void dispose() {
    _httpClient.close();
  }
}

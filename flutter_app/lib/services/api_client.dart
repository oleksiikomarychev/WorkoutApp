import 'dart:convert';
import 'dart:developer' as developer;
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../config/api_config.dart';
class ApiClient {
  final String baseUrl;
  final http.Client _httpClient;
  final Map<String, String> _defaultHeaders;
  ApiClient({
    String? baseUrl,
    http.Client? httpClient,
    Map<String, String>? defaultHeaders,
  }) : 
    baseUrl = baseUrl ?? ApiConfig.getBaseUrl(),
    _httpClient = httpClient ?? http.Client(),
    _defaultHeaders = defaultHeaders ?? {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  factory ApiClient.create() {
    return ApiClient(
      baseUrl: ApiConfig.getBaseUrl(),
    );
  }
  Future<dynamic> get(String endpoint, {Map<String, dynamic>? queryParams, String? context}) async {
    final uri = _buildUri(endpoint, queryParams);
    _logRequest('GET', uri, context: context);
    try {
      print('Making GET request to: ${uri.toString()}');
      final response = await _httpClient.get(
        uri,
        headers: _defaultHeaders,
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
    final uri = _buildUri(endpoint, queryParams);
    _logRequest('POST', uri, body: data, context: context);
    try {
      final response = await _httpClient.post(
        uri,
        headers: _defaultHeaders,
        body: json.encode(data),
      );
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('POST', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> put(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final uri = _buildUri(endpoint, queryParams);
    _logRequest('PUT', uri, body: data, context: context);
    try {
      final response = await _httpClient.put(
        uri,
        headers: _defaultHeaders,
        body: json.encode(data),
      );
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('PUT', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> delete(String endpoint, {Map<String, dynamic>? queryParams, String? context}) async {
    final uri = _buildUri(endpoint, queryParams);
    _logRequest('DELETE', uri, context: context);
    try {
      final response = await _httpClient.delete(
        uri,
        headers: _defaultHeaders,
      );
      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('DELETE', uri, e, context: context);
      rethrow;
    }
  }
  Uri _buildUri(String endpoint, Map<String, dynamic>? queryParams) {
    final uri = Uri.parse('$baseUrl$endpoint');
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(
        queryParameters: queryParams.map((key, value) => MapEntry(key, value.toString())),
      );
    }
    return uri;
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
  dynamic _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) {
        return null;
      }
      try {
        return json.decode(response.body);
      } catch (e) {
        return response.body;
      }
    } else {
      try {
        final error = json.decode(response.body);
        throw ApiException(
          statusCode: response.statusCode,
          message: error['detail'] ?? 'An error occurred',
          rawError: error,
        );
      } catch (e) {
        throw ApiException(
          statusCode: response.statusCode,
          message: 'An error occurred',
          rawResponse: response.body,
        );
      }
    }
  }
}
class ApiException implements Exception {
  final int statusCode;
  final String message;
  final dynamic rawError;
  final String? rawResponse;
  ApiException({
    required this.statusCode, 
    required this.message, 
    this.rawError, 
    this.rawResponse,
  });
  @override
  String toString() {
    return 'ApiException: $statusCode - $message';
  }
}

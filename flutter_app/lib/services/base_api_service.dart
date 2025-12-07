import 'dart:convert';
import 'package:http/http.dart';
import 'package:flutter/foundation.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/logger_service.dart';

abstract class BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('BaseApiService');

  BaseApiService(this._apiClient);



  @protected
  ApiClient get apiClient => _apiClient;

  Never handleError(String message, dynamic error, [StackTrace? stackTrace]) {

    if (error != null) {
      _logger.e('$message: ${error.toString()}');
      if (stackTrace != null) {
        _logger.e('Stack trace: $stackTrace');
      }
    } else {
      _logger.e('$message: No error details provided');
      if (stackTrace != null) {
        _logger.e('Stack trace: $stackTrace');
      }
    }

    if (error is Response) {
      throw ApiException.fromResponse(error);
    } else if (error is ApiException) {

      throw error;
    } else if (error is Exception) {

      throw ApiException(
        error.toString(),
        statusCode: 0,
        rawError: error,
      );
    } else {

      throw ApiException(
        error?.toString() ?? 'Unknown error occurred',
        statusCode: 0,
        rawError: error,
      );
    }
  }

  Future<T> patch<T>(
    String endpoint,
    Map<String, dynamic> data,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('PATCH request to: $endpoint');
      _logger.d('Request data: $data');

      final response = await _apiClient.patch(
        endpoint,
        data,
        queryParams: queryParams,
      );

      if (response is Map<String, dynamic>) {
        return fromJson(response);
      } else {
        throw Exception('Unexpected response format: expected Map<String, dynamic>');
      }
    } catch (e) {
      throw handleError('Failed to patch at $endpoint', e);
    }
  }

  Future<T?> getOptional<T>(
    String endpoint,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('GET (optional) request to: $endpoint');
      final response = await _apiClient.get(
        endpoint,
        queryParams: queryParams,
      );

      if (response == null) {
        return null;
      }

      if (response is Map<String, dynamic>) {
        return fromJson(response);
      } else {


        throw Exception('Unexpected response format for optional GET: expected Map or null');
      }
    } catch (e) {
      throw handleError('Failed to fetch optional data from $endpoint', e);
    }
  }

  Future<T> get<T>(String endpoint, T Function(Map<String, dynamic>) fromJson) async {
    try {
      _logger.d('GET request to: $endpoint');
      final response = await _apiClient.get(endpoint);

      if (response is Map<String, dynamic>) {
        return fromJson(response);
      } else {
        throw Exception('Unexpected response format: expected Map<String, dynamic>');
      }
    } catch (e) {
      throw handleError('Failed to fetch data from $endpoint', e);
    }
  }

  Future<List<T>> getList<T>(
    String endpoint,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('GET list request to: $endpoint');
      final response = await _apiClient.get(
        endpoint,
        queryParams: queryParams,
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((item) => fromJson(item))
            .toList();
      } else if (response is Map<String, dynamic>) {

        return [fromJson(response)];
      } else {
        throw Exception('Unexpected response format: expected List or Map');
      }
    } catch (e) {
      throw handleError('Failed to fetch list from $endpoint', e);
    }
  }

  Future<T> post<T>(
    String endpoint,
    dynamic data,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('POST request to: $endpoint');
      _logger.d('Request data: $data');

      final response = await _apiClient.post(
        endpoint,
        data,
        queryParams: queryParams,
      );

      if (response is Map<String, dynamic>) {
        return fromJson(response);
      } else {
        throw Exception('Unexpected response format: expected Map<String, dynamic>');
      }
    } catch (e) {
      throw handleError('Failed to post to $endpoint', e);
    }
  }

  Future<T> put<T>(
    String endpoint,
    Map<String, dynamic> data,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('PUT request to: $endpoint');
      _logger.d('Request data: $data');

      final response = await _apiClient.put(
        endpoint,
        data,
        queryParams: queryParams,
      );

      if (response is Map<String, dynamic>) {
        return fromJson(response);
      } else {
        throw Exception('Unexpected response format: expected Map<String, dynamic>');
      }
    } catch (e) {
      throw handleError('Failed to update at $endpoint', e);
    }
  }

  Future<bool> delete(
    String endpoint, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      _logger.d('DELETE request to: $endpoint');

      await _apiClient.delete(
        endpoint,
        queryParams: queryParams,
      );

      return true;
    } catch (e) {
      throw handleError('Failed to delete at $endpoint', e);
    }
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;
  final dynamic rawError;
  final String? rawResponse;

  ApiException(
    this.message, {
    required this.statusCode,
    this.rawError,
    this.rawResponse,
  });

  factory ApiException.fromResponse(Response response) {
    try {
      final errorBody = jsonDecode(response.body) as Map<String, dynamic>;
      return ApiException(
        errorBody['detail'] ?? errorBody['message'] ?? 'An error occurred',
        statusCode: response.statusCode,
        rawError: errorBody,
        rawResponse: response.body,
      );
    } catch (_) {
      return ApiException(
        'Request failed with status: ${response.statusCode}',
        statusCode: response.statusCode,
        rawResponse: response.body,
      );
    }
  }

  @override
  String toString() {
    return 'ApiException: $message (Status: $statusCode)';
  }
}

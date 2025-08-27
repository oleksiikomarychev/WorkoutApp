import 'dart:convert';
import 'package:http/http.dart';
import 'package:flutter/foundation.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/logger_service.dart';

/// Base class for API services to provide common functionality
abstract class BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('BaseApiService');

  BaseApiService(this._apiClient);

  /// Expose the underlying ApiClient to subclasses when they need
  /// lower-level control (e.g., to handle null/empty responses manually).
  @protected
  ApiClient get apiClient => _apiClient;

  /// Handles API errors and throws appropriate exceptions
  Never handleError(String message, dynamic error, [StackTrace? stackTrace]) {
    // Log the error with the message and stack trace
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
      // Re-throw if it's already an ApiException
      throw error;
    } else if (error is Exception) {
      // Wrap other exceptions in an ApiException
      throw ApiException(
        error.toString(),
        statusCode: 0, // 0 indicates a client-side error
        rawError: error,
      );
    } else {
      // Handle any other error type
      throw ApiException(
        error?.toString() ?? 'Unknown error occurred',
        statusCode: 0, // 0 indicates a client-side error
        rawError: error,
      );
    }
  }

  /// Generic GET request handler that may return null
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
        // If backend returns literal null, response will be null (handled above)
        // Any other unexpected format should throw
        throw Exception('Unexpected response format for optional GET: expected Map or null');
      }
    } catch (e) {
      throw handleError('Failed to fetch optional data from $endpoint', e);
    }
  }

  /// Generic GET request handler
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

  /// Generic GET list request handler
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
        // Handle case where the API returns a single item instead of a list
        return [fromJson(response)];
      } else {
        throw Exception('Unexpected response format: expected List or Map');
      }
    } catch (e) {
      throw handleError('Failed to fetch list from $endpoint', e);
    }
  }

  /// Generic POST request handler
  Future<T> post<T>(
    String endpoint, 
    Map<String, dynamic> data, 
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

  /// Generic PUT request handler
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

  /// Generic DELETE request handler
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
      
      return true; // Success
    } catch (e) {
      throw handleError('Failed to delete at $endpoint', e);
    }
  }
}

/// Custom exception class for API errors
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

  /// Factory constructor for creating an ApiException from a Response object
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

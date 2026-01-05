import 'dart:convert';
import 'dart:developer' as developer;
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../config/api_config.dart';
import 'logger_service.dart';
import 'base_api_service.dart';
import 'local_cache_store.dart';

class ApiClient {
  final http.Client _httpClient;
  final Map<String, String> _defaultHeaders;
  final LoggerService _logger = LoggerService('ApiClient');

  static LocalCacheStore? _cache;

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

  String _truncateForLog(String value, {int maxLen = 800}) {
    if (value.length <= maxLen) return value;
    return '${value.substring(0, maxLen)}…(truncated ${value.length - maxLen} chars)';
  }

  Future<dynamic> postMultipart(
    String endpoint, {
    Map<String, dynamic>? queryParams,
    required List<int> bytes,
    required String fileField,
    required String filename,
    MediaType? contentType,
    String? context,
    Duration timeout = const Duration(seconds: 30),
  }) async {
    final uri = _buildUri(endpoint, queryParams: queryParams);

    Future<dynamic> sendOnce({required bool forceRefresh}) async {
      final authHeaders = await _getHeaders(forceRefresh: forceRefresh);
      final headers = <String, String>{
        if (authHeaders['Authorization'] != null) 'Authorization': authHeaders['Authorization']!,
        'Accept': 'application/json',
      };

      final request = http.MultipartRequest('POST', uri);
      request.headers.addAll(headers);
      request.files.add(
        http.MultipartFile.fromBytes(
          fileField,
          bytes,
          filename: filename,
          contentType: contentType,
        ),
      );

      final streamed = await request.send().timeout(timeout);
      final response = await http.Response.fromStream(streamed);
      _logResponse(response, context: context);
      return _handleResponse(response);
    }

    _logRequest('POST(multipart)', uri, context: context);
    try {
      final result = await sendOnce(forceRefresh: false);
      return result;
    } catch (e) {
      if (e is ApiException && e.statusCode == 401) {
        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          return await sendOnce(forceRefresh: true);
        } catch (e2) {
          _logError('POST(multipart/retry)', uri, e2, context: context);
          rethrow;
        }
      }
      _logError('POST(multipart)', uri, e, context: context);
      rethrow;
    }
  }

  Future<LocalCacheStore> _getCache() async {
    final existing = _cache;
    if (existing != null) return existing;
    final created = await LocalCacheStore.instance();
    _cache = created;
    return created;
  }

  Uri _buildUri(
    String endpoint, {
    Map<String, dynamic>? queryParams,
  }) {
    final url = ApiConfig.buildFullUrl(endpoint);
    final base = Uri.parse(url);
    if (queryParams == null || queryParams.isEmpty) {
      return base;
    }

    final merged = <String, String>{...base.queryParameters};
    for (final entry in queryParams.entries) {
      final key = entry.key;
      final value = entry.value;
      if (key.trim().isEmpty || value == null) continue;
      merged[key] = value.toString();
    }
    return base.replace(queryParameters: merged);
  }

  String? _currentUserIdForCache() {
    try {
      return FirebaseAuth.instance.currentUser?.uid;
    } catch (_) {
      return null;
    }
  }

  String _cacheNamespace(String baseUrl, String userId) {
    return '${Uri.encodeComponent(baseUrl)}:${Uri.encodeComponent(userId)}';
  }

  String _cacheKeyForRequest({
    required String method,
    required Uri uri,
    required String baseUrl,
    required String userId,
  }) {
    final ns = _cacheNamespace(baseUrl, userId);

    final qp = uri.queryParametersAll;
    final parts = <String>[];
    final keys = qp.keys.toList()..sort();
    for (final k in keys) {
      final values = (qp[k] ?? []).toList()..sort();
      for (final v in values) {
        parts.add('${Uri.encodeQueryComponent(k)}=${Uri.encodeQueryComponent(v)}');
      }
    }
    final canonical = parts.join('&');
    final requestId = canonical.isEmpty ? uri.path : '${uri.path}?$canonical';
    final encodedRequestId = Uri.encodeComponent(requestId);

    return 'cache:v1:$ns:$method:$encodedRequestId';
  }

  List<String> _namespacedGroups(
    Iterable<String> groups, {
    required String baseUrl,
    required String userId,
  }) {
    final ns = _cacheNamespace(baseUrl, userId);
    final out = <String>[];
    for (final g in groups) {
      final trimmed = g.trim();
      if (trimmed.isEmpty) continue;
      out.add('cache_group:v1:$ns:$trimmed');
    }
    return out;
  }

  Future<void> invalidateCacheGroups(Iterable<String> groups) async {
    final userId = _currentUserIdForCache();
    if (userId == null || userId.isEmpty) return;
    final baseUrl = ApiConfig.getBaseUrl();
    final store = await _getCache();
    await store.invalidateGroups(
      _namespacedGroups(groups, baseUrl: baseUrl, userId: userId),
    );
  }

  Future<void> clearCacheForCurrentUser() async {
    final userId = _currentUserIdForCache();
    if (userId == null || userId.isEmpty) return;
    final baseUrl = ApiConfig.getBaseUrl();
    final ns = _cacheNamespace(baseUrl, userId);
    final store = await _getCache();
    await store.clearByPrefix('cache:v1:$ns:');
    await store.clearByPrefix('cache_index:v1:cache_group:v1:$ns:');
  }
  Future<dynamic> patch(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final url = ApiConfig.buildFullUrl(endpoint);
    final uri = Uri.parse(url).replace(queryParameters: queryParams);

    _logRequest('PATCH', uri, body: data, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _getHeaders(),
      };
      final response = await _httpClient.patch(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 401) {
        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          final retryHeaders = {
            ..._defaultHeaders,
            ...await _getHeaders(forceRefresh: true),
          };
          final retryResponse = await _httpClient
              .patch(
                uri,
                headers: retryHeaders,
                body: json.encode(data),
              )
              .timeout(const Duration(seconds: 10));
          _logResponse(retryResponse, context: context);
          return _handleResponse(retryResponse);
        } catch (e) {
          _logError('PATCH(retry)', uri, e, context: context);
        }
      }

      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('PATCH', uri, e, context: context);
      rethrow;
    }
  }

  Stream<dynamic> getSWR(
    String endpoint, {
    Map<String, dynamic>? queryParams,
    String? context,
    required int ttlSeconds,
    List<String> groups = const [],
    bool emitExpired = true,
    bool skipNetworkIfFresh = false,
    Duration timeout = const Duration(seconds: 10),
  }) async* {
    final userId = _currentUserIdForCache();
    final baseUrl = ApiConfig.getBaseUrl();

    final uri = _buildUri(endpoint, queryParams: queryParams);

    bool yieldedCache = false;
    bool cachedWasFresh = false;
    String? cachedFingerprint;

    if (userId != null && userId.isNotEmpty) {
      try {
        final store = await _getCache();
        final cacheKey = _cacheKeyForRequest(method: 'GET', uri: uri, baseUrl: baseUrl, userId: userId);
        final entry = await store.getEntry(cacheKey);
        if (entry != null && entry.data != null && (emitExpired || !entry.isExpired)) {
          yieldedCache = true;
          cachedWasFresh = !entry.isExpired;
          try {
            cachedFingerprint = jsonEncode(entry.data);
          } catch (_) {
            cachedFingerprint = null;
          }
          yield entry.data;
        }
      } catch (_) {
        yieldedCache = false;
        cachedWasFresh = false;
        cachedFingerprint = null;
      }
    }

    if (yieldedCache && cachedWasFresh && skipNetworkIfFresh) {
      return;
    }

    try {
      final fresh = await get(
        endpoint,
        queryParams: queryParams,
        context: context,
        timeout: timeout,
      );

      if (fresh != null && userId != null && userId.isNotEmpty) {
        try {
          final store = await _getCache();
          final cacheKey = _cacheKeyForRequest(method: 'GET', uri: uri, baseUrl: baseUrl, userId: userId);
          await store.setEntry(
            cacheKey,
            fresh,
            ttlSeconds: ttlSeconds,
            groups: _namespacedGroups(groups, baseUrl: baseUrl, userId: userId),
          );
        } catch (_) {}
      }

      if (!yieldedCache) {
        yield fresh;
        return;
      }

      String? freshFingerprint;
      try {
        freshFingerprint = jsonEncode(fresh);
      } catch (_) {
        freshFingerprint = null;
      }

      if (cachedFingerprint == null || freshFingerprint == null || cachedFingerprint != freshFingerprint) {
        yield fresh;
      }
    } catch (e) {
      if (!yieldedCache) {
        rethrow;
      }
    }
  }
  Future<Map<String, String>> _getHeaders({bool forceRefresh = false}) async {
    String? idToken;
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        idToken = await user.getIdToken(forceRefresh);
      }
    } catch (e) {

    }

    return {
      'Content-Type': 'application/json',
      if (idToken != null) 'Authorization': 'Bearer $idToken',
    };
  }

  Future<dynamic> get(
    String endpoint, {
    Map<String, dynamic>? queryParams,
    String? context,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final uri = _buildUri(endpoint, queryParams: queryParams);

    _logRequest('GET', uri, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _getHeaders(),
      };
      final response = await _httpClient.get(
        uri,
        headers: headers,
      ).timeout(timeout);

      if (kDebugMode) {
        _logger.d('GET ${uri.toString()} -> ${response.statusCode}');
        _logger.d('GET body: ${_truncateForLog(response.body)}');
      }

      if (response.statusCode == 401) {

        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          final retryHeaders = {
            ..._defaultHeaders,
            ...await _getHeaders(forceRefresh: true),
          };
          final retryResponse = await _httpClient
              .get(uri, headers: retryHeaders)
              .timeout(timeout);
          _logResponse(retryResponse, context: context);
          return _handleResponse(retryResponse);
        } catch (e) {
          _logError('GET(retry)', uri, e, context: context);
        }
      }

      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('GET', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> post(
    String endpoint,
    dynamic data, {
    Map<String, dynamic>? queryParams,
    String? context,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final uri = _buildUri(endpoint, queryParams: queryParams);

    _logRequest('POST', uri, body: data, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _getHeaders(),
      };

      if (kDebugMode) {
        _logger.d('POST ${uri.toString()}');
        try {
          _logger.d('POST body: ${_truncateForLog(json.encode(data))}');
        } catch (_) {}
      }

      final response = await _httpClient.post(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(timeout);

      if (kDebugMode) {
        _logger.d('POST ${uri.toString()} -> ${response.statusCode}');
        _logger.d('POST body: ${_truncateForLog(response.body)}');
      }

      if (response.statusCode == 401) {
        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          final retryHeaders = {
            ..._defaultHeaders,
            ...await _getHeaders(forceRefresh: true),
          };
          final retryResponse = await _httpClient
              .post(
                uri,
                headers: retryHeaders,
                body: json.encode(data),
              )
              .timeout(timeout);
          _logResponse(retryResponse, context: context);
          return _handleResponse(retryResponse);
        } catch (e) {
          _logError('POST(retry)', uri, e, context: context);
        }
      }

      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('POST', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> put(String endpoint, Map<String, dynamic> data, {Map<String, dynamic>? queryParams, String? context}) async {
    final uri = _buildUri(endpoint, queryParams: queryParams);

    _logRequest('PUT', uri, body: data, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _getHeaders(),
      };
      final response = await _httpClient.put(
        uri,
        headers: headers,
        body: json.encode(data),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 401) {
        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          final retryHeaders = {
            ..._defaultHeaders,
            ...await _getHeaders(forceRefresh: true),
          };
          final retryResponse = await _httpClient
              .put(
                uri,
                headers: retryHeaders,
                body: json.encode(data),
              )
              .timeout(const Duration(seconds: 10));
          _logResponse(retryResponse, context: context);
          return _handleResponse(retryResponse);
        } catch (e) {
          _logError('PUT(retry)', uri, e, context: context);
        }
      }

      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e) {
      _logError('PUT', uri, e, context: context);
      rethrow;
    }
  }
  Future<dynamic> delete(String endpoint, {Map<String, dynamic>? queryParams, String? context}) async {
    final uri = _buildUri(endpoint, queryParams: queryParams);

    _logRequest('DELETE', uri, context: context);
    try {
      final headers = {
        ..._defaultHeaders,
        ...await _getHeaders(),
      };

      final response = await _httpClient.delete(
        uri,
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (kDebugMode) {
        _logger.d('DELETE ${uri.toString()} -> ${response.statusCode}');
        _logger.d('DELETE body: ${_truncateForLog(response.body)}');
      }

      if (response.statusCode == 401) {
        try {
          await FirebaseAuth.instance.currentUser?.getIdToken(true);
          final retryHeaders = {
            ..._defaultHeaders,
            ...await _getHeaders(forceRefresh: true),
          };
          final retryResponse = await _httpClient
              .delete(
                uri,
                headers: retryHeaders,
              )
              .timeout(const Duration(seconds: 10));
          _logResponse(retryResponse, context: context);
          return _handleResponse(retryResponse);
        } catch (e, stackTrace) {
          print('Error in DELETE(retry) request to $uri: $e');
          _logError('DELETE(retry)', uri, e, context: context);
        }
      }

      _logResponse(response, context: context);
      return _handleResponse(response);
    } catch (e, stackTrace) {
      print('Error in DELETE request to $uri: $e');
      print('Stack trace: $stackTrace');
      _logError('DELETE', uri, e, context: context);
      rethrow;
    }
  }

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


  void dispose() {
    _httpClient.close();
  }
}

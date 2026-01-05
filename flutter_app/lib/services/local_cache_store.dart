import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class CacheEntry {
  final dynamic data;
  final bool isExpired;
  final int savedAtEpochSeconds;
  final int ttlSeconds;

  CacheEntry({
    required this.data,
    required this.isExpired,
    required this.savedAtEpochSeconds,
    required this.ttlSeconds,
  });
}

class LocalCacheStore {
  static const int _schemaVersion = 1;
  static const int _maxPayloadChars = 500000;

  static LocalCacheStore? _instance;
  final SharedPreferences _prefs;

  LocalCacheStore._(this._prefs);

  static Future<LocalCacheStore> instance() async {
    final existing = _instance;
    if (existing != null) return existing;
    final prefs = await SharedPreferences.getInstance();
    final created = LocalCacheStore._(prefs);
    _instance = created;
    return created;
  }

  Future<CacheEntry?> getEntry(String key) async {
    final raw = _prefs.getString(key);
    if (raw == null || raw.isEmpty) return null;

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) return null;

      final v = decoded['v'];
      if (v is! int || v != _schemaVersion) return null;

      final savedAt = decoded['savedAt'];
      final ttl = decoded['ttlSeconds'];
      final data = decoded['data'];

      if (savedAt is! int || ttl is! int) return null;

      final now = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
      final isExpired = (ttl > 0) ? (savedAt + ttl) <= now : false;

      return CacheEntry(
        data: data,
        isExpired: isExpired,
        savedAtEpochSeconds: savedAt,
        ttlSeconds: ttl,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> setEntry(
    String key,
    dynamic data, {
    required int ttlSeconds,
    List<String> groups = const [],
  }) async {
    final now = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;

    final payload = <String, dynamic>{
      'v': _schemaVersion,
      'savedAt': now,
      'ttlSeconds': ttlSeconds,
      'data': data,
    };

    final encoded = jsonEncode(payload);
    if (encoded.length > _maxPayloadChars) {
      return;
    }

    await _prefs.setString(key, encoded);

    if (groups.isEmpty) return;
    for (final group in groups) {
      if (group.trim().isEmpty) continue;
      await _addToGroupIndex(group.trim(), key);
    }
  }

  Future<void> invalidateGroup(String group) async {
    final indexKey = _indexKey(group);
    final raw = _prefs.getString(indexKey);
    if (raw == null || raw.isEmpty) return;

    List<dynamic> keys;
    try {
      final decoded = jsonDecode(raw);
      keys = decoded is List ? decoded : const [];
    } catch (_) {
      keys = const [];
    }

    for (final k in keys) {
      if (k is String && k.isNotEmpty) {
        await _prefs.remove(k);
      }
    }

    await _prefs.remove(indexKey);
  }

  Future<void> invalidateGroups(Iterable<String> groups) async {
    for (final g in groups) {
      if (g.trim().isEmpty) continue;
      await invalidateGroup(g.trim());
    }
  }

  Future<void> invalidateByPrefix(String prefix) async {
    final keys = _prefs.getKeys();
    for (final k in keys) {
      if (k.startsWith(prefix)) {
        await _prefs.remove(k);
      }
    }
  }

  Future<void> clearByPrefix(String prefix) async {
    await invalidateByPrefix(prefix);
  }

  String _indexKey(String group) => 'cache_index:v$_schemaVersion:$group';

  Future<void> _addToGroupIndex(String group, String dataKey) async {
    final indexKey = _indexKey(group);

    final raw = _prefs.getString(indexKey);
    final existing = <String>{};

    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          for (final v in decoded) {
            if (v is String && v.isNotEmpty) existing.add(v);
          }
        }
      } catch (_) {}
    }

    if (existing.add(dataKey)) {
      await _prefs.setString(indexKey, jsonEncode(existing.toList()));
    }
  }
}

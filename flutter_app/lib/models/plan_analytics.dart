import 'package:collection/collection.dart';

class PlanAnalyticsItem {
  final int workoutId;
  final int? orderIndex;
  final DateTime? date;
  final Map<String, double> metrics;

  const PlanAnalyticsItem({
    required this.workoutId,
    this.orderIndex,
    this.date,
    required this.metrics,
  });

  factory PlanAnalyticsItem.fromJson(Map<String, dynamic> json) {
    final rawMetrics = json['metrics'];
    final metrics = <String, double>{};
    if (rawMetrics is Map<String, dynamic>) {
      rawMetrics.forEach((key, value) {
        final parsed = _toDouble(value);
        if (parsed != null) metrics[key] = parsed;
      });
    }
    return PlanAnalyticsItem(
      workoutId: (json['workout_id'] as num).toInt(),
      orderIndex: (json['order_index'] as num?)?.toInt(),
      date: _parseDate(json['date']),
      metrics: UnmodifiableMapView(metrics),
    );
  }

  static DateTime? _parseDate(dynamic value) {
    if (value is String && value.isNotEmpty) {
      return DateTime.tryParse(value);
    }
    return null;
  }

  static double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }
}

class PlanAnalyticsResponse {
  final List<PlanAnalyticsItem> items;
  final Map<String, double> totals;

  const PlanAnalyticsResponse({
    required this.items,
    required this.totals,
  });

  factory PlanAnalyticsResponse.fromJson(Map<String, dynamic> json) {
    final itemsJson = json['items'];
    final totalsJson = json['totals'];
    final itemList = <PlanAnalyticsItem>[];
    if (itemsJson is List) {
      for (final item in itemsJson.whereType<Map<String, dynamic>>()) {
        itemList.add(PlanAnalyticsItem.fromJson(item));
      }
    }
    final totalsMap = <String, double>{};
    if (totalsJson is Map<String, dynamic>) {
      totalsJson.forEach((key, value) {
        final parsed = PlanAnalyticsItem._toDouble(value);
        if (parsed != null) totalsMap[key] = parsed;
      });
    }
    return PlanAnalyticsResponse(
      items: List.unmodifiable(itemList),
      totals: UnmodifiableMapView(totalsMap),
    );
  }
}

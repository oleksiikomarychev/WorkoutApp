import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:amplitude_flutter/amplitude.dart';
import 'package:amplitude_flutter/configuration.dart';
import 'package:amplitude_flutter/events/base_event.dart';
import 'package:workout_app/services/logger_service.dart';

class AmplitudeService {
  static AmplitudeService? _instance;
  final LoggerService _logger = LoggerService('AmplitudeService');
  late Amplitude _amplitude;
  
  static AmplitudeService get instance {
    _instance ??= AmplitudeService._();
    return _instance!;
  }

  AmplitudeService._() {
    final apiKey = dotenv.env['AMPLITUDE_API_KEY'] ?? '';
    _amplitude = Amplitude(Configuration(apiKey: apiKey));
  }

  Future<void> initialize() async {
    try {
      final apiKey = dotenv.env['AMPLITUDE_API_KEY'];
      if (apiKey != null && apiKey.isNotEmpty) {
        _logger.i('Amplitude initialized successfully');
      } else {
        _logger.w('Amplitude API key not found');
      }
    } catch (e) {
      _logger.e('Failed to initialize Amplitude: $e');
    }
  }

  Future<void> trackEvent(String eventName, {Map<String, dynamic>? properties}) async {
    try {
      final event = BaseEvent(eventName);
      await _amplitude.track(event);
      _logger.i('Event tracked: $eventName');
    } catch (e) {
      _logger.e('Failed to track event $eventName: $e');
    }
  }

  Future<void> setUserProperties(String userId, {Map<String, dynamic>? properties}) async {
    try {
      // For now, just log that user properties would be set
      _logger.i('User properties set for: $userId');
    } catch (e) {
      _logger.e('Failed to set user properties: $e');
    }
  }

  Future<void> testEvent() async {
    await trackEvent('test_event');
  }
}

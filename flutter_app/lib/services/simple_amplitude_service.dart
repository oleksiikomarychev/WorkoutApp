import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:amplitude_flutter/amplitude.dart';
import 'package:amplitude_flutter/configuration.dart';
import 'package:amplitude_flutter/events/base_event.dart';

class SimpleAmplitudeService {
  static SimpleAmplitudeService? _instance;
  late Amplitude _amplitude;
  
  static SimpleAmplitudeService get instance {
    _instance ??= SimpleAmplitudeService._();
    return _instance!;
  }

  SimpleAmplitudeService._() {
    final apiKey = dotenv.env['AMPLITUDE_API_KEY'] ?? '';
    _amplitude = Amplitude(Configuration(apiKey: apiKey));
  }

  void track(String eventName) {
    final event = BaseEvent(eventName);
    _amplitude.track(event);
  }
}

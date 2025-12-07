import 'package:flutter/foundation.dart' show kIsWeb, defaultTargetPlatform, TargetPlatform;
import 'package:flutter_dotenv/flutter_dotenv.dart';


class ChatConfig {
  static const String _defaultLocalUrl = 'ws://localhost:8006';
  static const String _androidEmulatorUrl = 'ws://10.0.2.2:8006';
  static const String _productionUrl = 'wss://agent.yourproductiondomain.com';


  static const String _overrideUrl = String.fromEnvironment('CHAT_WS_URL', defaultValue: '');


  static String getBaseUrl() {
    final envUrl = dotenv.maybeGet('CHAT_WS_URL') ?? '';

    if (_overrideUrl.isNotEmpty) {
      return _overrideUrl;
    }

    if (envUrl.isNotEmpty) {
      return envUrl;
    }

    if (kIsWeb) {
      return _defaultLocalUrl;
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return _androidEmulatorUrl;
    }

    return _defaultLocalUrl;
  }


  static Uri chatUri() {
    final base = getBaseUrl();
    final normalized = base.endsWith('/') ? base.substring(0, base.length - 1) : base;
    return Uri.parse('$normalized/chat/ws');
  }


  static String get productionUrl => _productionUrl;
}

import 'dart:convert';
import 'dart:developer' as developer;

class LoggerService {
  final String _context;

  LoggerService(this._context);

  void log(String message, {String level = 'info', dynamic error, StackTrace? stackTrace}) {
    developer.log(
      '$level [$_context]: $message',
      name: 'WorkoutApp',
      error: error,
      stackTrace: stackTrace,
    );
  }

  void v(String message) => log(message, level: 'verbose');
  void d(String message) {
    log(message, level: 'DEBUG');
  }

  void i(String message) {
    log(message, level: 'INFO');
  }

  void w(String message, [dynamic error, StackTrace? stackTrace]) {
    log(message, level: 'WARNING', error: error, stackTrace: stackTrace);
  }

  void e(String message, [dynamic error, StackTrace? stackTrace]) {
    log(message, level: 'ERROR', error: error, stackTrace: stackTrace);
  }
  void wtf(String message) => log(message, level: 'wtf');

  void json(String message, dynamic json) {
    try {
      final prettyString = json.toString();
      log('$message\n$prettyString', level: 'info');
    } catch (e) {
      log('Failed to convert JSON to string: $e', level: 'error');
    }
  }

  void request({
    required String method,
    required String url,
    Map<String, dynamic>? headers,
    dynamic body,
    Map<String, dynamic>? queryParameters,
  }) {
    final buffer = StringBuffer();
    buffer.writeln('\n════════════════════════════════════════');
    buffer.writeln('⬆️ REQUEST: $method $url');

    if (queryParameters != null && queryParameters.isNotEmpty) {
      buffer.writeln('Query Parameters:');
      queryParameters.forEach((key, value) {
        buffer.writeln('  $key: $value');
      });
    }

    if (headers != null && headers.isNotEmpty) {
      buffer.writeln('Headers:');
      headers.forEach((key, value) {
        if (key.toLowerCase() == 'authorization') {
          buffer.writeln('  $key: **********');
        } else {
          buffer.writeln('  $key: $value');
        }
      });
    }

    if (body != null) {
      buffer.writeln('Body:');
      buffer.writeln(body.toString());
    }

    buffer.writeln('════════════════════════════════════════\n');
    log(buffer.toString(), level: 'info');
  }

  void response({
    required String method,
    required String url,
    int? statusCode,
    Map<String, dynamic>? headers,
    dynamic body,
    Duration? duration,
  }) {
    final buffer = StringBuffer();
    buffer.writeln('\n════════════════════════════════════════');
    buffer.writeln('⬇️ RESPONSE: $method $url');

    if (statusCode != null) {
      final statusEmoji = statusCode >= 200 && statusCode < 300 ? '✅' : '❌';
      buffer.writeln('Status: $statusEmoji $statusCode');
    }

    if (duration != null) {
      buffer.writeln('Duration: ${duration.inMilliseconds}ms');
    }

    if (headers != null && headers.isNotEmpty) {
      buffer.writeln('Headers:');
      headers.forEach((key, value) {
        if (key.toLowerCase() == 'authorization') {
          buffer.writeln('  $key: **********');
        } else {
          buffer.writeln('  $key: $value');
        }
      });
    }

    if (body != null) {
      buffer.writeln('Body:');
      if (body is Map || body is List) {
        try {
          final prettyBody = jsonEncode(body);
          buffer.writeln(prettyBody);
        } catch (e) {
          buffer.writeln(body.toString());
        }
      } else {
        buffer.writeln(body.toString());
      }
    }

    buffer.writeln('════════════════════════════════════════\n');

    if (statusCode != null && statusCode >= 400) {
      log(buffer.toString(), level: 'error');
    } else {
      log(buffer.toString(), level: 'info');
    }
  }

  void error(
    String message, {
    dynamic error,
    StackTrace? stackTrace,
    bool showInRelease = false,
  }) {
    if (showInRelease) {



    }

    log(message, level: 'error');
  }
}

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status_codes;

import '../config/chat_config.dart';
import '../models/chat_message.dart';

/// Connection state for the chat service.
enum ChatConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

/// Events emitted by the chat service.
sealed class ChatEvent {
  const ChatEvent();
}

class SessionStartedEvent extends ChatEvent {
  const SessionStartedEvent(this.sessionId);

  final String sessionId;
}

class MessageReceivedEvent extends ChatEvent {
  const MessageReceivedEvent(this.message);

  final ChatMessage message;
}

class ConversationDoneEvent extends ChatEvent {
  const ConversationDoneEvent(this.sessionId);

  final String sessionId;
}

class ErrorEvent extends ChatEvent {
  const ErrorEvent(this.message);

  final String message;
}

class TypingEvent extends ChatEvent {
  const TypingEvent(this.isTyping);

  final bool isTyping;
}

/// Handles WebSocket connectivity, reconnection, and message parsing.
class ChatService {
  ChatService({
    Duration heartbeatInterval = const Duration(seconds: 30),
    Duration inactivityTimeout = const Duration(seconds: 45),
    Duration initialBackoff = const Duration(seconds: 1),
    Duration maxBackoff = const Duration(seconds: 30),
  })  : _heartbeatInterval = heartbeatInterval,
        _inactivityTimeout = inactivityTimeout,
        _initialBackoff = initialBackoff,
        _maxBackoff = maxBackoff;

  final Duration _heartbeatInterval;
  final Duration _inactivityTimeout;
  final Duration _initialBackoff;
  final Duration _maxBackoff;

  final StreamController<ChatEvent> _eventController =
      StreamController<ChatEvent>.broadcast();
  final StreamController<ChatConnectionState> _connectionController =
      StreamController<ChatConnectionState>.broadcast();

  WebSocketChannel? _channel;
  StreamSubscription? _channelSubscription;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  DateTime _lastMessageReceived = DateTime.now();
  Duration _currentBackoff = const Duration(seconds: 1);
  ChatConnectionState _connectionState = ChatConnectionState.disconnected;
  String? _sessionId;
  bool _manuallyClosed = false;

  Stream<ChatEvent> get events => _eventController.stream;
  Stream<ChatConnectionState> get connectionStream =>
      _connectionController.stream;
  ChatConnectionState get connectionState => _connectionState;
  String? get sessionId => _sessionId;

  Future<void> connect() async {
    if (_connectionState == ChatConnectionState.connecting ||
        _connectionState == ChatConnectionState.connected) {
      return;
    }

    _manuallyClosed = false;
    _setConnectionState(ChatConnectionState.connecting);
    await _openChannel();
  }

  Future<void> disconnect({bool graceful = true}) async {
    _manuallyClosed = true;
    _cancelHeartbeat();
    _cancelReconnectTimer();
    await _channelSubscription?.cancel();
    if (graceful) {
      await _channel?.sink.close(status_codes.goingAway);
    } else {
      await _channel?.sink.close();
    }
    _channel = null;
    _setConnectionState(ChatConnectionState.disconnected);
  }

  Future<void> retry() async {
    await disconnect(graceful: false);
    _currentBackoff = _initialBackoff;
    await connect();
  }

  Future<void> sendMessage(String content) async {
    if (_channel == null) {
      throw StateError('Cannot send message while channel is null');
    }

    final payload = jsonEncode({
      'type': 'message',
      'content': content,
    });

    try {
      _channel!.sink.add(payload);
      _eventController.add(
        MessageReceivedEvent(
          ChatMessage(
            id: DateTime.now().microsecondsSinceEpoch.toString(),
            role: ChatRole.user,
            content: content,
            timestamp: DateTime.now().toUtc(),
            sessionId: _sessionId ?? '',
          ),
        ),
      );
    } catch (e) {
      _eventController.add(ErrorEvent('Failed to send message: $e'));
      _scheduleReconnect();
    }
  }

  void dispose() {
    _manuallyClosed = true;
    _eventController.close();
    _connectionController.close();
    _cancelHeartbeat();
    _cancelReconnectTimer();
    _channelSubscription?.cancel();
    _channel?.sink.close();
  }

  Future<void> _openChannel() async {
    _cancelReconnectTimer();

    try {
      final uri = ChatConfig.chatUri();
      final channel = WebSocketChannel.connect(uri);
      _channel = channel;
      _setConnectionState(ChatConnectionState.connected);
      _currentBackoff = _initialBackoff;
      _lastMessageReceived = DateTime.now();
      _startHeartbeat();

      _channelSubscription = channel.stream.listen(
        _handleIncoming,
        onDone: _handleDone,
        onError: _handleError,
        cancelOnError: false,
      );
    } catch (e, stackTrace) {
      debugPrint('ChatService: failed to connect: $e\n$stackTrace');
      _setConnectionState(ChatConnectionState.error);
      _eventController.add(ErrorEvent('Failed to connect to chat: $e'));
      _scheduleReconnect();
    }
  }

  void _handleIncoming(dynamic data) {
    _lastMessageReceived = DateTime.now();

    try {
      final Map<String, dynamic> payload;
      if (data is String) {
        payload = jsonDecode(data) as Map<String, dynamic>;
      } else if (data is List<int>) {
        payload = jsonDecode(utf8.decode(data)) as Map<String, dynamic>;
      } else {
        throw const FormatException('Unsupported WebSocket payload type');
      }

      final type = payload['type']?.toString();
      switch (type) {
        case 'session_started':
          _sessionId = payload['session_id']?.toString();
          _eventController.add(SessionStartedEvent(_sessionId ?? ''));
        break;
        case 'message':
          final message = ChatMessage(
            id: DateTime.now().microsecondsSinceEpoch.toString(),
            role: roleFromString(payload['role']?.toString()),
            content: payload['content']?.toString() ?? '',
            timestamp: DateTime.now().toUtc(),
            sessionId: payload['session_id']?.toString() ?? _sessionId ?? '',
          );
          _eventController.add(MessageReceivedEvent(message));
          break;
        case 'done':
          final session = payload['session_id']?.toString() ?? _sessionId ?? '';
          _eventController.add(ConversationDoneEvent(session));
          break;
        case 'typing':
          final isTyping = payload['state'] == true ||
              payload['state']?.toString().toLowerCase() == 'true';
          _eventController.add(TypingEvent(isTyping));
          break;
        case 'error':
          final message = payload['message']?.toString() ?? 'Unknown error';
          _eventController.add(ErrorEvent(message));
          break;
        case 'pong':
          // Reset the last message time to prevent heartbeat timeout
          _lastMessageReceived = DateTime.now();
          break;
        default:
          debugPrint('ChatService: Unknown event type: $type');
      }
    } catch (e, stackTrace) {
      debugPrint('ChatService: Error parsing message: $e\n$stackTrace');
      _eventController.add(ErrorEvent('Malformed message received from server'));
    }}

  
  
  
  void _handleDone() {
    _cancelHeartbeat();
    if (_manuallyClosed) {
      _setConnectionState(ChatConnectionState.disconnected);
      return;
    }

    _setConnectionState(ChatConnectionState.reconnecting);
    _scheduleReconnect();
  }

  void _handleError(dynamic error, StackTrace stackTrace) {
    debugPrint('ChatService: WebSocket error: $error\n$stackTrace');
    _eventController.add(ErrorEvent('WebSocket error: $error'));
    _setConnectionState(ChatConnectionState.error);
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_manuallyClosed) {
      return;
    }

    _cancelReconnectTimer();
    final backoff = _currentBackoff;
    _setConnectionState(ChatConnectionState.reconnecting);
    _reconnectTimer = Timer(backoff, () async {
      if (_manuallyClosed) return;
      await _openChannel();
    });

    _currentBackoff = Duration(
      seconds: (_currentBackoff.inSeconds * 2).clamp(
        _initialBackoff.inSeconds,
        _maxBackoff.inSeconds,
      ),
    );
  }

  void _startHeartbeat() {
    _cancelHeartbeat();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      final sinceLastMessage = DateTime.now().difference(_lastMessageReceived);
      if (sinceLastMessage >= _inactivityTimeout) {
        debugPrint('ChatService: heartbeat timeout, reconnecting...');
        _scheduleReconnect();
      } else {
        try {
          _channel?.sink.add(jsonEncode({'type': 'ping'}));
        } catch (e) {
          debugPrint('ChatService: failed to send heartbeat: $e');
          _scheduleReconnect();
        }
      }
    });
  }

  void _cancelHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void _cancelReconnectTimer() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void _setConnectionState(ChatConnectionState state) {
    _connectionState = state;
    if (!_connectionController.isClosed) {
      _connectionController.add(state);
    }
  }
}

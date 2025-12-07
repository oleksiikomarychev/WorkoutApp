import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/chat_message.dart';
import '../services/chat_service.dart';

class ChatState {
  const ChatState({
    required this.messages,
    required this.connectionState,
    required this.isTyping,
    required this.sessionId,
    required this.errorMessage,
    required this.lastMassEditResult,
    required this.contextPayload,
  });

  factory ChatState.initial() => const ChatState(
        messages: <ChatMessage>[],
        connectionState: ChatConnectionState.disconnected,
        isTyping: false,
        sessionId: null,
        errorMessage: null,
        lastMassEditResult: null,
        contextPayload: null,
      );

  static const Object _noValue = Object();

  final List<ChatMessage> messages;
  final ChatConnectionState connectionState;
  final bool isTyping;
  final String? sessionId;
  final String? errorMessage;
  final Map<String, dynamic>? lastMassEditResult;
  final Map<String, dynamic>? contextPayload;

  ChatState copyWith({
    List<ChatMessage>? messages,
    ChatConnectionState? connectionState,
    bool? isTyping,
    Object? sessionId = _noValue,
    Object? errorMessage = _noValue,
    Object? lastMassEditResult = _noValue,
    Object? contextPayload = _noValue,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      connectionState: connectionState ?? this.connectionState,
      isTyping: isTyping ?? this.isTyping,
      sessionId:
          identical(sessionId, _noValue) ? this.sessionId : sessionId as String?,
      errorMessage: identical(errorMessage, _noValue)
          ? this.errorMessage
          : errorMessage as String?,
      lastMassEditResult: identical(lastMassEditResult, _noValue)
          ? this.lastMassEditResult
          : lastMassEditResult as Map<String, dynamic>?,
      contextPayload: identical(contextPayload, _noValue)
          ? this.contextPayload
          : contextPayload as Map<String, dynamic>?,
    );
  }
}

final chatServiceProvider = Provider<ChatService>((ref) {
  final service = ChatService();
  ref.onDispose(service.dispose);
  return service;
});

final chatControllerProvider =
    StateNotifierProvider<ChatController, ChatState>((ref) {
  final service = ref.watch(chatServiceProvider);
  final controller = ChatController(service);
  ref.onDispose(controller.dispose);
  return controller;
});

class ChatController extends StateNotifier<ChatState> {
  ChatController(this._service) : super(ChatState.initial()) {
    _eventSubscription = _service.events.listen(_handleEvent);
    _connectionSubscription =
        _service.connectionStream.listen(_handleConnectionState);

    _service.connect();
  }

  final ChatService _service;
  StreamSubscription<ChatEvent>? _eventSubscription;
  StreamSubscription<ChatConnectionState>? _connectionSubscription;

  Future<void> sendMessage(String content) async {
    if (content.trim().isEmpty) return;
    await _service.sendMessage(content.trim());
  }


  Future<void> sendContext(Map<String, dynamic> context) async {
    state = state.copyWith(contextPayload: context);
    await _service.sendContext(context);
  }

  Future<void> retry() async {
    await _service.retry();
  }

  Future<void> disconnect() async {
    await _service.disconnect();
  }

  Future<void> reconnect() async {
    await _service.retry();
  }

  void _handleEvent(ChatEvent event) {
    switch (event) {
      case SessionStartedEvent(:final sessionId):
        state = state.copyWith(
          sessionId: sessionId,
          messages: <ChatMessage>[],
          errorMessage: null,
          isTyping: false,
        );
      case MessageReceivedEvent(:final message):
        final updated = List<ChatMessage>.from(state.messages)
          ..add(message);
        final shouldStopTyping = message.role == ChatRole.assistant;
        state = state.copyWith(
          messages: updated,
          errorMessage: null,
          isTyping: shouldStopTyping ? false : state.isTyping,
        );
      case ConversationDoneEvent():
        state = state.copyWith(isTyping: false);
      case ErrorEvent(:final message):
        state = state.copyWith(errorMessage: message, isTyping: false);
      case TypingEvent(:final isTyping):
        state = state.copyWith(isTyping: isTyping);
      case MassEditResultEvent(:final payload):
        state = state.copyWith(
          lastMassEditResult: payload,
          errorMessage: null,
        );
    }
  }

  void clearMassEditResult() {
    state = state.copyWith(lastMassEditResult: null);
  }






  Future<void> applyMassEditFromPreview(Map<String, dynamic> payload) async {
    await _service.sendMassEditApply(payload);
  }

  Future<void> applyScheduleShiftFromPreview(Map<String, dynamic> payload) async {
    await _service.sendScheduleShiftApply(payload);
  }

  void _handleConnectionState(ChatConnectionState value) {
    state = state.copyWith(connectionState: value);
  }

  @override
  void dispose() {
    _eventSubscription?.cancel();
    _connectionSubscription?.cancel();
    _service.disconnect();
    super.dispose();
  }
}

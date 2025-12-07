import 'package:equatable/equatable.dart';

enum ChatRole { user, assistant, system }

ChatRole roleFromString(String? value) {
  switch (value) {
    case 'assistant':
      return ChatRole.assistant;
    case 'system':
      return ChatRole.system;
    case 'user':
    default:
      return ChatRole.user;
  }
}

String roleToString(ChatRole role) {
  switch (role) {
    case ChatRole.assistant:
      return 'assistant';
    case ChatRole.system:
      return 'system';
    case ChatRole.user:
    default:
      return 'user';
  }
}

class ChatMessage extends Equatable {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
    required this.sessionId,
  });

  final String id;
  final ChatRole role;
  final String content;
  final DateTime timestamp;
  final String sessionId;

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id']?.toString() ?? DateTime.now().microsecondsSinceEpoch.toString(),
      role: roleFromString(json['role'] as String?),
      content: json['content']?.toString() ?? '',
      timestamp: json['timestamp'] is DateTime
          ? json['timestamp'] as DateTime
          : DateTime.tryParse(json['timestamp']?.toString() ?? '') ?? DateTime.now().toUtc(),
      sessionId: json['session_id']?.toString() ?? json['sessionId']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'role': roleToString(role),
      'content': content,
      'timestamp': timestamp.toIso8601String(),
      'session_id': sessionId,
    };
  }

  ChatMessage copyWith({
    String? id,
    ChatRole? role,
    String? content,
    DateTime? timestamp,
    String? sessionId,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      content: content ?? this.content,
      timestamp: timestamp ?? this.timestamp,
      sessionId: sessionId ?? this.sessionId,
    );
  }

  @override
  List<Object?> get props => [id, role, content, timestamp, sessionId];
}

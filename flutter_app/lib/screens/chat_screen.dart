import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/chat_message.dart';
import '../providers/chat_provider.dart';
import '../services/chat_service.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key, this.embedded = false});

  /// When true, renders the chat content without its own Scaffold/AppBar
  /// so it can be embedded inside a parent Scaffold (e.g., tab).
  final bool embedded;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatControllerProvider);
    final connectionLabel = _mapConnectionLabel(chatState.connectionState);
    final canSend = chatState.connectionState == ChatConnectionState.connected ||
        chatState.connectionState == ChatConnectionState.reconnecting;

    // Listen for error changes and new messages to auto-scroll
    ref.listen<ChatState>(
      chatControllerProvider,
      (previous, next) {
        if (!mounted) return;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          final previousError = previous?.errorMessage;
          if (next.errorMessage != null && next.errorMessage != previousError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(next.errorMessage!)),
            );
          }
          final previousLength = previous?.messages.length ?? 0;
          if (next.messages.length != previousLength) {
            _scrollToBottom();
          }
        });
      },
    );
 

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.embedded)
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: _ConnectionBanner(
              label: connectionLabel,
              state: chatState.connectionState,
              sessionId: chatState.sessionId,
            ),
          ),
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.4),
              borderRadius: BorderRadius.circular(12),
            ),
            child: _buildMessageList(chatState.messages),
          ),
        ),
        if (chatState.isTyping)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: _TypingIndicator(sessionId: chatState.sessionId),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: _buildInputArea(canSend),
        ),
      ],
    );

    if (widget.embedded) {
      return SafeArea(
        top: false,
        bottom: false,
        child: content,
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Чат ассистента'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(72),
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: _ConnectionBanner(
              label: connectionLabel,
              state: chatState.connectionState,
              sessionId: chatState.sessionId,
            ),
          ),
        ),
      ),
      body: SafeArea(
        top: false,
        child: content,
      ),
    );
  }

Widget _buildMessageList(List<ChatMessage> messages) {
  if (messages.isEmpty) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24.0),
        child: Text(
          'Начните диалог, чтобы ассистент собрал ваши цели и предпочтения.',
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  return ListView.builder(
    controller: _scrollController,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
    itemCount: messages.length,
    itemBuilder: (context, index) {
      final message = messages[index];
      final isUser = message.role == ChatRole.user;
      return Padding(
        key: ValueKey('${message.id}_$index'),  // Use message ID instead of timestamp
        padding: const EdgeInsets.only(bottom: 12),
        child: Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: isUser
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(16).copyWith(
                  bottomLeft: const Radius.circular(4),
                  bottomRight: const Radius.circular(4),
                  topLeft: Radius.circular(isUser ? 16 : 4),
                  topRight: Radius.circular(isUser ? 4 : 16),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Column(
                  crossAxisAlignment:
                      isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    Text(
                      message.content,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: isUser
                                ? Theme.of(context).colorScheme.onPrimary
                                : Theme.of(context).colorScheme.onSurface,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatTimestamp(message.timestamp),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: (isUser
                                    ? Theme.of(context).colorScheme.onPrimary
                                    : Theme.of(context).colorScheme.onSurface)
                                .withOpacity(0.7),
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    },
  );
}

  Widget _buildInputArea(bool canSend) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: TextField(
            controller: _inputController,
            minLines: 1,
            maxLines: 5,
            textInputAction: TextInputAction.send,
            onSubmitted: (_) => _handleSend(),
            decoration: InputDecoration(
              hintText: 'Введите сообщение...',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
          ),
        ),
        const SizedBox(width: 8),
        IconButton(
          icon: const Icon(Icons.send_rounded),
          onPressed: canSend ? _handleSend : null,
          color: Theme.of(context).colorScheme.primary,
          tooltip: canSend ? 'Отправить' : 'Нет соединения',
        ),
      ],
    );
  }

  void _handleSend() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;
    ref.read(chatControllerProvider.notifier).sendMessage(text);
    _inputController.clear();
  }

void _scrollToBottom() {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    if (!_scrollController.hasClients || !_scrollController.position.hasContentDimensions) return;
    
    // Check if the scroll position is valid
    if (_scrollController.position.maxScrollExtent > 0 && 
        _scrollController.position.maxScrollExtent.isFinite) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  });
}

  String _formatTimestamp(DateTime timestamp) {
    final local = timestamp.toLocal();
    final time = TimeOfDay.fromDateTime(local);
    final hours = time.hour.toString().padLeft(2, '0');
    final minutes = time.minute.toString().padLeft(2, '0');
    return '$hours:$minutes';
  }

  String _mapConnectionLabel(ChatConnectionState state) {
    switch (state) {
      case ChatConnectionState.connected:
        return 'Подключено';
      case ChatConnectionState.connecting:
        return 'Подключение...';
      case ChatConnectionState.reconnecting:
        return 'Переподключение...';
      case ChatConnectionState.error:
        return 'Ошибка соединения';
      case ChatConnectionState.disconnected:
      default:
        return 'Отключено';
    }
  }
}

class _ConnectionBanner extends StatelessWidget {
  const _ConnectionBanner({
    required this.label,
    required this.state,
    required this.sessionId,
  });

  final String label;
  final ChatConnectionState state;
  final String? sessionId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    Color background;
    Color foreground;
    switch (state) {
      case ChatConnectionState.connected:
        background = colorScheme.primary.withOpacity(0.15);
        foreground = colorScheme.primary;
        break;
      case ChatConnectionState.connecting:
      case ChatConnectionState.reconnecting:
        background = colorScheme.secondary.withOpacity(0.15);
        foreground = colorScheme.secondary;
        break;
      case ChatConnectionState.error:
        background = theme.colorScheme.errorContainer;
        foreground = theme.colorScheme.onErrorContainer;
        break;
      case ChatConnectionState.disconnected:
      default:
        background = colorScheme.surfaceVariant;
        foreground = colorScheme.onSurfaceVariant;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            _iconForState(state),
            color: foreground,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: theme.textTheme.titleSmall?.copyWith(color: foreground),
                ),
                if (sessionId != null && sessionId!.isNotEmpty)
                  Text(
                    'Сессия: $sessionId',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: foreground.withOpacity(0.8),
                    ),
                  ),
              ],
            ),
          ),
          if (state == ChatConnectionState.error ||
              state == ChatConnectionState.disconnected)
            Consumer(
              builder: (context, ref, _) => TextButton.icon(
                onPressed: () {
                  ref.read(chatControllerProvider.notifier).reconnect();
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Повторить'),
                style: TextButton.styleFrom(foregroundColor: foreground),
              ),
            )
          else if (state == ChatConnectionState.reconnecting ||
              state == ChatConnectionState.connecting)
            SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(foreground),
              ),
            ),
        ],
      ),
    );
  }

  static IconData _iconForState(ChatConnectionState state) {
    switch (state) {
      case ChatConnectionState.connected:
        return Icons.check_circle_rounded;
      case ChatConnectionState.connecting:
      case ChatConnectionState.reconnecting:
        return Icons.sync_rounded;
      case ChatConnectionState.error:
        return Icons.error_outline_rounded;
      case ChatConnectionState.disconnected:
      default:
        return Icons.offline_bolt_outlined;
    }
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator({required this.sessionId});

  final String? sessionId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        const SizedBox(width: 4),
        const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            'Ассистент печатает...${sessionId?.isNotEmpty == true ? ' (сессия ${sessionId!})' : ''}',
            style: theme.textTheme.bodySmall,
          ),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../models/chat_message.dart';
import '../providers/chat_provider.dart';
import '../services/chat_service.dart';
import '../widgets/chat_tools/tool_widget_factory.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key, this.embedded = false, this.transparentBackground = false});

  /// When true, renders the chat content without its own Scaffold/AppBar
  /// so it can be embedded inside a parent Scaffold (e.g., tab).
  final bool embedded;

  /// When true, avoids drawing an extra card background so the parent can
  /// provide its own blur/overlay styling.
  final bool transparentBackground;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatCommand {
  const _ChatCommand({
    required this.trigger,
    required this.keyword,
    required this.display,
    required this.title,
    required this.description,
    required this.icon,
  });

  final String trigger;
  final String keyword;
  final String display;
  final String title;
  final String description;
  final IconData icon;
}

class _CommandTriggerInfo {
  const _CommandTriggerInfo({
    required this.trigger,
    required this.startIndex,
    required this.endIndex,
    required this.query,
  });

  final String trigger;
  final int startIndex;
  final int endIndex;
  final String query;
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  _ChatScreenState();

  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _inputFocusNode = FocusNode();

  _CommandTriggerInfo? _activeTrigger;

  static const List<_ChatCommand> _availableCommands = [
    _ChatCommand(
      trigger: '@',
      keyword: 'fsm_plan_generator',
      display: '@fsm_plan_generator',
      title: 'Генерация плана (FSM)',
      description: 'Запускает диалог finite state machine для составления тренировочного плана.',
      icon: Icons.auto_awesome_motion_rounded,
    ),
    _ChatCommand(
      trigger: '/',
      keyword: 'mass_edit',
      display: '/mass_edit',
      title: 'Mass edit',
      description: 'Массовое редактирование плана с помощью AI.',
      icon: Icons.edit_note_rounded,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _inputController.addListener(_handleInputChanged);
  }

  @override
  void dispose() {
    _inputController.removeListener(_handleInputChanged);
    _inputController.dispose();
    _scrollController.dispose();
    _inputFocusNode.dispose();
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
        if (widget.embedded && !widget.transparentBackground)
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: _ConnectionBanner(
              label: connectionLabel,
              state: chatState.connectionState,
              sessionId: chatState.sessionId,
            ),
          ),
        if (chatState.lastMassEditResult != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: ToolWidgetFactory(payload: chatState.lastMassEditResult!),
          ),
        Expanded(
          child: Container(
            decoration: widget.transparentBackground
                ? null
                : BoxDecoration(
                    color: Theme.of(context)
                        .colorScheme
                        .surfaceVariant
                        .withOpacity(0.4),
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

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Чат ассистента',
            onTitleTap: openChat,
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
      },
    );
  }

  Widget _buildMessageList(List<ChatMessage> messages) {
  if (messages.isEmpty) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24.0),
        ),
      );
    }

  final bool transparent = widget.transparentBackground;

  return ListView.builder(
    controller: _scrollController,
    padding: EdgeInsets.symmetric(
      horizontal: 16,
      vertical: transparent ? 24 : 16,
    ),
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
              maxWidth: MediaQuery.of(context).size.width * 0.8,
            ),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: isUser
                    ? (transparent
                        ? Theme.of(context)
                            .colorScheme
                            .primary
                            .withOpacity(0.9)
                        : Theme.of(context).colorScheme.primary)
                    : (transparent
                        ? Colors.white.withOpacity(0.92)
                        : Theme.of(context).colorScheme.surface),
                borderRadius: BorderRadius.circular(22).copyWith(
                  bottomLeft: const Radius.circular(10),
                  bottomRight: const Radius.circular(10),
                  topLeft: Radius.circular(isUser ? 22 : 10),
                  topRight: Radius.circular(isUser ? 10 : 22),
                ),
                boxShadow: transparent
                    ? [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.10),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ]
                    : [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
    final transparent = widget.transparentBackground;
    final suggestions = _buildCommandSuggestions();
    final theme = Theme.of(context);

    final inputRow = Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: transparent
              ? Container(
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.9),
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.12),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: TextField(
                    controller: _inputController,
                    focusNode: _inputFocusNode,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _handleSend(),
                    decoration: const InputDecoration(
                      hintText: 'Введите сообщение...',
                      border: InputBorder.none,
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                )
              : TextField(
                  controller: _inputController,
                  focusNode: _inputFocusNode,
                  minLines: 1,
                  maxLines: 5,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _handleSend(),
                  decoration: InputDecoration(
                    hintText: 'Введите сообщение...',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                  ),
                ),
        ),
        SizedBox(width: transparent ? 12 : 8),
        transparent
            ? Material(
                color: Theme.of(context).colorScheme.primary,
                shape: const CircleBorder(),
                elevation: 6,
                child: IconButton(
                  icon: const Icon(Icons.send_rounded, color: Colors.white),
                  onPressed: canSend ? _handleSend : null,
                  tooltip: canSend ? 'Отправить' : 'Нет соединения',
                ),
              )
            : IconButton(
                icon: const Icon(Icons.send_rounded),
                onPressed: canSend ? _handleSend : null,
                color: Theme.of(context).colorScheme.primary,
                tooltip: canSend ? 'Отправить' : 'Нет соединения',
              ),
      ],
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (suggestions != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: suggestions,
          ),
        inputRow,
      ],
    );
  }

  void _handleSend() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;
    ref.read(chatControllerProvider.notifier).sendMessage(text);
    _inputController.clear();
    setState(() {
      _activeTrigger = null;
    });
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

  void _handleInputChanged() {
    final nextTrigger = _detectCommandTrigger();
    if (mounted) {
      setState(() {
        _activeTrigger = nextTrigger;
      });
    }
  }

  _CommandTriggerInfo? _detectCommandTrigger() {
    final value = _inputController.value;
    final text = value.text;
    if (text.isEmpty) return null;

    final cursorIndex = value.selection.baseOffset;
    if (cursorIndex < 0 || cursorIndex > text.length) {
      return null;
    }

    var start = cursorIndex;
    while (start > 0 && !_isWhitespace(text[start - 1])) {
      start--;
    }

    if (start >= text.length) {
      return null;
    }

    final triggerChar = text[start];
    if (triggerChar != '@' && triggerChar != '/') {
      return null;
    }

    if (start > 0 && !_isWhitespace(text[start - 1])) {
      return null;
    }

    var end = cursorIndex;
    while (end < text.length && !_isWhitespace(text[end])) {
      end++;
    }

    final query = text.substring(start + 1, cursorIndex).toLowerCase();
    return _CommandTriggerInfo(
      trigger: triggerChar,
      startIndex: start,
      endIndex: end,
      query: query,
    );
  }

  Widget? _buildCommandSuggestions() {
    if (_activeTrigger == null || !_inputFocusNode.hasFocus) {
      return null;
    }

    final commands = _filteredCommands;
    if (commands.isEmpty) {
      return null;
    }

    final theme = Theme.of(context);
    final dividerColor = theme.dividerColor.withOpacity(0.2);

    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 200),
      child: Material(
        elevation: widget.transparentBackground ? 12 : 4,
        borderRadius: BorderRadius.circular(16),
        color: theme.colorScheme.surface,
        child: ListView.separated(
          shrinkWrap: true,
          padding: const EdgeInsets.symmetric(vertical: 4),
          itemCount: commands.length,
          itemBuilder: (context, index) {
            final command = commands[index];
            return ListTile(
              dense: true,
              leading: Icon(command.icon, color: theme.colorScheme.primary),
              title: Text(
                command.title,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              subtitle: Text(
                '${command.display} — ${command.description}',
                style: theme.textTheme.bodySmall,
              ),
              onTap: () => _handleCommandSelected(command),
            );
          },
          separatorBuilder: (_, __) => Divider(height: 1, color: dividerColor),
        ),
      ),
    );
  }

  List<_ChatCommand> get _filteredCommands {
    final trigger = _activeTrigger;
    if (trigger == null) {
      return const [];
    }

    final query = trigger.query.toLowerCase();

    final chatState = ref.watch(chatControllerProvider);
    final contextPayload = chatState.contextPayload;
    final Map<String, dynamic> autocomplete =
        (contextPayload != null && contextPayload['autocomplete'] is Map<String, dynamic>)
            ? contextPayload['autocomplete'] as Map<String, dynamic>
            : const {};
    final List<dynamic> workoutItems =
        autocomplete['workouts'] is List ? autocomplete['workouts'] as List<dynamic> : const [];
    final List<dynamic> exerciseItems =
        autocomplete['exercises'] is List ? autocomplete['exercises'] as List<dynamic> : const [];

    final List<_ChatCommand> base = _availableCommands
        .where((command) => command.trigger == trigger.trigger)
        .toList();

    final List<_ChatCommand> dsl = <_ChatCommand>[];
    if (trigger.trigger == '/') {
      for (final item in workoutItems) {
        if (item is! Map<String, dynamic>) continue;
        final alias = item['alias']?.toString() ?? '';
        if (alias.isEmpty) continue;
        final name = item['name']?.toString() ?? '';
        final keyword = alias.substring(1); // strip leading '/'
        final aliasLower = alias.toLowerCase();
        final keywordLower = keyword.toLowerCase();
        if (query.isNotEmpty &&
            !aliasLower.contains(query) &&
            !keywordLower.contains(query) &&
            !name.toLowerCase().contains(query)) {
          continue;
        }
        final title = name.isNotEmpty ? '$alias — $name' : alias;
        dsl.add(
          _ChatCommand(
            trigger: '/',
            keyword: keyword,
            display: alias,
            title: title,
            description: 'Ссылка на тренировку в активном плане',
            icon: Icons.fitness_center_rounded,
          ),
        );
      }

      for (final item in exerciseItems) {
        if (item is! Map<String, dynamic>) continue;
        final alias = item['alias']?.toString() ?? '';
        if (alias.isEmpty) continue;
        final name = item['name']?.toString() ?? '';
        final keyword = alias.substring(1); // strip leading '/'
        final aliasLower = alias.toLowerCase();
        final keywordLower = keyword.toLowerCase();
        if (query.isNotEmpty &&
            !aliasLower.contains(query) &&
            !keywordLower.contains(query) &&
            !name.toLowerCase().contains(query)) {
          continue;
        }
        final title = name.isNotEmpty ? '$alias — $name' : alias;
        dsl.add(
          _ChatCommand(
            trigger: '/',
            keyword: keyword,
            display: alias,
            title: title,
            description: 'Ссылка на упражнение',
            icon: Icons.fitness_center_outlined,
          ),
        );
      }
    }

    var all = <_ChatCommand>[...base, ...dsl];
    if (query.isEmpty) {
      return all;
    }

    all = all
        .where(
          (command) => command.keyword.toLowerCase().contains(query) ||
              command.display.toLowerCase().contains(query) ||
              command.title.toLowerCase().contains(query),
        )
        .toList();

    return all;
  }

  void _handleCommandSelected(_ChatCommand command) {
    final trigger = _activeTrigger;
    if (trigger == null) {
      return;
    }

    final text = _inputController.text;
    final safeEnd = trigger.endIndex.clamp(0, text.length);
    final safeStart = trigger.startIndex.clamp(0, safeEnd);
    final insertion = '${command.display} ';

    final newText = text.replaceRange(safeStart, safeEnd, insertion);
    final cursorPosition = safeStart + command.display.length + 1;

    _inputController.value = TextEditingValue(
      text: newText,
      selection: TextSelection.collapsed(offset: cursorPosition),
    );

    setState(() {
      _activeTrigger = null;
    });
  }

  bool _isWhitespace(String character) {
    return character.trim().isEmpty;
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

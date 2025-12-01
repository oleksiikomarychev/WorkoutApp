import 'package:flutter/material.dart';
import 'package:workout_app/widgets/assistant_chat_overlay.dart';

typedef AssistantChatBuilder = Widget Function(
  BuildContext context,
  VoidCallback openChat,
);

class AssistantChatHost extends StatefulWidget {
  const AssistantChatHost({
    super.key,
    required this.builder,
    this.initialMessage,
    this.contextBuilder,
  });

  final AssistantChatBuilder builder;
  final String? initialMessage;
  final Future<Map<String, dynamic>?> Function()? contextBuilder;

  static _AssistantChatHostState? of(BuildContext context) {
    return context.findAncestorStateOfType<_AssistantChatHostState>();
  }

  @override
  State<AssistantChatHost> createState() => _AssistantChatHostState();
}

class _AssistantChatHostState extends State<AssistantChatHost> {
  bool _visible = false;

  void openChat() {
    if (!_visible) {
      setState(() {
        _visible = true;
      });
    }
  }

  void _handleClose() {
    if (_visible) {
      setState(() {
        _visible = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        widget.builder(context, openChat),
        AssistantChatOverlay(
          visible: _visible,
          onClose: _handleClose,
          initialMessage: widget.initialMessage,
          contextBuilder: widget.contextBuilder,
        ),
      ],
    );
  }
}


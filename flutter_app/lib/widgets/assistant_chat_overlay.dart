import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/chat_provider.dart';
import 'package:workout_app/screens/chat_screen.dart';





class AssistantChatOverlay extends StatefulWidget {
  const AssistantChatOverlay({
    super.key,
    required this.visible,
    required this.onClose,
    this.initialMessage,
    this.contextBuilder,
  });

  final bool visible;
  final VoidCallback onClose;
  final String? initialMessage;
  final Future<Map<String, dynamic>?> Function()? contextBuilder;

  @override
  State<AssistantChatOverlay> createState() => _AssistantChatOverlayState();
}

class _AssistantChatOverlayState extends State<AssistantChatOverlay> {
  bool _seeded = false;

  @override
  void didUpdateWidget(covariant AssistantChatOverlay oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!oldWidget.visible && widget.visible) {
      _trySeedChat();
    } else if (!widget.visible) {
      _seeded = false;
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (widget.visible && !_seeded) {
      _trySeedChat();
    }
  }

  Future<void> _trySeedChat() async {
    if (_seeded || !mounted) return;
    _seeded = true;

    final contextPayload = widget.contextBuilder != null ? await widget.contextBuilder!() : null;

    await Future.microtask(() {
      final container = ProviderScope.containerOf(context, listen: false);
      final controller = container.read(chatControllerProvider.notifier);


      if (contextPayload != null) {
        controller.sendContext(contextPayload);
      }


      final message = widget.initialMessage?.trim();
      if (message != null && message.isNotEmpty) {
        controller.sendMessage(message);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.visible) {
      return const SizedBox.shrink();
    }

    return Positioned.fill(
      child: Stack(
        children: [
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onTap: widget.onClose,
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                child: Container(
                  color: Colors.black.withOpacity(0.10),
                ),
              ),
            ),
          ),
          const SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Material(
                type: MaterialType.transparency,
                child: ChatScreen(
                  embedded: true,
                  transparentBackground: true,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/messaging_service.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class CoachChatScreenArgs {
  final String channelId;
  final String title;

  CoachChatScreenArgs({required this.channelId, required this.title});
}

final _channelMessagesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>((ref, channelId) async {
  final messaging = ref.watch(sl.messagingServiceProvider);
  return await messaging.getChannelMessages(channelId: channelId);
});

class CoachChatScreen extends ConsumerStatefulWidget {
  final CoachChatScreenArgs args;

  const CoachChatScreen({super.key, required this.args});

  @override
  ConsumerState<CoachChatScreen> createState() => _CoachChatScreenState();
}

class _CoachChatScreenState extends ConsumerState<CoachChatScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>> _buildChatContext() async {
    final nowIso = DateTime.now().toUtc().toIso8601String();
    return <String, dynamic>{
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'coach_chat',
      'role': 'coach',
      'timestamp': nowIso,
      'entities': <String, dynamic>{
        'channel': {
          'id': widget.args.channelId,
          'title': widget.args.title,
          'type': 'coach_athlete',
        },
      },
    };
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) {
      return;
    }
    setState(() {
      _sending = true;
    });
    try {
      final messaging = ref.read(sl.messagingServiceProvider);
      await messaging.sendTextMessage(channelId: widget.args.channelId, content: text);
      _controller.clear();
      await ref.refresh(_channelMessagesProvider(widget.args.channelId).future);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncMessages = ref.watch(_channelMessagesProvider(widget.args.channelId));
    final df = DateFormat('dd.MM HH:mm');

    return AssistantChatHost(
      initialMessage:
          'Открываю ассистента из CoachChatScreen. Используй контекст v1, чтобы понимать текущий канал коуч–атлет.',
      contextBuilder: _buildChatContext,
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: widget.args.title,
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(_channelMessagesProvider(widget.args.channelId)),
              ),
            ],
          ),
          body: Column(
        children: [
          Expanded(
            child: asyncMessages.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Center(child: Text('Error: $error')),
              data: (messages) {
                if (messages.isEmpty) {
                  return const Center(child: Text('No messages yet.'));
                }
                return ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final msg = messages[index];
                    final content = msg['content']?.toString() ?? '';
                    final sender = msg['sender_id']?.toString() ?? 'user';
                    final createdAtRaw = msg['created_at']?.toString();
                    DateTime? createdAt;
                    if (createdAtRaw != null) {
                      createdAt = DateTime.tryParse(createdAtRaw);
                    }
                    return Card(
                      margin: const EdgeInsets.symmetric(vertical: 6),
                      child: ListTile(
                        title: Text(content),
                        subtitle: Text(
                          '${sender.toUpperCase()} · ${createdAt != null ? df.format(createdAt.toLocal()) : 'unknown'}',
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 4,
                      decoration: const InputDecoration(
                        hintText: 'Type a message...',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _sending ? null : _sendMessage,
                    child: _sending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
      },
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/session_log_screen.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class SessionHistoryScreen extends ConsumerStatefulWidget {
  const SessionHistoryScreen({super.key});

  @override
  ConsumerState<SessionHistoryScreen> createState() => _SessionHistoryScreenState();
}

class _SessionHistoryScreenState extends ConsumerState<SessionHistoryScreen> {
  final TextEditingController _workoutIdController = TextEditingController();
  final DateFormat _dateFormat = DateFormat('yyyy-MM-dd HH:mm');
  int? _filterWorkoutId;

  @override
  void initState() {
    super.initState();
    // No initial manual load; provider handles initial fetch
  }

  @override
  void dispose() {
    _workoutIdController.dispose();
    super.dispose();
  }

  Future<void> _handleLoadTapped() async {
    final raw = _workoutIdController.text.trim();
    if (raw.isEmpty) {
      setState(() {
        _filterWorkoutId = null;
      });
      return;
    }

    final workoutId = int.tryParse(raw);
    if (workoutId == null) {
      // Invalid input -> clear filter
      setState(() {
        _filterWorkoutId = null;
      });
      return;
    }

    setState(() {
      _filterWorkoutId = workoutId;
    });
  }

  String _formatDate(DateTime? dt) {
    if (dt == null) return '-';
    return _dateFormat.format(dt.toLocal());
  }

  Widget _buildSessionTile(WorkoutSession session) {
    final progress = session.progress;
    final completed = progress['completed'];
    int completedSets = 0;
    if (completed is Map) {
      for (final entry in completed.values) {
        if (entry is List) {
          completedSets += entry.length;
        }
      }
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      child: ListTile(
        title: Text('Session #${session.id ?? '-'} | ${session.status.toUpperCase()}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Started: ${_formatDate(session.startedAt)}'),
            Text('Finished: ${_formatDate(session.finishedAt)}'),
            Text('Duration: ${session.durationSeconds ?? 0} sec'),
            Text('Completed sets: $completedSets'),
          ],
        ),
        trailing: Icon(
          session.isActive ? Icons.play_arrow : Icons.check,
          color: session.isActive ? Colors.orange : Colors.green,
        ),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => SessionLogScreen(session: session),
            ),
          );
        }
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final sessionsAsync = ref.watch(completedSessionsProviderFamily(_filterWorkoutId));
    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Session History Debug',
            onTitleTap: openChat,
          ),
          body: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _workoutIdController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Workout ID (необязательно)',
                hintText: 'Оставьте пустым, чтобы загрузить все сессии',
              ),
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              onSubmitted: (_) => _handleLoadTapped(),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: _handleLoadTapped,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Загрузить истории'),
                ),
                const SizedBox(width: 12),
                IconButton(
                  icon: const Icon(Icons.clear),
                  tooltip: 'Сбросить фильтр',
                  onPressed: () {
                    _workoutIdController.clear();
                    setState(() {
                      _filterWorkoutId = null;
                    });
                  },
                ),
                sessionsAsync.isLoading ? const CircularProgressIndicator() : const SizedBox.shrink(),
              ],
            ),
            const SizedBox(height: 16),
            const SizedBox(height: 8),
            sessionsAsync.when(
              loading: () => const Expanded(
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (err, _) => Expanded(
                child: Center(
                  child: Text('Ошибка загрузки: $err', style: const TextStyle(color: Colors.red)),
                ),
              ),
              data: (sessions) => Expanded(
                child: sessions.isEmpty
                    ? const Center(child: Text('Нет данных для отображения'))
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              'Всего сессий: ${sessions.length}',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                          Expanded(
                            child: ListView.builder(
                              itemCount: sessions.length,
                              itemBuilder: (context, index) => _buildSessionTile(sessions[index]),
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          ],
        ),
      ),
    );
      },
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/session_log_screen.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/widgets/empty_state.dart';

class SessionHistoryScreen extends ConsumerStatefulWidget {
  const SessionHistoryScreen({super.key});

  @override
  ConsumerState<SessionHistoryScreen> createState() =>
      _SessionHistoryScreenState();
}

class _SessionHistoryScreenState extends ConsumerState<SessionHistoryScreen> {
  final TextEditingController _workoutIdController = TextEditingController();
  final DateFormat _dateFormat = DateFormat('yyyy-MM-dd HH:mm');
  int? _filterWorkoutId;

  @override
  void initState() {
    super.initState();
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
        title: Text(
          'Session #${session.id ?? '-'} | ${session.status.toUpperCase()}',
        ),
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
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final sessionsAsync = ref.watch(
      completedSessionsProviderFamily(_filterWorkoutId),
    );

    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'session_history',
        'entities': {'filter_workout_id': _filterWorkoutId},
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Session History',
            onTitleTap: openChat,
            showBack: true,
          ),
          body: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _workoutIdController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Workout ID',
                          border: OutlineInputBorder(),
                        ),
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                        ],
                        onSubmitted: (_) => _handleLoadTapped(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.search),
                      onPressed: _handleLoadTapped,
                    ),
                    IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _workoutIdController.clear();
                        setState(() => _filterWorkoutId = null);
                      },
                    ),
                  ],
                ),
              ),
              Expanded(
                child: sessionsAsync.when(
                  loading: () => const LoadingIndicator(),
                  error: (err, _) => ErrorMessage(
                    message: 'Error loading history: $err',
                    onRetry: () => ref.invalidate(
                      completedSessionsProviderFamily(_filterWorkoutId),
                    ),
                  ),
                  data: (sessions) {
                    if (sessions.isEmpty) {
                      return const EmptyState(
                        icon: Icons.history,
                        title: 'No sessions found',
                        description: 'Try changing your filter',
                      );
                    }
                    return ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      itemCount: sessions.length,
                      itemBuilder: (context, index) =>
                          _buildSessionTile(sessions[index]),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

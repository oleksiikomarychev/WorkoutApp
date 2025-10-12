import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/session_log_screen.dart';

class SessionHistoryScreen extends ConsumerStatefulWidget {
  const SessionHistoryScreen({super.key});

  @override
  ConsumerState<SessionHistoryScreen> createState() => _SessionHistoryScreenState();
}

class _SessionHistoryScreenState extends ConsumerState<SessionHistoryScreen> {
  final TextEditingController _workoutIdController = TextEditingController();
  final DateFormat _dateFormat = DateFormat('yyyy-MM-dd HH:mm');
  bool _isLoading = false;
  String? _error;
  List<WorkoutSession> _sessions = const [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadSessions();
    });
  }

  @override
  void dispose() {
    _workoutIdController.dispose();
    super.dispose();
  }

  Future<void> _loadSessions({int? workoutId}) async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final service = ref.read(workoutSessionServiceProvider);
      final items = workoutId != null
          ? await service.listSessions(workoutId)
          : await service.listAllSessions();
      setState(() {
        _sessions = items;
        if (items.isEmpty) {
          _error = 'Сессий не найдено';
        }
      });
    } catch (err) {
      setState(() {
        _error = 'Ошибка загрузки: $err';
        _sessions = const [];
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleLoadTapped() async {
    final raw = _workoutIdController.text.trim();
    if (raw.isEmpty) {
      await _loadSessions();
      return;
    }

    final workoutId = int.tryParse(raw);
    if (workoutId == null) {
      setState(() {
        _error = 'Введите корректный workout_id';
        _sessions = const [];
      });
      return;
    }

    await _loadSessions(workoutId: workoutId);
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Session History Debug'),
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
                  onPressed: _isLoading ? null : _handleLoadTapped,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Загрузить истории'),
                ),
                const SizedBox(width: 12),
                IconButton(
                  icon: const Icon(Icons.clear),
                  tooltip: 'Сбросить фильтр',
                  onPressed: _isLoading
                      ? null
                      : () {
                          _workoutIdController.clear();
                          _loadSessions();
                        },
                ),
                if (_isLoading) const CircularProgressIndicator(),
              ],
            ),
            const SizedBox(height: 16),
            if (_error != null)
              Text(
                _error!,
                style: const TextStyle(color: Colors.red),
              ),
            const SizedBox(height: 8),
            if (_sessions.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  'Всего сессий: ${_sessions.length}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            Expanded(
              child: _sessions.isEmpty
                  ? const Center(child: Text('Нет данных для отображения'))
                  : ListView.builder(
                      itemCount: _sessions.length,
                      itemBuilder: (context, index) => _buildSessionTile(_sessions[index]),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class WorkoutSessionHistoryScreen extends ConsumerStatefulWidget {
  final int workoutId;
  const WorkoutSessionHistoryScreen({super.key, required this.workoutId});

  @override
  ConsumerState<WorkoutSessionHistoryScreen> createState() => _WorkoutSessionHistoryScreenState();
}

class _WorkoutSessionHistoryScreenState extends ConsumerState<WorkoutSessionHistoryScreen> {
  final DateFormat _dateFormat = DateFormat('yyyy-MM-dd HH:mm');
  bool _isLoading = false;
  String? _error;
  List<WorkoutSession> _sessions = const [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final svc = ref.read(workoutSessionServiceProvider);
      final items = await svc.listSessions(widget.workoutId);
      setState(() {
        _sessions = items;
        if (items.isEmpty) {
          _error = 'История пуста';
        }
      });
    } catch (e) {
      setState(() {
        _error = 'Ошибка загрузки: $e';
        _sessions = const [];
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  String _formatDate(DateTime? dt) => dt == null ? '-' : _dateFormat.format(dt.toLocal());

  Widget _tile(WorkoutSession s) {
    int completedSets = 0;
    final completed = s.progress['completed'];
    if (completed is Map) {
      for (final v in completed.values) {
        if (v is List) completedSets += v.length;
      }
    }
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      child: ListTile(
        title: Text('Session #${s.id ?? '-'} | ${s.status.toUpperCase()}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Started: ${_formatDate(s.startedAt)}'),
            Text('Finished: ${_formatDate(s.finishedAt)}'),
            Text('Duration: ${s.durationSeconds ?? 0} sec'),
            Text('Completed sets: $completedSets'),
          ],
        ),
        trailing: Icon(
          s.isActive ? Icons.play_arrow : Icons.check,
          color: s.isActive ? Colors.orange : Colors.green,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: PrimaryAppBar(
            title: 'Session History',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _isLoading ? null : _load,
              ),
            ],
          ),
          body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : _sessions.isEmpty
                  ? const Center(child: Text('Нет данных для отображения'))
                  : ListView.builder(
                      itemCount: _sessions.length,
                      itemBuilder: (_, i) => _tile(_sessions[i]),
                    ),
        );
      },
    );
  }
}

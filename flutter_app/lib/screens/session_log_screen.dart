import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/models/exercise_set_dto.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class SessionLogScreen extends ConsumerStatefulWidget {
  final WorkoutSession session;
  const SessionLogScreen({super.key, required this.session});

  @override
  ConsumerState<SessionLogScreen> createState() => _SessionLogScreenState();
}

class _SessionLogScreenState extends ConsumerState<SessionLogScreen> {
  Workout? _workout;
  bool _loading = true;
  Map<int, Set<int>> _completedByInstance = {};

  String _fmtDate(DateTime? dt) {
    if (dt == null) return '-';
    return DateFormat('yyyy-MM-dd HH:mm').format(dt.toLocal());
    }

  @override
  void initState() {
    super.initState();
    _parseProgress(widget.session.progress);
    _loadWorkout();
  }

  void _parseProgress(Map<String, dynamic> progress) {
    _completedByInstance.clear();
    final completed = progress['completed'];
    if (completed is Map) {
      completed.forEach((k, v) {
        final instId = int.tryParse(k.toString());
        if (instId == null) return;
        final setIds = <int>{};
        if (v is List) {
          for (final x in v) {
            final sid = x is int ? x : int.tryParse(x.toString());
            if (sid != null) setIds.add(sid);
          }
        }
        _completedByInstance[instId] = setIds;
      });
    }
  }

  Future<void> _loadWorkout() async {
    setState(() => _loading = true);
    try {
      final svc = ref.read(workoutServiceProvider);
      final w = await svc.getWorkoutWithDetails(widget.session.workoutId);

      final instances = w.exerciseInstances;
      final ids = instances.map((e) => e.exerciseListId).toSet().toList();
      if (ids.isNotEmpty) {
        final exSvc = ref.read(exerciseServiceProvider);
        final defs = await exSvc.getExercisesByIds(ids);
        final defMap = {for (final d in defs) d.id: d};
        final withNames = instances
            .map((inst) => inst.copyWith(exerciseDefinition: defMap[inst.exerciseListId]))
            .toList();
        if (!mounted) return;
        setState(() {
          _workout = w.copyWith(exerciseInstances: withNames);
        });
        return;
      }
      if (!mounted) return;
      setState(() {
        _workout = w;
      });
    } catch (_) {

    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.session;

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: PrimaryAppBar(
            title: 'Session #${session.id ?? '-'} Logs',
            onTitleTap: openChat,
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
          _InfoRow(label: 'Workout ID', value: session.workoutId.toString()),
          _InfoRow(label: 'Status', value: session.status),
          _InfoRow(label: 'Started', value: _fmtDate(session.startedAt)),
          _InfoRow(label: 'Finished', value: _fmtDate(session.finishedAt)),
          _InfoRow(label: 'Duration (sec)', value: (session.durationSeconds ?? 0).toString()),
          const SizedBox(height: 16),
          Text('Exercises & Sets', style: AppTextStyles.titleMedium),
          const SizedBox(height: 8),
          if (_loading)
            const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator()))
          else if (_workout == null || _workout!.exerciseInstances.isEmpty)
            const Text('No exercise data available for this workout')
          else
            ..._workout!.exerciseInstances.map(_buildInstanceCard),
          const SizedBox(height: 16),
          Text('Raw Progress', style: AppTextStyles.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Diagnostics only: JSON с ключом completed, где ключи — id инстансов упражнения, а значения — массив id завершённых сетов. Используется для подсветки сетов выше.',
            style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              boxShadow: AppShadows.sm,
            ),
            child: Text(session.progress.toString()),
          ),
        ],
      ),
    );
      },
    );
  }

  Widget _buildInstanceCard(ExerciseInstance instance) {
    final name = instance.exerciseDefinition?.name ?? 'Exercise #${instance.id ?? instance.exerciseListId}';
    final completed = _completedByInstance[instance.id ?? -1] ?? const <int>{};
    final sets = instance.sets;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF6F4FF),
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.fitness_center, color: AppColors.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  name,
                  style: AppTextStyles.titleMedium.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              if (sets.isNotEmpty)
                Text('${sets.length} set${sets.length == 1 ? '' : 's'}', style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 8),
          if (sets.isEmpty)
            Text('No sets', style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final s in sets) _SetChip(set: s, completed: completed.contains(s.id)),
              ],
            ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary)),
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(value, style: AppTextStyles.bodyMedium)),
        ],
      ),
    );
  }
}

class _SetChip extends StatelessWidget {
  final ExerciseSetDto set;
  final bool completed;
  const _SetChip({required this.set, required this.completed});

  @override
  Widget build(BuildContext context) {
    final text = _formatSet(set);
    final bg = completed ? const Color(0xFFEFF8F2) : Colors.white;
    final border = completed ? const Color(0xFF2E7D32) : AppColors.textDisabled.withOpacity(0.2);
    final icon = completed ? Icons.check_circle : Icons.radio_button_unchecked;
    final iconColor = completed ? const Color(0xFF2E7D32) : AppColors.textDisabled;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
        boxShadow: AppShadows.xs,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: iconColor),
          const SizedBox(width: 6),
          Text(text, style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  String _formatSet(ExerciseSetDto s) {
    final reps = s.reps;
    final weight = s.weight;
    final rpe = s.rpe;
    final parts = <String>[];
    parts.add('${reps}×${_trimDouble(weight)}kg');
    if (rpe != null) parts.add('RPE ${_trimDouble(rpe)}');
    return parts.join(' · ');
  }

  String _trimDouble(double v) {
    return (v % 1 == 0) ? v.toStringAsFixed(0) : v.toStringAsFixed(1);
  }
}


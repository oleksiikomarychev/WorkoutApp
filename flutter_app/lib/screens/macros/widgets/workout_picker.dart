import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/providers/plan_providers.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/workout_service.dart';

class PickedWorkout {
  final int id;
  final String name;
  const PickedWorkout({required this.id, required this.name});
}

Future<PickedWorkout?> showWorkoutPickerBottomSheet(BuildContext context, WidgetRef ref) async {
  return showModalBottomSheet<PickedWorkout>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(12))),
    builder: (_) => const _WorkoutPickerSheet(),
  );
}

class _WorkoutPickerSheet extends ConsumerStatefulWidget {
  const _WorkoutPickerSheet();
  @override
  ConsumerState<_WorkoutPickerSheet> createState() => _WorkoutPickerSheetState();
}

class _WorkoutPickerSheetState extends ConsumerState<_WorkoutPickerSheet> {
  late final WorkoutService _ws;
  DateTime? _selectedDay;
  List<Workout> _workouts = const [];
  bool _loading = true;
  String? _error;
  int? _selectedWorkoutId;
  String? _selectedWorkoutName;

  @override
  void initState() {
    super.initState();
    _ws = WorkoutService(apiClient: ApiClient());
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final plan = await ref.read(activeAppliedPlanProvider.future);
      final id = plan?.id;
      if (id == null) {
        setState(() { _loading = false; _workouts = const []; _error = 'Активный план не найден'; });
        return;
      }
      final items = await _ws.getWorkoutsByAppliedPlan(id);
      items.sort((a, b) {
        final da = a.scheduledFor ?? DateTime.fromMillisecondsSinceEpoch(0);
        final db = b.scheduledFor ?? DateTime.fromMillisecondsSinceEpoch(0);
        return da.compareTo(db);
      });
      setState(() {
        _workouts = items;
        _loading = false;
        _selectedDay = items.firstWhere((w) => w.scheduledFor != null, orElse: () => items.isNotEmpty ? items.first : Workout(name: 'Workout', id: null)).scheduledFor ?? DateTime.now();
        _selectedWorkoutId = null;
        _selectedWorkoutName = null;
      });
    } catch (e) {
      setState(() { _loading = false; _error = e.toString(); });
    }
  }

  Iterable<Workout> _workoutsForDay(DateTime day) {
    final y = day.year, m = day.month, d = day.day;
    return _workouts.where((w) {
      final s = w.scheduledFor;
      if (s == null) return false;
      return s.year == y && s.month == m && s.day == d;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 16),
        child: _loading
            ? const Center(child: SizedBox(height: 56, width: 56, child: CircularProgressIndicator()))
            : _error != null
                ? Center(child: Text(_error!))
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('Выбор тренировки', style: theme.textTheme.titleMedium),
                          const Spacer(),
                          IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (_workouts.isEmpty) ...[
                        const Text('Нет тренировок в активном плане'),
                        const SizedBox(height: 8),
                        Align(
                          alignment: Alignment.centerRight,
                          child: FilledButton(onPressed: _load, child: const Text('Обновить')),
                        ),
                      ] else ...[
                        Container(
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.4),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          padding: const EdgeInsets.all(8),
                          child: CalendarDatePicker(
                            key: ValueKey((_selectedDay ?? DateTime.now()).toIso8601String()),
                            initialDate: _selectedDay ?? DateTime.now(),
                            firstDate: _workouts.first.scheduledFor?.subtract(const Duration(days: 31)) ?? DateTime.now().subtract(const Duration(days: 365)),
                            lastDate: _workouts.last.scheduledFor?.add(const Duration(days: 31)) ?? DateTime.now().add(const Duration(days: 365)),
                            onDateChanged: (d) => setState(() {
                              _selectedDay = d;
                              _selectedWorkoutId = null;
                              _selectedWorkoutName = null;
                            }),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text('Тренировки в выбранный день', style: theme.textTheme.titleSmall),
                        const SizedBox(height: 4),
                        Builder(builder: (context) {
                          final day = _selectedDay ?? DateTime.now();
                          final list = _workoutsForDay(day).toList();
                          if (list.isEmpty) {
                            return const Text('На эту дату нет тренировок');
                          }
                          return ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 320),
                            child: ListView.separated(
                              shrinkWrap: true,
                              itemBuilder: (_, i) {
                                final w = list[i];
                                final when = w.scheduledFor != null ? DateFormat('d MMM, HH:mm').format(w.scheduledFor!) : 'без даты';
                                return ListTile(
                                  title: Text(w.name),
                                  subtitle: Text(when),
                                  selected: _selectedWorkoutId == w.id,
                                  onTap: () {
                                    if (w.id != null) {
                                      setState(() {
                                        _selectedWorkoutId = w.id;
                                        _selectedWorkoutName = w.name;
                                        if (w.scheduledFor != null) _selectedDay = DateTime(w.scheduledFor!.year, w.scheduledFor!.month, w.scheduledFor!.day);
                                      });
                                    }
                                  },
                                );
                              },
                              separatorBuilder: (_, __) => const Divider(height: 1),
                              itemCount: list.length,
                            ),
                          );
                        }),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Text('Или выбрать из списка'),
                            const Spacer(),
                            OutlinedButton.icon(
                              onPressed: () async {
                                final res = await showDialog<PickedWorkout>(
                                  context: context,
                                  builder: (_) => _WorkoutListDialog(workouts: _workouts),
                                );
                                if (!mounted) return;
                                if (res != null) {
                                  setState(() {
                                    _selectedWorkoutId = res.id;
                                    _selectedWorkoutName = res.name;
                                    final w = _workouts.firstWhere((e) => e.id == res.id, orElse: () => const Workout(name: 'Workout'));
                                    if (w.scheduledFor != null) _selectedDay = DateTime(w.scheduledFor!.year, w.scheduledFor!.month, w.scheduledFor!.day);
                                  });
                                }
                              },
                              icon: const Icon(Icons.list),
                              label: const Text('Список'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton(
                                onPressed: (_selectedWorkoutId == null)
                                    ? null
                                    : () {
                                        Navigator.of(context).pop(PickedWorkout(id: _selectedWorkoutId!, name: _selectedWorkoutName ?? ''));
                                      },
                                child: const Text('Готово'),
                              ),
                            ),
                          ],
                        )
                      ],
                    ],
                  ),
      ),
    );
  }
}

class _WorkoutListDialog extends StatelessWidget {
  final List<Workout> workouts;
  const _WorkoutListDialog({required this.workouts});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Выберите тренировку'),
      content: SizedBox(
        width: 420,
        height: 420,
        child: ListView.separated(
          itemCount: workouts.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (_, i) {
            final w = workouts[i];
            final when = w.scheduledFor != null ? DateFormat('d MMM, HH:mm').format(w.scheduledFor!) : 'без даты';
            return ListTile(
              title: Text(w.name),
              subtitle: Text(when),
              onTap: () {
                if (w.id != null) Navigator.of(context).pop(PickedWorkout(id: w.id!, name: w.name));
              },
            );
          },
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Отмена')),
      ],
    );
  }
}

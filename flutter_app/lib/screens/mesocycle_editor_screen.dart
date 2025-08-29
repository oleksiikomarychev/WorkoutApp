import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/service_locator.dart';

class MesocycleEditorScreen extends ConsumerStatefulWidget {
  final int planId;
  const MesocycleEditorScreen({super.key, required this.planId});

  @override
  ConsumerState<MesocycleEditorScreen> createState() => _MesocycleEditorScreenState();
}

class _MesocycleEditorScreenState extends ConsumerState<MesocycleEditorScreen> {
  final _logger = LoggerService('MesocycleEditor');
  bool _loading = true;
  String? _error;
  List<Mesocycle> _mesocycles = [];

  @override
  void initState() {
    super.initState();
    _loadMesocycles();
  }

  String _getMesocyclePreview(Mesocycle mesocycle) {
    // For now, we'll show a placeholder since we don't load microcycles count here
    // In a real implementation, you might want to add microcycles count to the Mesocycle model
    final notes = mesocycle.notes;
    if (notes != null && notes.isNotEmpty) {
      return notes;
    }
    return 'Мезоцикл ${mesocycle.name}';
  }

  Future<void> _loadMesocycles() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    _logger.d('Loading mesocycles for plan ${widget.planId}...');
    try {
      final svc = ref.read(mesocycleServiceProvider);
      _logger.d('Calling svc.listMesocycles...');
      final items = await svc.listMesocycles(widget.planId);
      _logger.d('Loaded ${items.length} mesocycles.');
      items.sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
      if (!mounted) {
        _logger.w('Attempted to update state on unmounted component after loading.');
        return;
      }
      setState(() => _mesocycles = items);
    } catch (e, st) {
      _logger.e('Failed to load mesocycles', e, st);
      if (!mounted) {
        _logger.w('Attempted to update state on unmounted component after error.');
        return;
      }
      setState(() => _error = 'Не удалось загрузить мезоциклы');
    } finally {
      _logger.d('Finished loading mesocycles.');
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _showEditMesocycleDialog({Mesocycle? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final notesCtrl = TextEditingController(text: existing?.notes ?? '');
    final orderCtrl = TextEditingController(text: (existing?.orderIndex ?? 0).toString());
    final rootCtx = context;

    await showDialog(
      context: context,
      builder: (ctx) {
        bool submitting = false;
        return StatefulBuilder(builder: (context, setState) {
          Future<void> submit() async {
            setState(() => submitting = true);
            _logger.d('Submitting mesocycle form (existing: ${existing != null})...');
            try {
              final svc = ref.read(mesocycleServiceProvider);
              final name = nameCtrl.text.trim();
              final notes = notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim();
              final order = int.tryParse(orderCtrl.text.trim()) ?? 0;
              if (existing == null) {
                _logger.d('Creating new mesocycle...');
                await svc.createMesocycle(widget.planId, MesocycleUpdateDto(name: name, notes: notes, orderIndex: order));
              } else {
                _logger.d('Updating mesocycle ${existing.id}...');
                await svc.updateMesocycle(existing.id, MesocycleUpdateDto(name: name, notes: notes, orderIndex: order));
              }
              _logger.d('Submission successful.');
              if (!mounted) return;
              Navigator.of(ctx).pop();
              await _loadMesocycles();
            } catch (e, st) {
              _logger.e('Mesocycle submission failed', e, st);
              if (mounted) {
                setState(() => submitting = false);
                ScaffoldMessenger.maybeOf(rootCtx)?.showSnackBar(const SnackBar(content: Text('Ошибка сохранения')));
              }
            }
          }

          return AlertDialog(
            title: Text(existing == null ? 'Новый мезоцикл' : 'Редактировать мезоцикл'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Название'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: notesCtrl,
                    maxLength: 100,
                    decoration: const InputDecoration(labelText: 'Заметки (до 100 символов)'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: orderCtrl,
                    decoration: const InputDecoration(labelText: 'Порядок'),
                    keyboardType: TextInputType.number,
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: submitting ? null : () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
              FilledButton(onPressed: submitting ? null : submit, child: const Text('Сохранить')),
            ],
          );
        });
      },
    );
  }

  Future<void> _deleteMesocycle(Mesocycle m) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Удалить мезоцикл?'),
        content: Text('"${m.name}" будет удалён'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Удалить')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final svc = ref.read(mesocycleServiceProvider);
      await svc.deleteMesocycle(m.id);
      await _loadMesocycles();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Не удалось удалить')));
    }
  }

  Future<void> _openMicrocyclesSheet(Mesocycle m) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return _MicrocyclesSheet(mesocycle: m);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
              child: Row(
                children: [
                  const BackButton(),
                  Expanded(
                    child: Text(
                      'Мезоциклы',
                      style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(width: 48), // Balance BackButton
                ],
              ),
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text(_error!))
                      : _mesocycles.isEmpty
                          ? const Center(child: Text('Пока пусто'))
                          : ListView.builder(
                              padding: const EdgeInsets.all(12),
                              itemCount: _mesocycles.length,
                              itemBuilder: (context, index) {
                                final m = _mesocycles[index];
                                final previewText = _getMesocyclePreview(m);
                                return Card(
                                  child: ListTile(
                                    title: Text(m.name),
                                    subtitle: Text(previewText),
                                    leading: CircleAvatar(child: Text('${m.orderIndex}')),
                                    trailing: PopupMenuButton<String>(
                                      onSelected: (v) {
                                        switch (v) {
                                          case 'edit':
                                            _showEditMesocycleDialog(existing: m);
                                            break;
                                          case 'micro':
                                            _openMicrocyclesSheet(m);
                                            break;
                                          case 'del':
                                            _deleteMesocycle(m);
                                            break;
                                        }
                                      },
                                      itemBuilder: (ctx) => const [
                                        PopupMenuItem(value: 'edit', child: Text('Редактировать')),
                                        PopupMenuItem(value: 'micro', child: Text('Микроциклы')),
                                        PopupMenuItem(value: 'del', child: Text('Удалить')),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showEditMesocycleDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Добавить'),
      ),
    );
  }
}

class _MicrocyclesSheet extends ConsumerStatefulWidget {
  final Mesocycle mesocycle;
  const _MicrocyclesSheet({required this.mesocycle});

  @override
  ConsumerState<_MicrocyclesSheet> createState() => _MicrocyclesSheetState();
}

class _MicrocyclesSheetState extends ConsumerState<_MicrocyclesSheet> {
  final _logger = LoggerService('MicrocyclesSheet');
  bool _loading = true;
  String? _error;
  List<Microcycle> _items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _getSchedulePreview(Map<String, List<ExerciseScheduleItemDto>> schedule) {
    if (schedule.isEmpty) return 'Пустое расписание';
    
    final activeDays = schedule.entries
        .where((entry) => entry.value.isNotEmpty)
        .map((entry) => entry.key)
        .toList();
    
    if (activeDays.isEmpty) return 'Дни отдыха';
    
    final totalExercises = schedule.values
        .expand((exercises) => exercises)
        .length;
    
    return '${activeDays.length} тренировочных дней, $totalExercises упражнений';
  }

  Future<void> _load() async {
    _logger.d('Loading microcycles for mesocycle ${widget.mesocycle.id}...');
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final svc = ref.read(mesocycleServiceProvider);
      _logger.d('Calling svc.listMicrocycles...');
      final res = await svc.listMicrocycles(widget.mesocycle.id);
      _logger.d('Loaded ${res.length} microcycles.');
      res.sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
      if (!mounted) {
        _logger.w('Attempted to update state on unmounted component after loading microcycles.');
        return;
      }
      setState(() => _items = res);
    } catch (e, st) {
      _logger.e('Failed to load microcycles', e, st);
      if (!mounted) {
        _logger.w('Attempted to update state on unmounted component after microcycle loading error.');
        return;
      }
      setState(() => _error = 'Не удалось загрузить микроциклы');
    } finally {
      _logger.d('Finished loading microcycles.');
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _showEditMicrocycleDialog({Microcycle? existing}) async {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final notesCtrl = TextEditingController(text: existing?.notes ?? '');
    final orderCtrl = TextEditingController(text: (existing?.orderIndex ?? 0).toString());

    await showDialog(
      context: context,
      builder: (ctx) {
        bool submitting = false;
        return StatefulBuilder(builder: (context, setState) {
          Future<void> submit() async {
            setState(() => submitting = true);
            _logger.d('Submitting microcycle form (existing: ${existing != null})...');
            try {
              final svc = ref.read(mesocycleServiceProvider);
              final name = nameCtrl.text.trim();
              final notes = notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim();
              final order = int.tryParse(orderCtrl.text.trim()) ?? 0;
              if (existing == null) {
                _logger.d('Creating new microcycle...');
                final dto = MicrocycleUpdateDto(
                  name: name,
                  notes: notes,
                  orderIndex: order,
                  schedule: <String, List<ExerciseScheduleItemDto>>{},
                );
                await svc.createMicrocycle(widget.mesocycle.id, dto);
              } else {
                _logger.d('Updating microcycle ${existing.id}...');
                final dto = MicrocycleUpdateDto(
                  name: name,
                  notes: notes,
                  orderIndex: order,
                  // schedule omitted to avoid wiping existing data
                );
                await svc.updateMicrocycle(existing.id, dto);
              }
              _logger.d('Microcycle submission successful.');
              if (!mounted) return;
              Navigator.of(ctx).pop();
              await _load();
            } catch (e, st) {
              _logger.e('Microcycle submission failed', e, st);
              if (mounted) {
                setState(() => submitting = false);
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ошибка сохранения')));
              }
            }
          }

          return AlertDialog(
            title: Text(existing == null ? 'Новый микроцикл' : 'Редактировать микроцикл'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Название'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: notesCtrl,
                    maxLength: 100,
                    decoration: const InputDecoration(labelText: 'Заметки (до 100 символов)'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: orderCtrl,
                    decoration: const InputDecoration(labelText: 'Порядок'),
                    keyboardType: TextInputType.number,
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: submitting ? null : () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
              FilledButton(onPressed: submitting ? null : submit, child: const Text('Сохранить')),
            ],
          );
        });
      },
    );
  }

  Future<void> _deleteMicrocycle(Microcycle m) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Удалить микроцикл?'),
        content: Text('"${m.name}" будет удалён'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Удалить')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      final svc = ref.read(mesocycleServiceProvider);
      await svc.deleteMicrocycle(m.id);
      await _load();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Не удалось удалить')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final viewInsets = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: viewInsets),
      child: SafeArea(
        child: DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.8,
          minChildSize: 0.4,
          maxChildSize: 0.95,
          builder: (context, controller) {
            return Column(
              children: [
                ListTile(
                  title: Text('Микроциклы: ${widget.mesocycle.name}'),
                  trailing: IconButton(
                    icon: const Icon(Icons.add),
                    onPressed: () => _showEditMicrocycleDialog(),
                  ),
                ),
                const Divider(height: 1),
                Expanded(
                  child: _loading
                      ? const Center(child: CircularProgressIndicator())
                      : _error != null
                          ? Center(child: Text(_error!))
                          : _items.isEmpty
                              ? const Center(child: Text('Пока пусто'))
                              : ListView.builder(
                                  controller: controller,
                                  itemCount: _items.length,
                                  itemBuilder: (context, index) {
                                    final it = _items[index];
                                    final scheduleText = _getSchedulePreview(it.schedule);
                                    return ListTile(
                                      title: Text(it.name),
                                      subtitle: Text(scheduleText.isEmpty ? '—' : scheduleText),
                                      leading: CircleAvatar(child: Text('${it.orderIndex}')),
                                      trailing: PopupMenuButton<String>(
                                        onSelected: (v) {
                                          switch (v) {
                                            case 'edit':
                                              _showEditMicrocycleDialog(existing: it);
                                              break;
                                            case 'del':
                                              _deleteMicrocycle(it);
                                              break;
                                          }
                                        },
                                        itemBuilder: (ctx) => const [
                                          PopupMenuItem(value: 'edit', child: Text('Редактировать')),
                                          PopupMenuItem(value: 'del', child: Text('Удалить')),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

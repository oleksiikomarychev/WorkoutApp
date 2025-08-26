import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/calendar_plan_instance.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/screens/calendar_plan_instance_screen.dart';
import 'package:workout_app/screens/calendar_plan_screen.dart';
import 'package:workout_app/screens/calendar_plan_wizard_screen.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/calendar_plan_instance_service.dart';
import 'package:workout_app/services/calendar_plan_service.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/widgets/empty_state.dart';

class CalendarPlansScreen extends ConsumerStatefulWidget {
  const CalendarPlansScreen({super.key});

  @override
  ConsumerState<CalendarPlansScreen> createState() => _CalendarPlansScreenState();
}

class _MesocycleDraft {
  String name;
  String? notes;
  int weeksCount;
  int microcycleLength;

  _MesocycleDraft({required this.name, this.notes, this.weeksCount = 1, this.microcycleLength = 7});
}

// State notifier for calendar plans
class CalendarPlansNotifier extends StateNotifier<AsyncValue<List<CalendarPlan>>> {
  final CalendarPlanService _calendarPlanService;
  
  CalendarPlansNotifier(this._calendarPlanService) : super(const AsyncValue.loading()) {
    loadCalendarPlans();
  }
  
  Future<void> loadCalendarPlans() async {
    state = const AsyncValue.loading();
    try {
      final plans = await _calendarPlanService.getCalendarPlans();
      state = AsyncValue.data(plans);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }
}

// Provider for calendar plans notifier
final calendarPlansNotifierProvider = StateNotifierProvider<CalendarPlansNotifier, AsyncValue<List<CalendarPlan>>>((ref) {
  final calendarPlanService = ref.watch(calendarPlanServiceProvider);
  return CalendarPlansNotifier(calendarPlanService);
});

class _CalendarPlansScreenState extends ConsumerState<CalendarPlansScreen> {
  final LoggerService _logger = LoggerService('CalendarPlansScreen');
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _weeksController = TextEditingController(text: '12');
  
  int _tabIndex = 0; // 0: community, 1: saved
  Set<int> _favoritePlanIds = {};
  bool _isFavLoading = true;
  List<CalendarPlanInstance> _instances = [];
  bool _isInstancesLoading = true;
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(calendarPlansNotifierProvider.notifier).loadCalendarPlans();
    });
    _loadFavorites();
    _loadInstances();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _weeksController.dispose();
    super.dispose();
  }

  void _navigateToCreateScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const CalendarPlanCreateScreen()),
    );
  }

  Future<void> _loadFavorites() async {
    try {
      final service = ref.read(calendarPlanServiceProvider);
      final favPlans = await service.getFavoriteCalendarPlans();
      if (!mounted) return;
      setState(() {
        _favoritePlanIds = favPlans.map((p) => p.id).toSet();
        _isFavLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _favoritePlanIds = {};
        _isFavLoading = false;
      });
    }
  }

  Future<void> _loadInstances() async {
    if (mounted) {
      setState(() {
        _isInstancesLoading = true;
      });
    }
    try {
      final svc = ref.read(calendarPlanInstanceServiceProvider);
      final list = await svc.listInstances();
      if (!mounted) return;
      setState(() {
        _instances = list;
        _isInstancesLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _instances = [];
        _isInstancesLoading = false;
      });
    }
  }

  Future<void> _toggleFavorite(int planId) async {
    final service = ref.read(calendarPlanServiceProvider);
    final isFav = _favoritePlanIds.contains(planId);
    try {
      if (isFav) {
        await service.removeFavoriteCalendarPlan(planId);
      } else {
        await service.addFavoriteCalendarPlan(planId);
      }
      if (!mounted) return;
      setState(() {
        if (isFav) {
          _favoritePlanIds.remove(planId);
        } else {
          _favoritePlanIds.add(planId);
        }
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Не удалось изменить сохранение плана: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Calendar Plans'),
        actions: [
          if (_tabIndex == 1) // Only allow creating in Saved tab
            PopupMenuButton<String>(
              icon: const Icon(Icons.add),
              onSelected: (value) {
                switch (value) {
                  case 'classic':
                    _navigateToCreateScreen();
                    break;
                  case 'wizard':
                    _navigateToWizardScreen();
                    break;
                }
              },
              itemBuilder: (context) => const [
                PopupMenuItem(value: 'classic', child: Text('Создать (классический)')),
                PopupMenuItem(value: 'wizard', child: Text('Создать (мастер)')),
              ],
            ),
        ],
      ),
      body: Column(
        children: [
          const SizedBox(height: 8),
          // Top toggle
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: ToggleButtons(
              isSelected: [_tabIndex == 0, _tabIndex == 1],
              onPressed: (index) {
                setState(() => _tabIndex = index);
                if (index == 1) {
                  // When switching to Saved, refresh instances from backend
                  _loadInstances();
                }
              },
              borderRadius: BorderRadius.circular(8),
              constraints: const BoxConstraints(minHeight: 36, minWidth: 140),
              children: const [
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12.0),
                  child: Text('Планы сообщества'),
                ),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12.0),
                  child: Text('Сохраненные'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Consumer(
              builder: (context, ref, child) {
                final calendarPlansState = ref.watch(calendarPlansNotifierProvider);
                
                return calendarPlansState.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (error, stackTrace) {
                    _logger.e('Error loading calendar plans: $error\n$stackTrace');
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, color: Colors.red, size: 48),
                          const SizedBox(height: 16),
                          Text(
                            'Error loading calendar plans',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            error.toString(),
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: () => ref.refresh(calendarPlansNotifierProvider),
                            icon: const Icon(Icons.refresh),
                            label: const Text('Retry'),
                          ),
                        ],
                      ),
                    );
                  },
                  data: (plans) {
                    final displayPlans = _tabIndex == 0
                        ? plans
                        : plans.where((p) => _favoritePlanIds.contains(p.id)).toList();

                    return RefreshIndicator(
                      onRefresh: () async {
                        await ref.refresh(calendarPlansNotifierProvider);
                        await ref.read(calendarPlansNotifierProvider.notifier).loadCalendarPlans();
                        await _loadFavorites();
                        await _loadInstances();
                      },
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          // Plans section (community or saved)
                          if (displayPlans.isNotEmpty) ...[
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8.0),
                              child: Text(
                                _tabIndex == 0 ? 'Планы сообщества' : 'Сохраненные планы',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ),
                            ...displayPlans.map((plan) {
                              final isFav = _favoritePlanIds.contains(plan.id);
                              return Card(
                                margin: const EdgeInsets.only(bottom: 16),
                                child: ListTile(
                                  leading: const Icon(Icons.calendar_today),
                                  title: Text(
                                    plan.name,
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                  subtitle: Text(
                                    'Duration: ${plan.durationWeeks} weeks',
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                  trailing: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      IconButton(
                                        tooltip: isFav ? 'Убрать из сохраненных' : 'Сохранить',
                                        icon: Icon(isFav ? Icons.favorite : Icons.favorite_border, color: isFav ? Colors.pinkAccent : null),
                                        onPressed: () => _toggleFavorite(plan.id),
                                      ),
                                      if (_tabIndex == 1)
                                        IconButton(
                                          icon: const Icon(Icons.delete, color: Colors.redAccent),
                                          onPressed: () async {
                                            final confirm = await showDialog<bool>(
                                              context: context,
                                              builder: (ctx) => AlertDialog(
                                                title: const Text('Delete plan?'),
                                                content: Text('Are you sure you want to delete "${plan.name}"?'),
                                                actions: [
                                                  TextButton(
                                                    onPressed: () => Navigator.of(ctx).pop(false),
                                                    child: const Text('Cancel'),
                                                  ),
                                                  ElevatedButton(
                                                    onPressed: () => Navigator.of(ctx).pop(true),
                                                    child: const Text('Delete'),
                                                  ),
                                                ],
                                              ),
                                            );
                                            if (confirm != true) return;
                                            try {
                                              await ref.read(calendarPlanServiceProvider).deleteCalendarPlan(plan.id);
                                              if (!mounted) return;
                                              await ref.read(calendarPlansNotifierProvider.notifier).loadCalendarPlans();
                                            } catch (e) {
                                              if (!mounted) return;
                                              ScaffoldMessenger.of(context).showSnackBar(
                                                SnackBar(content: Text('Failed to delete plan: $e')),
                                              );
                                            }
                                          },
                                        ),
                                      const Icon(Icons.chevron_right),
                                    ],
                                  ),
                                  onTap: () {
                                    Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => CalendarPlanScreen(planId: plan.id),
                                      ),
                                    );
                                  },
                                ),
                              );
                            }).toList(),
                          ]
                          else ...[
                            if (_tabIndex == 0)
                              EmptyState(
                                icon: Icons.calendar_today,
                                title: 'Нет планов сообщества',
                                description: 'Планы сообщества пока отсутствуют.',
                                action: ElevatedButton.icon(
                                  onPressed: () => ref.refresh(calendarPlansNotifierProvider),
                                  icon: const Icon(Icons.refresh),
                                  label: const Text('Обновить'),
                                ),
                              ),
                          ],

                          // Instances section, only in Saved tab
                          if (_tabIndex == 1) ...[
                            const SizedBox(height: 8),
                            Padding(
                              padding: const EdgeInsets.only(bottom: 8.0),
                              child: Row(
                                children: [
                                  Text('Инстансы', style: Theme.of(context).textTheme.titleMedium),
                                  const SizedBox(width: 8),
                                  if (_isInstancesLoading)
                                    const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                                ],
                              ),
                            ),
                            if (!_isInstancesLoading && _instances.isEmpty)
                              Card(
                                margin: const EdgeInsets.only(bottom: 16),
                                child: ListTile(
                                  leading: const Icon(Icons.history_toggle_off),
                                  title: const Text('Нет инстансов'),
                                  subtitle: const Text('Создайте инстанс из плана, чтобы отслеживать прогресс'),
                                  trailing: const Icon(Icons.chevron_right),
                                  onTap: () {},
                                ),
                              )
                            else ..._instances.map((inst) => Card(
                                  margin: const EdgeInsets.only(bottom: 16),
                                  child: ListTile(
                                    leading: const Icon(Icons.playlist_add_check),
                                    title: Text(inst.name),
                                    subtitle: Text('Длительность: ${inst.durationWeeks} нед.'),
                                    trailing: const Icon(Icons.chevron_right),
                                    onTap: () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => CalendarPlanInstanceScreen(instanceId: inst.id),
                                        ),
                                      );
                                    },
                                  ),
                                )),
                          ],
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: _tabIndex == 1
          ? FloatingActionButton(
              onPressed: _navigateToCreateScreen,
              child: const Icon(Icons.add),
            )
          : null,
    );
  }
}

// ===== Create Plan Screen =====
class CalendarPlanCreateScreen extends ConsumerStatefulWidget {
  const CalendarPlanCreateScreen({super.key});

  @override
  ConsumerState<CalendarPlanCreateScreen> createState() => _CalendarPlanCreateScreenState();
}

class _ExerciseDraft {
  int exerciseId;
  List<_SetDraft> sets;
  _ExerciseDraft({required this.exerciseId, List<_SetDraft>? sets}) : sets = sets ?? [];
}

class _SetDraft {
  int? intensity;
  int? effort;
  int? volume;
  // Controllers for inline editing
  final TextEditingController intensityCtrl = TextEditingController();
  final TextEditingController effortCtrl = TextEditingController();
  final TextEditingController volumeCtrl = TextEditingController();
  // Track last two edited fields: 'intensity' | 'effort' | 'volume'
  final List<String> editedFields = [];
  _SetDraft({this.intensity, this.effort, this.volume}) {
    if (intensity != null) intensityCtrl.text = intensity.toString();
    if (effort != null) effortCtrl.text = effort.toString();
    if (volume != null) volumeCtrl.text = volume.toString();
  }
}

class _WeekDraft {
  String name;
  bool expanded;
  // day -> exercises
  Map<String, List<_ExerciseDraft>> schedule;
  // Normalization placed after this week (microcycle)
  double? normValue; // e.g., 2.5
  String? normUnit; // '%'
  _WeekDraft({
    required this.name,
    this.expanded = true,
    Map<String, List<_ExerciseDraft>>? schedule,
    this.normValue,
    this.normUnit,
  }) : schedule = schedule ?? {};
}

class _CalendarPlanCreateScreenState extends ConsumerState<CalendarPlanCreateScreen> {
  final _nameCtrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  // Weeks collection
  final List<_WeekDraft> _weeks = [
    _WeekDraft(name: 'Микроцикл 1', expanded: true),
  ];

  // Mesocycles collection (grouping of microcycles)
  final List<_MesocycleDraft> _mesocycles = [
    _MesocycleDraft(name: 'Мезоцикл 1', weeksCount: 1, microcycleLength: 7),
  ];

  bool _submitting = false;
  // Prevent feedback loop when updating fields programmatically
  bool _isSyncingFields = false;

  // RPE table is loaded from backend at runtime
  Map<int, Map<int, int>> _rpeTable = {};

  // Cache of selected exercise names
  final Map<int, String> _exerciseNames = {};

  @override
  void initState() {
    super.initState();
    _fetchRpeTable();
    // Initialize mesocycles based on current microcycles count
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initMesocycles(_weeks.length);
      setState(() {});
    });
  }

  // ===== Normalization helpers (classic screen) =====
  void _setNormalizationAfterWeek(int weekIndex, double value, String unit) {
    setState(() {
      _weeks[weekIndex].normValue = value;
      _weeks[weekIndex].normUnit = unit;
    });
  }

  void _clearNormalizationAfterWeek(int weekIndex) {
    setState(() {
      _weeks[weekIndex].normValue = null;
      _weeks[weekIndex].normUnit = null;
    });
  }

  void _moveNormalization(int fromWeekIndex, int toWeekIndex) {
    if (fromWeekIndex == toWeekIndex) return;
    final src = _weeks[fromWeekIndex];
    if (src.normValue == null || src.normUnit == null) return;
    setState(() {
      _weeks[toWeekIndex].normValue = src.normValue;
      _weeks[toWeekIndex].normUnit = src.normUnit;
      src.normValue = null;
      src.normUnit = null;
    });
  }

  Future<void> _showNormalizationDialog({
    required int weekIndex,
    double? initialValue,
    String? initialUnit,
  }) async {
    final valueCtrl = TextEditingController(text: initialValue?.toString() ?? '');
    String unit = initialUnit ?? '%';
    final res = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Нормировка'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: valueCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Значение'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Единица'),
              value: unit,
              items: const [
                DropdownMenuItem(value: '%', child: Text('%')),
                DropdownMenuItem(value: 'kg', child: Text('кг')),
              ],
              onChanged: (v) {
                if (v != null) unit = v;
              },
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
          ElevatedButton(
            onPressed: () {
              final parsed = double.tryParse(valueCtrl.text.replaceAll(',', '.').trim());
              if (parsed == null) return;
              _setNormalizationAfterWeek(weekIndex, parsed, unit);
              Navigator.of(ctx).pop(true);
            },
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );
    res; // ignore result
  }

  Widget _normalizationSlot({
    required int weekIndex,
  }) {
    final w = _weeks[weekIndex];
    final has = w.normValue != null && w.normUnit != null;
    final theme = Theme.of(context);
    return DragTarget<_NormDragData>(
      onWillAccept: (data) => data != null,
      onAccept: (data) => _moveNormalization(data.weekIndex, weekIndex),
      builder: (context, candidateData, rejected) {
        final isHover = candidateData.isNotEmpty;
        return Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
          decoration: BoxDecoration(
            color: isHover ? theme.colorScheme.primary.withOpacity(0.06) : theme.colorScheme.surface,
            border: Border.all(color: theme.dividerColor),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text('После недели ${weekIndex + 1}', style: theme.textTheme.bodyMedium),
              ),
              if (has)
                LongPressDraggable<_NormDragData>(
                  data: _NormDragData(weekIndex),
                  feedback: Material(
                    color: Colors.transparent,
                    child: Chip(
                      label: Text('${w.normValue} ${w.normUnit}'),
                      backgroundColor: theme.colorScheme.primaryContainer,
                    ),
                  ),
                  child: InputChip(
                    label: Text('${w.normValue} ${w.normUnit}'),
                    onPressed: () => _showNormalizationDialog(
                      weekIndex: weekIndex,
                      initialValue: w.normValue,
                      initialUnit: w.normUnit,
                    ),
                    onDeleted: () => _clearNormalizationAfterWeek(weekIndex),
                  ),
                )
              else
                TextButton.icon(
                  onPressed: () => _showNormalizationDialog(weekIndex: weekIndex),
                  icon: const Icon(Icons.add),
                  label: const Text('Добавить нормировку'),
                ),
            ],
          ),
        );
      },
    );
  }

  // Simple drag data holder
  // ignore: unused_element
  static _NormDragData _normDragData(int i) => _NormDragData(i);

  @override
  void dispose() {
    _nameCtrl.dispose();
    // Dispose all set controllers
    for (final w in _weeks) {
      for (final exList in w.schedule.values) {
        for (final ex in exList) {
          for (final s in ex.sets) {
            s.intensityCtrl.dispose();
            s.effortCtrl.dispose();
            s.volumeCtrl.dispose();
          }
        }
      }
    }
    super.dispose();
  }

  Future<void> _fetchRpeTable() async {
    try {
      final api = ApiClient.create();
      final dynamic json = await api.get(ApiConfig.rpeEndpoint, context: 'RPE');
      if (json is Map) {
        final Map<int, Map<int, int>> parsed = {};
        json.forEach((k, v) {
          final intKey = int.tryParse(k.toString());
          if (intKey != null && v is Map) {
            final inner = <int, int>{};
            v.forEach((ek, ev) {
              final eKey = int.tryParse(ek.toString());
              final eVal = ev is int ? ev : int.tryParse(ev.toString() ?? '');
              if (eKey != null && eVal != null) {
                inner[eKey] = eVal;
              }
            });
            parsed[intKey] = inner;
          }
        });
        if (mounted) {
          setState(() {
            _rpeTable = parsed;
          });
        }
      }
    } catch (_) {
      // Keep table empty on failure; helpers will return nulls
    }
  }

  

  void _initMesocycles(int totalWeeks) {
    _mesocycles
      ..clear()
      ..add(_MesocycleDraft(name: 'Мезоцикл 1', weeksCount: totalWeeks));
  }

  void _addMesocycle() {
    setState(() {
      _mesocycles.add(_MesocycleDraft(name: 'Мезоцикл ${_mesocycles.length + 1}', weeksCount: 1));
      _weeks.add(_WeekDraft(name: 'Микроцикл ${_weeks.length + 1}', expanded: true));
      _renumberWeeksNames();
    });
  }

  void _removeMesocycle(int index) {
    if (_mesocycles.length <= 1) return;

    setState(() {
      // Calculate the range of weeks to remove
      int weekStartIndex = 0;
      for (int i = 0; i < index; i++) {
        weekStartIndex += _mesocycles[i].weeksCount;
      }
      final weeksToRemove = _mesocycles[index].weeksCount;

      // Remove the mesocycle and its associated weeks
      _mesocycles.removeAt(index);
      if (_weeks.length >= weekStartIndex + weeksToRemove) {
        _weeks.removeRange(weekStartIndex, weekStartIndex + weeksToRemove);
      }

      _renumberWeeksNames();
    });
  }

  void _onReorderMesocycles(int oldIndex, int newIndex) {
    setState(() {
      if (newIndex > oldIndex) newIndex -= 1;
      final item = _mesocycles.removeAt(oldIndex);
      _mesocycles.insert(newIndex, item);
    });
  }

  void _onReorderWeeks(int oldIndex, int newIndex) {
    setState(() {
      if (newIndex > oldIndex) newIndex -= 1;
      final item = _weeks.removeAt(oldIndex);
      _weeks.insert(newIndex, item);
      _renumberWeeksNames();
    });
  }

  void _renumberWeeksNames() {
    int weekCounter = 0;
    for (final meso in _mesocycles) {
      for (int i = 0; i < meso.weeksCount; i++) {
        if (weekCounter < _weeks.length) {
          _weeks[weekCounter].name = 'Микроцикл ${i + 1}';
          weekCounter++;
        }
      }
    }
  }

  void _ensureDay(int weekIdx, String dayKey) {
    _weeks[weekIdx].schedule.putIfAbsent(dayKey, () => <_ExerciseDraft>[]);
  }

  void _addExercise(int weekIdx, String day) async {
    final selected = await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const ExerciseSelectionScreen()),
    );
    if (selected != null && mounted) {
      // expected: ExerciseDefinition
      final ex = selected;
      final id = ex.id as int?;
      if (id != null) {
        setState(() {
          _ensureDay(weekIdx, day);
          _weeks[weekIdx].schedule[day]!.add(_ExerciseDraft(exerciseId: id));
          _exerciseNames[id] = ex.name as String;
        });
      }
    }
  }

  void _addSet(int weekIdx, String day, int exIndex) {
    setState(() {
      _ensureDay(weekIdx, day);
      _weeks[weekIdx].schedule[day]![exIndex].sets.add(_SetDraft());
    });
  }

  void _addWeek() {
    final idx = _weeks.length + 1;
    setState(() {
      _weeks.add(_WeekDraft(name: 'Микроцикл $idx', expanded: true));
    });
  }

  void _addWeekToMesocycle(int mesoIndex) {
    // Insert new microcycle at the end of the selected mesocycle's block
    int insertIndex = 0;
    for (int i = 0; i < mesoIndex; i++) {
      insertIndex += _mesocycles[i].weeksCount;
    }
    insertIndex += _mesocycles[mesoIndex].weeksCount;
    setState(() {
      _weeks.insert(insertIndex, _WeekDraft(name: 'Микроцикл ${_weeks.length + 1}', expanded: true));
      _mesocycles[mesoIndex].weeksCount += 1;
      _renumberWeeksNames();
    });
  }

    Future<void> _submit() async {
    if (_submitting) return;
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Заполните имя')));
      return;
    }
    final hasContent = _weeks.any((w) => w.schedule.values.any((exList) => exList.any((ex) => ex.sets.isNotEmpty)));
    if (!hasContent) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Добавьте хотя бы одно упражнение и сет')));
      return;
    }

    setState(() => _submitting = true);

    try {
      final service = ref.read(calendarPlanServiceProvider);
      final payload = {
        'name': name,
        'duration_weeks': _weeks.length,
        'schedule': <String, dynamic>{},
      };
      final created = await service.createCalendarPlan(payload);

      final mesoSvc = ref.read(mesocycleServiceProvider);
      int weekPointer = 0;
      for (final (mi, meso) in _mesocycles.indexed) {
        final createdMeso = await mesoSvc.createMesocycle(
          created.id,
          MesocycleUpdateDto(
            name: meso.name,
            notes: (meso.notes?.trim().isEmpty ?? true) ? null : meso.notes!.trim(),
            orderIndex: mi + 1,
          ),
        );

        for (int mj = 0; mj < meso.weeksCount; mj++) {
          if (weekPointer >= _weeks.length) break;
          final w = _weeks[weekPointer++];
          final Map<String, List<ExerciseScheduleItemDto>> microSched = {};

          for (var d = 1; d <= meso.microcycleLength; d++) {
            final dayKey = 'day$d';
            final exList = List<_ExerciseDraft>.from(w.schedule[dayKey] ?? const <_ExerciseDraft>[]);
            final filtered = exList.where((ex) => ex.sets.isNotEmpty).toList();
            if (filtered.isEmpty) continue;

            microSched[dayKey] = filtered
                .map((ex) => ExerciseScheduleItemDto(
                      exerciseId: ex.exerciseId,
                      sets: ex.sets.map((s) => ParamsSets(intensity: s.intensity, effort: s.effort, volume: s.volume)).toList(),
                    ))
                .toList();
          }

          if (microSched.isEmpty) continue;

          await mesoSvc.createMicrocycle(
            createdMeso.id,
            MicrocycleUpdateDto(
              name: w.name,
              orderIndex: mj + 1,
              schedule: microSched,
              daysCount: meso.microcycleLength,
              normalizationValue: w.normValue,
              normalizationUnit: w.normUnit,
            ),
          );
        }
      }

      if (!mounted) return;
      // Refresh plans list before navigating
      ref.read(calendarPlansNotifierProvider.notifier).loadCalendarPlans();
      Navigator.of(context).pop(); // Go back to the list screen

    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка создания плана: $e')));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  int? _repsFromIntensityEffort(int intensity, int effort) {
    final rpeRow = _rpeTable[intensity];
    return rpeRow?[effort];
  }

  int? _effortFromIntensityReps(int intensity, int reps) {
    final rpeRow = _rpeTable[intensity];
    if (rpeRow == null) return null;
    for (final entry in rpeRow.entries) {
      if (entry.value == reps) return entry.key;
    }
    return null;
  }

  int? _intensityFromEffortReps(int effort, int reps) {
    int? bestIntensity;
    for (final entry in _rpeTable.entries) {
      final repsAtEffort = entry.value[effort];
      if (repsAtEffort == reps) {
        bestIntensity = entry.key;
        break;
      }
    }
    return bestIntensity;
  }

  void _onSetFieldChanged(_SetDraft s, String field, String value) {
    if (_isSyncingFields) return;
    int? parsed = int.tryParse(value.trim());
    switch (field) {
      case 'intensity':
        s.intensity = parsed != null ? parsed.clamp(1, 100) : null;
        if (parsed != null && parsed != s.intensity) {
          // if clamped, reflect in UI
          _isSyncingFields = true;
          s.intensityCtrl.text = s.intensity!.toString();
          _isSyncingFields = false;
        }
        break;
      case 'effort':
        s.effort = parsed != null ? parsed.clamp(1, 10) : null;
        if (parsed != null && parsed != s.effort) {
          _isSyncingFields = true;
          s.effortCtrl.text = s.effort!.toString();
          _isSyncingFields = false;
        }
        break;
      case 'volume':
        if (parsed != null && parsed < 1) parsed = 1;
        s.volume = parsed;
        if (parsed != null && s.volume != parsed) {
          _isSyncingFields = true;
          s.volumeCtrl.text = s.volume!.toString();
          _isSyncingFields = false;
        }
        break;
    }

    // Update edited order (keep last two distinct fields)
    s.editedFields.remove(field);
    s.editedFields.add(field);
    if (s.editedFields.length > 2) {
      s.editedFields.removeAt(0);
    }

    // If we have two distinct fields with values, recalc the third
    if (s.editedFields.length == 2) {
      final a = s.editedFields[0];
      final b = s.editedFields[1];
      final all = {'intensity', 'effort', 'volume'};
      final third = all.difference({a, b}).first;

      int? computed;
      if (third == 'volume' && s.intensity != null && s.effort != null) {
        computed = _repsFromIntensityEffort(s.intensity!, s.effort!);
      } else if (third == 'effort' && s.intensity != null && s.volume != null) {
        computed = _effortFromIntensityReps(s.intensity!, s.volume!);
        if (computed != null) computed = computed.clamp(1, 10);
      } else if (third == 'intensity' && s.effort != null && s.volume != null) {
        computed = _intensityFromEffortReps(s.effort!, s.volume!);
        if (computed != null) computed = computed.clamp(1, 100);
      }

      if (computed != null) {
        _isSyncingFields = true;
        if (third == 'volume') {
          s.volume = computed;
          s.volumeCtrl.text = computed.toString();
        } else if (third == 'effort') {
          s.effort = computed;
          s.effortCtrl.text = computed.toString();
        } else if (third == 'intensity') {
          s.intensity = computed;
          s.intensityCtrl.text = computed.toString();
        }
        _isSyncingFields = false;
      }
    }

    if (mounted) setState(() {});
  }

  Widget _numberField(String label, TextEditingController controller, ValueChanged<String> onChanged, {String? hint}) {
    final theme = Theme.of(context);
    return SizedBox(
      width: 120,
      child: TextField(
        controller: controller,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        ),
        onChanged: onChanged,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Создать план'),
        actions: [
          IconButton(onPressed: _submitting ? null : _submit, icon: const Icon(Icons.check)),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(controller: _nameCtrl, decoration: const InputDecoration(labelText: 'Название плана')),
            const SizedBox(height: 16),
            _MesocycleEditor(
              mesocycles: _mesocycles,
              onAdd: _addMesocycle,
              onRemove: _removeMesocycle,
              onReorder: _onReorderMesocycles,
              onUpdate: (fn) => setState(fn),
              onAddWeekToMesocycle: _addWeekToMesocycle,
              weeks: _weeks,
              buildWeekTile: (idx, week, len) => _buildWeekTile(idx, week, len),
            ),
          ],
        ),
      ),
      floatingActionButton: _submitting ? null : null,
    );
  }

  Widget _buildDayCard(int weekIdx, String dayKey, List<_ExerciseDraft> exercises) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(_dayLabel(dayKey), style: theme.textTheme.titleSmall),
                Row(
                  children: [
                    Text('${exercises.length} упражн.', style: theme.textTheme.bodySmall),
                    const SizedBox(width: 8),
                    IconButton(
                      onPressed: () => _addExercise(weekIdx, dayKey),
                      icon: const Icon(Icons.add_circle_outline),
                      tooltip: 'Добавить упражнение',
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (exercises.isEmpty) const Text('Нет упражнений')
            else ...exercises.asMap().entries.map((e) => _buildExerciseCard(weekIdx, dayKey, e.key, e.value)).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildExerciseCard(int weekIdx, String dayKey, int exIndex, _ExerciseDraft ex) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: theme.dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(_exerciseNames[ex.exerciseId] ?? 'Упражнение #${ex.exerciseId}', style: theme.textTheme.titleSmall),
                Row(children: [
                  Text('${ex.sets.length} сет(ов)', style: theme.textTheme.bodySmall),
                  const SizedBox(width: 8),
                  IconButton(onPressed: () => _addSet(weekIdx, dayKey, exIndex), icon: const Icon(Icons.add_circle_outline), tooltip: 'Добавить сет'),
                ]),
              ],
            ),
            const SizedBox(height: 8),
            if (ex.sets.isEmpty) const Text('Нет сетов')
            else ...ex.sets.asMap().entries.map((entry) {
              final idx = entry.key + 1;
              final s = entry.value;
              return Container(
                margin: const EdgeInsets.symmetric(vertical: 4),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  border: Border.all(color: theme.dividerColor),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(width: 28, height: 28, alignment: Alignment.center, decoration: BoxDecoration(color: theme.colorScheme.primary.withOpacity(0.1), shape: BoxShape.circle), child: Text('$idx', style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary))),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _numberField('Intensity', s.intensityCtrl, (v) => _onSetFieldChanged(s, 'intensity', v), hint: '1-100'),
                          _numberField('Effort', s.effortCtrl, (v) => _onSetFieldChanged(s, 'effort', v), hint: '1-10'),
                          _numberField('Reps', s.volumeCtrl, (v) => _onSetFieldChanged(s, 'volume', v), hint: '>=1'),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildWeekTile(int idx, _WeekDraft week, int microcycleLength) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: week.expanded,
          onExpansionChanged: (v) => setState(() => week.expanded = v),
          leading: CircleAvatar(radius: 14, backgroundColor: theme.colorScheme.primary.withOpacity(0.1), child: Text(week.name.split(' ').last, style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary))),
          title: Text(week.name, style: theme.textTheme.titleMedium),
          trailing: const Icon(Icons.expand_more),
          children: [
            const SizedBox(height: 8),
            ...List.generate(microcycleLength, (i) {
              final dayKey = 'day${i + 1}';
              _ensureDay(idx, dayKey);
              final exs = week.schedule[dayKey]!;
              return _buildDayCard(idx, dayKey, exs);
            }),
            const SizedBox(height: 8),
            // Normalization slot after this week
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0),
              child: _normalizationSlot(weekIndex: idx),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  String _dayLabel(String dayKey) {
    if (dayKey.startsWith('day')) {
      final n = int.tryParse(dayKey.substring(3));
      if (n != null) return 'День $n';
    }
    return dayKey;
  }
}

// Drag data for normalization chip movement
class _NormDragData {
  final int weekIndex;
  _NormDragData(this.weekIndex);
}

class _MesocycleEditor extends StatelessWidget {
  const _MesocycleEditor({
    required this.mesocycles,
    required this.onAdd,
    required this.onRemove,
    required this.onReorder,
    required this.onUpdate,
    required this.onAddWeekToMesocycle,
    required this.weeks,
    required this.buildWeekTile,
  });

  final List<_MesocycleDraft> mesocycles;
  final VoidCallback onAdd;
  final ValueSetter<int> onRemove;
  final ReorderCallback onReorder;
  final ValueSetter<VoidCallback> onUpdate;
  final ValueSetter<int> onAddWeekToMesocycle;
  final List<_WeekDraft> weeks;
  final Widget Function(int, _WeekDraft, int) buildWeekTile;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Мезоциклы', style: theme.textTheme.titleLarge),
            TextButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add),
              label: const Text('Добавить мезоцикл'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (mesocycles.isEmpty)
          Card(
            child: ListTile(
              title: const Text('Нет мезоциклов'),
              subtitle: const Text('Добавьте хотя бы один мезоцикл'),
              trailing: IconButton(icon: const Icon(Icons.add), onPressed: onAdd),
            ),
          )
        else
          ReorderableListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            onReorder: onReorder,
            itemCount: mesocycles.length,
            itemBuilder: (context, index) {
              final m = mesocycles[index];
              int weekStartIndex = 0;
              for (int i = 0; i < index; i++) {
                weekStartIndex += mesocycles[i].weeksCount;
              }

              final weekEndIndex = weekStartIndex + m.weeksCount;

              final weekTiles = weeks.length >= weekEndIndex
                  ? weeks.sublist(weekStartIndex, weekEndIndex).map((week) {
                      final weekIndex = weeks.indexOf(week);
                      return buildWeekTile(weekIndex, week, m.microcycleLength);
                    }).toList()
                  : <Widget>[];

              return Card(
                key: ValueKey(m.hashCode),
                margin: const EdgeInsets.symmetric(vertical: 6),
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              initialValue: m.name,
                              decoration: const InputDecoration(labelText: 'Название мезоцикла'),
                              onChanged: (v) => onUpdate(() => m.name = v),
                            ),
                          ),
                          IconButton(icon: const Icon(Icons.delete_outline), onPressed: () => onRemove(index)),
                          ReorderableDragStartListener(
                            index: index,
                            child: const Icon(Icons.drag_handle),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        initialValue: m.notes ?? '',
                        decoration: const InputDecoration(labelText: 'Заметки (до 100 символов)'),
                        maxLength: 100,
                        onChanged: (v) => onUpdate(() => m.notes = v),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(child: Text('Длина микроцикла (дней):', style: theme.textTheme.bodyMedium)),
                          IconButton(onPressed: m.microcycleLength > 1 ? () => onUpdate(() => m.microcycleLength--) : null, icon: const Icon(Icons.remove_circle_outline)),
                          Text('${m.microcycleLength}', style: theme.textTheme.titleMedium),
                          IconButton(onPressed: () => onUpdate(() => m.microcycleLength++), icon: const Icon(Icons.add_circle_outline)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ...weekTiles,
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: () => onAddWeekToMesocycle(index),
                          icon: const Icon(Icons.add),
                          label: const Text('Добавить микроцикл'),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}

extension _CreateNavigation on _CalendarPlansScreenState {
  void _navigateToCreateScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const CalendarPlanCreateScreen()),
    );
  }

  void _navigateToWizardScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const CalendarPlanWizardScreen()),
    );
  }
}

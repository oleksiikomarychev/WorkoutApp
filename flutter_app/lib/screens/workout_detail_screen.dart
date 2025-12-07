import '../config/api_config.dart';
import 'package:flutter/material.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
import '../models/exercise_definition.dart';
import '../models/exercise_set_dto.dart';
import '../services/workout_service.dart';
import '../services/exercise_service.dart';
import '../services/service_locator.dart';
import '../services/api_client.dart';
import '../models/workout_session.dart';
import '../services/workout_session_service.dart';
import 'dart:convert';
import 'dart:async';
import 'exercise_form_screen.dart';
import 'exercise_selection_screen.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/workout_provider.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/widgets/floating_header_bar.dart';
import 'package:workout_app/screens/user_profile_screen.dart';


class _SetEditor {
  final TextEditingController weightCtrl;
  final TextEditingController repsCtrl;
  final TextEditingController rpeCtrl;
  final List<String> editedFields = [];
  Timer? debounce;

  _SetEditor({
    required this.weightCtrl,
    required this.repsCtrl,
    required this.rpeCtrl,
  });

  void dispose() {
    debounce?.cancel();
    weightCtrl.dispose();
    repsCtrl.dispose();
    rpeCtrl.dispose();
  }

  void scheduleDebounce(VoidCallback action, {Duration delay = const Duration(milliseconds: 500)}) {
    debounce?.cancel();
    debounce = Timer(delay, action);
  }

  void cancelDebounce() {
    debounce?.cancel();
    debounce = null;
  }
}


class _BaselineSet {
  final int reps;
  final double? weight;
  const _BaselineSet({required this.reps, this.weight});
}

class WorkoutDetailScreen extends ConsumerWidget {
  final int workoutId;

  const WorkoutDetailScreen({super.key, required this.workoutId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {

    final workoutAsync = ref.watch(workoutProvider(workoutId));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: null,
      body: workoutAsync.when(
        data: (workout) => _WorkoutDetailContent(workout: workout),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
    );
  }
}

class _WorkoutDetailContent extends StatefulWidget {
  final Workout workout;

  const _WorkoutDetailContent({required this.workout});

  @override
  State<_WorkoutDetailContent> createState() => _WorkoutDetailContentState();
}

class _WorkoutDetailContentState extends State<_WorkoutDetailContent> {
  bool _isLoading = false;
  bool _isLoadingExercises = false;
  List<ExerciseDefinition> _uniqueExercises = [];
  Workout? _workout;


  WorkoutSession? _activeSession;
  Timer? _sessionTimer;
  Duration _elapsed = Duration.zero;
  final ValueNotifier<Duration> _elapsedNotifier = ValueNotifier(Duration.zero);
  final Map<int, Set<int>> _completedByInstance = {};
  bool _isTogglingSet = false;


  Map<int, Map<int, int>> _rpeTable = {};
  Map<int, int> _exerciseMaxByExerciseId = {};

  final Map<String, _SetEditor> _setEditors = <String, _SetEditor>{};
  bool _isSyncingFields = false;


  final TextEditingController _notesCtrl = TextEditingController();
  final TextEditingController _statusCtrl = TextEditingController();
  final TextEditingController _locationCtrl = TextEditingController();
  final TextEditingController _durationCtrl = TextEditingController();
  final TextEditingController _rpeSessionCtrl = TextEditingController();
  final TextEditingController _readinessCtrl = TextEditingController();
  DateTime? _editedStartedAt;
  bool _isSavingMetadata = false;


  double _readinessSlider = 10.0;
  bool _isApplyingReadiness = false;
  final bool _scaleRepsWithReadiness = true;
  bool _isProgrammaticReadinessUpdate = false;



  final Map<String, _BaselineSet> _baselineSets = <String, _BaselineSet>{};


  bool _sessionTickerRunning = false;
  int _sessionTickerGen = 0;

  double? _weight;

  WidgetRef? _ref;

  @override
  void initState() {
    super.initState();

    _workout = widget.workout;
    _syncMetadataControllers();


    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _loadExercises();
      if (kDebugMode) {
        _fetchRawWorkoutData();
      }
      if (_workout?.id != null) {
        _loadActiveSession();
      }
    });


    _fetchRpeTable();
  }

  @override
  void didUpdateWidget(covariant _WorkoutDetailContent oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (oldWidget.workout.id != widget.workout.id) {
      setState(() {
        _workout = widget.workout;
      });
      _syncMetadataControllers();

      _loadExercises();
      if (_workout?.id != null) {
        _loadActiveSession();
      }
    }
  }

  Future<void> _maybeShowMacroSuggestion() async {
    if (!mounted || _workout?.id == null) return;
    try {
      final api = ApiClient.create();
      final endpoint = ApiConfig.getSessionHistoryEndpoint(_workout!.id!.toString());
      final resp = await api.get(endpoint, context: 'MacroSuggestion');
      if (resp is List && resp.isNotEmpty) {
        final Map<String, dynamic>? latest = resp.first is Map<String, dynamic> ? resp.first as Map<String, dynamic> : null;
        final Map<String, dynamic>? suggestion = latest != null && latest['macro_suggestion'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(latest['macro_suggestion'] as Map)
            : null;
        if (suggestion == null) return;
        final summary = suggestion['summary'] as Map?;
        final injectCount = summary != null ? (summary['inject_mesocycles'] ?? 0) : 0;
        final hasPatches = summary != null ? (summary['has_patches'] == true) : false;
        final appliedPlanId = suggestion['applied_plan_id']?.toString();
        if (!mounted) return;
        await showDialog<void>(
          context: context,
          builder: (ctx) {
            return AlertDialog(
              title: const Text('Найдены изменения по макросам'),
              content: Text('Вставок мезоциклов: $injectCount\nПатчи на тренировки: ${hasPatches ? 'да' : 'нет'}'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Отмена'),
                ),
                TextButton(
                  onPressed: () async {
                    Navigator.of(ctx).pop();
                    if (appliedPlanId != null) {
                      final applyEndpoint = ApiConfig.applyMacrosEndpoint(appliedPlanId);
                      try {
                        await api.post(applyEndpoint, <String, dynamic>{}, context: 'ApplyMacros');
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Макросы применены')),
                          );
                        }
                      } catch (e) {
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Не удалось применить макросы: $e')),
                          );
                        }
                      }
                    }
                  },
                  child: const Text('Применить'),
                ),
              ],
            );
          },
        );
      }
    } catch (_) {
      return;
    }
  }


  double _roundToStep(double value, double step) {
    if (step <= 0) return value;
    final rounded = (value / step).roundToDouble() * step;

    return double.parse(rounded.toStringAsFixed(1));
  }

  Future<void> _applyReadinessScaling() async {
    if (_workout == null) return;
    if (_isApplyingReadiness) return;
    setState(() {
      _isApplyingReadiness = true;
    });


    _ensureBaselineSets();


    double factor = _readinessFactor(_readinessSlider.clamp(0, 10));
    int updates = 0;
    try {

      for (final instance in _workout!.exerciseInstances) {
        for (int i = 0; i < instance.sets.length; i++) {
          final set = instance.sets[i];
          final String key = _editorKey(instance, i, set);
          final _BaselineSet base = _baselineSets[key] ?? _BaselineSet(reps: set.reps, weight: set.weight);
          final double? baseWeight = base.weight;
          double? newWeight;
          bool weightChanged = false;
          if (baseWeight != null) {
            final double rawScaled = baseWeight * factor;
            final double step = rawScaled <= 20.0 ? 1.0 : 2.5;
            newWeight = (_roundToStep(rawScaled, step).clamp(0.0, double.infinity));
            final double currentWeight = set.weight ?? baseWeight;
            weightChanged = (newWeight - currentWeight).abs() > 0.0001;
          }
          final int newReps = _scaleRepsWithReadiness
              ? ((base.reps * factor).round().clamp(1, 10000))
              : set.reps;

          final bool repsChanged = newReps != set.reps;
          final bool changed = repsChanged || weightChanged;
          if (!changed) continue;

          await _updateSetField(
            instance,
            i,
            reps: repsChanged ? newReps : null,
            weight: weightChanged ? newWeight : null,
          );
          updates++;
        }
      }
      _reconcileEditors();
      await _saveWorkoutMetadata();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Applied readiness ${_readinessSlider.round()}/10 (x${factor.toStringAsFixed(2)}) to $updates set${updates == 1 ? '' : 's'}',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to apply readiness: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isApplyingReadiness = false;
        });
      }
    }
  }


  void _ensureBaselineSets() {
    if (_workout == null) return;
    final Map<String, _BaselineSet> snap = <String, _BaselineSet>{};
    for (final instance in _workout!.exerciseInstances) {
      for (int i = 0; i < instance.sets.length; i++) {
        final set = instance.sets[i];
        final key = _editorKey(instance, i, set);

        final existing = _baselineSets[key];
        snap[key] = existing ?? _BaselineSet(reps: set.reps, weight: set.weight);
      }
    }
    _baselineSets
      ..clear()
      ..addAll(snap);
  }

  void _writeReadinessText(double value) {
    final int clamped = value.clamp(0.0, 10.0).round();
    final String next = clamped.toString();
    if (_readinessCtrl.text == next) {
      return;
    }
    _isProgrammaticReadinessUpdate = true;
    _readinessCtrl.text = next;
    _isProgrammaticReadinessUpdate = false;
  }



  double _readinessFactor(double readiness) {
    final r = readiness.clamp(0.0, 10.0);
    const double base = 0.8;
    const double slope = 0.025;
    final double factor = base + slope * r;
    if (factor < 0.8) return 0.8;
    if (factor > 1.05) return 1.05;
    return factor;
  }



  Future<void> _updateSetField(
    ExerciseInstance instance,
    int setIndex, {
    int? reps,
    double? weight,
    double? rpe,
  }) async {
    if (_isLoading) return;
    if (setIndex < 0 || setIndex >= instance.sets.length) return;

    try {
      setState(() {
        _isLoading = true;
      });

      final current = instance.sets[setIndex];
      final oldSetId = current.id;
      final wasCompleted = instance.id != null && oldSetId != null && _isSetCompleted(instance.id!, oldSetId);

      final updatedSet = current.copyWith(
        reps: reps ?? current.reps,
        weight: weight ?? current.weight,
        rpe: rpe ?? current.rpe,
        order: current.order ?? setIndex,
      );

      final workoutService = _ref!.read(workoutServiceProvider);
      ExerciseInstance savedInstance;
      final setId = updatedSet.id ?? current.id;

      if (instance.id != null && setId != null) {

        savedInstance = await workoutService.updateExerciseSet(
          instanceId: instance.id!,
          setId: setId,
          reps: updatedSet.reps,
          weight: updatedSet.weight,
          rpe: updatedSet.rpe,
          order: updatedSet.order,
        );
      } else {

        final newSets = List<ExerciseSetDto>.from(instance.sets);
        newSets[setIndex] = updatedSet;
        final updatedInstance = instance.copyWith(sets: newSets);
        savedInstance = await workoutService.updateExerciseInstance(updatedInstance);
      }

      if (_workout != null && mounted) {
        setState(() {
          final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
          final idx = updatedInstances.indexWhere((i) => i.id == savedInstance.id);
          if (idx != -1) {
            updatedInstances[idx] = savedInstance;
            _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
          }
        });
      }
      final newSets = savedInstance.sets;
      final newSetId = (setIndex >= 0 && setIndex < newSets.length) ? newSets[setIndex].id : null;
      if (wasCompleted && instance.id != null && oldSetId != null && newSetId != null && newSetId != oldSetId) {
        await _handleCompletedSetIdMigration(instance.id!, oldSetId, newSetId);
      }
      await _loadExercises();
      _reconcileEditors();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update set: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      } else {
        _isLoading = false;
      }
    }
  }


  Future<void> _fetchRawWorkoutData() async {
    if (_workout?.id == null) return;

    try {
      final api = ApiClient.create();
      final data = await api.get(
        ApiConfig.getWorkoutEndpoint(_workout!.id!.toString()),
        context: 'RawWorkoutDebug',
      );

      print('\nRAW WORKOUT DATA:');
      print(jsonEncode(data));

      if (data is Map && data['exercise_instances'] is List) {
        print('\nEXERCISE INSTANCES (${data['exercise_instances'].length}):');
        for (var instance in data['exercise_instances']) {
          print('Instance ID: ${instance['id']}');
          print('Exercise Definition ID: ${instance['exercise_list_id']}');
          print('Workout ID: ${instance['workout_id']}');
          print('Sets: ${instance['sets']}');
          print('Exercise Definition: ${instance['exercise_definition'] != null}');
          if (instance['exercise_definition'] != null) {
            print('  Exercise Name: ${instance['exercise_definition']['name']}');
          }
          print('---');
        }
      } else {
        print('No exercise instances found or invalid format');
      }
    } catch (e, stackTrace) {
      print('Error fetching raw workout data: $e');
      print('Stack trace: $stackTrace');
    }
  }

  Future<void> _deleteExerciseInstance(ExerciseInstance instance) async {
    try {
      setState(() {
        _isLoading = true;
      });


      final shouldDelete = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Delete Exercise'),
          content: const Text('Are you sure you want to remove this exercise from your workout?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      );

      if (shouldDelete != true) {
        print('User cancelled deletion');
        return;
      }


      final workoutService = _ref!.read(workoutServiceProvider);
      if (instance.id != null) {
        await workoutService.deleteExerciseInstance(instance.id!);
        print('Successfully deleted instance from backend');


        await _loadExercises();
        print('Successfully refreshed workout data after deletion');

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Exercise removed from workout')),
          );
        }
      } else {
        print('Cannot delete instance with null ID');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Error: Cannot delete unsaved exercise')),
          );
        }
      }
    } catch (e, stackTrace) {
      print('Error deleting exercise instance: $e');
      print('Stack trace: $stackTrace');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to remove exercise: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _addSetToInstance(ExerciseInstance instance) async {
    if (_isLoading) return;

    try {
      print('Adding set to instance ${instance.id}');
      setState(() {
        _isLoading = true;
      });


      int lastReps = 5;
      double lastWeight = 0.0;

      if (instance.sets.isNotEmpty) {

        final lastSet = instance.sets.last;
        lastReps = lastSet.reps;
        lastWeight = lastSet.weight;
      }

      final newSet = ExerciseSetDto(
        id: null,
        reps: lastReps,
        weight: lastWeight,
        order: instance.sets.length,
        exerciseInstanceId: instance.id,
        localId: null,
        volume: (lastReps * lastWeight).round(),
      );

      print('Created new set: $newSet');


      final updatedInstance = instance.copyWith(
        sets: [...instance.sets, newSet],
      );

      print('Updated instance with new set: ${updatedInstance.sets.length} total sets');


      final workoutService = _ref!.read(workoutServiceProvider);
      final savedInstance = await workoutService.updateExerciseInstance(updatedInstance);

      print('Successfully updated instance in backend');


      if (_workout != null && mounted) {
        setState(() {

          final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
          final index = updatedInstances.indexWhere((i) => i.id == savedInstance.id);
          if (index != -1) {
            updatedInstances[index] = savedInstance;
            _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
          }
        });
      }
      _reconcileEditors();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Set added successfully')),
        );
      }
        } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to add set: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadExercises() async {
    if (_workout == null) return;

    setState(() {
      _isLoadingExercises = true;
    });

    try {
      final workoutService = _ref!.read(workoutServiceProvider);
      final updatedWorkout = await workoutService.getWorkoutWithDetails(_workout!.id!);

      print('Fetched workout with ${updatedWorkout.exerciseInstances.length} exercise instances');


      final exerciseListIds = updatedWorkout.exerciseInstances
          .map((e) => e.exerciseListId)
          .toSet()
          .toList();

      if (exerciseListIds.isNotEmpty) {

        final exerciseService = _ref!.read(exerciseServiceProvider);
        final exercises = await exerciseService.getExercisesByIds(exerciseListIds);


        final exerciseMap = {
          for (var e in exercises) e.id: e,
        };


        final updatedInstances = updatedWorkout.exerciseInstances.map((instance) {
          final def = exerciseMap[instance.exerciseListId];
          return instance.copyWith(exerciseDefinition: def);
        }).toList();


        final exerciseDefinitions = exerciseMap.values.toList();

        setState(() {
          _workout = updatedWorkout.copyWith(exerciseInstances: updatedInstances);
          _uniqueExercises = exerciseDefinitions.cast<ExerciseDefinition>();
          print('Found ${_uniqueExercises.length} unique exercises');
        });
      } else {
        setState(() {
          _workout = updatedWorkout;
          _uniqueExercises = [];
          print('No exercise instances found in workout');
        });
      }
          _reconcileEditors();
    } catch (e, stackTrace) {
      print('Error loading exercises: $e');
      print('Stack trace: $stackTrace');

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load exercises: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingExercises = false;
        });
      }
    }
  }


  Future<void> _fetchRpeTable() async {
    try {
      final api = ApiClient.create();
      final dynamic json = await api.get(ApiConfig.rpeTableEndpoint, context: 'RPE');
      if (json is Map) {
        final Map<int, Map<int, int>> parsed = {};
        json.forEach((k, v) {
          final intKey = int.tryParse(k.toString());
          if (intKey != null && v is Map) {
            final inner = <int, int>{};
            v.forEach((ek, ev) {
              final eKey = int.tryParse(ek.toString());
              final eVal = ev is int ? ev : int.tryParse(ev.toString());
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

    }
  }


  void _d(String msg) {
    if (kDebugMode) {

      print('[WorkoutDetail] ${DateTime.now().toIso8601String()} | $msg');
    }
  }

  void _syncMetadataControllers() {
    final w = _workout;
    _notesCtrl.text = w?.notes ?? '';
    _statusCtrl.text = w?.status ?? '';
    _locationCtrl.text = w?.location ?? '';
    _durationCtrl.text = (w?.durationSeconds ?? '').toString();
    _rpeSessionCtrl.text = (w?.rpeSession == null)
        ? ''
        : ((w!.rpeSession! % 1 == 0)
            ? w.rpeSession!.toStringAsFixed(0)
            : w.rpeSession!.toStringAsFixed(1));

    final double readinessRaw = (w?.readinessScore?.toDouble() ?? 10.0);
    final double normalized = readinessRaw > 10.0 ? readinessRaw / 10.0 : readinessRaw;
    _readinessSlider = normalized.clamp(0.0, 10.0);
    _writeReadinessText(_readinessSlider);
    _editedStartedAt = w?.startedAt;
  }

  Future<void> _saveWorkoutMetadata() async {
    if (_workout?.id == null) return;
    if (_isSavingMetadata) return;
    setState(() => _isSavingMetadata = true);
    try {
      int? parseInt(String s) => int.tryParse(s.trim());
      double? parseDouble(String s) => double.tryParse(s.trim().replaceAll(',', '.'));
      String? emptyToNull(String s) => s.trim().isEmpty ? null : s.trim();


      final int? dur = parseInt(_durationCtrl.text);
      final double? rpeRaw = parseDouble(_rpeSessionCtrl.text);
      final double? rpe = (rpeRaw == null)
          ? null
          : (rpeRaw < 1.0)
              ? 1.0
              : (rpeRaw > 10.0)
                  ? 10.0
                  : rpeRaw;
      final int readiness = _readinessSlider.round().clamp(0, 10);

      final updated = _workout!.copyWith(
        notes: emptyToNull(_notesCtrl.text),
        status: emptyToNull(_statusCtrl.text),
        startedAt: _editedStartedAt,
        durationSeconds: dur,
        rpeSession: rpe,
        location: emptyToNull(_locationCtrl.text),
        readinessScore: readiness,
      );

      _d('Saving workout metadata for id=${updated.id}');
      final svc = _ref!.read(workoutServiceProvider);
      final saved = await svc.updateWorkout(updated);
      if (!mounted) return;
      setState(() {
        _workout = saved;
      });
      _syncMetadataControllers();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Workout updated')),
        );
      }
    } catch (e, st) {
      _d('Failed to save workout metadata: $e\n$st');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update workout: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSavingMetadata = false);
    }
  }


  Future<void> _loadActiveSession() async {
    if (_workout?.id == null) return;
    try {
      final svc = _ref!.read(workoutSessionServiceProvider);
      final session = await svc.getActiveSession(_workout!.id!);
      if (!mounted) return;
      setState(() {
        _activeSession = session;

        if (session != null && session.finishedAt != null) {

        }
      });
      _d('Active session loaded: id=${_activeSession?.id}, isActive=${_activeSession?.isActive}');
      _parseProgressFromSession();
      if (_activeSession?.isActive == true) {
        _startSessionTicker();
      } else {
        _stopSessionTicker();
      }
    } catch (_) {

    }
  }

  void _parseProgressFromSession() {
    _completedByInstance.clear();
    final Map<String, dynamic> progress = _activeSession?.progress ?? const <String, dynamic>{};
    if (progress.isNotEmpty) {
      final completed = progress['completed'];
      if (completed is Map) {
        completed.forEach((key, value) {
          final instId = int.tryParse(key.toString());
          if (instId != null) {
            final setIds = <int>{};
            if (value is List) {
              for (final v in value) {
                final sid = v is int ? v : int.tryParse(v.toString());
                if (sid != null) setIds.add(sid);
              }
            }
            _completedByInstance[instId] = setIds;
          }
        });
      }
    }
    if (mounted) setState(() {});
  }

  void _startSessionTicker() {

    _sessionTickerGen++;
    final myGen = _sessionTickerGen;
    _sessionTimer?.cancel();
    _sessionTickerRunning = true;
    _d('Session ticker START gen=$myGen');

    void tick() {
      if (!_sessionTickerRunning || myGen != _sessionTickerGen) {
        _d('Tick ignored (running=$_sessionTickerRunning, myGen=$myGen, currentGen=$_sessionTickerGen)');
        return;
      }
      if (!mounted || _activeSession == null) {
        _d('Tick aborted (mounted=$mounted, active=${_activeSession != null})');
        return;
      }
      final start = _activeSession!.startedAt;
      final end = _activeSession!.finishedAt;
      final now = DateTime.now();
      final dur = (end ?? now).difference(start);
      _elapsed = dur.isNegative ? Duration.zero : dur;
      _elapsedNotifier.value = _elapsed;
      if (end != null) {
        _d('Session ended; stopping ticker gen=$myGen');
        _stopSessionTicker();
      }
    }

    tick();
    _sessionTimer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
  }

  void _stopSessionTicker() {
    _d('Session ticker STOP (before cancel) running=$_sessionTickerRunning');
    _sessionTickerRunning = false;
    _sessionTimer?.cancel();
    _sessionTimer = null;
    _d('Session ticker STOP (after cancel)');
  }

  String _formatDuration(Duration d) {
    final hours = d.inHours;
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return hours > 0 ? '$hours:$minutes:$seconds' : '$minutes:$seconds';
  }

  Future<void> _startSession() async {
    if (_workout?.id == null) return;
    try {
      _d('Starting session for workoutId=${_workout?.id}');
      setState(() => _isLoading = true);

      final workoutSvc = _ref!.read(workoutServiceProvider);
      final updated = await workoutSvc.startWorkoutBff(_workout!.id!, includeDefinitions: true);
      if (!mounted) return;
      setState(() {
        _workout = updated;

        _editedStartedAt = updated.startedAt;
        _durationCtrl.text = '0';
      });

      await _loadActiveSession();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Workout started')),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start session: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _finishSession({bool cancelled = false, bool markWorkoutCompleted = false}) async {
    if (_workout?.id == null) return;
    try {
      _d('Finishing workoutId=${_workout?.id} cancelled=$cancelled markCompleted=$markWorkoutCompleted');
      setState(() => _isLoading = true);

      final workoutSvc = _ref!.read(workoutServiceProvider);
      final updated = await workoutSvc.finishWorkoutBff(
        _workout!.id!,
        includeDefinitions: true,
        cancelled: cancelled,
        markWorkoutCompleted: markWorkoutCompleted,
      );
      if (!mounted) return;

      _stopSessionTicker();
      await _loadActiveSession();

      setState(() {
        _workout = updated;
        _editedStartedAt ??= updated.startedAt;
        if ((updated.durationSeconds ?? 0) > 0) {
          _durationCtrl.text = (updated.durationSeconds!).toString();
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(cancelled ? 'Session cancelled' : 'Workout finished')),
      );

      await _maybeShowMacroSuggestion();



    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to finish session: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _advanceToNextWorkoutInPlan(BuildContext context) async {
    try {
      final workoutSvc = _ref!.read(workoutServiceProvider);

      final nextWorkout = await workoutSvc.getNextWorkoutInPlan(_workout!.id!);
      if (nextWorkout == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No next workout found in this plan')),
          );
        }
        return;
      }

      if (_workout?.id == nextWorkout.id) return;

      if (!mounted) return;

      _stopSessionTicker();
      setState(() {
        _workout = nextWorkout;
        _activeSession = null;
        _elapsed = Duration.zero;
        _elapsedNotifier.value = Duration.zero;
        _completedByInstance.clear();
      });
      await _loadExercises();
      await _loadActiveSession();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Loaded next workout: ${nextWorkout.name}')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load next workout: $e')),
        );
      }
    }
  }

  bool _isSetCompleted(int instanceId, int setId) {
    final s = _completedByInstance[instanceId];
    return s != null && s.contains(setId);
  }

  Future<void> _toggleSetCompletion(ExerciseInstance instance, ExerciseSetDto set) async {
    if (_activeSession?.id == null || _activeSession?.isActive != true) return;
    if (instance.id == null || set.id == null) return;
    if (_isTogglingSet) return;
    _isTogglingSet = true;
    try {
      final svc = _ref!.read(workoutSessionServiceProvider);
      final desired = !_isSetCompleted(instance.id!, set.id!);
      final session = await svc.updateSetCompletion(
        sessionId: _activeSession!.id!,
        instanceId: instance.id!,
        setId: set.id!,
        completed: desired,
      );
      if (!mounted) return;
      setState(() => _activeSession = session);
      _parseProgressFromSession();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update set completion: $e')),
        );
      }
    } finally {
      _isTogglingSet = false;
    }
  }

  int? _repsFromIntensityEffort(int intensity, int effort) {
    final row = _rpeTable[intensity];
    return row?[effort];
  }

  int? _effortFromIntensityReps(int intensity, int reps) {
    final row = _rpeTable[intensity];
    if (row == null) return null;
    for (final e in row.entries) {
      if (e.value == reps) return e.key;
    }
    return null;
  }

  int? _intensityFromEffortReps(int effort, int reps) {
    int? best;
    for (final entry in _rpeTable.entries) {
      if (entry.value[effort] == reps) {
        best = entry.key;
        break;
      }
    }
    return best;
  }

  int? _intensityFromWeight(int exerciseId, double w) {
    final max = _exerciseMaxByExerciseId[exerciseId];
    if (max == null || max <= 0) return null;
    int pct = ((w / max) * 100).round();
    if (pct < 1) pct = 1;
    if (pct > 100) pct = 100;
    return pct;
  }

  String _editorKey(ExerciseInstance instance, int setIndex, ExerciseSetDto set) {
    final instKey = instance.id?.toString() ?? 'inst';
    final setKey = set.id?.toString() ?? 'idx$setIndex';
    return '$instKey-$setKey';
  }



















  _SetEditor _getSetEditor(ExerciseInstance instance, int setIndex, ExerciseSetDto set) {
    final key = _editorKey(instance, setIndex, set);
    final existing = _setEditors[key];
    if (existing != null) return existing;
    String fmtWeight(double w) => (w % 1 == 0) ? w.toStringAsFixed(0) : w.toStringAsFixed(1);
    final editor = _SetEditor(
      weightCtrl: TextEditingController(text: fmtWeight(set.weight)),
      repsCtrl: TextEditingController(text: set.reps.toString()),
      rpeCtrl: TextEditingController(text: set.rpe == null ? '' : ((set.rpe! % 1 == 0) ? set.rpe!.toStringAsFixed(0) : set.rpe!.toStringAsFixed(1))),
    );
    _setEditors[key] = editor;
    return editor;
  }

  Future<void> _handleCompletedSetIdMigration(int instanceId, int oldSetId, int newSetId) async {
    final localChanged = _updateLocalCompletion(instanceId, oldSetId, newSetId);
    final sessionActive = _activeSession?.id != null && _activeSession?.isActive == true;
    if (!sessionActive || _ref == null) {
      if (localChanged && mounted) {
        setState(() {});
      }
      return;
    }
    try {
      final svc = _ref!.read(workoutSessionServiceProvider);
      final sessionId = _activeSession!.id!;
      await svc.updateSetCompletion(
        sessionId: sessionId,
        instanceId: instanceId,
        setId: oldSetId,
        completed: false,
      );
      final session = await svc.updateSetCompletion(
        sessionId: sessionId,
        instanceId: instanceId,
        setId: newSetId,
        completed: true,
      );
      if (!mounted) return;
      setState(() => _activeSession = session);
      _parseProgressFromSession();
    } catch (e) {
      _d('Failed to resync set completion: $e');
    }
  }

  bool _updateLocalCompletion(int instanceId, int oldSetId, int newSetId) {
    final current = _completedByInstance[instanceId];
    if (current == null || !current.contains(oldSetId)) {
      return false;
    }
    final updated = Set<int>.from(current);
    updated.remove(oldSetId);
    updated.add(newSetId);
    _completedByInstance[instanceId] = updated;
    return true;
  }

  void _onInlineFieldChanged(
    ExerciseInstance instance,
    int setIndex,
    ExerciseSetDto set,
    String field,
    String value,
  ) {
    if (_isSyncingFields) return;
    final editor = _getSetEditor(instance, setIndex, set);

    editor.editedFields.remove(field);
    editor.editedFields.add(field);
    if (editor.editedFields.length > 2) editor.editedFields.removeAt(0);


    double? parseDouble(String s) => double.tryParse(s.replaceAll(',', '.').trim());
    int? parseInt(String s) => int.tryParse(s.trim());

    final w = parseDouble(editor.weightCtrl.text);
    final r = parseInt(editor.repsCtrl.text);
    final eRaw = parseDouble(editor.rpeCtrl.text);
    final e = eRaw?.round();

    final bool hasTwo = editor.editedFields.length >= 2;
    String? third;
    if (hasTwo) {
      final a = editor.editedFields[0];
      final b = editor.editedFields[1];
      third = {'weight', 'reps', 'rpe'}.difference({a, b}).first;
    }

    String fmtWeight(double v) => (v % 1 == 0) ? v.toStringAsFixed(0) : v.toStringAsFixed(1);

    int exerciseId = instance.exerciseListId;
    _isSyncingFields = true;
    try {
      if (hasTwo && third == 'weight' && r != null && e != null) {
        final intensity = _intensityFromEffortReps(e.clamp(1, 10), r.clamp(1, 1000));
        final max = _exerciseMaxByExerciseId[exerciseId];
        if (intensity != null && max != null) {
          final newWeight = max * (intensity / 100.0);
          editor.weightCtrl.text = fmtWeight(newWeight);
        }
      } else if (hasTwo && third == 'reps' && w != null && e != null) {
        final intensity = _intensityFromWeight(exerciseId, w);
        final reps = (intensity != null) ? _repsFromIntensityEffort(intensity, e.clamp(1, 10)) : null;
        if (reps != null) editor.repsCtrl.text = reps.toString();
      } else if (hasTwo && third == 'rpe' && w != null && r != null) {
        final intensity = _intensityFromWeight(exerciseId, w);
        final eff = (intensity != null) ? _effortFromIntensityReps(intensity, r.clamp(1, 1000)) : null;
        if (eff != null) editor.rpeCtrl.text = eff.toString();
      }
    } finally {
      _isSyncingFields = false;
    }
    if (mounted) setState(() {});

    editor.scheduleDebounce(() {
      if (!mounted) return;
      editor.cancelDebounce();
      unawaited(_onInlineFieldSubmitted(instance, setIndex, set));
    });
  }

  Future<void> _onInlineFieldSubmitted(
    ExerciseInstance instance,
    int setIndex,
    ExerciseSetDto set,
  ) async {
    final editor = _getSetEditor(instance, setIndex, set);
    editor.cancelDebounce();
    double? parseDouble(String s) => double.tryParse(s.replaceAll(',', '.').trim());
    int? parseInt(String s) => int.tryParse(s.trim());

    final double? weight = parseDouble(editor.weightCtrl.text);
    final int? reps = parseInt(editor.repsCtrl.text);
    final double? rpe = parseDouble(editor.rpeCtrl.text)?.clamp(1.0, 10.0);


    final fields = <String, bool>{
      'weight': weight != null,
      'reps': reps != null,
      'rpe': rpe != null,
    };
    final known = fields.entries.where((e) => e.value).map((e) => e.key).toList();
    if (known.length == 2) {
      _isSyncingFields = true;
      try {
        int exerciseId = instance.exerciseListId;
        final a = known[0];
        final b = known[1];
        final third = {'weight', 'reps', 'rpe'}.difference({a, b}).first;

        String fmtWeight(double v) => (v % 1 == 0) ? v.toStringAsFixed(0) : v.toStringAsFixed(1);

        if (third == 'weight' && reps != null && rpe != null) {
          final intensity = _intensityFromEffortReps((rpe.round()).clamp(1, 10), reps.clamp(1, 1000));
          final max = _exerciseMaxByExerciseId[exerciseId];
          if (intensity != null && max != null) {
            final w = max * (intensity / 100.0);
            editor.weightCtrl.text = fmtWeight(w);
          }
        } else if (third == 'reps' && weight != null && rpe != null) {
          final intensity = _intensityFromWeight(exerciseId, weight);
          final repsCalc = (intensity != null) ? _repsFromIntensityEffort(intensity, rpe.round().clamp(1, 10)) : null;
          if (repsCalc != null) editor.repsCtrl.text = repsCalc.toString();
        } else if (third == 'rpe' && weight != null && reps != null) {
          final intensity = _intensityFromWeight(exerciseId, weight);
          final eff = (intensity != null) ? _effortFromIntensityReps(intensity, reps.clamp(1, 1000)) : null;
          if (eff != null) editor.rpeCtrl.text = eff.toString();
        }
      } finally {
        _isSyncingFields = false;
      }
    }

    final double? finalWeightRaw = double.tryParse(editor.weightCtrl.text.replaceAll(',', '.'));
    final int? finalRepsRaw = int.tryParse(editor.repsCtrl.text.trim());
    final double? finalRpeRaw = double.tryParse(editor.rpeCtrl.text.trim());
    final double? finalWeight = finalWeightRaw?.clamp(0.0, 10000.0);
    final int? finalReps = finalRepsRaw?.clamp(1, 1000);
    final double? finalRpe = finalRpeRaw?.clamp(1.0, 10.0);

    await _updateSetField(
      instance,
      setIndex,
      reps: finalReps,
      weight: finalWeight,
      rpe: finalRpe,
    );
  }

  Future<void> _handleDeleteSet(ExerciseInstance instance, int setIndex) async {
    try {
      if (instance.id == null) {
        throw Exception('Cannot delete set: Instance ID is null');
      }

      if (setIndex < 0 || setIndex >= instance.sets.length) {
        throw Exception('Invalid set index: $setIndex');
      }

      final setToDelete = instance.sets[setIndex];


      final confirm = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Delete Set'),
          content: const Text('Are you sure you want to delete this set? This action cannot be undone.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('CANCEL'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              style: TextButton.styleFrom(
                foregroundColor: Colors.red,
              ),
              child: const Text('DELETE'),
            ),
          ],
        ),
      );

      if (confirm != true) return;

      setState(() {
        _isLoading = true;
      });

      if (setToDelete.id == null) {

        final workoutService = _ref!.read(workoutServiceProvider);
        try {

          await _loadExercises();


          final refreshedInstance = _workout?.exerciseInstances
              .firstWhere((i) => i.id == instance.id, orElse: () => instance);

          if (refreshedInstance != null && setIndex >= 0 && setIndex < refreshedInstance.sets.length) {
            final refreshedSet = refreshedInstance.sets[setIndex];
            if (refreshedSet.id != null && instance.id != null) {

              await workoutService.deleteExerciseSet(instance.id!, refreshedSet.id!);


              final updatedSets = List<ExerciseSetDto>.from(refreshedInstance.sets)..removeAt(setIndex);
              final updatedInstance = refreshedInstance.copyWith(sets: updatedSets);

              if (_workout != null) {
                final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
                final idx = updatedInstances.indexWhere((i) => i.id == updatedInstance.id);
                if (idx != -1) {
                  updatedInstances[idx] = updatedInstance;
                  setState(() {
                    _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
                  });
                }
              }
              _reconcileEditors();

              await _loadExercises();
            } else {

              final updatedSets = List<ExerciseSetDto>.from(instance.sets)..removeAt(setIndex);
              final updatedInstance = instance.copyWith(sets: updatedSets);
              if (_workout != null) {
                final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
                final idx = updatedInstances.indexWhere((i) => i.id == instance.id);
                if (idx != -1) {
                  updatedInstances[idx] = updatedInstance;
                  setState(() {
                    _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
                  });
                }
              }
              _reconcileEditors();
            }
          } else {

            final updatedSets = List<ExerciseSetDto>.from(instance.sets)..removeAt(setIndex);
            final updatedInstance = instance.copyWith(sets: updatedSets);
            if (_workout != null) {
              final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
              final idx = updatedInstances.indexWhere((i) => i.id == instance.id);
              if (idx != -1) {
                updatedInstances[idx] = updatedInstance;
                setState(() {
                  _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
                });
              }
            }
            _reconcileEditors();
          }
        } catch (e) {

          final updatedSets = List<ExerciseSetDto>.from(instance.sets)..removeAt(setIndex);
          final updatedInstance = instance.copyWith(sets: updatedSets);
          if (_workout != null) {
            final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
            final idx = updatedInstances.indexWhere((i) => i.id == instance.id);
            if (idx != -1) {
              updatedInstances[idx] = updatedInstance;
              setState(() {
                _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
              });
            }
          }
          _reconcileEditors();
        }
      } else {

        final workoutService = _ref!.read(workoutServiceProvider);
        await workoutService.deleteExerciseSet(instance.id!, setToDelete.id!);


        final updatedSets = List<ExerciseSetDto>.from(instance.sets)..removeAt(setIndex);
        final updatedInstance = instance.copyWith(sets: updatedSets);

        if (_workout != null) {
          final updatedInstances = List<ExerciseInstance>.from(_workout!.exerciseInstances);
          final index = updatedInstances.indexWhere((i) => i.id == instance.id);
          if (index != -1) {
            updatedInstances[index] = updatedInstance;
            setState(() {
              _workout = _workout!.copyWith(exerciseInstances: updatedInstances);
            });
          }
        }
        _reconcileEditors();


        await _loadExercises();
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Set deleted successfully'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e, stackTrace) {
      print('Error deleting set: $e');
      print('Stack trace: $stackTrace');

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete set: ${e.toString()}'),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  double _calculateTotalVolume(ExerciseInstance instance) {
    return instance.sets.fold<double>(
      0,
      (sum, set) => sum + (set.weight * set.reps),
    );
  }

  Future<void> _showAddExerciseDialog() async {
    try {
      if (_workout?.id == null) {
        throw Exception('Workout ID is required');
      }

      final selectedExercise = await Navigator.push<ExerciseDefinition>(
        context,
        MaterialPageRoute(
          builder: (context) => const ExerciseSelectionScreen(),
        ),
      );

      if (selectedExercise != null) {
        final result = await Navigator.push<Map<String, dynamic>>(
          context,
          MaterialPageRoute(
            builder: (context) => ExerciseFormScreen(
              exercise: selectedExercise,
              workoutId: _workout!.id!,
              defaultOrder: _workout?.exerciseInstances.length,
            ),
          ),
        );

        final instance = result?['instance'];
        if (instance is ExerciseInstance) {
          final workoutService = _ref!.read(workoutServiceProvider);
          setState(() => _isLoading = true);
          try {
            final created = await workoutService.createExerciseInstance(instance);
            _d('Created new exercise instance: ${created.id}');
            await _loadExercises();
          } finally {
            if (mounted) {
              setState(() => _isLoading = false);
            }
          }

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Exercise added successfully')),
            );
          }
        }
      }
    } catch (e, stackTrace) {
      print('Error adding exercise: $e');
      print('Stack trace: $stackTrace');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to add exercise: ${e.toString()}')),
        );
      }
    }
  }

  Future<void> _navigateToExerciseForm(ExerciseDefinition exercise, ExerciseInstance? instance) async {
    if (_workout?.id == null) return;

    try {
      final exerciseDef = instance?.exerciseDefinition ?? exercise;

      final result = await Navigator.push<Map<String, dynamic>>(
        context,
        MaterialPageRoute(
          builder: (context) => ExerciseFormScreen(
            exercise: exerciseDef,
            workoutId: _workout!.id!,
            defaultOrder: _workout?.exerciseInstances.length,
            initialInstance: instance,
          ),
        ),
      );

      if (result != null && mounted) {
        final updatedInstance = result['instance'] as ExerciseInstance?;
        final refresh = result['refresh'] == true;

        if (updatedInstance != null) {
          final workoutService = _ref!.read(workoutServiceProvider);
          setState(() => _isLoading = true);
          try {
            if (updatedInstance.id == null) {
              await workoutService.createExerciseInstance(updatedInstance);
            } else {
              await workoutService.updateExerciseInstance(updatedInstance);
            }
          } finally {
            if (mounted) {
              setState(() => _isLoading = false);
            }
          }
        }

        if (refresh) {
          await _loadExercises();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  updatedInstance?.id == null
                      ? 'Exercise added successfully'
                      : 'Exercise updated successfully',
                ),
              ),
            );
          }
        }
      }
    } catch (e, stackTrace) {
      print('Error in exercise form: $e');
      print('Stack trace: $stackTrace');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error updating exercise: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _deleteExercise(int exerciseId) async {
    try {
      setState(() {
        _isLoading = true;
      });

      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Delete Exercise'),
          content: const Text('Are you sure you want to remove this exercise and all its sets from the workout?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('CANCEL'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
              child: const Text('DELETE'),
            ),
          ],
        ),
      );

      if (confirmed == true && mounted) {
        final instancesToDelete = _workout?.exerciseInstances
                .where((inst) => inst.exerciseListId == exerciseId)
                .toList() ?? [];

        if (instancesToDelete.isEmpty) {
          throw Exception('No exercise instances found for this exercise');
        }

        final workoutService = _ref!.read(workoutServiceProvider);
        for (final inst in instancesToDelete) {
          if (inst.id != null) {
            await workoutService.deleteExerciseInstance(inst.id!);
          }
        }

        await _loadExercises();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Exercise removed from workout')),
          );
        }
      }
    } catch (e, stackTrace) {
      print('Error deleting exercise: $e');
      print('Stack trace: $stackTrace');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error deleting exercise: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _promptEditWeight(ExerciseInstance instance, int setIndex, double initialWeight) async {
    final controller = TextEditingController(
      text: initialWeight % 1 == 0 ? initialWeight.toStringAsFixed(0) : initialWeight.toStringAsFixed(1),
    );

    final result = await showDialog<double>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Set weight (kg)'),
          content: TextField(
            controller: controller,
            autofocus: true,
            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
            decoration: const InputDecoration(hintText: 'e.g. 82.5'),
            onSubmitted: (_) {
              final raw = controller.text.replaceAll(',', '.').trim();
              final value = double.tryParse(raw);
              Navigator.of(context).pop(value);
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                final raw = controller.text.replaceAll(',', '.').trim();
                final value = double.tryParse(raw);
                Navigator.of(context).pop(value);
              },
              child: const Text('OK'),
            ),
          ],
        );
      },
    );

    if (result != null) {
      final clamped = result.clamp(0.0, 10000.0);
      await _updateSetField(
        instance,
        setIndex,
        weight: clamped,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer(
      builder: (context, ref, _) {
        _ref = ref;
        if (_isLoading) {
          return Scaffold(
            backgroundColor: AppColors.background,
            body: const Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        return Scaffold(
          backgroundColor: AppColors.background,
          body: Stack(
            children: [
              SafeArea(
                bottom: false,
                child: _buildBody(),
              ),
              Align(
                alignment: Alignment.topCenter,
                child: FloatingHeaderBar(
                  title: _workout?.name ?? 'Workout Details',
                  leading: IconButton(
                    icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
                    onPressed: () => Navigator.of(context).maybePop(),
                  ),
                  actions: [
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      onPressed: _loadExercises,
                      color: AppColors.primary,
                    ),
                  ],
                  onProfileTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const UserProfileScreen()),
                    );
                  },
                ),
              ),
            ],
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: _showAddExerciseDialog,
            backgroundColor: AppColors.primary,
            icon: const Icon(Icons.add),
            label: const Text('Add Exercise'),
          ),
        );
      },
    );
  }

  Widget _buildBody() {
    if (_isLoadingExercises) {
      return const Center(child: CircularProgressIndicator());
    }

    Widget content;
    if (_uniqueExercises.isEmpty) {
      content = Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: const Color(0xFFE8ECFF),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.fitness_center,
                  size: 48,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'No exercises yet',
                style: AppTextStyles.headlineMedium,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Tap "Add Exercise" to get started',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    } else {
      content = ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        itemCount: _uniqueExercises.length,
        itemBuilder: (context, index) {
          final exercise = _uniqueExercises[index];
          return _buildExerciseCard(exercise);
        },
      );
    }

    return Column(
      children: [
        const SizedBox(height: 72),
        _buildMetadataCard(),
        _buildSessionBanner(),
        Expanded(child: content),
      ],
    );
  }

  Widget _buildMetadataCard() {
    final theme = Theme.of(context);
    if (_workout == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFE8ECFF),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.fitness_center,
              color: AppColors.primary,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Готовность к тренировке',
                  style: AppTextStyles.titleMedium.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Коэффициент нагрузки: x${_readinessFactor(_readinessSlider).toStringAsFixed(2)}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 32,
                height: 32,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  icon: const Icon(Icons.remove, size: 18),
                  color: AppColors.primary,
                  tooltip: 'Уменьшить',
                  onPressed: () {
                    final current = int.tryParse(_readinessCtrl.text) ?? _readinessSlider.round();
                    final next = (current - 1).clamp(0, 10);
                    setState(() {
                      _readinessSlider = next.toDouble();
                      _writeReadinessText(_readinessSlider);
                    });
                  },
                ),
              ),
              Container(
                width: 48,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE8ECFF),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _readinessSlider.round().toString(),
                  style: AppTextStyles.titleMedium.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              SizedBox(
                width: 32,
                height: 32,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  icon: const Icon(Icons.add, size: 18),
                  color: AppColors.primary,
                  tooltip: 'Увеличить',
                  onPressed: () {
                    final current = int.tryParse(_readinessCtrl.text) ?? _readinessSlider.round();
                    final next = (current + 1).clamp(0, 10);
                    setState(() {
                      _readinessSlider = next.toDouble();
                      _writeReadinessText(_readinessSlider);
                    });
                  },
                ),
              ),
            ],
          ),
          const SizedBox(width: 12),
          ElevatedButton(
            onPressed: (_isApplyingReadiness || _workout == null) ? null : _applyReadinessScaling,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isApplyingReadiness
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Применить'),
          ),
        ],
      ),
    );
  }

  Widget _buildSessionBanner() {
    final theme = Theme.of(context);
    final isActive = _activeSession?.isActive == true;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(20, 8, 20, 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isActive ? const Color(0xFFEFF8F2) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
        border: Border.all(
          color: isActive ? const Color(0xFF4CAF50).withOpacity(0.3) : AppColors.border,
          width: 1.5,
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: isActive ? const Color(0xFF4CAF50) : AppColors.textDisabled,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      isActive ? 'Active session' : 'No active session',
                      style: AppTextStyles.titleMedium.copyWith(
                        fontWeight: FontWeight.w600,
                        color: isActive ? const Color(0xFF2E7D32) : AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
                if (isActive)
                  ValueListenableBuilder<Duration>(
                    valueListenable: _elapsedNotifier,
                    builder: (_, d, __) => Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        'Elapsed: ${_formatDuration(d)}',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  ),
                if (!isActive && _activeSession?.finishedAt != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Last session: ${_formatDuration(_elapsed)}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          if (!isActive)
            ElevatedButton.icon(
              onPressed: (_workout?.id != null && !_isLoading) ? _startSession : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4CAF50),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start'),
            )
          else
            Row(
              children: [
                OutlinedButton.icon(
                  onPressed: _isLoading ? null : () => _finishSession(cancelled: true),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.error,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    side: const BorderSide(color: AppColors.error),
                  ),
                  icon: const Icon(Icons.stop_circle_outlined, size: 18),
                  label: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _finishSession(cancelled: false, markWorkoutCompleted: true),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF4CAF50),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  icon: const Icon(Icons.check_circle_outline, size: 18),
                  label: const Text('Finish'),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildExerciseCard(ExerciseDefinition exercise) {

    final instances = _workout?.exerciseInstances
        .where((instance) => instance.exerciseListId == exercise.id)
        .toList() ?? [];


    if (instances.isEmpty) {
      return Container();
    }


    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: instances.map((instance) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 4, top: 8, bottom: 12),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8ECFF),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.fitness_center,
                      color: AppColors.primary,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          exercise.name ?? '-',
                          style: AppTextStyles.headlineSmall,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${exercise.muscleGroup ?? 'No muscle group'} • ${exercise.equipment ?? 'No equipment'}',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            _buildInstanceCard(instance),
          ],
        );
      }).toList(),
    );
  }

  Widget _buildInstanceCard(ExerciseInstance instance) {
    final theme = Theme.of(context);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${instance.sets.length} ${instance.sets.length == 1 ? 'Set' : 'Sets'}',
                        style: AppTextStyles.titleMedium.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (instance.notes?.isNotEmpty == true) ...[
                        const SizedBox(height: 4),
                        Text(
                          instance.notes!,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline, size: 20),
                      onPressed: () => _addSetToInstance(instance),
                      tooltip: 'Add set',
                      color: AppColors.primary,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                    const SizedBox(width: 4),
                    IconButton(
                      icon: const Icon(Icons.edit_outlined, size: 20),
                      onPressed: () => _navigateToExerciseForm(
                        instance.exerciseDefinition ??
                          ExerciseDefinition(
                            id: instance.exerciseListId,
                            name: 'Unknown',
                            muscleGroup: '',
                            equipment: '',
                          ),
                        instance,
                      ),
                      tooltip: 'Edit exercise',
                      color: AppColors.primary,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                    const SizedBox(width: 4),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 20),
                      onPressed: () => _deleteExerciseInstance(instance),
                      tooltip: 'Delete exercise',
                      color: AppColors.error,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (instance.sets.isNotEmpty) ...[
            Divider(height: 1, thickness: 1, color: AppColors.border),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  SizedBox(
                    width: 40,
                    child: Text(
                      'DONE',
                      style: AppTextStyles.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                        letterSpacing: 0.5,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  Text(
                    'SET',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Text(
                    'WEIGHT',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Text(
                    'REPS',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Text(
                    'RPE',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 24),
                ],
              ),
            ),
          ],
          ...instance.sets.asMap().entries.map((entry) {
            final set = entry.value;
            final bool isCompleted = _activeSession != null && instance.id != null && set.id != null
                ? _isSetCompleted(instance.id!, set.id!)
                : false;
            final bool canToggle = _activeSession?.isActive == true && instance.id != null && set.id != null;

            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4.0),
              decoration: BoxDecoration(
                color: isCompleted ? const Color(0xFFEFF8F2) : AppColors.background.withOpacity(0.3),
                borderRadius: BorderRadius.circular(12.0),
                border: Border.all(
                  color: isCompleted ? const Color(0xFF4CAF50).withOpacity(0.3) : Colors.transparent,
                  width: 1,
                ),
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(12.0),
                  onTap: canToggle ? () => _toggleSetCompletion(instance, set) : null,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 12.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        SizedBox(
                          width: 40,
                          child: Checkbox(
                            value: isCompleted,
                            onChanged: canToggle ? (v) => _toggleSetCompletion(instance, set) : null,
                          ),
                        ),
                        SizedBox(
                          width: 40,
                          child: Text(
                            '${entry.key + 1}',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w500,
                              color: isCompleted ? theme.primaryColor : theme.textTheme.bodyMedium?.color,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),

                        SizedBox(
                          width: 100,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).weightCtrl,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w500,
                            ),
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.primary, width: 1.5),
                              ),
                              hintText: 'kg',
                              hintStyle: AppTextStyles.bodySmall.copyWith(
                                color: AppColors.textHint,
                              ),
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'weight', v),
                            onSubmitted: (_) {
                              final editor = _getSetEditor(instance, entry.key, set);
                              editor.cancelDebounce();
                              _onInlineFieldSubmitted(instance, entry.key, set);
                            },
                          ),
                        ),

                        SizedBox(
                          width: 64,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).repsCtrl,
                            keyboardType: TextInputType.number,
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w500,
                            ),
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.primary, width: 1.5),
                              ),
                              hintText: 'reps',
                              hintStyle: AppTextStyles.bodySmall.copyWith(
                                color: AppColors.textHint,
                              ),
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'reps', v),
                            onSubmitted: (_) {
                              final editor = _getSetEditor(instance, entry.key, set);
                              editor.cancelDebounce();
                              _onInlineFieldSubmitted(instance, entry.key, set);
                            },
                          ),
                        ),

                        SizedBox(
                          width: 64,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).rpeCtrl,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w500,
                            ),
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.border),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: AppColors.primary, width: 1.5),
                              ),
                              hintText: 'RPE',
                              hintStyle: AppTextStyles.bodySmall.copyWith(
                                color: AppColors.textHint,
                              ),
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'rpe', v),
                            onSubmitted: (_) {
                              final editor = _getSetEditor(instance, entry.key, set);
                              editor.cancelDebounce();
                              _onInlineFieldSubmitted(instance, entry.key, set);
                            },
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 18),
                          color: AppColors.textSecondary,
                          onPressed: _isLoading
                              ? null
                              : () => _handleDeleteSet(instance, entry.key),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                          tooltip: 'Delete set',
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  void _reconcileEditors() {
    if (_workout == null) return;
    final validKeys = <String>{};
    _isSyncingFields = true;
    try {
      for (final instance in _workout!.exerciseInstances) {
        for (int i = 0; i < instance.sets.length; i++) {
          final set = instance.sets[i];
          final key = _editorKey(instance, i, set);
          validKeys.add(key);
          final editor = _setEditors[key] ?? _getSetEditor(instance, i, set);

          String fmtWeight(double w) => (w % 1 == 0) ? w.toStringAsFixed(0) : w.toStringAsFixed(1);
          final desiredWeight = fmtWeight(set.weight);
          final desiredReps = set.reps.toString();
          final desiredRpe = set.rpe == null
              ? ''
              : ((set.rpe! % 1 == 0)
                  ? set.rpe!.toStringAsFixed(0)
                  : set.rpe!.toStringAsFixed(1));
          if (editor.weightCtrl.text != desiredWeight) editor.weightCtrl.text = desiredWeight;
          if (editor.repsCtrl.text != desiredReps) editor.repsCtrl.text = desiredReps;
          if (editor.rpeCtrl.text != desiredRpe) editor.rpeCtrl.text = desiredRpe;
        }
      }
    } finally {
      _isSyncingFields = false;
    }

    final toRemove = _setEditors.keys.where((k) => !validKeys.contains(k)).toList();
    for (final k in toRemove) {
      _setEditors[k]?.dispose();
      _setEditors.remove(k);
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {

    for (final e in _setEditors.values) {
      e.dispose();
    }
    _d('Disposing WorkoutDetailScreen; cleaning up');
    _stopSessionTicker();
    _elapsedNotifier.dispose();

    _notesCtrl.dispose();
    _statusCtrl.dispose();
    _locationCtrl.dispose();
    _durationCtrl.dispose();
    _rpeSessionCtrl.dispose();
    _readinessCtrl.dispose();
    super.dispose();
  }
}

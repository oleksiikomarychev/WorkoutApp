import '../config/api_config.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
import '../models/exercise_definition.dart';
import '../models/exercise_set_dto.dart';
import '../services/workout_service.dart';
import '../services/applied_calendar_plan_service.dart';
import '../services/exercise_service.dart';
import '../services/service_locator.dart';
import '../services/user_max_service.dart';
import '../services/api_client.dart';
import '../models/workout_session.dart';
import '../services/workout_session_service.dart';
import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'exercise_form_screen.dart';
import 'exercise_selection_screen.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

// Top-level editor to manage TextEditingControllers for inline set editing
class _SetEditor {
  final TextEditingController weightCtrl;
  final TextEditingController repsCtrl;
  final TextEditingController rpeCtrl;
  final List<String> editedFields = [];
  _SetEditor({
    required this.weightCtrl,
    required this.repsCtrl,
    required this.rpeCtrl,
  });
  void dispose() {
    weightCtrl.dispose();
    repsCtrl.dispose();
    rpeCtrl.dispose();
  }
}

// Top-level container for baseline values used by readiness scaling
class _BaselineSet {
  final int reps;
  final double weight;
  const _BaselineSet({required this.reps, required this.weight});
}

class WorkoutDetailScreen extends StatefulWidget {
  final Workout? workout;

  const WorkoutDetailScreen({Key? key, this.workout}) : super(key: key);

  @override
  _WorkoutDetailScreenState createState() => _WorkoutDetailScreenState();
}

class _WorkoutDetailScreenState extends State<WorkoutDetailScreen> {
  bool _isLoading = false;
  bool _isLoadingExercises = false;
  List<ExerciseDefinition> _uniqueExercises = [];
  Workout? _workout;

  // Session state
  WorkoutSession? _activeSession;
  Timer? _sessionTimer;
  Duration _elapsed = Duration.zero;
  final ValueNotifier<Duration> _elapsedNotifier = ValueNotifier(Duration.zero);
  final Map<int, Set<int>> _completedByInstance = {};
  bool _isTogglingSet = false;

  // RPE table and user max cache
  Map<int, Map<int, int>> _rpeTable = {};
  Map<int, int> _exerciseMaxByExerciseId = {};
  // Inline editors storage per set
  final Map<String, _SetEditor> _setEditors = <String, _SetEditor>{};
  bool _isSyncingFields = false;

  // Metadata controllers
  final TextEditingController _notesCtrl = TextEditingController();
  final TextEditingController _statusCtrl = TextEditingController();
  final TextEditingController _locationCtrl = TextEditingController();
  final TextEditingController _durationCtrl = TextEditingController();
  final TextEditingController _rpeSessionCtrl = TextEditingController();
  // Manual coefficient for readiness scaling (multiplier)
  final TextEditingController _manualCoeffCtrl = TextEditingController(text: '1.00');
  DateTime? _editedStartedAt;
  bool _isSavingMetadata = false;

  // Readiness controls
  double _readinessSlider = 10.0;
  bool _isApplyingReadiness = false;
  bool _scaleRepsWithReadiness = true;

  // Baseline snapshot to make scaling reversible and non-destructive
  // Keyed by editor key (instance+set identity)
  final Map<String, _BaselineSet> _baselineSets = <String, _BaselineSet>{};

  // Session ticker guards and diagnostics
  bool _sessionTickerRunning = false;
  int _sessionTickerGen = 0;

  @override
  void initState() {
    super.initState();
    _workout = widget.workout;
    _syncMetadataControllers();
    if (_workout != null) {
      _loadExercises();
      // Also fetch raw API response for debugging (debug builds only, with timeout)
      if (kDebugMode) {
        _fetchRawWorkoutData();
      }
    }
    // Load helpers for inline recalculation
    _fetchRpeTable();
    _loadUserMaxes();
    // Load active session if any
    if (_workout?.id != null) {
      _loadActiveSession();
    }
  }

  // --- Readiness scaling helpers ---
  double _roundToStep(double value, double step) {
    if (step <= 0) return value;
    final rounded = (value / step).roundToDouble() * step;
    // limit to 1 decimal to align with UI formatting
    return double.parse(rounded.toStringAsFixed(1));
  }

  Future<void> _applyReadinessScaling() async {
    if (_workout == null) return;
    if (_isApplyingReadiness) return;
    setState(() {
      _isApplyingReadiness = true;
    });

    // Ensure we have a baseline snapshot for all sets so scaling is reversible.
    _ensureBaselineSets();

    // Use a gentle mapping so 5/10 ~= 0.95 (not 0.5), 0/10 ~= 0.85, 10/10 ~= 1.05
    double factor = _readinessFactor(_readinessSlider.clamp(0, 10));
    // Apply manual coefficient if provided (e.g., 0.95, 1.05). Sanitize input.
    final raw = _manualCoeffCtrl.text.replaceAll(',', '.').trim();
    final parsed = double.tryParse(raw);
    if (parsed != null && parsed.isFinite && parsed > 0) {
      // Clamp to a reasonable range to avoid accidental extremes
      final clamped = parsed.clamp(0.5, 1.5);
      factor *= clamped;
    }
    int updates = 0;
    try {
      // Dynamic rounding: <=20 kg -> step 1.0, otherwise -> step 2.5
      for (final instance in _workout!.exerciseInstances) {
        for (int i = 0; i < instance.sets.length; i++) {
          final set = instance.sets[i];
          final String key = _editorKey(instance, i, set);
          final _BaselineSet base = _baselineSets[key] ?? _BaselineSet(reps: set.reps, weight: set.weight);
          final double rawScaled = base.weight * factor;
          final double step = rawScaled <= 20.0 ? 1.0 : 2.5;
          final double newWeight = (_roundToStep(rawScaled, step).clamp(0.0, double.infinity)) as double;
          final int newReps = _scaleRepsWithReadiness
              ? ((base.reps * factor).round().clamp(1, 10000)) as int
              : set.reps;

          final bool changed = (newReps != set.reps) || (newWeight - set.weight).abs() > 0.0001;
          if (!changed) continue;

          await _updateSetField(
            instance,
            i,
            reps: newReps,
            weight: newWeight,
          );
          updates++;
        }
      }
      _reconcileEditors();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Applied readiness ${_readinessSlider.round()}/10 to $updates set${updates == 1 ? '' : 's'}')),
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

  // Build or refresh baseline snapshot to match current workout structure
  void _ensureBaselineSets() {
    if (_workout == null) return;
    final Map<String, _BaselineSet> snap = <String, _BaselineSet>{};
    for (final instance in _workout!.exerciseInstances) {
      for (int i = 0; i < instance.sets.length; i++) {
        final set = instance.sets[i];
        final key = _editorKey(instance, i, set);
        // Preserve existing baseline if present; otherwise seed from current values
        final existing = _baselineSets[key];
        snap[key] = existing ?? _BaselineSet(reps: set.reps, weight: set.weight);
      }
    }
    _baselineSets
      ..clear()
      ..addAll(snap);
  }

  // Map readiness (0..10) to a gentle scaling factor around 1.0
  // Defaults: 0 -> 0.85, 5 -> 0.95, 10 -> 1.05
  double _readinessFactor(double readiness) {
    final r = readiness.clamp(0.0, 10.0);
    const double minF = 0.85;
    const double maxF = 1.05;
    return minF + (maxF - minF) * (r / 10.0);
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
      final updatedSet = current.copyWith(
        reps: reps ?? current.reps,
        weight: weight ?? current.weight,
        rpe: rpe ?? current.rpe,
        order: current.order ?? setIndex,
      );

      final workoutService = Provider.of<WorkoutService>(context, listen: false);

      ExerciseInstance savedInstance;
      final setId = updatedSet.id ?? current.id;

      if (instance.id != null && setId != null) {
        // Preferred: update a single set via new endpoint
        savedInstance = await workoutService.updateExerciseSet(
          instanceId: instance.id!,
          setId: setId,
          reps: updatedSet.reps,
          weight: updatedSet.weight,
          rpe: updatedSet.rpe,
          order: updatedSet.order,
        );
      } else {
        // Fallback: update entire instance if set lacks an ID (e.g., just created locally)
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
      }
    }
  }

  // Helper method to fetch raw API response
  Future<void> _fetchRawWorkoutData() async {
    if (_workout?.id == null) return;
    
    try {
      final url = 'http://localhost:8000/api/v1/workouts/${_workout!.id}';
      print('Fetching raw workout data from: $url');
      
      final response = await http
          .get(
            Uri.parse(url),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(const Duration(seconds: 5));
      
      print('Response status: ${response.statusCode}');
      print('Response headers: ${response.headers}');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
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
      } else {
        print('Failed to fetch raw workout data: ${response.statusCode}');
        print('Response body: ${response.body}');
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

      // Show confirmation dialog
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

      // Delete the instance from the backend
      final workoutService = Provider.of<WorkoutService>(context, listen: false);
      if (instance.id != null) {
        await workoutService.deleteExerciseInstance(instance.id!);
        print('Successfully deleted instance from backend');
        
        // Refresh the workout data
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

      // Create a new set with default values based on the last set or default values
      int lastReps = 5;
      double lastWeight = 0.0;
      
      if (instance.sets.isNotEmpty) {
        // Use values from the last set as defaults
        final lastSet = instance.sets.last;
        lastReps = lastSet.reps;
        lastWeight = lastSet.weight;
      }

      final newSet = ExerciseSetDto(
        id: null, // Will be set by the backend
        reps: lastReps,
        weight: lastWeight,
        order: instance.sets.length, // Next order
        exerciseInstanceId: instance.id, // Will be set by the backend
        localId: null,
        volume: (lastReps * lastWeight).round(), // Calculate and round volume to nearest integer
      );

      print('Created new set: $newSet');

      // Add the set to the instance
      final updatedInstance = instance.copyWith(
        sets: [...instance.sets, newSet],
      );
      
      print('Updated instance with new set: ${updatedInstance.sets.length} total sets');
      
      // Update the instance in the backend
      final workoutService = Provider.of<WorkoutService>(context, listen: false);
      final savedInstance = await workoutService.updateExerciseInstance(updatedInstance);
      
      if (savedInstance != null) {
        print('Successfully updated instance in backend');
        
        // Update the local state with the saved instance
        if (_workout != null && mounted) {
          setState(() {
            // Create a new list to avoid modifying the unmodifiable one
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
      } else {
        throw Exception('Failed to save set');
      }
    } catch (e, stackTrace) {
      print('Error adding set: $e');
      print('Stack trace: $stackTrace');
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
      final workoutService = Provider.of<WorkoutService>(context, listen: false);
      final updatedWorkout = await workoutService.getWorkoutWithDetails(_workout!.id!);
      
      if (updatedWorkout != null) {
        print('Fetched workout with ${updatedWorkout.exerciseInstances.length} exercise instances');
        
        // Get all unique exercise list IDs from instances
        final exerciseListIds = updatedWorkout.exerciseInstances
            .map((e) => e.exerciseListId)
            .toSet()
            .toList();
        
        if (exerciseListIds.isNotEmpty) {
          // Fetch exercise definitions
          final exerciseService = Provider.of<ExerciseService>(context, listen: false);
          final exercises = await exerciseService.getExercisesByIds(exerciseListIds);
          
          // Create a map of exercise ID to exercise definition
          final exerciseMap = {
            for (var e in exercises) e.id: e,
          };
          
          // Build a new list of instances with their exercise definitions via copyWith
          final updatedInstances = updatedWorkout.exerciseInstances.map((instance) {
            final def = exerciseMap[instance.exerciseListId];
            return instance.copyWith(exerciseDefinition: def);
          }).toList();

          // Create a list of unique exercise definitions
          final exerciseDefinitions = exerciseMap.values.toList();
          
          setState(() {
            _workout = updatedWorkout.copyWith(exerciseInstances: updatedInstances);
            _uniqueExercises = exerciseDefinitions;
            print('Found ${_uniqueExercises.length} unique exercises');
          });
        } else {
          setState(() {
            _workout = updatedWorkout;
            _uniqueExercises = [];
            print('No exercise instances found in workout');
          });
        }
      }
      _reconcileEditors();
    } catch (e, stackTrace) {
      print('Error loading exercises: $e');
      print('Stack trace: $stackTrace');
      // Show error to user
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

  // --- RPE table and user max helpers ---
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
      // ignore errors; leave table empty
    }
  }

  Future<void> _loadUserMaxes() async {
    try {
      final userMaxService = Provider.of<UserMaxService>(context, listen: false);
      final maxes = await userMaxService.getUserMaxes();
      if (mounted) {
        setState(() {
          _exerciseMaxByExerciseId = {
            for (final m in maxes) m.exerciseId: m.maxWeight,
          };
        });
      }
    } catch (_) {
      // ignore; no user maxes available
    }
  }

  // --- Metadata editing helpers ---
  void _d(String msg) {
    if (kDebugMode) {
      // Lightweight debug logger
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
    // Normalize readiness to 0–10. If legacy value >10 (0–100), convert to /10.
    final double readinessRaw = (w?.readinessScore?.toDouble() ?? 10.0);
    final double normalized = readinessRaw > 10.0 ? readinessRaw / 10.0 : readinessRaw;
    _readinessSlider = normalized.clamp(0.0, 10.0);
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

      // Clamp and sanitize inputs
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
      final svc = Provider.of<WorkoutService>(context, listen: false);
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

  // --- Session helpers ---
  Future<void> _loadActiveSession() async {
    if (_workout?.id == null) return;
    try {
      final svc = Provider.of<WorkoutSessionService>(context, listen: false);
      final session = await svc.getActiveSession(_workout!.id!);
      if (!mounted) return;
      setState(() {
        _activeSession = session;
        // If a session exists, reflect its start time in the edited startedAt (without overriding manual edits)
        if (session?.startedAt != null && _editedStartedAt == null) {
          _editedStartedAt = session!.startedAt;
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
      // ignore errors; treated as no active session
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
    // Guard with generation token and running flag to avoid stray ticks after stop/dispose
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
      final end = _activeSession!.endedAt;
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
      final svc = Provider.of<WorkoutSessionService>(context, listen: false);
      final session = await svc.startSession(_workout!.id!);
      if (!mounted) return;
      setState(() {
        _activeSession = session;
        // Auto-set workout startedAt and reset duration counter when session begins
        _editedStartedAt = session.startedAt;
        _durationCtrl.text = '0';
      });
      _parseProgressFromSession();
      _startSessionTicker();
      // Persist startedAt to workout metadata
      await _saveWorkoutMetadata();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Workout session started')), 
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
    if (_activeSession?.id == null) return;
    try {
      _d('Finishing session id=${_activeSession?.id} cancelled=$cancelled markCompleted=$markWorkoutCompleted');
      setState(() => _isLoading = true);
      final svc = Provider.of<WorkoutSessionService>(context, listen: false);
      final session = await svc.finishSession(
        _activeSession!.id!,
        cancelled: cancelled,
        markWorkoutCompleted: markWorkoutCompleted,
      );
      if (!mounted) return;
      setState(() {
        _activeSession = session;
      });
      _parseProgressFromSession();
      _stopSessionTicker();
      // On finish, auto-calculate and persist workout duration/startedAt
      final started = session.startedAt;
      final ended = session.endedAt;
      if (started != null && ended != null) {
        final secs = ended.difference(started).inSeconds;
        setState(() {
          _editedStartedAt ??= started;
          _durationCtrl.text = secs.toString();
        });
        await _saveWorkoutMetadata();
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(cancelled ? 'Session cancelled' : 'Session finished')), 
      );

      // If workout was marked completed and this workout belongs to an applied plan,
      // attempt to auto-advance to the next workout in the active plan.
      if (markWorkoutCompleted) {
        await _advanceToNextWorkoutInPlan();
      }
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

  Future<void> _advanceToNextWorkoutInPlan() async {
    try {
      final appliedPlanSvc = Provider.of<AppliedCalendarPlanService>(context, listen: false);
      final plan = await appliedPlanSvc.getActiveAppliedCalendarPlan();
      if (plan?.nextWorkout == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Plan completed! No next workout.')),
          );
        }
        return;
      }

      final nextId = plan!.nextWorkout!.id;
      // If already showing the same workout (unlikely), skip.
      if (_workout?.id == nextId) return;

      final workoutSvc = Provider.of<WorkoutService>(context, listen: false);
      final nextWorkout = await workoutSvc.getWorkoutWithDetails(nextId);

      if (!mounted) return;
      // Reset session-related state and load next workout
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
      final svc = Provider.of<WorkoutSessionService>(context, listen: false);
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

  int? _intensityFromWeight(int exerciseId, double weight) {
    final max = _exerciseMaxByExerciseId[exerciseId];
    if (max == null || max <= 0) return null;
    int pct = ((weight / max) * 100).round();
    if (pct < 1) pct = 1;
    if (pct > 100) pct = 100;
    return pct;
  }

  String _editorKey(ExerciseInstance instance, int setIndex, ExerciseSetDto set) {
    final instKey = instance.id?.toString() ?? 'inst';
    final setKey = set.id?.toString() ?? 'idx$setIndex';
    return '$instKey-$setKey';
  }

  // Moved to top-level: _SetEditor
  // class _SetEditor {
  //   final TextEditingController weightCtrl;
  //   final TextEditingController repsCtrl;
  //   final TextEditingController rpeCtrl;
  //   final List<String> editedFields = [];
  //   _SetEditor({
  //     required this.weightCtrl,
  //     required this.repsCtrl,
  //     required this.rpeCtrl,
  //   });
  //   void dispose() {
  //     weightCtrl.dispose();
  //     repsCtrl.dispose();
  //     rpeCtrl.dispose();
  //   }
  // }

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

  void _onInlineFieldChanged(
    ExerciseInstance instance,
    int setIndex,
    ExerciseSetDto set,
    String field,
    String value,
  ) {
    if (_isSyncingFields) return;
    final editor = _getSetEditor(instance, setIndex, set);
    // Track edit order (last two distinct)
    editor.editedFields.remove(field);
    editor.editedFields.add(field);
    if (editor.editedFields.length > 2) editor.editedFields.removeAt(0);

    // Parse current values from controllers
    double? parseDouble(String s) => double.tryParse(s.replaceAll(',', '.').trim());
    int? parseInt(String s) => int.tryParse(s.trim());

    final w = parseDouble(editor.weightCtrl.text);
    final r = parseInt(editor.repsCtrl.text);
    final eRaw = parseDouble(editor.rpeCtrl.text);
    final e = eRaw?.round(); // RPE table uses ints

    if (editor.editedFields.length < 2) return;
    final a = editor.editedFields[0];
    final b = editor.editedFields[1];
    final third = {'weight', 'reps', 'rpe'}.difference({a, b}).first;

    String fmtWeight(double v) => (v % 1 == 0) ? v.toStringAsFixed(0) : v.toStringAsFixed(1);

    int exerciseId = instance.exerciseListId;
    _isSyncingFields = true;
    try {
      if (third == 'weight' && r != null && e != null) {
        final intensity = _intensityFromEffortReps(e.clamp(1, 10), r.clamp(1, 1000));
        final max = _exerciseMaxByExerciseId[exerciseId];
        if (intensity != null && max != null) {
          final newWeight = max * (intensity / 100.0);
          editor.weightCtrl.text = fmtWeight(newWeight);
        }
      } else if (third == 'reps' && w != null && e != null) {
        final intensity = _intensityFromWeight(exerciseId, w);
        if (intensity != null) {
          final reps = _repsFromIntensityEffort(intensity, e.clamp(1, 10));
          if (reps != null) editor.repsCtrl.text = reps.toString();
        }
      } else if (third == 'rpe' && w != null && r != null) {
        final intensity = _intensityFromWeight(exerciseId, w);
        if (intensity != null) {
          final effort = _effortFromIntensityReps(intensity, r.clamp(1, 1000));
          if (effort != null) editor.rpeCtrl.text = effort.toString();
        }
      }
    } finally {
      _isSyncingFields = false;
    }
    if (mounted) setState(() {});
  }

  Future<void> _onInlineFieldSubmitted(
    ExerciseInstance instance,
    int setIndex,
    ExerciseSetDto set,
  ) async {
    final editor = _getSetEditor(instance, setIndex, set);
    double? parseDouble(String s) => double.tryParse(s.replaceAll(',', '.').trim());
    int? parseInt(String s) => int.tryParse(s.trim());

    final double? weight = parseDouble(editor.weightCtrl.text);
    final int? reps = parseInt(editor.repsCtrl.text);
    final double? rpe = parseDouble(editor.rpeCtrl.text)?.clamp(1.0, 10.0);

    // If we have two fields, compute the third to persist a consistent triple
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
          final intensity = _intensityFromEffortReps((rpe!.round()).clamp(1, 10), reps!.clamp(1, 1000));
          final max = _exerciseMaxByExerciseId[exerciseId];
          if (intensity != null && max != null) {
            final w = max * (intensity / 100.0);
            editor.weightCtrl.text = fmtWeight(w);
          }
        } else if (third == 'reps' && weight != null && rpe != null) {
          final intensity = weight != null ? _intensityFromWeight(exerciseId, weight) : null;
          final repsCalc = (intensity != null) ? _repsFromIntensityEffort(intensity, rpe!.round().clamp(1, 10)) : null;
          if (repsCalc != null) editor.repsCtrl.text = repsCalc.toString();
        } else if (third == 'rpe' && weight != null && reps != null) {
          final intensity = weight != null ? _intensityFromWeight(exerciseId, weight) : null;
          final eff = (intensity != null) ? _effortFromIntensityReps(intensity, reps!.clamp(1, 1000)) : null;
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
    final int? finalReps = finalRepsRaw != null ? finalRepsRaw.clamp(1, 1000) : null;
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
      
      // Show confirmation dialog
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
        // Local set (no ID). Try to resolve the server set at the same index and delete it on backend.
        final workoutService = Provider.of<WorkoutService>(context, listen: false);
        try {
          // Reload latest workout to sync sets with backend and get IDs
          await _loadExercises();

          // Find the refreshed instance
          final refreshedInstance = _workout?.exerciseInstances
              .firstWhere((i) => i.id == instance.id, orElse: () => instance);

          if (refreshedInstance != null && setIndex >= 0 && setIndex < refreshedInstance.sets.length) {
            final refreshedSet = refreshedInstance.sets[setIndex];
            if (refreshedSet.id != null && instance.id != null) {
              // Delete by resolved server set ID
              await workoutService.deleteExerciseSet(instance.id!, refreshedSet.id!);

              // Update local state to reflect deletion immediately
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
              // Ensure consistency with backend
              await _loadExercises();
            } else {
              // No server ID even after refresh -> purely local set, remove locally only
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
            // Fallback: remove locally
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
          // If anything goes wrong, at least remove locally to keep UX responsive
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
        // Delete the set from the backend
        final workoutService = Provider.of<WorkoutService>(context, listen: false);
        await workoutService.deleteExerciseSet(instance.id!, setToDelete.id!);
        
        // Update local state immediately for better UX
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
        
        // Still refresh the workout data to ensure consistency
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

      // Navigate to exercise selection screen
      final selectedExercise = await Navigator.push<ExerciseDefinition>(
        context,
        MaterialPageRoute(
          builder: (context) => const ExerciseSelectionScreen(),
        ),
      );

      if (selectedExercise != null) {
        setState(() {
          _isLoading = true;
        });

        // Create a new exercise instance
        final newInstance = ExerciseInstance(
          id: null, // Will be set by the backend
          exerciseListId: selectedExercise.id!,
          exerciseDefinition: selectedExercise,
          workoutId: _workout!.id!,
          order: _workout?.exerciseInstances.length ?? 0,
          sets: [],
          notes: null,
        );

        // Add a default set
        final defaultSet = ExerciseSetDto(
          id: null, // Will be set by the backend
          reps: 5,
          weight: 0.0,
          order: 0,
          exerciseInstanceId: 0, // This will be set by the backend
          localId: null,
          volume: (5 * 0.0).round(), // Calculate and round volume to nearest integer
        );
        newInstance.sets.add(defaultSet);

        // Save the new instance
        final workoutService = Provider.of<WorkoutService>(context, listen: false);
        final createdInstance = await workoutService.createExerciseInstance(newInstance);
        print('Created new exercise instance: ${createdInstance.id}');
        
        // Navigate to the exercise form to edit the new instance
        if (mounted) {
          await _navigateToExerciseForm(
            selectedExercise,
            createdInstance,
          );
          
          // Show success message
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Exercise added successfully')),
          );
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
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _navigateToExerciseForm(ExerciseDefinition exercise, ExerciseInstance? instance) async {
    if (_workout?.id == null) return;

    try {
      setState(() {
        _isLoading = true;
      });

      // Ensure we have a valid exercise definition
      final exerciseDef = instance?.exerciseDefinition ?? exercise;
      if (exerciseDef == null) {
        throw Exception('Exercise definition is required');
      }

      final result = await Navigator.push<Map<String, dynamic>>(
        context,
        MaterialPageRoute(
          builder: (context) => ExerciseFormScreen(
            workoutId: _workout!.id!,
            exercise: exerciseDef,
            instance: instance,
          ),
        ),
      );

      if (result != null && result['refresh'] == true && mounted) {
        // Refresh the exercise data
        await _loadExercises();
        
        // Show success message
        final message = result['isNew'] == true 
            ? 'Exercise added successfully' 
            : 'Exercise updated successfully';
            
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
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

      // Show confirmation dialog
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
              child: const Text('DELETE'),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
            ),
          ],
        ),
      );

      if (confirmed == true && mounted) {
        // Find all instances of this exercise in the workout
        final instancesToDelete = _workout?.exerciseInstances
            .where((instance) => instance.exerciseListId == exerciseId)
            .toList() ?? [];
        
        if (instancesToDelete.isEmpty) {
          throw Exception('No exercise instances found for this exercise');
        }
        
        // Delete each instance
        final workoutService = Provider.of<WorkoutService>(context, listen: false);
        for (final instance in instancesToDelete) {
          if (instance.id != null) {
            await workoutService.deleteExerciseInstance(instance.id!);
          }
        }
        
        // Refresh the workout data
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
      await _updateSetField(instance, setIndex, weight: clamped);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_workout?.name ?? 'Workout Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadExercises,
          ),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddExerciseDialog,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoadingExercises) {
      return const Center(child: CircularProgressIndicator());
    }

    Widget content;
    if (_uniqueExercises.isEmpty) {
      content = const Center(
        child: Text('No exercises added yet. Tap + to add some!'),
      );
    } else {
      content = ListView.builder(
        itemCount: _uniqueExercises.length,
        itemBuilder: (context, index) {
          final exercise = _uniqueExercises[index];
          return _buildExerciseCard(exercise);
        },
      );
    }

    return Column(
      children: [
        _buildMetadataCard(),
        _buildSessionBanner(),
        Expanded(child: content),
      ],
    );
  }

  Widget _buildMetadataCard() {
    final theme = Theme.of(context);
    if (_workout == null) return const SizedBox.shrink();
    final startedText = _editedStartedAt != null
        ? _editedStartedAt!.toLocal().toString().split('.').first
        : 'Not set';
    return Card(
      margin: const EdgeInsets.all(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Workout metadata',
              style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TextField(
                    controller: _notesCtrl,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(labelText: 'Notes'),
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('RPE', style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 32,
                          height: 32,
                          child: IconButton(
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            tooltip: 'Decrease',
                            icon: const Icon(Icons.remove, size: 18),
                            onPressed: () {
                              final current = int.tryParse(_rpeSessionCtrl.text) ?? 5;
                              final next = (current - 1).clamp(1, 10);
                              setState(() => _rpeSessionCtrl.text = next.toString());
                            },
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            border: Border.all(color: theme.dividerColor),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            (int.tryParse(_rpeSessionCtrl.text) ?? 0) == 0 ? '-' : _rpeSessionCtrl.text,
                            style: theme.textTheme.titleMedium,
                          ),
                        ),
                        SizedBox(
                          width: 32,
                          height: 32,
                          child: IconButton(
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            tooltip: 'Increase',
                            icon: const Icon(Icons.add, size: 18),
                            onPressed: () {
                              final current = int.tryParse(_rpeSessionCtrl.text) ?? 5;
                              final next = (current + 1).clamp(1, 10);
                              setState(() => _rpeSessionCtrl.text = next.toString());
                            },
                          ),
                        ),
                      ],
                    ),
                    // Chips removed; +/- controls above handle quick changes.
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            const SizedBox(height: 8),
            // StartedAt and Duration are intentionally hidden from the metadata UI.
            const SizedBox(height: 8),
            // Removed separate Session RPE TextField; now controlled by quick buttons above.
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Readiness quick controls (responsive)
                      Wrap(
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('Rdy:', style: theme.textTheme.bodyMedium),
                              const SizedBox(width: 4),
                              SizedBox(
                                width: 28, height: 28,
                                child: IconButton(
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  tooltip: 'Readiness -',
                                  icon: const Icon(Icons.remove, size: 16),
                                  onPressed: _isApplyingReadiness ? null : () {
                                    final next = (_readinessSlider.round() - 1).clamp(0, 10);
                                    setState(() => _readinessSlider = next.toDouble());
                                  },
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  border: Border.all(color: theme.dividerColor),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(_readinessSlider.round().toString(), style: theme.textTheme.titleMedium),
                              ),
                              SizedBox(
                                width: 28, height: 28,
                                child: IconButton(
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  tooltip: 'Readiness +',
                                  icon: const Icon(Icons.add, size: 16),
                                  onPressed: _isApplyingReadiness ? null : () {
                                    final next = (_readinessSlider.round() + 1).clamp(0, 10);
                                    setState(() => _readinessSlider = next.toDouble());
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          Switch(
                            value: _scaleRepsWithReadiness,
                            onChanged: _isApplyingReadiness ? null : (v) {
                              setState(() => _scaleRepsWithReadiness = v);
                            },
                          ),
                          const SizedBox(width: 4),
                          const Text('Scale reps too'),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: (_workout?.id != null && !_isApplyingReadiness && !_isLoading)
                      ? _applyReadinessScaling
                      : null,
                  icon: _isApplyingReadiness
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.auto_fix_high),
                  label: const Text('Apply'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton(
                  onPressed: (_workout?.id != null && !_isSavingMetadata) ? _saveWorkoutMetadata : null,
                  child: _isSavingMetadata
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Save'),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: _isSavingMetadata
                      ? null
                      : () {
                          _syncMetadataControllers();
                          setState(() {});
                        },
                  child: const Text('Revert'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSessionBanner() {
    final theme = Theme.of(context);
    final isActive = _activeSession?.isActive == true;
    return Container
    (
      width: double.infinity,
      color: theme.colorScheme.surfaceVariant,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isActive ? 'Active session' : 'No active session',
                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                if (isActive)
                  ValueListenableBuilder<Duration>(
                    valueListenable: _elapsedNotifier,
                    builder: (_, d, __) => Text(
                      'Elapsed: ${_formatDuration(d)}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
                if (!isActive && _activeSession?.endedAt != null)
                  Text('Last session: ${_formatDuration(_elapsed)}', style: theme.textTheme.bodySmall),
              ],
            ),
          ),
          if (!isActive)
            ElevatedButton.icon(
              onPressed: (_workout?.id != null && !_isLoading) ? _startSession : null,
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start'),
            )
          else
            Row(
              children: [
                OutlinedButton.icon(
                  onPressed: _isLoading ? null : () => _finishSession(cancelled: true),
                  icon: const Icon(Icons.stop_circle_outlined),
                  label: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _finishSession(cancelled: false, markWorkoutCompleted: true),
                  icon: const Icon(Icons.check_circle_outline),
                  label: const Text('Finish'),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildExerciseCard(ExerciseDefinition exercise) {
    // Get all instances for this exercise
    final instances = _workout?.exerciseInstances
        .where((instance) => instance.exerciseListId == exercise.id)
        .toList() ?? [];
    
    // If no instances, return an empty container
    if (instances.isEmpty) {
      return Container();
    }
    
    // Show all instances in a column with their own cards
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: instances.map((instance) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    exercise.name,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('${exercise.muscleGroup ?? 'No muscle group'} • ${exercise.equipment ?? 'No equipment'}'),
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
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 4.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            title: Text(
              '${instance.sets.length} ${instance.sets.length == 1 ? 'Set' : 'Sets'}',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: instance.notes?.isNotEmpty == true 
                ? Text(
                    instance.notes!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  )
                : null,
            contentPadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: const Icon(Icons.add_circle_outline, size: 22),
                  onPressed: () => _addSetToInstance(instance),
                  tooltip: 'Add set',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
                const SizedBox(width: 4),
                IconButton(
                  icon: Icon(Icons.edit_outlined, size: 20, color: theme.primaryColor),
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
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20, color: Colors.red),
                  onPressed: () => _deleteExerciseInstance(instance),
                  tooltip: 'Delete exercise',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
          ),
          if (instance.sets.isNotEmpty) ...[
            const Divider(height: 1, thickness: 1),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  SizedBox(
                    width: 40,
                    child: Text('DONE', style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.hintColor,
                    ), textAlign: TextAlign.center),
                  ),
                  Text('SET', style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.hintColor,
                  )),
                  Text('WEIGHT', style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.hintColor,
                  )),
                  Text('REPS', style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  )),
                  Text('RPE', style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.hintColor,
                  )),
                  const SizedBox(width: 24), // Space for delete button
                ],
              ),
            ),
          ],
          ...instance.sets.asMap().entries.map((entry) {
            final set = entry.value;
            final bool isCompleted = _activeSession != null && instance.id != null && set.id != null
                ? _isSetCompleted(instance.id!, set.id!)
                : false; // derived from session progress
            final bool canToggle = _activeSession?.isActive == true && instance.id != null && set.id != null;
            
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 2.0),
              decoration: BoxDecoration(
                color: isCompleted ? theme.colorScheme.surfaceVariant.withOpacity(0.5) : null,
                borderRadius: BorderRadius.circular(8.0),
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(8.0),
                  onTap: canToggle ? () => _toggleSetCompletion(instance, set) : null,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 12.0),
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
                        // Inline weight editor
                        SizedBox(
                          width: 100,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).weightCtrl,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(4)),
                              hintText: 'kg',
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'weight', v),
                            onSubmitted: (_) => _onInlineFieldSubmitted(instance, entry.key, set),
                          ),
                        ),
                        // Inline reps editor
                        SizedBox(
                          width: 64,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).repsCtrl,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(4)),
                              hintText: 'reps',
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'reps', v),
                            onSubmitted: (_) => _onInlineFieldSubmitted(instance, entry.key, set),
                          ),
                        ),
                        // Inline RPE editor
                        SizedBox(
                          width: 64,
                          child: TextField(
                            controller: _getSetEditor(instance, entry.key, set).rpeCtrl,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: false),
                            decoration: InputDecoration(
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(4)),
                              hintText: 'RPE',
                            ),
                            enabled: !isCompleted,
                            onChanged: (v) => _onInlineFieldChanged(instance, entry.key, set, 'rpe', v),
                            onSubmitted: (_) => _onInlineFieldSubmitted(instance, entry.key, set),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 18, color: Colors.grey),
                          onPressed: _isLoading 
                              ? null 
                              : () => _handleDeleteSet(instance, entry.key),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                          tooltip: 'Delete set',
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
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
          // Sync controller texts to model values (avoid redundant updates)
          String fmtWeight(double w) => (w % 1 == 0) ? w.toStringAsFixed(0) : w.toStringAsFixed(1);
          final desiredWeight = fmtWeight(set.weight);
          final desiredReps = set.reps.toString();
          final desiredRpe = set.rpe == null
              ? ''
              : ((set.rpe! % 1 == 0) ? set.rpe!.toStringAsFixed(0) : set.rpe!.toStringAsFixed(1));
          if (editor.weightCtrl.text != desiredWeight) editor.weightCtrl.text = desiredWeight;
          if (editor.repsCtrl.text != desiredReps) editor.repsCtrl.text = desiredReps;
          if (editor.rpeCtrl.text != desiredRpe) editor.rpeCtrl.text = desiredRpe;
        }
      }
    } finally {
      _isSyncingFields = false;
    }
    // Dispose any editors that no longer correspond to existing sets
    final toRemove = _setEditors.keys.where((k) => !validKeys.contains(k)).toList();
    for (final k in toRemove) {
      _setEditors[k]?.dispose();
      _setEditors.remove(k);
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    // Dispose inline editors
    for (final e in _setEditors.values) {
      e.dispose();
    }
    _d('Disposing WorkoutDetailScreen; cleaning up');
    _stopSessionTicker();
    _elapsedNotifier.dispose();
    // Dispose metadata controllers
    _notesCtrl.dispose();
    _statusCtrl.dispose();
    _locationCtrl.dispose();
    _durationCtrl.dispose();
    _rpeSessionCtrl.dispose();
    _manualCoeffCtrl.dispose();
    super.dispose();
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart' as provider_package;
import 'package:workout_app/main.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import '../services/rpe_service.dart';

class ExerciseWithSets {
  final ExerciseDefinition exercise;
  List<ParamsSets> sets;
  List<SetDraft> setDrafts;

  ExerciseWithSets({required this.exercise, required this.sets})
      : setDrafts = sets.map((set) => SetDraft(
          intensity: set.intensity,
          effort: set.effort,
          volume: set.volume,
        )).toList();

  Map<String, dynamic> toJson() => {
        'exercise_definition_id': exercise.id,
        'sets': setDrafts.map((draft) {
          int? intensity = draft.intensity?.round();
          if (intensity != null) {
            if (intensity < 0) intensity = 0;
            if (intensity > 100) intensity = 100;
          }

          int? effort = draft.effort?.round();
          if (effort != null) {
            if (effort < 1) effort = 1;
            if (effort > 10) effort = 10;
          }

          int? volume = draft.volume?.round();
          if (volume != null) {
            if (volume < 1) volume = 1;
          }

          return {
            'intensity': intensity,
            'effort': effort,
            'volume': volume,
          };
        }).toList(),
      };
}

class SetDraft {
  double? intensity;
  double? effort;
  double? volume;
  final TextEditingController intensityCtrl = TextEditingController();
  final TextEditingController effortCtrl = TextEditingController();
  final TextEditingController volumeCtrl = TextEditingController();
  final List<String> editedFields = [];
  DateTime? lastIntensityChange;
  DateTime? lastEffortChange;
  DateTime? lastVolumeChange;

  SetDraft({this.intensity, this.effort, this.volume}) {
    if (intensity != null) intensityCtrl.text = intensity.toString();
    if (effort != null) effortCtrl.text = effort.toString();
    if (volume != null) volumeCtrl.text = volume.toString();

    // Добавляем слушатели для отслеживания изменений
    intensityCtrl.addListener(() {
      lastIntensityChange = DateTime.now();
    });
    effortCtrl.addListener(() {
      lastEffortChange = DateTime.now();
    });
    volumeCtrl.addListener(() {
      lastVolumeChange = DateTime.now();
    });
  }

  void updateFromControllers() {
    intensity = double.tryParse(intensityCtrl.text);
    effort = double.tryParse(effortCtrl.text);
    volume = double.tryParse(volumeCtrl.text);
  }

  /// Определяет, какой параметр был изменен первым
  String? getFirstEditedField() {
    final times = [
      if (lastIntensityChange != null) MapEntry('intensity', lastIntensityChange!),
      if (lastEffortChange != null) MapEntry('effort', lastEffortChange!),
      if (lastVolumeChange != null) MapEntry('volume', lastVolumeChange!),
    ];

    if (times.isEmpty) return null;

    times.sort((a, b) => a.value.compareTo(b.value)); // Сортируем по времени возрастания (первый введенный)
    return times.first.key;
  }

  /// Очищает первый введенный параметр
  void clearFirstEditedField() {
    final firstField = getFirstEditedField();
    switch (firstField) {
      case 'intensity':
        intensityCtrl.clear();
        intensity = null;
        lastIntensityChange = null;
        break;
      case 'effort':
        effortCtrl.clear();
        effort = null;
        lastEffortChange = null;
        break;
      case 'volume':
        volumeCtrl.clear();
        volume = null;
        lastVolumeChange = null;
        break;
      default:
        // Если не удалось определить, очищаем effort (RPE) по умолчанию
        effortCtrl.clear();
        effort = null;
        lastEffortChange = null;
    }
  }
}

class Workout {
  String? name;
  List<ExerciseWithSets> exercises;

  Workout({this.name, required this.exercises});

  Map<String, dynamic> toJson() => {
    'name': name,
    'exercises': exercises.map((e) => e.toJson()).toList(),
  };
}

class CalendarPlanCreate extends ConsumerStatefulWidget {
  const CalendarPlanCreate({super.key});

  @override
  ConsumerState<CalendarPlanCreate> createState() => _CalendarPlanCreateState();
}

class _CalendarPlanCreateState extends ConsumerState<CalendarPlanCreate> {
  bool updating = false;
  late RpeService _rpeService;

  @override
  void initState() {
    super.initState();
    _rpeService = provider_package.Provider.of<RpeService>(context, listen: false);
    
    // Add initial mesocycle with one microcycle
    _mesocycles.add(MesocycleCreate(
      name: '',
      microcycleLengthDays: 7,
      orderIndex: 0,
      microcycles: [
        MicrocycleCreate(
          name: 'Microcycle 1',
          daysCount: 7,
          schedule: {},
          orderIndex: 0,
        ),
      ],
    ));
  }

  final TextEditingController _planNameController = TextEditingController();
  final ApiClient _apiClient = ApiClient.create();
  final List<MesocycleCreate> _mesocycles = [];
  bool _isSaving = false;
  int? editingDay;
  Map<int, ExerciseDefinition?> selectedExercises = {};

  void _removeMesocycle(int index) {
    setState(() {
      _mesocycles.removeAt(index);
    });
  }

  void _updateMesocycleName(int index, String name) {
    setState(() {
      _mesocycles[index] = _mesocycles[index].copyWith(name: name);
    });
  }

  void _updateMicrocyclesCount(int index, int microcyclesCount) {
    setState(() {
      final oldCount = _mesocycles[index].microcycles.length;
      _mesocycles[index] = _mesocycles[index].copyWith(microcycles: []);

      // Automatically generate microcycles
      for (int i = 0; i < microcyclesCount; i++) {
        _mesocycles[index].microcycles.add(MicrocycleCreate(
          name: 'Microcycle ${i+1}',
          daysCount: _mesocycles[index].microcycleLengthDays,
          schedule: {},
          orderIndex: i,
        ));
      }
    });
  }

  void _updateMicrocycleLengthDays(int index, int microcycleLengthDays) {
    setState(() {
      _mesocycles[index] = _mesocycles[index].copyWith(microcycleLengthDays: microcycleLengthDays);
      
      // Update all existing microcycles to match the new length
      for (int i = 0; i < _mesocycles[index].microcycles.length; i++) {
        _mesocycles[index].microcycles[i] = _mesocycles[index].microcycles[i].copyWith(daysCount: microcycleLengthDays);
      }
    });
  }

  void _addExerciseForDay(int mesocycleIndex, int microcycleIndex, int day, ExerciseDefinition exercise) {
    setState(() {
      final schedule = _mesocycles[mesocycleIndex].microcycles[microcycleIndex].schedule;
      
      // Initialize day if not exists
      schedule['$day'] ??= [Workout(name: 'Workout ${(schedule['$day']?.length ?? 0) + 1}', exercises: [])];
      
      // Add exercise to the first workout of the day
      schedule['$day']!.first.exercises.add(
        ExerciseWithSets(
          exercise: exercise,
          sets: [ParamsSets()],
        ),
      );
    });
  }

  void _selectExerciseForDay(int mesocycleIndex, int microcycleIndex, int day) async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ExerciseSelectionScreen()),
    );

    if (result != null && result is ExerciseDefinition) {
      _addExerciseForDay(mesocycleIndex, microcycleIndex, day, result);
    }
  }

  void _editExercise(int mesocycleIndex, int microcycleIndex, int day, ExerciseWithSets exercise) async {
    setState(() {
      editingDay = day;
      selectedExercises[day] = exercise.exercise;
    });
  }

  Future<void> _savePlan() async {
    if (_planNameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a plan name')),
      );
      return;
    }

    setState(() {
      _isSaving = true;
    });

    try {
      // Create the plan data
      final planData = {
        'name': _planNameController.text,
        'duration_weeks': _mesocycles.fold<int>(0, (sum, meso) => sum + meso.microcycles.length),
        'mesocycles': _mesocycles.map((meso) => meso.toJson()).toList(),
      };

      final response = await _apiClient.post(ApiConfig.createCalendarPlanEndpoint(), planData);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Plan created successfully')),
      );

      Navigator.pop(context); // Go back to the plans screen
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to create plan: $e')),
      );
    } finally {
      setState(() {
        _isSaving = false;
      });
    }
  }

  @override
  void dispose() {
    _planNameController.dispose();
    super.dispose();
  }

  void _startEditingDay(int mesocycleIndex, int microcycleIndex, int day) {
    setState(() {
      editingDay = day;
      selectedExercises[day] = null;
    });
  }

  void _addMesocycle() {
    setState(() {
      _mesocycles.add(MesocycleCreate(
        name: '',
        microcycleLengthDays: 7,
        orderIndex: _mesocycles.length,
        microcycles: [
          MicrocycleCreate(
            name: 'Microcycle ${_mesocycles.length+1}',
            daysCount: 7,
            schedule: {},
            orderIndex: 0,
          ),
        ],
      ));
    });
  }

  @override
  Widget build(BuildContext context) {
    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Create Calendar Plan',
            onTitleTap: openChat,
            actions: [
              TextButton(
                onPressed: _isSaving ? null : _savePlan,
                child: _isSaving
                    ? const CircularProgressIndicator()
                    : const Text('Save', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
          body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _planNameController,
              decoration: const InputDecoration(
                labelText: 'Plan Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            const Text('Mesocycles', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            Expanded(
              child: ListView.builder(
                itemCount: _mesocycles.length,
                itemBuilder: (context, index) {
                  return _buildMesocycleCard(index);
                },
              ),
            ),
            IconButton(
              onPressed: _addMesocycle,
              icon: const Icon(Icons.add),
              tooltip: 'Add Mesocycle',
            ),
            IconButton(
              onPressed: () => _removeMesocycle(_mesocycles.length - 1),
              icon: const Icon(Icons.delete),
              tooltip: 'Remove Mesocycle',
            ),
          ],
        ),
      ),
    );
      },
    );
  }

  Widget _buildSetRow(int mesocycleIndex, int microcycleIndex, int day, ExerciseWithSets exercise, int setIndex, ParamsSets set) {
    final draft = exercise.setDrafts[setIndex];
    if (draft == null) return Container();

    draft.intensityCtrl.addListener(() async {
      await updateThirdParameter(draft);
    });
    draft.effortCtrl.addListener(() async {
      await updateThirdParameter(draft);
    });
    draft.volumeCtrl.addListener(() async {
      await updateThirdParameter(draft);
    });

    return Row(
      children: [
        Expanded(child: TextField(
          controller: draft.intensityCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d*')),
            LengthLimitingTextInputFormatter(5), // Ограничение длины
          ],
          decoration: InputDecoration(hintText: 'Intensity (%)')
        )),
        Expanded(child: TextField(
          controller: draft.volumeCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(3), // Максимум 3 цифры для количества повторений
          ],
          decoration: InputDecoration(hintText: 'Volume')
        )),
        Expanded(child: TextField(
          controller: draft.effortCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
            LengthLimitingTextInputFormatter(3), // RPE от 1 до 10
          ],
          decoration: InputDecoration(hintText: 'Effort')
        )),
        Expanded(
          child: IconButton(
            icon: const Icon(Icons.delete),
            onPressed: () {
              setState(() {
                exercise.sets.removeAt(setIndex);
              });
            },
          ),
        ),
      ],
    );
  }

  Widget _buildMesocycleCard(int index) {
    final mesocycle = _mesocycles[index];
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(labelText: 'Mesocycle Name'),
                    onChanged: (value) => _updateMesocycleName(index, value),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Text('Microcycles: '),
                IconButton(
                  onPressed: () => _updateMicrocyclesCount(index, mesocycle.microcycles.length - 1),
                  icon: const Icon(Icons.remove),
                ),
                Text('${mesocycle.microcycles.length}'),
                IconButton(
                  onPressed: () => _updateMicrocyclesCount(index, mesocycle.microcycles.length + 1),
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            Row(
              children: [
                const Text('Microcycle Length (days): '),
                IconButton(
                  onPressed: () => _updateMicrocycleLengthDays(index, mesocycle.microcycleLengthDays - 1),
                  icon: const Icon(Icons.remove),
                ),
                Text('${mesocycle.microcycleLengthDays}'),
                IconButton(
                  onPressed: () => _updateMicrocycleLengthDays(index, mesocycle.microcycleLengthDays + 1),
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text('Microcycles', style: TextStyle(fontWeight: FontWeight.bold)),
            ...mesocycle.microcycles.map((microcycle) {
              final microIndex = mesocycle.microcycles.indexOf(microcycle);
              return ExpansionTile(
                title: Text(microcycle.name),
                children: [
                  for (int day = 1; day <= microcycle.daysCount; day++) ...[
                    ListTile(
                      title: Text('Day $day'),
                      trailing: IconButton(
                        icon: const Icon(Icons.add),
                        onPressed: () => _selectExerciseForDay(index, microIndex, day),
                      ),
                      onTap: () => _startEditingDay(index, microIndex, day),
                    ),
                    ...(microcycle.schedule['$day'] ?? []).map((workout) => Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(left: 16.0),
                          child: Text(workout.name ?? '', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                        ListView.builder(
                          shrinkWrap: true,
                          itemCount: workout.exercises.length,
                          itemBuilder: (context, index) {
                            final exercise = workout.exercises[index];
                            return ListTile(
                              title: Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: exercise.setDrafts[0].intensityCtrl,
                                      decoration: InputDecoration(labelText: 'Intensity'),
                                      keyboardType: TextInputType.number,
                                      inputFormatters: [
                                        FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
                                        LengthLimitingTextInputFormatter(5),
                                      ],
                                      onChanged: (value) {
                                        updateThirdParameter(exercise.setDrafts[0]);
                                      },
                                    ),
                                  ),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: TextField(
                                      controller: exercise.setDrafts[0].volumeCtrl,
                                      decoration: InputDecoration(labelText: 'Volume'),
                                      keyboardType: TextInputType.number,
                                      inputFormatters: [
                                        FilteringTextInputFormatter.digitsOnly,
                                        LengthLimitingTextInputFormatter(3),
                                      ],
                                      onChanged: (value) {
                                        updateThirdParameter(exercise.setDrafts[0]);
                                      },
                                    ),
                                  ),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: TextField(
                                      controller: exercise.setDrafts[0].effortCtrl,
                                      decoration: InputDecoration(labelText: 'Effort'),
                                      keyboardType: TextInputType.number,
                                      inputFormatters: [
                                        FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
                                        LengthLimitingTextInputFormatter(3),
                                      ],
                                      onChanged: (value) {
                                        updateThirdParameter(exercise.setDrafts[0]);
                                      },
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ],
                    )),
                  ],
                ],
              );
            }),
          ],
        ),
      ),
    );
  }

  Future<void> updateThirdParameter(SetDraft draft) async {
    if (updating) return;
    updating = true;

    try {
      draft.updateFromControllers();
      double? intensity = draft.intensity;
      double? effort = draft.effort;  // RPE
      double? volume = draft.volume;    // reps

      print('updateThirdParameter called with: intensity=$intensity, effort=$effort, volume=$volume');

      // Валидация значений
      if (intensity != null && intensity > 100) {
        draft.intensityCtrl.text = '100';
        draft.intensity = 100;
        intensity = 100;
      }
      if (effort != null && effort > 10) {
        draft.effortCtrl.text = '10';
        draft.effort = 10;
        effort = 10;
      }

      // Count non-null parameters
      int nonNullCount = 0;
      if (intensity != null) nonNullCount++;
      if (effort != null) nonNullCount++;
      if (volume != null) nonNullCount++;

      // Если все три параметра введены, очищаем первый введенный и пересчитываем его
      if (nonNullCount == 3) {
        print('All three parameters entered - clearing the first entered one and recalculating it');

        // Определяем, какой параметр был введен первым
        final firstField = draft.getFirstEditedField();
        print('First entered field: $firstField');

        // Очищаем первый введенный параметр
        draft.clearFirstEditedField();
        print('Cleared first entered value, now recalculating...');

        // Теперь у нас есть только 2 параметра, пересчитываем очищенный
        draft.updateFromControllers();

        // Пересчитываем очищенный параметр на основе оставшихся двух
        if (firstField == 'effort' && draft.intensity != null && draft.volume != null) {
          print('Recalculating RPE from intensity and volume');
          final calculatedEffort = await _rpeService.calculateRpe(draft.intensity!, draft.volume!.toInt());
          if (calculatedEffort != null) {
            draft.effortCtrl.text = calculatedEffort.toStringAsFixed(1);
            draft.effort = calculatedEffort;
          }
        } else if (firstField == 'volume' && draft.intensity != null && draft.effort != null) {
          print('Recalculating reps from intensity and RPE');
          final calculatedVolume = await _rpeService.calculateReps(draft.intensity!, draft.effort!);
          if (calculatedVolume != null) {
            draft.volumeCtrl.text = calculatedVolume.toStringAsFixed(0);
            draft.volume = calculatedVolume.toDouble();
          }
        } else if (firstField == 'intensity' && draft.effort != null && draft.volume != null) {
          print('Recalculating intensity from reps and RPE');
          final calculatedIntensity = await _rpeService.calculateIntensity(draft.volume!.toInt(), draft.effort!);
          if (calculatedIntensity != null) {
            draft.intensityCtrl.text = calculatedIntensity.toStringAsFixed(1);
            draft.intensity = calculatedIntensity;
          }
        }

        return;
      }

      // Only recalculate if exactly two parameters are provided
      if (nonNullCount == 2) {
        if (intensity != null && volume != null) {
          print('Calculating RPE from intensity and volume (reps)');
          final calculatedEffort = await _rpeService.calculateRpe(intensity, volume.toInt());
          if (calculatedEffort != null) {
            draft.effortCtrl.text = calculatedEffort.toStringAsFixed(1);
            draft.effort = calculatedEffort;
          }
        } else if (intensity != null && effort != null) {
          print('Calculating reps from intensity and effort (RPE)');
          final calculatedVolume = await _rpeService.calculateReps(intensity, effort);
          if (calculatedVolume != null) {
            draft.volumeCtrl.text = calculatedVolume.toStringAsFixed(0);
            draft.volume = calculatedVolume.toDouble();
          }
        } else if (effort != null && volume != null) {
          print('Calculating intensity from reps and RPE');
          final calculatedIntensity = await _rpeService.calculateIntensity(volume.toInt(), effort);
          if (calculatedIntensity != null) {
            draft.intensityCtrl.text = calculatedIntensity.toStringAsFixed(1);
            draft.intensity = calculatedIntensity;
          }
        }
      } else {
        print('Skipping calculation: exactly two parameters required');
      }
    } catch (e) {
      print('Error in updateThirdParameter: $e');
    } finally {
      updating = false;
    }
  }
}

class MesocycleCreate {
  final String name;
  final int microcycleLengthDays;
  final List<MicrocycleCreate> microcycles;
  final int orderIndex;

  MesocycleCreate({
    required this.name,
    required this.microcycleLengthDays,
    required this.microcycles,
    required this.orderIndex,
  });

  MesocycleCreate copyWith({
    String? name,
    int? microcycleLengthDays,
    List<MicrocycleCreate>? microcycles,
    int? orderIndex,
  }) {
    return MesocycleCreate(
      name: name ?? this.name,
      microcycleLengthDays: microcycleLengthDays ?? this.microcycleLengthDays,
      microcycles: microcycles ?? this.microcycles,
      orderIndex: orderIndex ?? this.orderIndex,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'duration_weeks': microcycles.length,
      'microcycles': microcycles.map((m) => m.toJson()).toList(),
      'order_index': orderIndex,
    };
  }
}

class MicrocycleCreate {
  final String name;
  final int daysCount;
  final Map<String, List<Workout>> schedule;
  final int orderIndex;

  MicrocycleCreate({
    required this.name,
    required this.daysCount,
    required this.schedule,
    required this.orderIndex,
  });

  MicrocycleCreate copyWith({
    String? name,
    int? daysCount,
    Map<String, List<Workout>>? schedule,
    int? orderIndex,
  }) {
    return MicrocycleCreate(
      name: name ?? this.name,
      daysCount: daysCount ?? this.daysCount,
      schedule: schedule ?? this.schedule,
      orderIndex: orderIndex ?? this.orderIndex,
    );
  }

  Map<String, dynamic> toJson() {
    // Build plan_workouts from the schedule map
    final List<Map<String, dynamic>> planWorkouts = [];
    final entries = schedule.entries.toList()
      ..sort((a, b) => int.tryParse(a.key)?.compareTo(int.tryParse(b.key) ?? 0) ?? 0);

    for (final entry in entries) {
      final int day = int.tryParse(entry.key) ?? 0;
      final List<Workout> workouts = entry.value;

      // Flatten all exercises from all workouts within the day
      final List<Map<String, dynamic>> exercises = [];
      for (final workout in workouts) {
        for (final ex in workout.exercises) {
          exercises.add(ex.toJson());
        }
      }

      if (exercises.isNotEmpty) {
        planWorkouts.add({
          'day_label': 'Day $day',
          'order_index': day > 0 ? day - 1 : 0,
          'exercises': exercises,
        });
      }
    }

    return {
      'name': name,
      'days_count': daysCount,
      'order_index': orderIndex,
      'plan_workouts': planWorkouts,
    };
  }
}

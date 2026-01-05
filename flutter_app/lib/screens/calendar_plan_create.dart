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


  String? getFirstEditedField() {
    final times = [
      if (lastIntensityChange != null) MapEntry('intensity', lastIntensityChange!),
      if (lastEffortChange != null) MapEntry('effort', lastEffortChange!),
      if (lastVolumeChange != null) MapEntry('volume', lastVolumeChange!),
    ];

    if (times.isEmpty) return null;

    times.sort((a, b) => a.value.compareTo(b.value));
    return times.first.key;
  }


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
  static const List<String> _normalizationUnits = ['kg', '%'];

  @override
  void initState() {
    super.initState();
    _rpeService = provider_package.Provider.of<RpeService>(context, listen: false);


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


      for (int i = 0; i < _mesocycles[index].microcycles.length; i++) {
        _mesocycles[index].microcycles[i] = _mesocycles[index].microcycles[i].copyWith(daysCount: microcycleLengthDays);
      }
    });
  }

  void _addExerciseForDay(int mesocycleIndex, int microcycleIndex, int day, ExerciseDefinition exercise) {
    setState(() {
      final schedule = _mesocycles[mesocycleIndex].microcycles[microcycleIndex].schedule;


      schedule['$day'] ??= [Workout(name: 'Workout ${(schedule['$day']?.length ?? 0) + 1}', exercises: [])];


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

  void _replaceMicrocycle(int mesocycleIndex, int microcycleIndex, MicrocycleCreate updated) {
    final updatedMicrocycles = List<MicrocycleCreate>.from(_mesocycles[mesocycleIndex].microcycles);
    updatedMicrocycles[microcycleIndex] = updated;
    _mesocycles[mesocycleIndex] = _mesocycles[mesocycleIndex].copyWith(microcycles: updatedMicrocycles);
  }

  void _updateMicrocycleNameField(int mesocycleIndex, int microcycleIndex, String name) {
    setState(() {
      final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
      _replaceMicrocycle(mesocycleIndex, microcycleIndex, micro.copyWith(name: name));
    });
  }

  void _updateMicrocycleNormalizationValue(int mesocycleIndex, int microcycleIndex, String rawValue) {
    final sanitized = rawValue.replaceAll(',', '.');
    final trimmed = sanitized.trim();
    setState(() {
      final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
      _replaceMicrocycle(
        mesocycleIndex,
        microcycleIndex,
        micro.copyWith(
          normalizationValueInput: trimmed,
          resetNormalizationValue: trimmed.isEmpty,
        ),
      );
    });
  }

  void _updateMicrocycleNormalizationUnit(int mesocycleIndex, int microcycleIndex, String? unit) {
    final trimmed = unit?.trim() ?? '';
    setState(() {
      final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
      _replaceMicrocycle(
        mesocycleIndex,
        microcycleIndex,
        micro.copyWith(
          normalizationUnit: trimmed.isEmpty ? null : trimmed,
          resetNormalizationUnit: trimmed.isEmpty,
        ),
      );
    });
  }

  void _addNormalizationRule(int mesocycleIndex, int microcycleIndex) {
    setState(() {
      final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
      final rules = List<NormalizationRuleDraft>.from(micro.normalizationRules);
      rules.add(NormalizationRuleDraft());
      _replaceMicrocycle(mesocycleIndex, microcycleIndex, micro.copyWith(normalizationRules: rules));
    });
  }

  void _removeNormalizationRule(int mesocycleIndex, int microcycleIndex, int ruleIndex) {
    setState(() {
      final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
      final rules = List<NormalizationRuleDraft>.from(micro.normalizationRules);
      if (ruleIndex >= 0 && ruleIndex < rules.length) {
        rules.removeAt(ruleIndex);
        _replaceMicrocycle(mesocycleIndex, microcycleIndex, micro.copyWith(normalizationRules: rules));
      }
    });
  }

  void _updateNormalizationRule(
    int mesocycleIndex,
    int microcycleIndex,
    int ruleIndex,
    void Function(NormalizationRuleDraft rule) updater,
  ) {
    final micro = _mesocycles[mesocycleIndex].microcycles[microcycleIndex];
    final rules = List<NormalizationRuleDraft>.from(micro.normalizationRules);
    if (ruleIndex < 0 || ruleIndex >= rules.length) {
      return;
    }
    updater(rules[ruleIndex]);
    setState(() {
      _replaceMicrocycle(mesocycleIndex, microcycleIndex, micro.copyWith(normalizationRules: rules));
    });
  }

  String _normalizationSummary(MicrocycleCreate microcycle) {
    final value = microcycle.normalizationValueInput.trim();
    final unit = microcycle.normalizationUnit?.trim() ?? '';
    final rulesCount = microcycle.normalizationRules.length;
    if (value.isEmpty || unit.isEmpty) {
      return rulesCount > 0 ? 'Индивид. правил: $rulesCount' : 'Нормализация не задана';
    }
    final unitLabel = unit == '%' ? '% от 1RM' : 'кг';
    final rulesLabel = rulesCount > 0 ? ', правил: $rulesCount' : '';
    return 'Δ $value $unitLabel$rulesLabel';
  }

  Widget _buildNormalizationSection(int mesocycleIndex, int microIndex, MicrocycleCreate microcycle) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Нормализация после микроцикла',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                key: ValueKey('norm-value-$mesocycleIndex-$microIndex'),
                initialValue: microcycle.normalizationValueInput,
                keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                decoration: const InputDecoration(
                  labelText: 'Изменение (например, -2.5)',
                  hintText: 'В кг или %',
                ),
                onChanged: (value) => _updateMicrocycleNormalizationValue(mesocycleIndex, microIndex, value),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DropdownButtonFormField<String>(
                key: ValueKey('norm-unit-$mesocycleIndex-$microIndex'),
                value: microcycle.normalizationUnit,
                hint: const Text('Ед. измерения'),
                items: _normalizationUnits
                    .map(
                      (unit) => DropdownMenuItem(
                        value: unit,
                        child: Text(unit == '%' ? '% (мультипликативно)' : 'кг (абсолютно)'),
                      ),
                    )
                    .toList(),
                onChanged: (value) => _updateMicrocycleNormalizationUnit(mesocycleIndex, microIndex, value),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Можно указать одно общее изменение и/или список правил для конкретных упражнений, групп мышц или target-мышц.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Правила нормализации', style: TextStyle(fontWeight: FontWeight.w600)),
            TextButton.icon(
              onPressed: () => _addNormalizationRule(mesocycleIndex, microIndex),
              icon: const Icon(Icons.add),
              label: const Text('Добавить правило'),
            ),
          ],
        ),
        if (microcycle.normalizationRules.isEmpty)
          const Padding(
            padding: EdgeInsets.only(bottom: 8.0),
            child: Text('Пока нет индивидуальных правил'),
          )
        else
          ...microcycle.normalizationRules.asMap().entries.map(
                (entry) => _buildNormalizationRuleCard(
                  mesocycleIndex,
                  microIndex,
                  entry.key,
                  entry.value,
                ),
              ),
      ],
    );
  }

  Widget _buildNormalizationRuleCard(
    int mesocycleIndex,
    int microIndex,
    int ruleIndex,
    NormalizationRuleDraft rule,
  ) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Правило ${ruleIndex + 1}', style: const TextStyle(fontWeight: FontWeight.w600)),
                IconButton(
                  tooltip: 'Удалить правило',
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () => _removeNormalizationRule(mesocycleIndex, microIndex, ruleIndex),
                ),
              ],
            ),
            TextFormField(
              key: ValueKey('rule-ex-$mesocycleIndex-$microIndex-$ruleIndex'),
              initialValue: rule.exerciseIdsRaw,
              decoration: const InputDecoration(
                labelText: 'ID упражнений (через запятую)',
                hintText: 'Напр.: 12, 45, 103',
              ),
              onChanged: (value) => _updateNormalizationRule(
                mesocycleIndex,
                microIndex,
                ruleIndex,
                (r) => r.exerciseIdsRaw = value,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              key: ValueKey('rule-mg-$mesocycleIndex-$microIndex-$ruleIndex'),
              initialValue: rule.muscleGroupsRaw,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Muscle groups (через запятую)',
                hintText: 'Напр.: chest, quads',
              ),
              onChanged: (value) => _updateNormalizationRule(
                mesocycleIndex,
                microIndex,
                ruleIndex,
                (r) => r.muscleGroupsRaw = value,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              key: ValueKey('rule-target-$mesocycleIndex-$microIndex-$ruleIndex'),
              initialValue: rule.targetMusclesRaw,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Target muscles (через запятую)',
                hintText: 'Напр.: biceps_long, lats',
              ),
              onChanged: (value) => _updateNormalizationRule(
                mesocycleIndex,
                microIndex,
                ruleIndex,
                (r) => r.targetMusclesRaw = value,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    key: ValueKey('rule-value-$mesocycleIndex-$microIndex-$ruleIndex'),
                    initialValue: rule.valueRaw,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                    decoration: const InputDecoration(labelText: 'Δ значение'),
                    onChanged: (value) => _updateNormalizationRule(
                      mesocycleIndex,
                      microIndex,
                      ruleIndex,
                      (r) => r.valueRaw = value,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    key: ValueKey('rule-unit-$mesocycleIndex-$microIndex-$ruleIndex'),
                    value: rule.unit,
                    hint: const Text('Ед. изм.'),
                    items: _normalizationUnits
                        .map(
                          (unit) => DropdownMenuItem(
                            value: unit,
                            child: Text(unit == '%' ? '% (мультипликативно)' : 'кг (абсолютно)'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => _updateNormalizationRule(
                      mesocycleIndex,
                      microIndex,
                      ruleIndex,
                      (r) => r.unit = value,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
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

      final planData = {
        'name': _planNameController.text,
        'duration_weeks': _mesocycles.fold<int>(0, (sum, meso) => sum + meso.microcycles.length),
        'mesocycles': _mesocycles.map((meso) => meso.toJson()).toList(),
      };

      final response = await _apiClient.post(ApiConfig.createCalendarPlanEndpoint(), planData);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Plan created successfully')),
      );

      Navigator.pop(context);
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
            LengthLimitingTextInputFormatter(5),
          ],
          decoration: InputDecoration(hintText: 'Intensity (%)')
        )),
        Expanded(child: TextField(
          controller: draft.volumeCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(3),
          ],
          decoration: InputDecoration(hintText: 'Volume')
        )),
        Expanded(child: TextField(
          controller: draft.effortCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
            LengthLimitingTextInputFormatter(3),
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
            ...mesocycle.microcycles.asMap().entries.map((entry) {
              final microIndex = entry.key;
              final microcycle = entry.value;
              return ExpansionTile(
                title: Text(microcycle.name.isEmpty ? 'Microcycle ${microIndex + 1}' : microcycle.name),
                subtitle: Text(_normalizationSummary(microcycle)),
                childrenPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                children: [
                  TextFormField(
                    key: ValueKey('micro-name-$index-$microIndex'),
                    initialValue: microcycle.name,
                    decoration: const InputDecoration(labelText: 'Название микроцикла'),
                    onChanged: (value) => _updateMicrocycleNameField(index, microIndex, value),
                  ),
                  const SizedBox(height: 12),
                  _buildNormalizationSection(index, microIndex, microcycle),
                  const Divider(height: 32),
                  for (int day = 1; day <= microcycle.daysCount; day++) ...[
                    ListTile(
                      title: Text('Day $day'),
                      trailing: IconButton(
                        icon: const Icon(Icons.add),
                        onPressed: () => _selectExerciseForDay(index, microIndex, day),
                      ),
                      onTap: () => _startEditingDay(index, microIndex, day),
                    ),
                    ...(microcycle.schedule['$day'] ?? []).map(
                      (workout) => Column(
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(left: 16.0, bottom: 4),
                            child: Text(
                              workout.name ?? '',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                          ListView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: workout.exercises.length,
                            itemBuilder: (context, exerciseIndex) {
                              final exercise = workout.exercises[exerciseIndex];
                              return ListTile(
                                title: Row(
                                  children: [
                                    Expanded(
                                      child: TextField(
                                        controller: exercise.setDrafts[0].intensityCtrl,
                                        decoration: const InputDecoration(labelText: 'Intensity'),
                                        keyboardType: TextInputType.number,
                                        inputFormatters: [
                                          FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
                                          LengthLimitingTextInputFormatter(5),
                                        ],
                                        onChanged: (value) => updateThirdParameter(exercise.setDrafts[0]),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: TextField(
                                        controller: exercise.setDrafts[0].volumeCtrl,
                                        decoration: const InputDecoration(labelText: 'Volume'),
                                        keyboardType: TextInputType.number,
                                        inputFormatters: [
                                          FilteringTextInputFormatter.digitsOnly,
                                          LengthLimitingTextInputFormatter(3),
                                        ],
                                        onChanged: (value) => updateThirdParameter(exercise.setDrafts[0]),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: TextField(
                                        controller: exercise.setDrafts[0].effortCtrl,
                                        decoration: const InputDecoration(labelText: 'Effort'),
                                        keyboardType: TextInputType.number,
                                        inputFormatters: [
                                          FilteringTextInputFormatter.allow(RegExp(r'\d*\.?\d*')),
                                          LengthLimitingTextInputFormatter(3),
                                        ],
                                        onChanged: (value) => updateThirdParameter(exercise.setDrafts[0]),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ],
                      ),
                    ),
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
      double? effort = draft.effort;
      double? volume = draft.volume;

      print('updateThirdParameter called with: intensity=$intensity, effort=$effort, volume=$volume');


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


      int nonNullCount = 0;
      if (intensity != null) nonNullCount++;
      if (effort != null) nonNullCount++;
      if (volume != null) nonNullCount++;


      if (nonNullCount == 3) {
        print('All three parameters entered - clearing the first entered one and recalculating it');


        final firstField = draft.getFirstEditedField();
        print('First entered field: $firstField');


        draft.clearFirstEditedField();
        print('Cleared first entered value, now recalculating...');


        draft.updateFromControllers();


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
  final String normalizationValueInput;
  final String? normalizationUnit;
  final List<NormalizationRuleDraft> normalizationRules;

  MicrocycleCreate({
    required this.name,
    required this.daysCount,
    required this.schedule,
    required this.orderIndex,
    this.normalizationValueInput = '',
    this.normalizationUnit,
    List<NormalizationRuleDraft>? normalizationRules,
  }) : normalizationRules = normalizationRules ?? const [];

  MicrocycleCreate copyWith({
    String? name,
    int? daysCount,
    Map<String, List<Workout>>? schedule,
    int? orderIndex,
    String? normalizationValueInput,
    String? normalizationUnit,
    List<NormalizationRuleDraft>? normalizationRules,
    bool resetNormalizationValue = false,
    bool resetNormalizationUnit = false,
  }) {
    return MicrocycleCreate(
      name: name ?? this.name,
      daysCount: daysCount ?? this.daysCount,
      schedule: schedule ?? this.schedule,
      orderIndex: orderIndex ?? this.orderIndex,
      normalizationValueInput: resetNormalizationValue
          ? ''
          : (normalizationValueInput ?? this.normalizationValueInput),
      normalizationUnit: resetNormalizationUnit ? null : (normalizationUnit ?? this.normalizationUnit),
      normalizationRules: normalizationRules ?? this.normalizationRules,
    );
  }

  Map<String, dynamic> toJson() {
    final List<Map<String, dynamic>> planWorkouts = [];
    final entries = schedule.entries.toList()
      ..sort((a, b) => int.tryParse(a.key)?.compareTo(int.tryParse(b.key) ?? 0) ?? 0);

    for (final entry in entries) {
      final int day = int.tryParse(entry.key) ?? 0;
      final List<Workout> workouts = entry.value;

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

    final sanitizedValue = normalizationValueInput.replaceAll(',', '.').trim();
    final normalizedValue = double.tryParse(sanitizedValue);
    final normalizedUnit = (normalizationUnit ?? '').trim();
    final rulePayloads = normalizationRules
        .map((rule) => rule.toJson())
        .whereType<Map<String, dynamic>>()
        .toList();

    return {
      'name': name,
      'days_count': daysCount,
      'order_index': orderIndex,
      'plan_workouts': planWorkouts,
      if (normalizedValue != null) 'normalization_value': normalizedValue,
      if (normalizedUnit.isNotEmpty) 'normalization_unit': normalizedUnit,
      if (rulePayloads.isNotEmpty) 'normalization_rules': rulePayloads,
    };
  }
}

class NormalizationRuleDraft {
  String exerciseIdsRaw;
  String muscleGroupsRaw;
  String targetMusclesRaw;
  String valueRaw;
  String? unit;

  NormalizationRuleDraft({
    this.exerciseIdsRaw = '',
    this.muscleGroupsRaw = '',
    this.targetMusclesRaw = '',
    this.valueRaw = '',
    this.unit,
  });

  Map<String, dynamic>? toJson() {
    final sanitizedValue = valueRaw.replaceAll(',', '.').trim();
    final value = double.tryParse(sanitizedValue);
    final unitValue = (unit ?? '').trim();
    if (value == null || unitValue.isEmpty) {
      return null;
    }

    final exerciseIds = exerciseIdsRaw
        .split(RegExp(r'[,\s]+'))
        .map((token) => int.tryParse(token))
        .whereType<int>()
        .toSet()
        .toList()
      ..sort();
    final muscleGroups = muscleGroupsRaw
        .split(RegExp(r'[,\n]+'))
        .map((token) => token.trim())
        .where((token) => token.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    final targetMuscles = targetMusclesRaw
        .split(RegExp(r'[,\n]+'))
        .map((token) => token.trim())
        .where((token) => token.isNotEmpty)
        .toSet()
        .toList()
      ..sort();

    if (exerciseIds.isEmpty && muscleGroups.isEmpty && targetMuscles.isEmpty) {
      return null;
    }

    return {
      'exercise_ids': exerciseIds,
      'muscle_groups': muscleGroups,
      'target_muscles': targetMuscles,
      'value': value,
      'unit': unitValue,
    };
  }
}


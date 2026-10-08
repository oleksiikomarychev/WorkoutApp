// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Workout App';

  @override
  String get missingAthleteId => 'Missing athleteId';

  @override
  String get missingChatArguments => 'Missing chat arguments';

  @override
  String get fieldRequired => 'Required';

  @override
  String get exerciseName => 'Exercise name';

  @override
  String get exerciseListEmptyNameError => 'Please enter an exercise name';

  @override
  String activePlanLoadError(Object error) {
    return 'Failed to load plan: $error';
  }

  @override
  String get activePlanNoWorkoutsOnDay => 'No workouts on this day';

  @override
  String get activePlanNotesLabel => 'Notes';

  @override
  String get coachAthletePlanNoActivePlan => 'No active plan';

  @override
  String get coachAthletePlanSetsLabel => 'Sets';

  @override
  String get coachAthletePlanMassEditExerciseHint => 'Enter note for exercises';

  @override
  String coachAthletePlanMassEditError(Object error) {
    return 'Mass edit error: $error';
  }

  @override
  String get search => 'Search...';

  @override
  String get done => 'Done';

  @override
  String get refresh => 'Refresh';

  @override
  String get edit => 'Edit';

  @override
  String get delete => 'Delete';

  @override
  String get apply => 'Apply';

  @override
  String get cancel => 'Cancel';

  @override
  String get retry => 'Retry';

  @override
  String get hide => 'Hide';

  @override
  String get noDate => 'no date';

  @override
  String idPrefix(Object id) {
    return 'ID: $id';
  }

  @override
  String get filter => 'Filter';

  @override
  String get changes => 'Changes';

  @override
  String statuses(Object statuses) {
    return 'Statuses: $statuses';
  }

  @override
  String exercises(Object exercises) {
    return 'Exercises: $exercises';
  }

  @override
  String workoutsAffected(Object count) {
    return 'Workouts affected: $count';
  }

  @override
  String workoutsShifted(Object count) {
    return 'Workouts shifted: $count';
  }

  @override
  String setsModified(Object count) {
    return 'Sets modified: $count';
  }

  @override
  String setsToBeModified(Object count) {
    return 'Sets to be modified: $count';
  }

  @override
  String shiftDays(Object sign, Object days) {
    return 'Shift: $sign$days d.';
  }

  @override
  String startingFrom(Object date) {
    return 'Starting from: $date';
  }

  @override
  String upToDate(Object date) {
    return 'Up to date (inclusive): $date';
  }

  @override
  String get onlyFutureWorkouts => 'Only future workouts';

  @override
  String dateNotEarlierThan(Object date) {
    return 'Date not earlier than $date';
  }

  @override
  String dateNotLaterThan(Object date) {
    return 'Date not later than $date';
  }

  @override
  String get clampNonNegative => 'Do not allow negative values';

  @override
  String replaceExerciseTo(Object name, Object id) {
    return 'Replace exercise to $name (ID $id)';
  }

  @override
  String renameExerciseTo(Object name) {
    return 'Rename exercise to \"$name\"';
  }

  @override
  String addNewExercises(Object count) {
    return 'Add new exercises: $count';
  }

  @override
  String setIntensity(Object value) {
    return 'Set intensity = $value';
  }

  @override
  String increaseIntensityBy(Object value) {
    return 'Increase intensity by $value';
  }

  @override
  String decreaseIntensityBy(Object value) {
    return 'Decrease intensity by $value';
  }

  @override
  String setVolume(Object value) {
    return 'Set reps = $value';
  }

  @override
  String increaseVolumeBy(Object value) {
    return 'Increase reps by $value';
  }

  @override
  String decreaseVolumeBy(Object value) {
    return 'Decrease reps by $value';
  }

  @override
  String setWeight(Object value) {
    return 'Set weight = $value kg';
  }

  @override
  String increaseWeightBy(Object value) {
    return 'Increase weight by $value kg';
  }

  @override
  String decreaseWeightBy(Object value) {
    return 'Decrease weight by $value kg';
  }

  @override
  String setEffort(Object value) {
    return 'Set RPE = $value';
  }

  @override
  String increaseEffortBy(Object value) {
    return 'Increase RPE by $value';
  }

  @override
  String decreaseEffortBy(Object value) {
    return 'Decrease RPE by $value';
  }

  @override
  String get massEditPreviewTitle => 'Active plan mass edit preview';

  @override
  String get massEditAppliedTitle => 'Active plan changes applied';

  @override
  String get scheduleShiftPreviewTitle => 'Active plan schedule shift preview';

  @override
  String get scheduleShiftTitle => 'Active plan schedule shift applied';

  @override
  String get shiftParameters => 'Shift parameters';

  @override
  String get modeChangeIntervals => 'Mode: change intervals between workouts';

  @override
  String get modeScheduleShift => 'Mode: schedule shift';

  @override
  String get macroActionByPercent => 'By Percent';

  @override
  String get macroActionToTarget => 'To Target (RPE)';

  @override
  String get macroActionByValue => 'By Value';

  @override
  String get macroActionByTemplate => 'By Template';

  @override
  String get macroActionByExisting => 'By Existing (ID)';

  @override
  String get macroActionCreateManual => 'Create Manually';

  @override
  String get macroActionHintPercent => 'percent, e.g. -5 or 2.5';

  @override
  String get macroActionHintReps => 'reps delta, e.g. +1 or -1';

  @override
  String get macroActionHintTargetRpe => 'target RPE, e.g. 8';

  @override
  String get macroActionHintSets => '±N sets, e.g. 1 or -2';

  @override
  String get macroActionHintGeneric => 'value';

  @override
  String get macroActionAdjustLoad => 'Adjust Load';

  @override
  String get macroActionAdjustReps => 'Adjust Reps';

  @override
  String get macroActionAdjustSets => 'Adjust Sets';

  @override
  String get macroActionInjectMesocycle => 'Inject Mesocycle';

  @override
  String get macroActionTypeLabel => 'Action Type';

  @override
  String get macroActionModeLabel => 'Mode';

  @override
  String get macroActionValueLabel => 'Value';

  @override
  String get macroActionNoTemplates => 'No mesocycle templates';

  @override
  String get macroActionTemplateLabel => 'Mesocycle Template';

  @override
  String macroActionLoadTemplatesError(Object error) {
    return 'Error loading templates: $error';
  }

  @override
  String macroActionMesoLabel(Object index) {
    return 'Mesocycle $index';
  }

  @override
  String get macroActionChooseMeso => 'Choose Mesocycle';

  @override
  String get macroActionOtherId => 'Other (enter ID)';

  @override
  String get macroActionExistingIdLabel => 'Existing mesocycle ID';

  @override
  String get macroActionEnterNumber => 'Enter a number';

  @override
  String get macroActionDurationWeeks => 'Duration (weeks)';

  @override
  String get macroActionDaysInMicro => 'Days in microcycle';

  @override
  String macroActionDayLabel(Object index, Object type) {
    return 'Day $index: $type';
  }

  @override
  String get macroActionRest => 'rest';

  @override
  String get macroActionWork => 'workout';

  @override
  String get macroActionFocusTags => 'Focus Tags';

  @override
  String get macroActionPlacement => 'Placement';

  @override
  String get macroActionAppendEnd => 'Append to end';

  @override
  String get macroActionInsertAfterWorkout => 'After workout';

  @override
  String get macroActionInsertAfterMeso => 'After mesocycle';

  @override
  String get macroActionSelectAnchorWorkout => 'Select anchor workout';

  @override
  String get macroActionPickWorkout => 'Pick workout';

  @override
  String get macroActionNotSelected => 'Not selected';

  @override
  String macroActionAfterAnchor(Object name) {
    return 'After: $name';
  }

  @override
  String get macroActionNoMesoInPlan => 'No mesocycles in plan';

  @override
  String get macroActionMesoIndexLabel => 'Mesocycle: ';

  @override
  String get macroActionConflicts => 'Conflicts';

  @override
  String get macroActionReplacePlanned => 'Replace planned';

  @override
  String get macroActionShiftForward => 'Shift forward';

  @override
  String get macroActionSkipConflict => 'Skip on conflict';

  @override
  String get macroActionTarget => 'Target';

  @override
  String get macroActionTargetHelp =>
      'If target is not specified — action applies to all exercises of selected workouts.';

  @override
  String get macroConditionGreater => 'greater >';

  @override
  String get macroConditionLess => 'less <';

  @override
  String get macroConditionEqual => 'equal =';

  @override
  String get macroConditionNotEqual => 'not equal ≠';

  @override
  String get macroConditionInRange => 'in range';

  @override
  String get macroConditionNotInRange => 'not in range';

  @override
  String get macroConditionStagnates => 'stagnation for N windows';

  @override
  String get macroConditionDeviates => 'deviation from average';

  @override
  String get macroConditionHoldsForWorkouts => 'holds for N workouts in a row';

  @override
  String get macroConditionHoldsForSets =>
      'holds for N sets in a row (within workout)';

  @override
  String get macroConditionOperatorLabel => 'Operator';

  @override
  String get macroConditionRangeFrom => 'from';

  @override
  String get macroConditionNumberHint => 'number';

  @override
  String get macroConditionRangeTo => 'to';

  @override
  String get macroConditionWindowCount => 'n (windows)';

  @override
  String get macroConditionWindowCountHint => 'integer, e.g. 5';

  @override
  String get macroConditionEpsilonPercent => 'epsilon_percent (threshold, %)';

  @override
  String get macroConditionValuePercent => 'value_percent (deviation, %)';

  @override
  String get macroConditionPositive => 'positive';

  @override
  String get macroConditionNegative => 'negative';

  @override
  String get macroConditionDirection => 'direction (optional)';

  @override
  String get macroConditionGreaterEqual => 'greater or equal ≥';

  @override
  String get macroConditionLessEqual => 'less or equal ≤';

  @override
  String get macroConditionRelationLabel => 'relation';

  @override
  String get macroConditionWorkoutCount => 'n (workouts)';

  @override
  String get macroConditionWorkoutCountHint => 'integer, e.g. 3';

  @override
  String get macroConditionDeltaHint => 'delta, e.g. -2 for reps';

  @override
  String get macroConditionSetCount => 'n (sets in a row)';

  @override
  String get macroConditionSetCountHint => 'integer, e.g. 12';

  @override
  String get macroConditionValueLabel => 'value';

  @override
  String get macroDurationNextNWorkouts => 'Next N workouts';

  @override
  String get macroDurationUntilLastWorkout => 'Until last workout';

  @override
  String get macroDurationUntilEndOfMeso => 'Until end of mesocycle';

  @override
  String get macroDurationUntilEndOfMicro => 'Until end of microcycle';

  @override
  String get macroDurationUntilWorkoutX => 'Until workout X';

  @override
  String get macroDurationScopeLabel => 'Scope';

  @override
  String get macroDurationCountLabel => 'Count';

  @override
  String get macroTargetBy => 'Target by:';

  @override
  String get macroTargetTags => 'Tags';

  @override
  String get macroTargetIds => 'IDs';

  @override
  String get macroTargetIdsLabel => 'exercise_ids (CSV)';

  @override
  String get macroTriggerChooseExercises => 'Choose exercises';

  @override
  String get macroTriggerMetricReadiness => 'Readiness (workout)';

  @override
  String get macroTriggerMetricRpeSession => 'Session RPE';

  @override
  String get macroTriggerMetricTotalReps => 'Total Reps';

  @override
  String get macroTriggerMetricE1rm => 'e1RM estimate';

  @override
  String get macroTriggerMetricPerformanceTrend => 'Performance Trend';

  @override
  String get macroTriggerMetricRpeDelta => 'RPE Delta from Plan';

  @override
  String get macroTriggerMetricRepsDelta => 'Reps Delta from Plan';

  @override
  String get macroTriggerMetricLabel => 'Trigger Metric';

  @override
  String get macroWorkoutPickerTitle => 'Choose workout';

  @override
  String get macroWorkoutPickerNoWorkouts => 'No workouts in active plan';

  @override
  String get macroWorkoutPickerNoWorkoutsOnDate => 'No workouts on this date';

  @override
  String get macroWorkoutPickerOrChooseFromList => 'Or choose from list';

  @override
  String get macroWorkoutPickerListButton => 'List';

  @override
  String get macroWorkoutPickerWorkoutsOnDate => 'Workouts on this date';

  @override
  String get macroWorkoutPickerOrSelectFromList => 'Or select from list';

  @override
  String get macroWorkoutPickerList => 'List';

  @override
  String analyticsPlanTitle(Object planName) {
    return 'Plan analytics $planName';
  }

  @override
  String get errorLoadingActivePlan => 'Failed to load active plan';

  @override
  String get selectTwoMetrics => 'Select two metrics';

  @override
  String get activePlanNotFound => 'Active plan not found';

  @override
  String get errorLoadingData => 'Error loading data';

  @override
  String get axisX => 'X axis';

  @override
  String get axisY => 'Y axis';

  @override
  String get showChart => 'Show chart';

  @override
  String get selectRangeAndMetrics => 'Select a range and metrics';

  @override
  String get noDataForSelectedMetrics => 'No data for selected metrics';

  @override
  String get metricVolumeKg => 'Volume (kg)';

  @override
  String get metricEffortRpe => 'Effort (RPE)';

  @override
  String get metricKpsh => 'KPSH';

  @override
  String get metricReps => 'Reps';

  @override
  String get metricOneRm => '1RM';

  @override
  String get language => 'Language';

  @override
  String get languageSystem => 'System';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageUkrainian => 'Ukrainian';

  @override
  String get accountTitle => 'Account';

  @override
  String get editProfileTitle => 'Edit profile';

  @override
  String get displayName => 'Display name';

  @override
  String get bio => 'Bio';

  @override
  String get bodyweightKg => 'Bodyweight (kg)';

  @override
  String get heightCm => 'Height (cm)';

  @override
  String get age => 'Age';

  @override
  String get trainingYears => 'Training years';

  @override
  String get publicProfile => 'Public profile';

  @override
  String get units => 'Units';

  @override
  String get unitsMetric => 'Metric';

  @override
  String get unitsImperial => 'Imperial';

  @override
  String get timezone => 'Timezone';

  @override
  String get notifications => 'Notifications';

  @override
  String get save => 'Save';

  @override
  String get profileUpdated => 'Profile updated';

  @override
  String get failedToUpdateProfile => 'Failed to update profile';

  @override
  String get editProfileButton => 'Edit profile';

  @override
  String get coachingSettingsButton => 'Coaching settings';

  @override
  String get coachingTitle => 'Coaching';

  @override
  String get coachingAcceptingNewClients => 'Accepting new clients';

  @override
  String get coachingNotAccepting => 'Not accepting';

  @override
  String get coachingDisabled => 'Coaching disabled';

  @override
  String get coachingDisabledDescription =>
      'This user has not enabled coaching options.';

  @override
  String get coachingSpecializations => 'Specializations';

  @override
  String get coachingLanguages => 'Languages';

  @override
  String get coachingExperience => 'Experience';

  @override
  String get coachingTimezone => 'Timezone';

  @override
  String get coachingRate => 'Rate';

  @override
  String get coachingCustomRate => 'Custom rate';

  @override
  String get requestCoaching => 'Request coaching';

  @override
  String get statsTotalWorkouts => 'Total Workouts';

  @override
  String get statsVolumeKg => 'Volume (kg)';

  @override
  String get statsActiveDays => 'Active Days';

  @override
  String get activityTitle => 'Activity';

  @override
  String lastWeeks(Object weeks) {
    return 'Last $weeks weeks';
  }

  @override
  String maxKgPerDay(Object value) {
    return 'Max: $value kg/day';
  }

  @override
  String sessionsCount(Object count) {
    return '$count session(s)';
  }

  @override
  String get noActivity => 'No activity';

  @override
  String get less => 'Less';

  @override
  String get more => 'More';

  @override
  String get completedWorkoutsTitle => 'Completed Workouts';

  @override
  String get noCompletedWorkoutsYet => 'No completed workouts yet';

  @override
  String get exerciseFormTitleAdd => 'Add exercise';

  @override
  String get exerciseFormExerciseNameLabel => 'Exercise name';

  @override
  String get exerciseFormPleaseEnterName => 'Please enter a name';

  @override
  String get exerciseFormMuscleGroupLabel => 'Muscle group';

  @override
  String get exerciseFormLoading => 'Loading...';

  @override
  String get exerciseFormSelectGroup => 'Select group';

  @override
  String get exerciseFormLoadingGroups => 'Loading groups...';

  @override
  String get exerciseFormPleaseSelectMuscleGroup =>
      'Please select a muscle group';

  @override
  String get exerciseFormProgressionTemplateOptional =>
      'Progression template (optional)';

  @override
  String get exerciseFormSelectTemplate => 'Select template';

  @override
  String get exerciseFormNoTemplate => 'No template';

  @override
  String get exerciseFormSetsTitle => 'Sets';

  @override
  String get exerciseFormAddSet => 'Add set';

  @override
  String get exerciseFormSaveExercise => 'Save exercise';

  @override
  String get exerciseFormWeightKg => 'Weight (kg)';

  @override
  String get exerciseFormReps => 'Reps';

  @override
  String get exerciseFormRequired => 'Required';

  @override
  String exerciseFormFailedToLoadData(Object error) {
    return 'Failed to load data: $error';
  }

  @override
  String exerciseFormErrorSaving(Object error) {
    return 'Error saving: $error';
  }

  @override
  String get exerciseDefinitionIdRequired =>
      'Exercise definition id is required';

  @override
  String get exerciseFormDefaultReps => '5';

  @override
  String get exerciseFormDefaultWeight => '0';

  @override
  String get exerciseListTitle => 'Exercises';

  @override
  String get exerciseListAddExerciseTitle => 'Add exercise';

  @override
  String get exerciseListNameLabel => 'Name';

  @override
  String get exerciseListMuscleGroupLabel => 'Muscle group';

  @override
  String get exerciseListEquipmentLabel => 'Equipment';

  @override
  String get exerciseListLoading => 'Loading...';

  @override
  String get exerciseListSelectGroup => 'Select group';

  @override
  String get exerciseListLoadingGroups => 'Loading groups...';

  @override
  String get exerciseListSelectMuscleGroupValidator => 'Select a muscle group';

  @override
  String get exerciseListEnterExerciseName => 'Enter exercise name';

  @override
  String get exerciseListSelectMuscleGroupSnack => 'Select a muscle group';

  @override
  String exerciseListErrorLoadingMuscleGroups(Object error) {
    return 'Failed to load muscle groups: $error';
  }

  @override
  String exerciseListErrorGeneric(Object error) {
    return 'Error: $error';
  }

  @override
  String get exerciseListEmpty => 'No exercises. Add a new one!';

  @override
  String exerciseListMuscleGroupPrefix(Object value) {
    return 'Muscle group: $value';
  }

  @override
  String exerciseListEquipmentPrefix(Object value) {
    return 'Equipment: $value';
  }

  @override
  String get exerciseListDeleteExerciseTitle => 'Delete exercise?';

  @override
  String get exerciseListDeleteExerciseBody => 'This action cannot be undone.';

  @override
  String get exerciseListDelete => 'Delete';

  @override
  String exerciseListErrorDeleting(Object error) {
    return 'Failed to delete: $error';
  }

  @override
  String get userMaxTitle => 'Add max';

  @override
  String get userMaxExerciseLabel => 'Exercise';

  @override
  String get userMaxSelectExerciseValidator => 'Select an exercise';

  @override
  String get userMaxWeightKgLabel => 'Weight (kg)';

  @override
  String get userMaxWeightGtZeroValidator => 'Enter weight > 0';

  @override
  String get userMaxRepsLabel => 'Reps';

  @override
  String get userMaxRepsGtZeroValidator => 'Enter reps > 0';

  @override
  String get userMaxRepsMax12Validator => 'Maximum 12 reps';

  @override
  String get userMaxFillAllFieldsSnack =>
      'Fill all fields and select an exercise';

  @override
  String get userMaxSaving => 'Saving...';

  @override
  String get userMaxSave => 'Save max';

  @override
  String userMaxFailedToSave(Object error) {
    return 'Failed to save max: $error';
  }

  @override
  String get yes => 'Yes';

  @override
  String get no => 'No';

  @override
  String get planDraftMicrocycle => 'Microcycle';

  @override
  String get planDraftMesocycle => 'Mesocycle';

  @override
  String massEditToolWorkoutsMatched(Object count) {
    return 'Workouts matched: $count';
  }

  @override
  String massEditToolSetsModified(Object count) {
    return 'Sets modified: $count';
  }

  @override
  String massEditToolSetsToBeModified(Object count) {
    return 'Sets to be modified: $count';
  }

  @override
  String get workoutDetailMacrosChangesFoundTitle => 'Macro changes found';

  @override
  String workoutDetailMacrosChangesFoundBody(
    Object injectCount,
    Object hasPatches,
  ) {
    return 'Mesocycle injections: $injectCount\nWorkout patches: $hasPatches';
  }

  @override
  String get workoutDetailMacrosApplied => 'Macros applied';

  @override
  String workoutDetailFailedToApplyMacros(Object error) {
    return 'Failed to apply macros: $error';
  }

  @override
  String get workoutDetailFailedToRefreshWorkoutBeforeApplyingReadiness =>
      'Failed to refresh workout before applying readiness';

  @override
  String get workoutDetailWorkoutNotReadyMissingIds =>
      'Workout is not ready for set updates (missing ids)';

  @override
  String get workoutDetailIncreaseTooltip => 'Increase';

  @override
  String get workoutDetailSessionActive => 'Active session';

  @override
  String get workoutDetailSessionNone => 'No active session';

  @override
  String get workoutDetailSelectSetTypeTitle => 'Select set type';

  @override
  String get workoutDetailSetTypeNormal => 'Normal set';

  @override
  String get workoutDetailSetTypeDrop => 'Drop set';

  @override
  String get workoutDetailSetTypeCluster => 'Cluster set';

  @override
  String get workoutDetailSetTypeRestPause => 'Rest-pause set';

  @override
  String workoutDetailFailedToUpdateSetType(Object error) {
    return 'Failed to update set type: $error';
  }

  @override
  String get activePlanTitle => 'Active plan';

  @override
  String activePlanFailedToLoad(Object error) {
    return 'Failed to load active plan: $error';
  }

  @override
  String get activePlanNone => 'No active plan';

  @override
  String get activePlanAiMassEditTitle => 'AI mass edit (chat)';

  @override
  String get activePlanAiMassEditHint =>
      'For example: Increase RPE by 1 and add 1 set to all bench presses on Mondays';

  @override
  String get activePlanAiMassEditSend => 'Send';

  @override
  String activePlanAiMassEditStarted(Object taskId) {
    return 'AI mass edit started (task: $taskId)';
  }

  @override
  String activePlanAiMassEditFailedToSend(Object error) {
    return 'Failed to send AI mass edit command: $error';
  }

  @override
  String activePlanMassEditTitle(Object end, Object start) {
    return 'Mass edit (from $start to $end)';
  }

  @override
  String get activePlanRangeLabel => 'Range:';

  @override
  String get activePlanRangeFutureFromWeek => 'Future from week';

  @override
  String get activePlanRangeByMesoMicro => 'By meso/micro';

  @override
  String get activePlanIntensityLabel => 'Intensity %';

  @override
  String get activePlanRpeLabel => 'RPE';

  @override
  String get activePlanRepsLabel => 'Reps';

  @override
  String get activePlanModeSet => 'Set';

  @override
  String get activePlanModeOffset => 'Offset';

  @override
  String get activePlanModeScale => 'Scale';

  @override
  String get activePlanHintEg75 => 'e.g. 75';

  @override
  String get activePlanHintPercentOffset => '+/- % (e.g. -2)';

  @override
  String get activePlanHintFactor => '× factor (e.g. 1.05)';

  @override
  String get activePlanHintEg8 => 'e.g. 8';

  @override
  String get activePlanHintEg5 => 'e.g. 5';

  @override
  String get activePlanHintRepsOffset => '+/- reps (e.g. +1)';

  @override
  String get activePlanHintFactorReps => '× factor (e.g. 0.9)';

  @override
  String get activePlanRecalcTargetLabel => 'Recalc target:';

  @override
  String get activePlanRecalcTargetAuto => 'Auto';

  @override
  String get activePlanRecalcTargetReps => 'Reps';

  @override
  String get activePlanRecalcTargetRpe => 'RPE';

  @override
  String get activePlanRecalcTargetIntensity => 'Intensity';

  @override
  String get activePlanValidatorLabel => 'Validator:';

  @override
  String get activePlanValidatorNone => 'None';

  @override
  String get activePlanValidatorFixReps => 'Fix reps';

  @override
  String get activePlanValidatorFixIntensity => 'Fix intensity';

  @override
  String get activePlanSelectAtLeastOneExercise =>
      'Select at least one exercise';

  @override
  String get activePlanSelectAtLeastOneParameter =>
      'Select at least one parameter';

  @override
  String get activePlanPlanCancelled => 'Plan cancelled';

  @override
  String get activePlanFailedToCancelPlan => 'Failed to cancel plan';

  @override
  String activePlanExerciseIdFallback(Object id) {
    return 'Exercise $id';
  }

  @override
  String activePlanReplaceTitle(Object end, Object start) {
    return 'Replace exercises (from $start to $end)';
  }

  @override
  String get activePlanSelectSourceExercises => 'Select source exercises:';

  @override
  String get activePlanSelectTargetExercise => 'Select target exercise';

  @override
  String get activePlanPreserveIntensity => 'Preserve intensity via 1RM';

  @override
  String get activePlanSelectAtLeastOneSourceExercise =>
      'Select at least one source exercise';

  @override
  String get activePlanSelectTargetExerciseSnack => 'Select a target exercise';

  @override
  String get activePlanPreviewReplacementTitle => 'Preview replacement';

  @override
  String activePlanPreviewTarget(Object name) {
    return 'Target: $name';
  }

  @override
  String activePlanPreviewExercisesToReplace(Object count) {
    return 'Exercises to replace: $count';
  }

  @override
  String activePlanPreviewSetsAffected(Object count) {
    return 'Sets affected: $count';
  }

  @override
  String get activePlanDropoutReasonNotEnjoyable => 'Not enjoyable';

  @override
  String get activePlanDropoutReasonOther => 'Other / prefer not to say';

  @override
  String get activePlanDropoutSkip => 'Skip';

  @override
  String get activePlanDropoutConfirm => 'Confirm';

  @override
  String activePlanUpdatedSets(Object count) {
    return 'Updated $count sets';
  }

  @override
  String activePlanFailed(Object error) {
    return 'Failed: $error';
  }

  @override
  String get activePlanReplacementCancelledOneRmRequired =>
      'Replacement cancelled: 1RM required';

  @override
  String activePlanEnterOneRmTitle(Object exerciseName) {
    return 'Enter 1RM for $exerciseName';
  }

  @override
  String get activePlanOneRmLabel => '1RM (kg)';

  @override
  String get activePlanOneRmHint => 'e.g. 120';

  @override
  String get activePlanOneRmHelp => 'Enter your current max for this exercise.';

  @override
  String get activePlanEnterNumberGtZero => 'Enter a number > 0';

  @override
  String activePlanShiftedWorkouts(Object count, Object days) {
    return 'Shifted $count workouts by +$days day(s)';
  }

  @override
  String activePlanShiftFailed(Object error) {
    return 'Shift failed: $error';
  }

  @override
  String get activePlanKeep => 'Keep';

  @override
  String get activePlanCancelPlan => 'Cancel plan';

  @override
  String get activePlanWhyCancelling => 'Why are you cancelling?';

  @override
  String get activePlanDropoutReasonNotEnoughTime => 'Not enough time';

  @override
  String get activePlanDropoutReasonInjury => 'Injury / pain';

  @override
  String get activePlanDropoutReasonTooHard => 'Too hard';

  @override
  String activePlanReplaceSuccess(Object exercises, Object sets) {
    return 'Replaced $exercises exercises, updated $sets sets';
  }

  @override
  String activePlanReplaceFailed(Object error) {
    return 'Replace failed: $error';
  }

  @override
  String get activePlanCancelConfirmTitle => 'Cancel active plan?';

  @override
  String get activePlanCancelConfirmBody =>
      'This will stop tracking this applied plan. Existing workouts will remain.';

  @override
  String activePlanDroppedPrefix(Object reason, Object date) {
    return 'Dropped: $reason$date';
  }

  @override
  String activePlanAdherencePercent(Object value) {
    return 'Adherence: $value%';
  }

  @override
  String activePlanFailedToLoadAnalytics(Object error) {
    return 'Failed to load analytics: $error';
  }

  @override
  String get activePlanStatusActive => 'Active';

  @override
  String get coachRelationshipsTitle => 'Coach ↔ Athletes';

  @override
  String get coachRelationshipsFilterAll => 'All';

  @override
  String get coachRelationshipsFilterPending => 'Pending';

  @override
  String get coachRelationshipsFilterActive => 'Active';

  @override
  String get coachRelationshipsFilterPaused => 'Paused';

  @override
  String get coachRelationshipsFilterEnded => 'Ended';

  @override
  String coachRelationshipsError(Object error) {
    return 'Error: $error';
  }

  @override
  String get coachRelationshipsEmpty => 'No relationships yet';

  @override
  String coachRelationshipsAthletePrefix(Object name) {
    return 'Athlete: $name';
  }

  @override
  String coachRelationshipsStatusPrefix(Object status) {
    return 'Status: $status';
  }

  @override
  String coachRelationshipsNotePrefix(Object note) {
    return 'Note: $note';
  }

  @override
  String coachRelationshipsChannelPrefix(Object channel) {
    return 'Channel: $channel';
  }

  @override
  String get coachRelationshipsChannelNotCreated => 'not created';

  @override
  String coachRelationshipsSessions12w(Object count) {
    return 'Sessions (12w): $count';
  }

  @override
  String coachRelationshipsLastWorkout(Object date, Object suffix) {
    return 'Last workout: $date$suffix';
  }

  @override
  String get coachRelationshipsLastWorkoutNA => 'n/a';

  @override
  String coachRelationshipsDaysAgoSuffix(Object days) {
    return ' · ${days}d ago';
  }

  @override
  String get coachRelationshipsLoadingTrainingSummary =>
      'Loading training summary...';

  @override
  String get coachRelationshipsRequestAccepted => 'Request accepted';

  @override
  String coachRelationshipsFailedToAccept(Object error) {
    return 'Failed to accept: $error';
  }

  @override
  String get coachRelationshipsAccept => 'Accept';

  @override
  String get coachRelationshipsDecline => 'Decline';

  @override
  String get coachRelationshipsDeclineRequestTitle => 'Decline request';

  @override
  String get coachRelationshipsDeclineReasonHint => 'Reason (optional)';

  @override
  String get coachRelationshipsRequestDeclined => 'Request declined';

  @override
  String coachRelationshipsFailedToDecline(Object error) {
    return 'Failed to decline: $error';
  }

  @override
  String get coachRelationshipsCoachingPaused => 'Coaching paused';

  @override
  String coachRelationshipsFailedToPause(Object error) {
    return 'Failed to pause: $error';
  }

  @override
  String get coachRelationshipsCoachingResumed => 'Coaching resumed';

  @override
  String coachRelationshipsFailedToResume(Object error) {
    return 'Failed to resume: $error';
  }

  @override
  String get coachRelationshipsChatTooltip => 'Chat';

  @override
  String get coachRelationshipsAnalyticsTooltip => 'Analytics';

  @override
  String get coachRelationshipsNudgeTooltip => 'Nudge';

  @override
  String get coachRelationshipsPauseCoaching => 'Pause coaching';

  @override
  String get coachRelationshipsResumeCoaching => 'Resume coaching';

  @override
  String get coachRelationshipsEndCoaching => 'End coaching';

  @override
  String get coachRelationshipsCoachingEnded => 'Coaching ended';

  @override
  String coachRelationshipsFailedToEnd(Object error) {
    return 'Failed to end: $error';
  }

  @override
  String get coachRelationshipsChatChannelNotAvailable =>
      'Chat channel is not available';

  @override
  String get coachRelationshipsNudgeSent => 'Nudge sent';

  @override
  String coachRelationshipsFailedToSendNudge(Object error) {
    return 'Failed to send nudge: $error';
  }

  @override
  String coachRelationshipsNudgeMessageWithDays(Object athleteId, Object days) {
    return 'Hey $athleteId, it\'s been $days day(s) since your last workout. Let\'s plan the next session!';
  }

  @override
  String coachRelationshipsNudgeMessageNoDays(Object athleteId) {
    return 'Hey $athleteId, let\'s schedule our next workout soon!';
  }

  @override
  String coachRelationshipsVolumeAndPlan(Object volume, Object plan) {
    return 'Volume: $volume | Active plan: $plan';
  }

  @override
  String get coachRelationshipsVolumeDash => '-';

  @override
  String get coachRelationshipsMenuAll => 'All';

  @override
  String get coachRelationshipsMenuPending => 'Pending';

  @override
  String get coachRelationshipsMenuActive => 'Active';

  @override
  String get coachRelationshipsMenuPaused => 'Paused';

  @override
  String get coachRelationshipsMenuEnded => 'Ended';

  @override
  String get coachRelationshipsMenuPauseCoaching => 'Pause coaching';

  @override
  String get coachRelationshipsMenuResumeCoaching => 'Resume coaching';

  @override
  String get coachRelationshipsMenuEndCoaching => 'End coaching';

  @override
  String planEditorTitle(Object name) {
    return 'Editor: $name';
  }

  @override
  String get planEditorMacros => 'Macros';

  @override
  String get planEditorNoPlanId => 'No plan ID';

  @override
  String planEditorBulk(Object count) {
    return 'Bulk ($count)';
  }

  @override
  String get planEditorReplace => 'Replace';

  @override
  String get planEditorSearchHint => 'Search exercise by name...';

  @override
  String get planEditorMesocycles => 'Mesocycles';

  @override
  String get planEditorDayFilterLabel => 'Filter: day (number, optional)';

  @override
  String get planEditorSelectTargetError => 'Choose target exercise';

  @override
  String get planEditorSelectSourceError =>
      'Select at least one exercise to replace';

  @override
  String get planEditorDeleteMesocycleTitle => 'Delete mesocycle';

  @override
  String planEditorDeleteMesocycleBody(Object name) {
    return 'Are you sure you want to delete mesocycle \"$name\" and all its microcycles?';
  }

  @override
  String get planEditorDeleteMesocycle => 'Delete';

  @override
  String get planEditorMesocycleDeleted => 'Mesocycle deleted';

  @override
  String planEditorDeleteFailed(Object error) {
    return 'Delete failed: $error';
  }

  @override
  String get planEditorDeleteMesocycleTooltip => 'Delete mesocycle';

  @override
  String planEditorMicroDays(Object count) {
    return 'Days: $count';
  }

  @override
  String planEditorExerciseIdFallback(Object id) {
    return 'Exercise $id';
  }

  @override
  String get planEditorChangesSaved => 'Changes saved';

  @override
  String get planEditorMicrocycleDeleted => 'Microcycle deleted';

  @override
  String get planEditorDeleteMicrocycleTitle => 'Delete microcycle';

  @override
  String planEditorDeleteMicrocycleBody(Object name) {
    return 'Are you sure you want to delete microcycle \"$name\"?';
  }

  @override
  String get planEditorDeleteMicrocycleTooltip => 'Delete microcycle';

  @override
  String get planEditorMassEditTitle => 'Mass edits: selected microcycles';

  @override
  String planEditorSkipNoRights(Object count) {
    return 'Skipped $count microcycles without access rights';
  }

  @override
  String planEditorRightsCheckUnavailableApplyAll(Object error) {
    return 'Rights check unavailable, applying to all selected: $error';
  }

  @override
  String planEditorMassEditsResult(Object success, Object failed) {
    return 'Mass edits: success $success, failed $failed';
  }

  @override
  String coachAthletePlanTitleFallback(Object id) {
    return 'Athlete $id';
  }

  @override
  String coachAthletePlanLoadAnalyticsError(Object error) {
    return 'Failed to load plan analytics: $error';
  }

  @override
  String get coachAthletePlanMetricSets => 'Sets';

  @override
  String get coachAthletePlanMetricReps => 'Reps';

  @override
  String get coachAthletePlanMetricIntensity => 'Intensity (avg)';

  @override
  String get coachAthletePlanMetricEffort => 'Effort (RPE avg)';

  @override
  String get coachAthletePlanAxisX => 'Axis X';

  @override
  String get coachAthletePlanAxisY => 'Axis Y';

  @override
  String get coachAthletePlanNoAnalytics => 'No analytics for this plan';

  @override
  String coachAthletePlanSessionsCompleted(Object completed, Object planned) {
    return '$completed / $planned sessions';
  }

  @override
  String coachAthletePlanPeriod(Object start, Object end) {
    return 'Period: $start – $end';
  }

  @override
  String coachAthletePlanNotes(Object notes) {
    return 'Notes: $notes';
  }

  @override
  String get coachAthletePlanMassEditTooltip => 'Mass edit athlete plan';

  @override
  String get coachAthletePlanMassEditMenu => 'Mass edit (notes/day)';

  @override
  String get coachAthletePlanWorkoutNotesHint => 'Enter note for athlete';

  @override
  String get coachAthletePlanWorkoutRescheduled => 'Workout rescheduled';

  @override
  String get coachAthletePlanWorkoutNotesUpdated => 'Note updated';

  @override
  String get coachAthletePlanNoExercises => 'No exercise data in this workout';

  @override
  String get coachAthletePlanEditExercise => 'Edit exercise';

  @override
  String get coachAthletePlanAddExercise => 'Add exercise';

  @override
  String get coachAthletePlanDeleteExerciseConfirmTitle => 'Delete exercise?';

  @override
  String coachAthletePlanDeleteExerciseConfirmBody(Object name) {
    return 'Are you sure you want to delete $name from workout?';
  }

  @override
  String get coachAthletePlanExerciseDeleted => 'Exercise deleted';

  @override
  String coachAthletePlanDeleteError(Object error) {
    return 'Error while deleting: $error';
  }

  @override
  String coachAthletePlanOrder(Object order) {
    return 'Order: $order';
  }

  @override
  String coachAthletePlanSets(Object count) {
    return 'Sets: $count';
  }

  @override
  String get coachAthletePlanNoSets => 'No sets';

  @override
  String get coachAthletePlanAddSet => 'Add set';

  @override
  String get coachAthletePlanMassEditErrorNoWorkouts =>
      'No workouts for mass edits';

  @override
  String get coachAthletePlanMassEditErrorNoWorkoutsOnDay =>
      'No workouts on selected day';

  @override
  String get coachAthletePlanMassEditUpdateWorkouts => 'Update workout notes';

  @override
  String get coachAthletePlanMassEditUpdateExercises => 'Update exercise notes';

  @override
  String get coachAthletePlanMassEditNoChanges => 'No changes to apply';

  @override
  String get coachAthletePlanMassEditApplied =>
      'Mass edit applied for selected day';

  @override
  String get coachAthletePlanMassEditWorkoutHint =>
      'New note for all workouts on this day';

  @override
  String get planEditorMassReplaceTitle => 'Mass exercise replacement';

  @override
  String get planEditorChooseTarget => 'Choose target exercise';

  @override
  String planEditorTargetPrefix(Object name) {
    return 'Target: $name';
  }

  @override
  String get planEditorSelectAll => 'Select all';

  @override
  String get planEditorClearAll => 'Clear all';

  @override
  String planEditorOccurrences(Object count) {
    return 'Occurrences: $count';
  }

  @override
  String get planEditorPreview => 'Preview';

  @override
  String planEditorRightsCheckUnavailable(Object error) {
    return 'Rights check unavailable, continuing without it: $error';
  }

  @override
  String get planEditorNoAccessibleMicrocycles =>
      'No accessible microcycles for replacement';

  @override
  String get planEditorNoExercisesToReplace => 'No exercises to replace';

  @override
  String get planEditorPreviewReplaceTitle => 'Replacement preview';

  @override
  String planEditorPreviewTarget(Object name) {
    return 'Target: $name';
  }

  @override
  String planEditorPreviewTotals(Object exercises, Object sets) {
    return 'Exercises to replace: $exercises, sets affected: $sets';
  }

  @override
  String planEditorPreviewMicroStats(Object ex, Object sets) {
    return 'Exercises: $ex · Sets: $sets';
  }

  @override
  String planEditorApplyReplaceResult(Object success, Object failed) {
    return 'Replacement: success $success, failed $failed';
  }

  @override
  String get workoutListTitle => 'Workouts';

  @override
  String get workoutListAddWorkout => 'Add Workout';

  @override
  String get workoutListWorkoutName => 'Workout Name';

  @override
  String get workoutListEnterNameError => 'Please enter a workout name';

  @override
  String workoutListCreateError(Object error) {
    return 'Error creating workout: $error';
  }

  @override
  String get workoutListNextWorkout => 'Next Workout';

  @override
  String get workoutListEmpty => 'No workouts in this progression';

  @override
  String exerciseCount(num count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.compact(
      locale: localeName,
    );
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString exercises',
      one: '1 exercise',
    );
    return '$_temp0';
  }

  @override
  String get nutritionSessionsTitle => 'Nutrition Sessions';

  @override
  String get nutritionSessionsEmpty => 'No nutrition sessions yet';

  @override
  String get nutritionSessionsEmptyDesc =>
      'Start tracking your nutrition by creating your first session';

  @override
  String nutritionSessionTitle(Object id) {
    return 'Session $id';
  }

  @override
  String userIdLabel(Object id) {
    return 'User ID: $id';
  }

  @override
  String entriesCount(num count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.compact(
      locale: localeName,
    );
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString entries',
      one: '1 entry',
    );
    return '$_temp0';
  }

  @override
  String get nutritionEntriesLabel => 'Entries';

  @override
  String get nutritionNoEntries => 'No entries';

  @override
  String get dateLabel => 'Date';

  @override
  String get workoutIdLabel => 'Workout ID';

  @override
  String get appliedPlanWorkoutIdLabel => 'Applied Plan Workout ID';

  @override
  String get typeLabel => 'Type';

  @override
  String get dosageLabel => 'Dosage';

  @override
  String get nutritionEditSession => 'Edit Nutrition Session';

  @override
  String get nutritionCreateSession => 'Create Nutrition Session';

  @override
  String get nutritionSessionConfig => 'Session Configuration';

  @override
  String get nutritionSessionId => 'Session ID';

  @override
  String get workoutIdOptional => 'Workout ID (optional)';

  @override
  String get appliedPlanWorkoutIdOptional =>
      'Applied Plan Workout ID (optional)';

  @override
  String get nutritionSelectedEntries => 'Selected Entries';

  @override
  String get nutritionNoEntriesSelected => 'No entries selected';

  @override
  String get nutritionAvailableItems => 'Available Items';

  @override
  String get foodLabel => 'Food';

  @override
  String get supplementsLabel => 'Supplements';

  @override
  String get medicationsLabel => 'Medications';

  @override
  String get nutritionNoItemsAvailable => 'No items available';

  @override
  String get updateSession => 'Update Session';

  @override
  String get createSession => 'Create Session';

  @override
  String get exerciseListEmptyDesc =>
      'Try changing the filter or add a new exercise';
}

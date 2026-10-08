import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_uk.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('uk'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Workout App'**
  String get appTitle;

  /// No description provided for @missingAthleteId.
  ///
  /// In en, this message translates to:
  /// **'Missing athleteId'**
  String get missingAthleteId;

  /// No description provided for @missingChatArguments.
  ///
  /// In en, this message translates to:
  /// **'Missing chat arguments'**
  String get missingChatArguments;

  /// No description provided for @fieldRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get fieldRequired;

  /// No description provided for @exerciseName.
  ///
  /// In en, this message translates to:
  /// **'Exercise name'**
  String get exerciseName;

  /// No description provided for @exerciseListEmptyNameError.
  ///
  /// In en, this message translates to:
  /// **'Please enter an exercise name'**
  String get exerciseListEmptyNameError;

  /// No description provided for @activePlanLoadError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load plan: {error}'**
  String activePlanLoadError(Object error);

  /// No description provided for @activePlanNoWorkoutsOnDay.
  ///
  /// In en, this message translates to:
  /// **'No workouts on this day'**
  String get activePlanNoWorkoutsOnDay;

  /// No description provided for @activePlanNotesLabel.
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get activePlanNotesLabel;

  /// No description provided for @coachAthletePlanNoActivePlan.
  ///
  /// In en, this message translates to:
  /// **'No active plan'**
  String get coachAthletePlanNoActivePlan;

  /// No description provided for @coachAthletePlanSetsLabel.
  ///
  /// In en, this message translates to:
  /// **'Sets'**
  String get coachAthletePlanSetsLabel;

  /// No description provided for @coachAthletePlanMassEditExerciseHint.
  ///
  /// In en, this message translates to:
  /// **'Enter note for exercises'**
  String get coachAthletePlanMassEditExerciseHint;

  /// No description provided for @coachAthletePlanMassEditError.
  ///
  /// In en, this message translates to:
  /// **'Mass edit error: {error}'**
  String coachAthletePlanMassEditError(Object error);

  /// No description provided for @search.
  ///
  /// In en, this message translates to:
  /// **'Search...'**
  String get search;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @refresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get refresh;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @apply.
  ///
  /// In en, this message translates to:
  /// **'Apply'**
  String get apply;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @hide.
  ///
  /// In en, this message translates to:
  /// **'Hide'**
  String get hide;

  /// No description provided for @noDate.
  ///
  /// In en, this message translates to:
  /// **'no date'**
  String get noDate;

  /// No description provided for @idPrefix.
  ///
  /// In en, this message translates to:
  /// **'ID: {id}'**
  String idPrefix(Object id);

  /// No description provided for @filter.
  ///
  /// In en, this message translates to:
  /// **'Filter'**
  String get filter;

  /// No description provided for @changes.
  ///
  /// In en, this message translates to:
  /// **'Changes'**
  String get changes;

  /// No description provided for @statuses.
  ///
  /// In en, this message translates to:
  /// **'Statuses: {statuses}'**
  String statuses(Object statuses);

  /// No description provided for @exercises.
  ///
  /// In en, this message translates to:
  /// **'Exercises: {exercises}'**
  String exercises(Object exercises);

  /// No description provided for @workoutsAffected.
  ///
  /// In en, this message translates to:
  /// **'Workouts affected: {count}'**
  String workoutsAffected(Object count);

  /// No description provided for @workoutsShifted.
  ///
  /// In en, this message translates to:
  /// **'Workouts shifted: {count}'**
  String workoutsShifted(Object count);

  /// No description provided for @setsModified.
  ///
  /// In en, this message translates to:
  /// **'Sets modified: {count}'**
  String setsModified(Object count);

  /// No description provided for @setsToBeModified.
  ///
  /// In en, this message translates to:
  /// **'Sets to be modified: {count}'**
  String setsToBeModified(Object count);

  /// No description provided for @shiftDays.
  ///
  /// In en, this message translates to:
  /// **'Shift: {sign}{days} d.'**
  String shiftDays(Object sign, Object days);

  /// No description provided for @startingFrom.
  ///
  /// In en, this message translates to:
  /// **'Starting from: {date}'**
  String startingFrom(Object date);

  /// No description provided for @upToDate.
  ///
  /// In en, this message translates to:
  /// **'Up to date (inclusive): {date}'**
  String upToDate(Object date);

  /// No description provided for @onlyFutureWorkouts.
  ///
  /// In en, this message translates to:
  /// **'Only future workouts'**
  String get onlyFutureWorkouts;

  /// No description provided for @dateNotEarlierThan.
  ///
  /// In en, this message translates to:
  /// **'Date not earlier than {date}'**
  String dateNotEarlierThan(Object date);

  /// No description provided for @dateNotLaterThan.
  ///
  /// In en, this message translates to:
  /// **'Date not later than {date}'**
  String dateNotLaterThan(Object date);

  /// No description provided for @clampNonNegative.
  ///
  /// In en, this message translates to:
  /// **'Do not allow negative values'**
  String get clampNonNegative;

  /// No description provided for @replaceExerciseTo.
  ///
  /// In en, this message translates to:
  /// **'Replace exercise to {name} (ID {id})'**
  String replaceExerciseTo(Object name, Object id);

  /// No description provided for @renameExerciseTo.
  ///
  /// In en, this message translates to:
  /// **'Rename exercise to \"{name}\"'**
  String renameExerciseTo(Object name);

  /// No description provided for @addNewExercises.
  ///
  /// In en, this message translates to:
  /// **'Add new exercises: {count}'**
  String addNewExercises(Object count);

  /// No description provided for @setIntensity.
  ///
  /// In en, this message translates to:
  /// **'Set intensity = {value}'**
  String setIntensity(Object value);

  /// No description provided for @increaseIntensityBy.
  ///
  /// In en, this message translates to:
  /// **'Increase intensity by {value}'**
  String increaseIntensityBy(Object value);

  /// No description provided for @decreaseIntensityBy.
  ///
  /// In en, this message translates to:
  /// **'Decrease intensity by {value}'**
  String decreaseIntensityBy(Object value);

  /// No description provided for @setVolume.
  ///
  /// In en, this message translates to:
  /// **'Set reps = {value}'**
  String setVolume(Object value);

  /// No description provided for @increaseVolumeBy.
  ///
  /// In en, this message translates to:
  /// **'Increase reps by {value}'**
  String increaseVolumeBy(Object value);

  /// No description provided for @decreaseVolumeBy.
  ///
  /// In en, this message translates to:
  /// **'Decrease reps by {value}'**
  String decreaseVolumeBy(Object value);

  /// No description provided for @setWeight.
  ///
  /// In en, this message translates to:
  /// **'Set weight = {value} kg'**
  String setWeight(Object value);

  /// No description provided for @increaseWeightBy.
  ///
  /// In en, this message translates to:
  /// **'Increase weight by {value} kg'**
  String increaseWeightBy(Object value);

  /// No description provided for @decreaseWeightBy.
  ///
  /// In en, this message translates to:
  /// **'Decrease weight by {value} kg'**
  String decreaseWeightBy(Object value);

  /// No description provided for @setEffort.
  ///
  /// In en, this message translates to:
  /// **'Set RPE = {value}'**
  String setEffort(Object value);

  /// No description provided for @increaseEffortBy.
  ///
  /// In en, this message translates to:
  /// **'Increase RPE by {value}'**
  String increaseEffortBy(Object value);

  /// No description provided for @decreaseEffortBy.
  ///
  /// In en, this message translates to:
  /// **'Decrease RPE by {value}'**
  String decreaseEffortBy(Object value);

  /// No description provided for @massEditPreviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Active plan mass edit preview'**
  String get massEditPreviewTitle;

  /// No description provided for @massEditAppliedTitle.
  ///
  /// In en, this message translates to:
  /// **'Active plan changes applied'**
  String get massEditAppliedTitle;

  /// No description provided for @scheduleShiftPreviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Active plan schedule shift preview'**
  String get scheduleShiftPreviewTitle;

  /// No description provided for @scheduleShiftTitle.
  ///
  /// In en, this message translates to:
  /// **'Active plan schedule shift applied'**
  String get scheduleShiftTitle;

  /// No description provided for @shiftParameters.
  ///
  /// In en, this message translates to:
  /// **'Shift parameters'**
  String get shiftParameters;

  /// No description provided for @modeChangeIntervals.
  ///
  /// In en, this message translates to:
  /// **'Mode: change intervals between workouts'**
  String get modeChangeIntervals;

  /// No description provided for @modeScheduleShift.
  ///
  /// In en, this message translates to:
  /// **'Mode: schedule shift'**
  String get modeScheduleShift;

  /// No description provided for @macroActionByPercent.
  ///
  /// In en, this message translates to:
  /// **'By Percent'**
  String get macroActionByPercent;

  /// No description provided for @macroActionToTarget.
  ///
  /// In en, this message translates to:
  /// **'To Target (RPE)'**
  String get macroActionToTarget;

  /// No description provided for @macroActionByValue.
  ///
  /// In en, this message translates to:
  /// **'By Value'**
  String get macroActionByValue;

  /// No description provided for @macroActionByTemplate.
  ///
  /// In en, this message translates to:
  /// **'By Template'**
  String get macroActionByTemplate;

  /// No description provided for @macroActionByExisting.
  ///
  /// In en, this message translates to:
  /// **'By Existing (ID)'**
  String get macroActionByExisting;

  /// No description provided for @macroActionCreateManual.
  ///
  /// In en, this message translates to:
  /// **'Create Manually'**
  String get macroActionCreateManual;

  /// No description provided for @macroActionHintPercent.
  ///
  /// In en, this message translates to:
  /// **'percent, e.g. -5 or 2.5'**
  String get macroActionHintPercent;

  /// No description provided for @macroActionHintReps.
  ///
  /// In en, this message translates to:
  /// **'reps delta, e.g. +1 or -1'**
  String get macroActionHintReps;

  /// No description provided for @macroActionHintTargetRpe.
  ///
  /// In en, this message translates to:
  /// **'target RPE, e.g. 8'**
  String get macroActionHintTargetRpe;

  /// No description provided for @macroActionHintSets.
  ///
  /// In en, this message translates to:
  /// **'±N sets, e.g. 1 or -2'**
  String get macroActionHintSets;

  /// No description provided for @macroActionHintGeneric.
  ///
  /// In en, this message translates to:
  /// **'value'**
  String get macroActionHintGeneric;

  /// No description provided for @macroActionAdjustLoad.
  ///
  /// In en, this message translates to:
  /// **'Adjust Load'**
  String get macroActionAdjustLoad;

  /// No description provided for @macroActionAdjustReps.
  ///
  /// In en, this message translates to:
  /// **'Adjust Reps'**
  String get macroActionAdjustReps;

  /// No description provided for @macroActionAdjustSets.
  ///
  /// In en, this message translates to:
  /// **'Adjust Sets'**
  String get macroActionAdjustSets;

  /// No description provided for @macroActionInjectMesocycle.
  ///
  /// In en, this message translates to:
  /// **'Inject Mesocycle'**
  String get macroActionInjectMesocycle;

  /// No description provided for @macroActionTypeLabel.
  ///
  /// In en, this message translates to:
  /// **'Action Type'**
  String get macroActionTypeLabel;

  /// No description provided for @macroActionModeLabel.
  ///
  /// In en, this message translates to:
  /// **'Mode'**
  String get macroActionModeLabel;

  /// No description provided for @macroActionValueLabel.
  ///
  /// In en, this message translates to:
  /// **'Value'**
  String get macroActionValueLabel;

  /// No description provided for @macroActionNoTemplates.
  ///
  /// In en, this message translates to:
  /// **'No mesocycle templates'**
  String get macroActionNoTemplates;

  /// No description provided for @macroActionTemplateLabel.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle Template'**
  String get macroActionTemplateLabel;

  /// No description provided for @macroActionLoadTemplatesError.
  ///
  /// In en, this message translates to:
  /// **'Error loading templates: {error}'**
  String macroActionLoadTemplatesError(Object error);

  /// No description provided for @macroActionMesoLabel.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle {index}'**
  String macroActionMesoLabel(Object index);

  /// No description provided for @macroActionChooseMeso.
  ///
  /// In en, this message translates to:
  /// **'Choose Mesocycle'**
  String get macroActionChooseMeso;

  /// No description provided for @macroActionOtherId.
  ///
  /// In en, this message translates to:
  /// **'Other (enter ID)'**
  String get macroActionOtherId;

  /// No description provided for @macroActionExistingIdLabel.
  ///
  /// In en, this message translates to:
  /// **'Existing mesocycle ID'**
  String get macroActionExistingIdLabel;

  /// No description provided for @macroActionEnterNumber.
  ///
  /// In en, this message translates to:
  /// **'Enter a number'**
  String get macroActionEnterNumber;

  /// No description provided for @macroActionDurationWeeks.
  ///
  /// In en, this message translates to:
  /// **'Duration (weeks)'**
  String get macroActionDurationWeeks;

  /// No description provided for @macroActionDaysInMicro.
  ///
  /// In en, this message translates to:
  /// **'Days in microcycle'**
  String get macroActionDaysInMicro;

  /// No description provided for @macroActionDayLabel.
  ///
  /// In en, this message translates to:
  /// **'Day {index}: {type}'**
  String macroActionDayLabel(Object index, Object type);

  /// No description provided for @macroActionRest.
  ///
  /// In en, this message translates to:
  /// **'rest'**
  String get macroActionRest;

  /// No description provided for @macroActionWork.
  ///
  /// In en, this message translates to:
  /// **'workout'**
  String get macroActionWork;

  /// No description provided for @macroActionFocusTags.
  ///
  /// In en, this message translates to:
  /// **'Focus Tags'**
  String get macroActionFocusTags;

  /// No description provided for @macroActionPlacement.
  ///
  /// In en, this message translates to:
  /// **'Placement'**
  String get macroActionPlacement;

  /// No description provided for @macroActionAppendEnd.
  ///
  /// In en, this message translates to:
  /// **'Append to end'**
  String get macroActionAppendEnd;

  /// No description provided for @macroActionInsertAfterWorkout.
  ///
  /// In en, this message translates to:
  /// **'After workout'**
  String get macroActionInsertAfterWorkout;

  /// No description provided for @macroActionInsertAfterMeso.
  ///
  /// In en, this message translates to:
  /// **'After mesocycle'**
  String get macroActionInsertAfterMeso;

  /// No description provided for @macroActionSelectAnchorWorkout.
  ///
  /// In en, this message translates to:
  /// **'Select anchor workout'**
  String get macroActionSelectAnchorWorkout;

  /// No description provided for @macroActionPickWorkout.
  ///
  /// In en, this message translates to:
  /// **'Pick workout'**
  String get macroActionPickWorkout;

  /// No description provided for @macroActionNotSelected.
  ///
  /// In en, this message translates to:
  /// **'Not selected'**
  String get macroActionNotSelected;

  /// No description provided for @macroActionAfterAnchor.
  ///
  /// In en, this message translates to:
  /// **'After: {name}'**
  String macroActionAfterAnchor(Object name);

  /// No description provided for @macroActionNoMesoInPlan.
  ///
  /// In en, this message translates to:
  /// **'No mesocycles in plan'**
  String get macroActionNoMesoInPlan;

  /// No description provided for @macroActionMesoIndexLabel.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle: '**
  String get macroActionMesoIndexLabel;

  /// No description provided for @macroActionConflicts.
  ///
  /// In en, this message translates to:
  /// **'Conflicts'**
  String get macroActionConflicts;

  /// No description provided for @macroActionReplacePlanned.
  ///
  /// In en, this message translates to:
  /// **'Replace planned'**
  String get macroActionReplacePlanned;

  /// No description provided for @macroActionShiftForward.
  ///
  /// In en, this message translates to:
  /// **'Shift forward'**
  String get macroActionShiftForward;

  /// No description provided for @macroActionSkipConflict.
  ///
  /// In en, this message translates to:
  /// **'Skip on conflict'**
  String get macroActionSkipConflict;

  /// No description provided for @macroActionTarget.
  ///
  /// In en, this message translates to:
  /// **'Target'**
  String get macroActionTarget;

  /// No description provided for @macroActionTargetHelp.
  ///
  /// In en, this message translates to:
  /// **'If target is not specified — action applies to all exercises of selected workouts.'**
  String get macroActionTargetHelp;

  /// No description provided for @macroConditionGreater.
  ///
  /// In en, this message translates to:
  /// **'greater >'**
  String get macroConditionGreater;

  /// No description provided for @macroConditionLess.
  ///
  /// In en, this message translates to:
  /// **'less <'**
  String get macroConditionLess;

  /// No description provided for @macroConditionEqual.
  ///
  /// In en, this message translates to:
  /// **'equal ='**
  String get macroConditionEqual;

  /// No description provided for @macroConditionNotEqual.
  ///
  /// In en, this message translates to:
  /// **'not equal ≠'**
  String get macroConditionNotEqual;

  /// No description provided for @macroConditionInRange.
  ///
  /// In en, this message translates to:
  /// **'in range'**
  String get macroConditionInRange;

  /// No description provided for @macroConditionNotInRange.
  ///
  /// In en, this message translates to:
  /// **'not in range'**
  String get macroConditionNotInRange;

  /// No description provided for @macroConditionStagnates.
  ///
  /// In en, this message translates to:
  /// **'stagnation for N windows'**
  String get macroConditionStagnates;

  /// No description provided for @macroConditionDeviates.
  ///
  /// In en, this message translates to:
  /// **'deviation from average'**
  String get macroConditionDeviates;

  /// No description provided for @macroConditionHoldsForWorkouts.
  ///
  /// In en, this message translates to:
  /// **'holds for N workouts in a row'**
  String get macroConditionHoldsForWorkouts;

  /// No description provided for @macroConditionHoldsForSets.
  ///
  /// In en, this message translates to:
  /// **'holds for N sets in a row (within workout)'**
  String get macroConditionHoldsForSets;

  /// No description provided for @macroConditionOperatorLabel.
  ///
  /// In en, this message translates to:
  /// **'Operator'**
  String get macroConditionOperatorLabel;

  /// No description provided for @macroConditionRangeFrom.
  ///
  /// In en, this message translates to:
  /// **'from'**
  String get macroConditionRangeFrom;

  /// No description provided for @macroConditionNumberHint.
  ///
  /// In en, this message translates to:
  /// **'number'**
  String get macroConditionNumberHint;

  /// No description provided for @macroConditionRangeTo.
  ///
  /// In en, this message translates to:
  /// **'to'**
  String get macroConditionRangeTo;

  /// No description provided for @macroConditionWindowCount.
  ///
  /// In en, this message translates to:
  /// **'n (windows)'**
  String get macroConditionWindowCount;

  /// No description provided for @macroConditionWindowCountHint.
  ///
  /// In en, this message translates to:
  /// **'integer, e.g. 5'**
  String get macroConditionWindowCountHint;

  /// No description provided for @macroConditionEpsilonPercent.
  ///
  /// In en, this message translates to:
  /// **'epsilon_percent (threshold, %)'**
  String get macroConditionEpsilonPercent;

  /// No description provided for @macroConditionValuePercent.
  ///
  /// In en, this message translates to:
  /// **'value_percent (deviation, %)'**
  String get macroConditionValuePercent;

  /// No description provided for @macroConditionPositive.
  ///
  /// In en, this message translates to:
  /// **'positive'**
  String get macroConditionPositive;

  /// No description provided for @macroConditionNegative.
  ///
  /// In en, this message translates to:
  /// **'negative'**
  String get macroConditionNegative;

  /// No description provided for @macroConditionDirection.
  ///
  /// In en, this message translates to:
  /// **'direction (optional)'**
  String get macroConditionDirection;

  /// No description provided for @macroConditionGreaterEqual.
  ///
  /// In en, this message translates to:
  /// **'greater or equal ≥'**
  String get macroConditionGreaterEqual;

  /// No description provided for @macroConditionLessEqual.
  ///
  /// In en, this message translates to:
  /// **'less or equal ≤'**
  String get macroConditionLessEqual;

  /// No description provided for @macroConditionRelationLabel.
  ///
  /// In en, this message translates to:
  /// **'relation'**
  String get macroConditionRelationLabel;

  /// No description provided for @macroConditionWorkoutCount.
  ///
  /// In en, this message translates to:
  /// **'n (workouts)'**
  String get macroConditionWorkoutCount;

  /// No description provided for @macroConditionWorkoutCountHint.
  ///
  /// In en, this message translates to:
  /// **'integer, e.g. 3'**
  String get macroConditionWorkoutCountHint;

  /// No description provided for @macroConditionDeltaHint.
  ///
  /// In en, this message translates to:
  /// **'delta, e.g. -2 for reps'**
  String get macroConditionDeltaHint;

  /// No description provided for @macroConditionSetCount.
  ///
  /// In en, this message translates to:
  /// **'n (sets in a row)'**
  String get macroConditionSetCount;

  /// No description provided for @macroConditionSetCountHint.
  ///
  /// In en, this message translates to:
  /// **'integer, e.g. 12'**
  String get macroConditionSetCountHint;

  /// No description provided for @macroConditionValueLabel.
  ///
  /// In en, this message translates to:
  /// **'value'**
  String get macroConditionValueLabel;

  /// No description provided for @macroDurationNextNWorkouts.
  ///
  /// In en, this message translates to:
  /// **'Next N workouts'**
  String get macroDurationNextNWorkouts;

  /// No description provided for @macroDurationUntilLastWorkout.
  ///
  /// In en, this message translates to:
  /// **'Until last workout'**
  String get macroDurationUntilLastWorkout;

  /// No description provided for @macroDurationUntilEndOfMeso.
  ///
  /// In en, this message translates to:
  /// **'Until end of mesocycle'**
  String get macroDurationUntilEndOfMeso;

  /// No description provided for @macroDurationUntilEndOfMicro.
  ///
  /// In en, this message translates to:
  /// **'Until end of microcycle'**
  String get macroDurationUntilEndOfMicro;

  /// No description provided for @macroDurationUntilWorkoutX.
  ///
  /// In en, this message translates to:
  /// **'Until workout X'**
  String get macroDurationUntilWorkoutX;

  /// No description provided for @macroDurationScopeLabel.
  ///
  /// In en, this message translates to:
  /// **'Scope'**
  String get macroDurationScopeLabel;

  /// No description provided for @macroDurationCountLabel.
  ///
  /// In en, this message translates to:
  /// **'Count'**
  String get macroDurationCountLabel;

  /// No description provided for @macroTargetBy.
  ///
  /// In en, this message translates to:
  /// **'Target by:'**
  String get macroTargetBy;

  /// No description provided for @macroTargetTags.
  ///
  /// In en, this message translates to:
  /// **'Tags'**
  String get macroTargetTags;

  /// No description provided for @macroTargetIds.
  ///
  /// In en, this message translates to:
  /// **'IDs'**
  String get macroTargetIds;

  /// No description provided for @macroTargetIdsLabel.
  ///
  /// In en, this message translates to:
  /// **'exercise_ids (CSV)'**
  String get macroTargetIdsLabel;

  /// No description provided for @macroTriggerChooseExercises.
  ///
  /// In en, this message translates to:
  /// **'Choose exercises'**
  String get macroTriggerChooseExercises;

  /// No description provided for @macroTriggerMetricReadiness.
  ///
  /// In en, this message translates to:
  /// **'Readiness (workout)'**
  String get macroTriggerMetricReadiness;

  /// No description provided for @macroTriggerMetricRpeSession.
  ///
  /// In en, this message translates to:
  /// **'Session RPE'**
  String get macroTriggerMetricRpeSession;

  /// No description provided for @macroTriggerMetricTotalReps.
  ///
  /// In en, this message translates to:
  /// **'Total Reps'**
  String get macroTriggerMetricTotalReps;

  /// No description provided for @macroTriggerMetricE1rm.
  ///
  /// In en, this message translates to:
  /// **'e1RM estimate'**
  String get macroTriggerMetricE1rm;

  /// No description provided for @macroTriggerMetricPerformanceTrend.
  ///
  /// In en, this message translates to:
  /// **'Performance Trend'**
  String get macroTriggerMetricPerformanceTrend;

  /// No description provided for @macroTriggerMetricRpeDelta.
  ///
  /// In en, this message translates to:
  /// **'RPE Delta from Plan'**
  String get macroTriggerMetricRpeDelta;

  /// No description provided for @macroTriggerMetricRepsDelta.
  ///
  /// In en, this message translates to:
  /// **'Reps Delta from Plan'**
  String get macroTriggerMetricRepsDelta;

  /// No description provided for @macroTriggerMetricLabel.
  ///
  /// In en, this message translates to:
  /// **'Trigger Metric'**
  String get macroTriggerMetricLabel;

  /// No description provided for @macroWorkoutPickerTitle.
  ///
  /// In en, this message translates to:
  /// **'Choose workout'**
  String get macroWorkoutPickerTitle;

  /// No description provided for @macroWorkoutPickerNoWorkouts.
  ///
  /// In en, this message translates to:
  /// **'No workouts in active plan'**
  String get macroWorkoutPickerNoWorkouts;

  /// No description provided for @macroWorkoutPickerNoWorkoutsOnDate.
  ///
  /// In en, this message translates to:
  /// **'No workouts on this date'**
  String get macroWorkoutPickerNoWorkoutsOnDate;

  /// No description provided for @macroWorkoutPickerOrChooseFromList.
  ///
  /// In en, this message translates to:
  /// **'Or choose from list'**
  String get macroWorkoutPickerOrChooseFromList;

  /// No description provided for @macroWorkoutPickerListButton.
  ///
  /// In en, this message translates to:
  /// **'List'**
  String get macroWorkoutPickerListButton;

  /// No description provided for @macroWorkoutPickerWorkoutsOnDate.
  ///
  /// In en, this message translates to:
  /// **'Workouts on this date'**
  String get macroWorkoutPickerWorkoutsOnDate;

  /// No description provided for @macroWorkoutPickerOrSelectFromList.
  ///
  /// In en, this message translates to:
  /// **'Or select from list'**
  String get macroWorkoutPickerOrSelectFromList;

  /// No description provided for @macroWorkoutPickerList.
  ///
  /// In en, this message translates to:
  /// **'List'**
  String get macroWorkoutPickerList;

  /// No description provided for @analyticsPlanTitle.
  ///
  /// In en, this message translates to:
  /// **'Plan analytics {planName}'**
  String analyticsPlanTitle(Object planName);

  /// No description provided for @errorLoadingActivePlan.
  ///
  /// In en, this message translates to:
  /// **'Failed to load active plan'**
  String get errorLoadingActivePlan;

  /// No description provided for @selectTwoMetrics.
  ///
  /// In en, this message translates to:
  /// **'Select two metrics'**
  String get selectTwoMetrics;

  /// No description provided for @activePlanNotFound.
  ///
  /// In en, this message translates to:
  /// **'Active plan not found'**
  String get activePlanNotFound;

  /// No description provided for @errorLoadingData.
  ///
  /// In en, this message translates to:
  /// **'Error loading data'**
  String get errorLoadingData;

  /// No description provided for @axisX.
  ///
  /// In en, this message translates to:
  /// **'X axis'**
  String get axisX;

  /// No description provided for @axisY.
  ///
  /// In en, this message translates to:
  /// **'Y axis'**
  String get axisY;

  /// No description provided for @showChart.
  ///
  /// In en, this message translates to:
  /// **'Show chart'**
  String get showChart;

  /// No description provided for @selectRangeAndMetrics.
  ///
  /// In en, this message translates to:
  /// **'Select a range and metrics'**
  String get selectRangeAndMetrics;

  /// No description provided for @noDataForSelectedMetrics.
  ///
  /// In en, this message translates to:
  /// **'No data for selected metrics'**
  String get noDataForSelectedMetrics;

  /// No description provided for @metricVolumeKg.
  ///
  /// In en, this message translates to:
  /// **'Volume (kg)'**
  String get metricVolumeKg;

  /// No description provided for @metricEffortRpe.
  ///
  /// In en, this message translates to:
  /// **'Effort (RPE)'**
  String get metricEffortRpe;

  /// No description provided for @metricKpsh.
  ///
  /// In en, this message translates to:
  /// **'KPSH'**
  String get metricKpsh;

  /// No description provided for @metricReps.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get metricReps;

  /// No description provided for @metricOneRm.
  ///
  /// In en, this message translates to:
  /// **'1RM'**
  String get metricOneRm;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @languageSystem.
  ///
  /// In en, this message translates to:
  /// **'System'**
  String get languageSystem;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @languageUkrainian.
  ///
  /// In en, this message translates to:
  /// **'Ukrainian'**
  String get languageUkrainian;

  /// No description provided for @accountTitle.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get accountTitle;

  /// No description provided for @editProfileTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit profile'**
  String get editProfileTitle;

  /// No description provided for @displayName.
  ///
  /// In en, this message translates to:
  /// **'Display name'**
  String get displayName;

  /// No description provided for @bio.
  ///
  /// In en, this message translates to:
  /// **'Bio'**
  String get bio;

  /// No description provided for @bodyweightKg.
  ///
  /// In en, this message translates to:
  /// **'Bodyweight (kg)'**
  String get bodyweightKg;

  /// No description provided for @heightCm.
  ///
  /// In en, this message translates to:
  /// **'Height (cm)'**
  String get heightCm;

  /// No description provided for @age.
  ///
  /// In en, this message translates to:
  /// **'Age'**
  String get age;

  /// No description provided for @trainingYears.
  ///
  /// In en, this message translates to:
  /// **'Training years'**
  String get trainingYears;

  /// No description provided for @publicProfile.
  ///
  /// In en, this message translates to:
  /// **'Public profile'**
  String get publicProfile;

  /// No description provided for @units.
  ///
  /// In en, this message translates to:
  /// **'Units'**
  String get units;

  /// No description provided for @unitsMetric.
  ///
  /// In en, this message translates to:
  /// **'Metric'**
  String get unitsMetric;

  /// No description provided for @unitsImperial.
  ///
  /// In en, this message translates to:
  /// **'Imperial'**
  String get unitsImperial;

  /// No description provided for @timezone.
  ///
  /// In en, this message translates to:
  /// **'Timezone'**
  String get timezone;

  /// No description provided for @notifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @profileUpdated.
  ///
  /// In en, this message translates to:
  /// **'Profile updated'**
  String get profileUpdated;

  /// No description provided for @failedToUpdateProfile.
  ///
  /// In en, this message translates to:
  /// **'Failed to update profile'**
  String get failedToUpdateProfile;

  /// No description provided for @editProfileButton.
  ///
  /// In en, this message translates to:
  /// **'Edit profile'**
  String get editProfileButton;

  /// No description provided for @coachingSettingsButton.
  ///
  /// In en, this message translates to:
  /// **'Coaching settings'**
  String get coachingSettingsButton;

  /// No description provided for @coachingTitle.
  ///
  /// In en, this message translates to:
  /// **'Coaching'**
  String get coachingTitle;

  /// No description provided for @coachingAcceptingNewClients.
  ///
  /// In en, this message translates to:
  /// **'Accepting new clients'**
  String get coachingAcceptingNewClients;

  /// No description provided for @coachingNotAccepting.
  ///
  /// In en, this message translates to:
  /// **'Not accepting'**
  String get coachingNotAccepting;

  /// No description provided for @coachingDisabled.
  ///
  /// In en, this message translates to:
  /// **'Coaching disabled'**
  String get coachingDisabled;

  /// No description provided for @coachingDisabledDescription.
  ///
  /// In en, this message translates to:
  /// **'This user has not enabled coaching options.'**
  String get coachingDisabledDescription;

  /// No description provided for @coachingSpecializations.
  ///
  /// In en, this message translates to:
  /// **'Specializations'**
  String get coachingSpecializations;

  /// No description provided for @coachingLanguages.
  ///
  /// In en, this message translates to:
  /// **'Languages'**
  String get coachingLanguages;

  /// No description provided for @coachingExperience.
  ///
  /// In en, this message translates to:
  /// **'Experience'**
  String get coachingExperience;

  /// No description provided for @coachingTimezone.
  ///
  /// In en, this message translates to:
  /// **'Timezone'**
  String get coachingTimezone;

  /// No description provided for @coachingRate.
  ///
  /// In en, this message translates to:
  /// **'Rate'**
  String get coachingRate;

  /// No description provided for @coachingCustomRate.
  ///
  /// In en, this message translates to:
  /// **'Custom rate'**
  String get coachingCustomRate;

  /// No description provided for @requestCoaching.
  ///
  /// In en, this message translates to:
  /// **'Request coaching'**
  String get requestCoaching;

  /// No description provided for @statsTotalWorkouts.
  ///
  /// In en, this message translates to:
  /// **'Total Workouts'**
  String get statsTotalWorkouts;

  /// No description provided for @statsVolumeKg.
  ///
  /// In en, this message translates to:
  /// **'Volume (kg)'**
  String get statsVolumeKg;

  /// No description provided for @statsActiveDays.
  ///
  /// In en, this message translates to:
  /// **'Active Days'**
  String get statsActiveDays;

  /// No description provided for @activityTitle.
  ///
  /// In en, this message translates to:
  /// **'Activity'**
  String get activityTitle;

  /// No description provided for @lastWeeks.
  ///
  /// In en, this message translates to:
  /// **'Last {weeks} weeks'**
  String lastWeeks(Object weeks);

  /// No description provided for @maxKgPerDay.
  ///
  /// In en, this message translates to:
  /// **'Max: {value} kg/day'**
  String maxKgPerDay(Object value);

  /// No description provided for @sessionsCount.
  ///
  /// In en, this message translates to:
  /// **'{count} session(s)'**
  String sessionsCount(Object count);

  /// No description provided for @noActivity.
  ///
  /// In en, this message translates to:
  /// **'No activity'**
  String get noActivity;

  /// No description provided for @less.
  ///
  /// In en, this message translates to:
  /// **'Less'**
  String get less;

  /// No description provided for @more.
  ///
  /// In en, this message translates to:
  /// **'More'**
  String get more;

  /// No description provided for @completedWorkoutsTitle.
  ///
  /// In en, this message translates to:
  /// **'Completed Workouts'**
  String get completedWorkoutsTitle;

  /// No description provided for @noCompletedWorkoutsYet.
  ///
  /// In en, this message translates to:
  /// **'No completed workouts yet'**
  String get noCompletedWorkoutsYet;

  /// No description provided for @exerciseFormTitleAdd.
  ///
  /// In en, this message translates to:
  /// **'Add exercise'**
  String get exerciseFormTitleAdd;

  /// No description provided for @exerciseFormExerciseNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Exercise name'**
  String get exerciseFormExerciseNameLabel;

  /// No description provided for @exerciseFormPleaseEnterName.
  ///
  /// In en, this message translates to:
  /// **'Please enter a name'**
  String get exerciseFormPleaseEnterName;

  /// No description provided for @exerciseFormMuscleGroupLabel.
  ///
  /// In en, this message translates to:
  /// **'Muscle group'**
  String get exerciseFormMuscleGroupLabel;

  /// No description provided for @exerciseFormLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get exerciseFormLoading;

  /// No description provided for @exerciseFormSelectGroup.
  ///
  /// In en, this message translates to:
  /// **'Select group'**
  String get exerciseFormSelectGroup;

  /// No description provided for @exerciseFormLoadingGroups.
  ///
  /// In en, this message translates to:
  /// **'Loading groups...'**
  String get exerciseFormLoadingGroups;

  /// No description provided for @exerciseFormPleaseSelectMuscleGroup.
  ///
  /// In en, this message translates to:
  /// **'Please select a muscle group'**
  String get exerciseFormPleaseSelectMuscleGroup;

  /// No description provided for @exerciseFormProgressionTemplateOptional.
  ///
  /// In en, this message translates to:
  /// **'Progression template (optional)'**
  String get exerciseFormProgressionTemplateOptional;

  /// No description provided for @exerciseFormSelectTemplate.
  ///
  /// In en, this message translates to:
  /// **'Select template'**
  String get exerciseFormSelectTemplate;

  /// No description provided for @exerciseFormNoTemplate.
  ///
  /// In en, this message translates to:
  /// **'No template'**
  String get exerciseFormNoTemplate;

  /// No description provided for @exerciseFormSetsTitle.
  ///
  /// In en, this message translates to:
  /// **'Sets'**
  String get exerciseFormSetsTitle;

  /// No description provided for @exerciseFormAddSet.
  ///
  /// In en, this message translates to:
  /// **'Add set'**
  String get exerciseFormAddSet;

  /// No description provided for @exerciseFormSaveExercise.
  ///
  /// In en, this message translates to:
  /// **'Save exercise'**
  String get exerciseFormSaveExercise;

  /// No description provided for @exerciseFormWeightKg.
  ///
  /// In en, this message translates to:
  /// **'Weight (kg)'**
  String get exerciseFormWeightKg;

  /// No description provided for @exerciseFormReps.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get exerciseFormReps;

  /// No description provided for @exerciseFormRequired.
  ///
  /// In en, this message translates to:
  /// **'Required'**
  String get exerciseFormRequired;

  /// No description provided for @exerciseFormFailedToLoadData.
  ///
  /// In en, this message translates to:
  /// **'Failed to load data: {error}'**
  String exerciseFormFailedToLoadData(Object error);

  /// No description provided for @exerciseFormErrorSaving.
  ///
  /// In en, this message translates to:
  /// **'Error saving: {error}'**
  String exerciseFormErrorSaving(Object error);

  /// No description provided for @exerciseDefinitionIdRequired.
  ///
  /// In en, this message translates to:
  /// **'Exercise definition id is required'**
  String get exerciseDefinitionIdRequired;

  /// No description provided for @exerciseFormDefaultReps.
  ///
  /// In en, this message translates to:
  /// **'5'**
  String get exerciseFormDefaultReps;

  /// No description provided for @exerciseFormDefaultWeight.
  ///
  /// In en, this message translates to:
  /// **'0'**
  String get exerciseFormDefaultWeight;

  /// No description provided for @exerciseListTitle.
  ///
  /// In en, this message translates to:
  /// **'Exercises'**
  String get exerciseListTitle;

  /// No description provided for @exerciseListAddExerciseTitle.
  ///
  /// In en, this message translates to:
  /// **'Add exercise'**
  String get exerciseListAddExerciseTitle;

  /// No description provided for @exerciseListNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get exerciseListNameLabel;

  /// No description provided for @exerciseListMuscleGroupLabel.
  ///
  /// In en, this message translates to:
  /// **'Muscle group'**
  String get exerciseListMuscleGroupLabel;

  /// No description provided for @exerciseListEquipmentLabel.
  ///
  /// In en, this message translates to:
  /// **'Equipment'**
  String get exerciseListEquipmentLabel;

  /// No description provided for @exerciseListLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get exerciseListLoading;

  /// No description provided for @exerciseListSelectGroup.
  ///
  /// In en, this message translates to:
  /// **'Select group'**
  String get exerciseListSelectGroup;

  /// No description provided for @exerciseListLoadingGroups.
  ///
  /// In en, this message translates to:
  /// **'Loading groups...'**
  String get exerciseListLoadingGroups;

  /// No description provided for @exerciseListSelectMuscleGroupValidator.
  ///
  /// In en, this message translates to:
  /// **'Select a muscle group'**
  String get exerciseListSelectMuscleGroupValidator;

  /// No description provided for @exerciseListEnterExerciseName.
  ///
  /// In en, this message translates to:
  /// **'Enter exercise name'**
  String get exerciseListEnterExerciseName;

  /// No description provided for @exerciseListSelectMuscleGroupSnack.
  ///
  /// In en, this message translates to:
  /// **'Select a muscle group'**
  String get exerciseListSelectMuscleGroupSnack;

  /// No description provided for @exerciseListErrorLoadingMuscleGroups.
  ///
  /// In en, this message translates to:
  /// **'Failed to load muscle groups: {error}'**
  String exerciseListErrorLoadingMuscleGroups(Object error);

  /// No description provided for @exerciseListErrorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Error: {error}'**
  String exerciseListErrorGeneric(Object error);

  /// No description provided for @exerciseListEmpty.
  ///
  /// In en, this message translates to:
  /// **'No exercises. Add a new one!'**
  String get exerciseListEmpty;

  /// No description provided for @exerciseListMuscleGroupPrefix.
  ///
  /// In en, this message translates to:
  /// **'Muscle group: {value}'**
  String exerciseListMuscleGroupPrefix(Object value);

  /// No description provided for @exerciseListEquipmentPrefix.
  ///
  /// In en, this message translates to:
  /// **'Equipment: {value}'**
  String exerciseListEquipmentPrefix(Object value);

  /// No description provided for @exerciseListDeleteExerciseTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete exercise?'**
  String get exerciseListDeleteExerciseTitle;

  /// No description provided for @exerciseListDeleteExerciseBody.
  ///
  /// In en, this message translates to:
  /// **'This action cannot be undone.'**
  String get exerciseListDeleteExerciseBody;

  /// No description provided for @exerciseListDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get exerciseListDelete;

  /// No description provided for @exerciseListErrorDeleting.
  ///
  /// In en, this message translates to:
  /// **'Failed to delete: {error}'**
  String exerciseListErrorDeleting(Object error);

  /// No description provided for @userMaxTitle.
  ///
  /// In en, this message translates to:
  /// **'Add max'**
  String get userMaxTitle;

  /// No description provided for @userMaxExerciseLabel.
  ///
  /// In en, this message translates to:
  /// **'Exercise'**
  String get userMaxExerciseLabel;

  /// No description provided for @userMaxSelectExerciseValidator.
  ///
  /// In en, this message translates to:
  /// **'Select an exercise'**
  String get userMaxSelectExerciseValidator;

  /// No description provided for @userMaxWeightKgLabel.
  ///
  /// In en, this message translates to:
  /// **'Weight (kg)'**
  String get userMaxWeightKgLabel;

  /// No description provided for @userMaxWeightGtZeroValidator.
  ///
  /// In en, this message translates to:
  /// **'Enter weight > 0'**
  String get userMaxWeightGtZeroValidator;

  /// No description provided for @userMaxRepsLabel.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get userMaxRepsLabel;

  /// No description provided for @userMaxRepsGtZeroValidator.
  ///
  /// In en, this message translates to:
  /// **'Enter reps > 0'**
  String get userMaxRepsGtZeroValidator;

  /// No description provided for @userMaxRepsMax12Validator.
  ///
  /// In en, this message translates to:
  /// **'Maximum 12 reps'**
  String get userMaxRepsMax12Validator;

  /// No description provided for @userMaxFillAllFieldsSnack.
  ///
  /// In en, this message translates to:
  /// **'Fill all fields and select an exercise'**
  String get userMaxFillAllFieldsSnack;

  /// No description provided for @userMaxSaving.
  ///
  /// In en, this message translates to:
  /// **'Saving...'**
  String get userMaxSaving;

  /// No description provided for @userMaxSave.
  ///
  /// In en, this message translates to:
  /// **'Save max'**
  String get userMaxSave;

  /// No description provided for @userMaxFailedToSave.
  ///
  /// In en, this message translates to:
  /// **'Failed to save max: {error}'**
  String userMaxFailedToSave(Object error);

  /// No description provided for @yes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get yes;

  /// No description provided for @no.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get no;

  /// No description provided for @planDraftMicrocycle.
  ///
  /// In en, this message translates to:
  /// **'Microcycle'**
  String get planDraftMicrocycle;

  /// No description provided for @planDraftMesocycle.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle'**
  String get planDraftMesocycle;

  /// No description provided for @massEditToolWorkoutsMatched.
  ///
  /// In en, this message translates to:
  /// **'Workouts matched: {count}'**
  String massEditToolWorkoutsMatched(Object count);

  /// No description provided for @massEditToolSetsModified.
  ///
  /// In en, this message translates to:
  /// **'Sets modified: {count}'**
  String massEditToolSetsModified(Object count);

  /// No description provided for @massEditToolSetsToBeModified.
  ///
  /// In en, this message translates to:
  /// **'Sets to be modified: {count}'**
  String massEditToolSetsToBeModified(Object count);

  /// No description provided for @workoutDetailMacrosChangesFoundTitle.
  ///
  /// In en, this message translates to:
  /// **'Macro changes found'**
  String get workoutDetailMacrosChangesFoundTitle;

  /// No description provided for @workoutDetailMacrosChangesFoundBody.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle injections: {injectCount}\nWorkout patches: {hasPatches}'**
  String workoutDetailMacrosChangesFoundBody(
    Object injectCount,
    Object hasPatches,
  );

  /// No description provided for @workoutDetailMacrosApplied.
  ///
  /// In en, this message translates to:
  /// **'Macros applied'**
  String get workoutDetailMacrosApplied;

  /// No description provided for @workoutDetailFailedToApplyMacros.
  ///
  /// In en, this message translates to:
  /// **'Failed to apply macros: {error}'**
  String workoutDetailFailedToApplyMacros(Object error);

  /// No description provided for @workoutDetailFailedToRefreshWorkoutBeforeApplyingReadiness.
  ///
  /// In en, this message translates to:
  /// **'Failed to refresh workout before applying readiness'**
  String get workoutDetailFailedToRefreshWorkoutBeforeApplyingReadiness;

  /// No description provided for @workoutDetailWorkoutNotReadyMissingIds.
  ///
  /// In en, this message translates to:
  /// **'Workout is not ready for set updates (missing ids)'**
  String get workoutDetailWorkoutNotReadyMissingIds;

  /// No description provided for @workoutDetailIncreaseTooltip.
  ///
  /// In en, this message translates to:
  /// **'Increase'**
  String get workoutDetailIncreaseTooltip;

  /// No description provided for @workoutDetailSessionActive.
  ///
  /// In en, this message translates to:
  /// **'Active session'**
  String get workoutDetailSessionActive;

  /// No description provided for @workoutDetailSessionNone.
  ///
  /// In en, this message translates to:
  /// **'No active session'**
  String get workoutDetailSessionNone;

  /// No description provided for @workoutDetailSelectSetTypeTitle.
  ///
  /// In en, this message translates to:
  /// **'Select set type'**
  String get workoutDetailSelectSetTypeTitle;

  /// No description provided for @workoutDetailSetTypeNormal.
  ///
  /// In en, this message translates to:
  /// **'Normal set'**
  String get workoutDetailSetTypeNormal;

  /// No description provided for @workoutDetailSetTypeDrop.
  ///
  /// In en, this message translates to:
  /// **'Drop set'**
  String get workoutDetailSetTypeDrop;

  /// No description provided for @workoutDetailSetTypeCluster.
  ///
  /// In en, this message translates to:
  /// **'Cluster set'**
  String get workoutDetailSetTypeCluster;

  /// No description provided for @workoutDetailSetTypeRestPause.
  ///
  /// In en, this message translates to:
  /// **'Rest-pause set'**
  String get workoutDetailSetTypeRestPause;

  /// No description provided for @workoutDetailFailedToUpdateSetType.
  ///
  /// In en, this message translates to:
  /// **'Failed to update set type: {error}'**
  String workoutDetailFailedToUpdateSetType(Object error);

  /// No description provided for @activePlanTitle.
  ///
  /// In en, this message translates to:
  /// **'Active plan'**
  String get activePlanTitle;

  /// No description provided for @activePlanFailedToLoad.
  ///
  /// In en, this message translates to:
  /// **'Failed to load active plan: {error}'**
  String activePlanFailedToLoad(Object error);

  /// No description provided for @activePlanNone.
  ///
  /// In en, this message translates to:
  /// **'No active plan'**
  String get activePlanNone;

  /// No description provided for @activePlanAiMassEditTitle.
  ///
  /// In en, this message translates to:
  /// **'AI mass edit (chat)'**
  String get activePlanAiMassEditTitle;

  /// No description provided for @activePlanAiMassEditHint.
  ///
  /// In en, this message translates to:
  /// **'For example: Increase RPE by 1 and add 1 set to all bench presses on Mondays'**
  String get activePlanAiMassEditHint;

  /// No description provided for @activePlanAiMassEditSend.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get activePlanAiMassEditSend;

  /// No description provided for @activePlanAiMassEditStarted.
  ///
  /// In en, this message translates to:
  /// **'AI mass edit started (task: {taskId})'**
  String activePlanAiMassEditStarted(Object taskId);

  /// No description provided for @activePlanAiMassEditFailedToSend.
  ///
  /// In en, this message translates to:
  /// **'Failed to send AI mass edit command: {error}'**
  String activePlanAiMassEditFailedToSend(Object error);

  /// No description provided for @activePlanMassEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Mass edit (from {start} to {end})'**
  String activePlanMassEditTitle(Object end, Object start);

  /// No description provided for @activePlanRangeLabel.
  ///
  /// In en, this message translates to:
  /// **'Range:'**
  String get activePlanRangeLabel;

  /// No description provided for @activePlanRangeFutureFromWeek.
  ///
  /// In en, this message translates to:
  /// **'Future from week'**
  String get activePlanRangeFutureFromWeek;

  /// No description provided for @activePlanRangeByMesoMicro.
  ///
  /// In en, this message translates to:
  /// **'By meso/micro'**
  String get activePlanRangeByMesoMicro;

  /// No description provided for @activePlanIntensityLabel.
  ///
  /// In en, this message translates to:
  /// **'Intensity %'**
  String get activePlanIntensityLabel;

  /// No description provided for @activePlanRpeLabel.
  ///
  /// In en, this message translates to:
  /// **'RPE'**
  String get activePlanRpeLabel;

  /// No description provided for @activePlanRepsLabel.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get activePlanRepsLabel;

  /// No description provided for @activePlanModeSet.
  ///
  /// In en, this message translates to:
  /// **'Set'**
  String get activePlanModeSet;

  /// No description provided for @activePlanModeOffset.
  ///
  /// In en, this message translates to:
  /// **'Offset'**
  String get activePlanModeOffset;

  /// No description provided for @activePlanModeScale.
  ///
  /// In en, this message translates to:
  /// **'Scale'**
  String get activePlanModeScale;

  /// No description provided for @activePlanHintEg75.
  ///
  /// In en, this message translates to:
  /// **'e.g. 75'**
  String get activePlanHintEg75;

  /// No description provided for @activePlanHintPercentOffset.
  ///
  /// In en, this message translates to:
  /// **'+/- % (e.g. -2)'**
  String get activePlanHintPercentOffset;

  /// No description provided for @activePlanHintFactor.
  ///
  /// In en, this message translates to:
  /// **'× factor (e.g. 1.05)'**
  String get activePlanHintFactor;

  /// No description provided for @activePlanHintEg8.
  ///
  /// In en, this message translates to:
  /// **'e.g. 8'**
  String get activePlanHintEg8;

  /// No description provided for @activePlanHintEg5.
  ///
  /// In en, this message translates to:
  /// **'e.g. 5'**
  String get activePlanHintEg5;

  /// No description provided for @activePlanHintRepsOffset.
  ///
  /// In en, this message translates to:
  /// **'+/- reps (e.g. +1)'**
  String get activePlanHintRepsOffset;

  /// No description provided for @activePlanHintFactorReps.
  ///
  /// In en, this message translates to:
  /// **'× factor (e.g. 0.9)'**
  String get activePlanHintFactorReps;

  /// No description provided for @activePlanRecalcTargetLabel.
  ///
  /// In en, this message translates to:
  /// **'Recalc target:'**
  String get activePlanRecalcTargetLabel;

  /// No description provided for @activePlanRecalcTargetAuto.
  ///
  /// In en, this message translates to:
  /// **'Auto'**
  String get activePlanRecalcTargetAuto;

  /// No description provided for @activePlanRecalcTargetReps.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get activePlanRecalcTargetReps;

  /// No description provided for @activePlanRecalcTargetRpe.
  ///
  /// In en, this message translates to:
  /// **'RPE'**
  String get activePlanRecalcTargetRpe;

  /// No description provided for @activePlanRecalcTargetIntensity.
  ///
  /// In en, this message translates to:
  /// **'Intensity'**
  String get activePlanRecalcTargetIntensity;

  /// No description provided for @activePlanValidatorLabel.
  ///
  /// In en, this message translates to:
  /// **'Validator:'**
  String get activePlanValidatorLabel;

  /// No description provided for @activePlanValidatorNone.
  ///
  /// In en, this message translates to:
  /// **'None'**
  String get activePlanValidatorNone;

  /// No description provided for @activePlanValidatorFixReps.
  ///
  /// In en, this message translates to:
  /// **'Fix reps'**
  String get activePlanValidatorFixReps;

  /// No description provided for @activePlanValidatorFixIntensity.
  ///
  /// In en, this message translates to:
  /// **'Fix intensity'**
  String get activePlanValidatorFixIntensity;

  /// No description provided for @activePlanSelectAtLeastOneExercise.
  ///
  /// In en, this message translates to:
  /// **'Select at least one exercise'**
  String get activePlanSelectAtLeastOneExercise;

  /// No description provided for @activePlanSelectAtLeastOneParameter.
  ///
  /// In en, this message translates to:
  /// **'Select at least one parameter'**
  String get activePlanSelectAtLeastOneParameter;

  /// No description provided for @activePlanPlanCancelled.
  ///
  /// In en, this message translates to:
  /// **'Plan cancelled'**
  String get activePlanPlanCancelled;

  /// No description provided for @activePlanFailedToCancelPlan.
  ///
  /// In en, this message translates to:
  /// **'Failed to cancel plan'**
  String get activePlanFailedToCancelPlan;

  /// No description provided for @activePlanExerciseIdFallback.
  ///
  /// In en, this message translates to:
  /// **'Exercise {id}'**
  String activePlanExerciseIdFallback(Object id);

  /// No description provided for @activePlanReplaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Replace exercises (from {start} to {end})'**
  String activePlanReplaceTitle(Object end, Object start);

  /// No description provided for @activePlanSelectSourceExercises.
  ///
  /// In en, this message translates to:
  /// **'Select source exercises:'**
  String get activePlanSelectSourceExercises;

  /// No description provided for @activePlanSelectTargetExercise.
  ///
  /// In en, this message translates to:
  /// **'Select target exercise'**
  String get activePlanSelectTargetExercise;

  /// No description provided for @activePlanPreserveIntensity.
  ///
  /// In en, this message translates to:
  /// **'Preserve intensity via 1RM'**
  String get activePlanPreserveIntensity;

  /// No description provided for @activePlanSelectAtLeastOneSourceExercise.
  ///
  /// In en, this message translates to:
  /// **'Select at least one source exercise'**
  String get activePlanSelectAtLeastOneSourceExercise;

  /// No description provided for @activePlanSelectTargetExerciseSnack.
  ///
  /// In en, this message translates to:
  /// **'Select a target exercise'**
  String get activePlanSelectTargetExerciseSnack;

  /// No description provided for @activePlanPreviewReplacementTitle.
  ///
  /// In en, this message translates to:
  /// **'Preview replacement'**
  String get activePlanPreviewReplacementTitle;

  /// No description provided for @activePlanPreviewTarget.
  ///
  /// In en, this message translates to:
  /// **'Target: {name}'**
  String activePlanPreviewTarget(Object name);

  /// No description provided for @activePlanPreviewExercisesToReplace.
  ///
  /// In en, this message translates to:
  /// **'Exercises to replace: {count}'**
  String activePlanPreviewExercisesToReplace(Object count);

  /// No description provided for @activePlanPreviewSetsAffected.
  ///
  /// In en, this message translates to:
  /// **'Sets affected: {count}'**
  String activePlanPreviewSetsAffected(Object count);

  /// No description provided for @activePlanDropoutReasonNotEnjoyable.
  ///
  /// In en, this message translates to:
  /// **'Not enjoyable'**
  String get activePlanDropoutReasonNotEnjoyable;

  /// No description provided for @activePlanDropoutReasonOther.
  ///
  /// In en, this message translates to:
  /// **'Other / prefer not to say'**
  String get activePlanDropoutReasonOther;

  /// No description provided for @activePlanDropoutSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get activePlanDropoutSkip;

  /// No description provided for @activePlanDropoutConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get activePlanDropoutConfirm;

  /// No description provided for @activePlanUpdatedSets.
  ///
  /// In en, this message translates to:
  /// **'Updated {count} sets'**
  String activePlanUpdatedSets(Object count);

  /// No description provided for @activePlanFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed: {error}'**
  String activePlanFailed(Object error);

  /// No description provided for @activePlanReplacementCancelledOneRmRequired.
  ///
  /// In en, this message translates to:
  /// **'Replacement cancelled: 1RM required'**
  String get activePlanReplacementCancelledOneRmRequired;

  /// No description provided for @activePlanEnterOneRmTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter 1RM for {exerciseName}'**
  String activePlanEnterOneRmTitle(Object exerciseName);

  /// No description provided for @activePlanOneRmLabel.
  ///
  /// In en, this message translates to:
  /// **'1RM (kg)'**
  String get activePlanOneRmLabel;

  /// No description provided for @activePlanOneRmHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 120'**
  String get activePlanOneRmHint;

  /// No description provided for @activePlanOneRmHelp.
  ///
  /// In en, this message translates to:
  /// **'Enter your current max for this exercise.'**
  String get activePlanOneRmHelp;

  /// No description provided for @activePlanEnterNumberGtZero.
  ///
  /// In en, this message translates to:
  /// **'Enter a number > 0'**
  String get activePlanEnterNumberGtZero;

  /// No description provided for @activePlanShiftedWorkouts.
  ///
  /// In en, this message translates to:
  /// **'Shifted {count} workouts by +{days} day(s)'**
  String activePlanShiftedWorkouts(Object count, Object days);

  /// No description provided for @activePlanShiftFailed.
  ///
  /// In en, this message translates to:
  /// **'Shift failed: {error}'**
  String activePlanShiftFailed(Object error);

  /// No description provided for @activePlanKeep.
  ///
  /// In en, this message translates to:
  /// **'Keep'**
  String get activePlanKeep;

  /// No description provided for @activePlanCancelPlan.
  ///
  /// In en, this message translates to:
  /// **'Cancel plan'**
  String get activePlanCancelPlan;

  /// No description provided for @activePlanWhyCancelling.
  ///
  /// In en, this message translates to:
  /// **'Why are you cancelling?'**
  String get activePlanWhyCancelling;

  /// No description provided for @activePlanDropoutReasonNotEnoughTime.
  ///
  /// In en, this message translates to:
  /// **'Not enough time'**
  String get activePlanDropoutReasonNotEnoughTime;

  /// No description provided for @activePlanDropoutReasonInjury.
  ///
  /// In en, this message translates to:
  /// **'Injury / pain'**
  String get activePlanDropoutReasonInjury;

  /// No description provided for @activePlanDropoutReasonTooHard.
  ///
  /// In en, this message translates to:
  /// **'Too hard'**
  String get activePlanDropoutReasonTooHard;

  /// No description provided for @activePlanReplaceSuccess.
  ///
  /// In en, this message translates to:
  /// **'Replaced {exercises} exercises, updated {sets} sets'**
  String activePlanReplaceSuccess(Object exercises, Object sets);

  /// No description provided for @activePlanReplaceFailed.
  ///
  /// In en, this message translates to:
  /// **'Replace failed: {error}'**
  String activePlanReplaceFailed(Object error);

  /// No description provided for @activePlanCancelConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Cancel active plan?'**
  String get activePlanCancelConfirmTitle;

  /// No description provided for @activePlanCancelConfirmBody.
  ///
  /// In en, this message translates to:
  /// **'This will stop tracking this applied plan. Existing workouts will remain.'**
  String get activePlanCancelConfirmBody;

  /// No description provided for @activePlanDroppedPrefix.
  ///
  /// In en, this message translates to:
  /// **'Dropped: {reason}{date}'**
  String activePlanDroppedPrefix(Object reason, Object date);

  /// No description provided for @activePlanAdherencePercent.
  ///
  /// In en, this message translates to:
  /// **'Adherence: {value}%'**
  String activePlanAdherencePercent(Object value);

  /// No description provided for @activePlanFailedToLoadAnalytics.
  ///
  /// In en, this message translates to:
  /// **'Failed to load analytics: {error}'**
  String activePlanFailedToLoadAnalytics(Object error);

  /// No description provided for @activePlanStatusActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get activePlanStatusActive;

  /// No description provided for @coachRelationshipsTitle.
  ///
  /// In en, this message translates to:
  /// **'Coach ↔ Athletes'**
  String get coachRelationshipsTitle;

  /// No description provided for @coachRelationshipsFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get coachRelationshipsFilterAll;

  /// No description provided for @coachRelationshipsFilterPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get coachRelationshipsFilterPending;

  /// No description provided for @coachRelationshipsFilterActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get coachRelationshipsFilterActive;

  /// No description provided for @coachRelationshipsFilterPaused.
  ///
  /// In en, this message translates to:
  /// **'Paused'**
  String get coachRelationshipsFilterPaused;

  /// No description provided for @coachRelationshipsFilterEnded.
  ///
  /// In en, this message translates to:
  /// **'Ended'**
  String get coachRelationshipsFilterEnded;

  /// No description provided for @coachRelationshipsError.
  ///
  /// In en, this message translates to:
  /// **'Error: {error}'**
  String coachRelationshipsError(Object error);

  /// No description provided for @coachRelationshipsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No relationships yet'**
  String get coachRelationshipsEmpty;

  /// No description provided for @coachRelationshipsAthletePrefix.
  ///
  /// In en, this message translates to:
  /// **'Athlete: {name}'**
  String coachRelationshipsAthletePrefix(Object name);

  /// No description provided for @coachRelationshipsStatusPrefix.
  ///
  /// In en, this message translates to:
  /// **'Status: {status}'**
  String coachRelationshipsStatusPrefix(Object status);

  /// No description provided for @coachRelationshipsNotePrefix.
  ///
  /// In en, this message translates to:
  /// **'Note: {note}'**
  String coachRelationshipsNotePrefix(Object note);

  /// No description provided for @coachRelationshipsChannelPrefix.
  ///
  /// In en, this message translates to:
  /// **'Channel: {channel}'**
  String coachRelationshipsChannelPrefix(Object channel);

  /// No description provided for @coachRelationshipsChannelNotCreated.
  ///
  /// In en, this message translates to:
  /// **'not created'**
  String get coachRelationshipsChannelNotCreated;

  /// No description provided for @coachRelationshipsSessions12w.
  ///
  /// In en, this message translates to:
  /// **'Sessions (12w): {count}'**
  String coachRelationshipsSessions12w(Object count);

  /// No description provided for @coachRelationshipsLastWorkout.
  ///
  /// In en, this message translates to:
  /// **'Last workout: {date}{suffix}'**
  String coachRelationshipsLastWorkout(Object date, Object suffix);

  /// No description provided for @coachRelationshipsLastWorkoutNA.
  ///
  /// In en, this message translates to:
  /// **'n/a'**
  String get coachRelationshipsLastWorkoutNA;

  /// No description provided for @coachRelationshipsDaysAgoSuffix.
  ///
  /// In en, this message translates to:
  /// **' · {days}d ago'**
  String coachRelationshipsDaysAgoSuffix(Object days);

  /// No description provided for @coachRelationshipsLoadingTrainingSummary.
  ///
  /// In en, this message translates to:
  /// **'Loading training summary...'**
  String get coachRelationshipsLoadingTrainingSummary;

  /// No description provided for @coachRelationshipsRequestAccepted.
  ///
  /// In en, this message translates to:
  /// **'Request accepted'**
  String get coachRelationshipsRequestAccepted;

  /// No description provided for @coachRelationshipsFailedToAccept.
  ///
  /// In en, this message translates to:
  /// **'Failed to accept: {error}'**
  String coachRelationshipsFailedToAccept(Object error);

  /// No description provided for @coachRelationshipsAccept.
  ///
  /// In en, this message translates to:
  /// **'Accept'**
  String get coachRelationshipsAccept;

  /// No description provided for @coachRelationshipsDecline.
  ///
  /// In en, this message translates to:
  /// **'Decline'**
  String get coachRelationshipsDecline;

  /// No description provided for @coachRelationshipsDeclineRequestTitle.
  ///
  /// In en, this message translates to:
  /// **'Decline request'**
  String get coachRelationshipsDeclineRequestTitle;

  /// No description provided for @coachRelationshipsDeclineReasonHint.
  ///
  /// In en, this message translates to:
  /// **'Reason (optional)'**
  String get coachRelationshipsDeclineReasonHint;

  /// No description provided for @coachRelationshipsRequestDeclined.
  ///
  /// In en, this message translates to:
  /// **'Request declined'**
  String get coachRelationshipsRequestDeclined;

  /// No description provided for @coachRelationshipsFailedToDecline.
  ///
  /// In en, this message translates to:
  /// **'Failed to decline: {error}'**
  String coachRelationshipsFailedToDecline(Object error);

  /// No description provided for @coachRelationshipsCoachingPaused.
  ///
  /// In en, this message translates to:
  /// **'Coaching paused'**
  String get coachRelationshipsCoachingPaused;

  /// No description provided for @coachRelationshipsFailedToPause.
  ///
  /// In en, this message translates to:
  /// **'Failed to pause: {error}'**
  String coachRelationshipsFailedToPause(Object error);

  /// No description provided for @coachRelationshipsCoachingResumed.
  ///
  /// In en, this message translates to:
  /// **'Coaching resumed'**
  String get coachRelationshipsCoachingResumed;

  /// No description provided for @coachRelationshipsFailedToResume.
  ///
  /// In en, this message translates to:
  /// **'Failed to resume: {error}'**
  String coachRelationshipsFailedToResume(Object error);

  /// No description provided for @coachRelationshipsChatTooltip.
  ///
  /// In en, this message translates to:
  /// **'Chat'**
  String get coachRelationshipsChatTooltip;

  /// No description provided for @coachRelationshipsAnalyticsTooltip.
  ///
  /// In en, this message translates to:
  /// **'Analytics'**
  String get coachRelationshipsAnalyticsTooltip;

  /// No description provided for @coachRelationshipsNudgeTooltip.
  ///
  /// In en, this message translates to:
  /// **'Nudge'**
  String get coachRelationshipsNudgeTooltip;

  /// No description provided for @coachRelationshipsPauseCoaching.
  ///
  /// In en, this message translates to:
  /// **'Pause coaching'**
  String get coachRelationshipsPauseCoaching;

  /// No description provided for @coachRelationshipsResumeCoaching.
  ///
  /// In en, this message translates to:
  /// **'Resume coaching'**
  String get coachRelationshipsResumeCoaching;

  /// No description provided for @coachRelationshipsEndCoaching.
  ///
  /// In en, this message translates to:
  /// **'End coaching'**
  String get coachRelationshipsEndCoaching;

  /// No description provided for @coachRelationshipsCoachingEnded.
  ///
  /// In en, this message translates to:
  /// **'Coaching ended'**
  String get coachRelationshipsCoachingEnded;

  /// No description provided for @coachRelationshipsFailedToEnd.
  ///
  /// In en, this message translates to:
  /// **'Failed to end: {error}'**
  String coachRelationshipsFailedToEnd(Object error);

  /// No description provided for @coachRelationshipsChatChannelNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'Chat channel is not available'**
  String get coachRelationshipsChatChannelNotAvailable;

  /// No description provided for @coachRelationshipsNudgeSent.
  ///
  /// In en, this message translates to:
  /// **'Nudge sent'**
  String get coachRelationshipsNudgeSent;

  /// No description provided for @coachRelationshipsFailedToSendNudge.
  ///
  /// In en, this message translates to:
  /// **'Failed to send nudge: {error}'**
  String coachRelationshipsFailedToSendNudge(Object error);

  /// No description provided for @coachRelationshipsNudgeMessageWithDays.
  ///
  /// In en, this message translates to:
  /// **'Hey {athleteId}, it\'s been {days} day(s) since your last workout. Let\'s plan the next session!'**
  String coachRelationshipsNudgeMessageWithDays(Object athleteId, Object days);

  /// No description provided for @coachRelationshipsNudgeMessageNoDays.
  ///
  /// In en, this message translates to:
  /// **'Hey {athleteId}, let\'s schedule our next workout soon!'**
  String coachRelationshipsNudgeMessageNoDays(Object athleteId);

  /// No description provided for @coachRelationshipsVolumeAndPlan.
  ///
  /// In en, this message translates to:
  /// **'Volume: {volume} | Active plan: {plan}'**
  String coachRelationshipsVolumeAndPlan(Object volume, Object plan);

  /// No description provided for @coachRelationshipsVolumeDash.
  ///
  /// In en, this message translates to:
  /// **'-'**
  String get coachRelationshipsVolumeDash;

  /// No description provided for @coachRelationshipsMenuAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get coachRelationshipsMenuAll;

  /// No description provided for @coachRelationshipsMenuPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get coachRelationshipsMenuPending;

  /// No description provided for @coachRelationshipsMenuActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get coachRelationshipsMenuActive;

  /// No description provided for @coachRelationshipsMenuPaused.
  ///
  /// In en, this message translates to:
  /// **'Paused'**
  String get coachRelationshipsMenuPaused;

  /// No description provided for @coachRelationshipsMenuEnded.
  ///
  /// In en, this message translates to:
  /// **'Ended'**
  String get coachRelationshipsMenuEnded;

  /// No description provided for @coachRelationshipsMenuPauseCoaching.
  ///
  /// In en, this message translates to:
  /// **'Pause coaching'**
  String get coachRelationshipsMenuPauseCoaching;

  /// No description provided for @coachRelationshipsMenuResumeCoaching.
  ///
  /// In en, this message translates to:
  /// **'Resume coaching'**
  String get coachRelationshipsMenuResumeCoaching;

  /// No description provided for @coachRelationshipsMenuEndCoaching.
  ///
  /// In en, this message translates to:
  /// **'End coaching'**
  String get coachRelationshipsMenuEndCoaching;

  /// No description provided for @planEditorTitle.
  ///
  /// In en, this message translates to:
  /// **'Editor: {name}'**
  String planEditorTitle(Object name);

  /// No description provided for @planEditorMacros.
  ///
  /// In en, this message translates to:
  /// **'Macros'**
  String get planEditorMacros;

  /// No description provided for @planEditorNoPlanId.
  ///
  /// In en, this message translates to:
  /// **'No plan ID'**
  String get planEditorNoPlanId;

  /// No description provided for @planEditorBulk.
  ///
  /// In en, this message translates to:
  /// **'Bulk ({count})'**
  String planEditorBulk(Object count);

  /// No description provided for @planEditorReplace.
  ///
  /// In en, this message translates to:
  /// **'Replace'**
  String get planEditorReplace;

  /// No description provided for @planEditorSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search exercise by name...'**
  String get planEditorSearchHint;

  /// No description provided for @planEditorMesocycles.
  ///
  /// In en, this message translates to:
  /// **'Mesocycles'**
  String get planEditorMesocycles;

  /// No description provided for @planEditorDayFilterLabel.
  ///
  /// In en, this message translates to:
  /// **'Filter: day (number, optional)'**
  String get planEditorDayFilterLabel;

  /// No description provided for @planEditorSelectTargetError.
  ///
  /// In en, this message translates to:
  /// **'Choose target exercise'**
  String get planEditorSelectTargetError;

  /// No description provided for @planEditorSelectSourceError.
  ///
  /// In en, this message translates to:
  /// **'Select at least one exercise to replace'**
  String get planEditorSelectSourceError;

  /// No description provided for @planEditorDeleteMesocycleTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete mesocycle'**
  String get planEditorDeleteMesocycleTitle;

  /// No description provided for @planEditorDeleteMesocycleBody.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete mesocycle \"{name}\" and all its microcycles?'**
  String planEditorDeleteMesocycleBody(Object name);

  /// No description provided for @planEditorDeleteMesocycle.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get planEditorDeleteMesocycle;

  /// No description provided for @planEditorMesocycleDeleted.
  ///
  /// In en, this message translates to:
  /// **'Mesocycle deleted'**
  String get planEditorMesocycleDeleted;

  /// No description provided for @planEditorDeleteFailed.
  ///
  /// In en, this message translates to:
  /// **'Delete failed: {error}'**
  String planEditorDeleteFailed(Object error);

  /// No description provided for @planEditorDeleteMesocycleTooltip.
  ///
  /// In en, this message translates to:
  /// **'Delete mesocycle'**
  String get planEditorDeleteMesocycleTooltip;

  /// No description provided for @planEditorMicroDays.
  ///
  /// In en, this message translates to:
  /// **'Days: {count}'**
  String planEditorMicroDays(Object count);

  /// No description provided for @planEditorExerciseIdFallback.
  ///
  /// In en, this message translates to:
  /// **'Exercise {id}'**
  String planEditorExerciseIdFallback(Object id);

  /// No description provided for @planEditorChangesSaved.
  ///
  /// In en, this message translates to:
  /// **'Changes saved'**
  String get planEditorChangesSaved;

  /// No description provided for @planEditorMicrocycleDeleted.
  ///
  /// In en, this message translates to:
  /// **'Microcycle deleted'**
  String get planEditorMicrocycleDeleted;

  /// No description provided for @planEditorDeleteMicrocycleTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete microcycle'**
  String get planEditorDeleteMicrocycleTitle;

  /// No description provided for @planEditorDeleteMicrocycleBody.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete microcycle \"{name}\"?'**
  String planEditorDeleteMicrocycleBody(Object name);

  /// No description provided for @planEditorDeleteMicrocycleTooltip.
  ///
  /// In en, this message translates to:
  /// **'Delete microcycle'**
  String get planEditorDeleteMicrocycleTooltip;

  /// No description provided for @planEditorMassEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Mass edits: selected microcycles'**
  String get planEditorMassEditTitle;

  /// No description provided for @planEditorSkipNoRights.
  ///
  /// In en, this message translates to:
  /// **'Skipped {count} microcycles without access rights'**
  String planEditorSkipNoRights(Object count);

  /// No description provided for @planEditorRightsCheckUnavailableApplyAll.
  ///
  /// In en, this message translates to:
  /// **'Rights check unavailable, applying to all selected: {error}'**
  String planEditorRightsCheckUnavailableApplyAll(Object error);

  /// No description provided for @planEditorMassEditsResult.
  ///
  /// In en, this message translates to:
  /// **'Mass edits: success {success}, failed {failed}'**
  String planEditorMassEditsResult(Object success, Object failed);

  /// No description provided for @coachAthletePlanTitleFallback.
  ///
  /// In en, this message translates to:
  /// **'Athlete {id}'**
  String coachAthletePlanTitleFallback(Object id);

  /// No description provided for @coachAthletePlanLoadAnalyticsError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load plan analytics: {error}'**
  String coachAthletePlanLoadAnalyticsError(Object error);

  /// No description provided for @coachAthletePlanMetricSets.
  ///
  /// In en, this message translates to:
  /// **'Sets'**
  String get coachAthletePlanMetricSets;

  /// No description provided for @coachAthletePlanMetricReps.
  ///
  /// In en, this message translates to:
  /// **'Reps'**
  String get coachAthletePlanMetricReps;

  /// No description provided for @coachAthletePlanMetricIntensity.
  ///
  /// In en, this message translates to:
  /// **'Intensity (avg)'**
  String get coachAthletePlanMetricIntensity;

  /// No description provided for @coachAthletePlanMetricEffort.
  ///
  /// In en, this message translates to:
  /// **'Effort (RPE avg)'**
  String get coachAthletePlanMetricEffort;

  /// No description provided for @coachAthletePlanAxisX.
  ///
  /// In en, this message translates to:
  /// **'Axis X'**
  String get coachAthletePlanAxisX;

  /// No description provided for @coachAthletePlanAxisY.
  ///
  /// In en, this message translates to:
  /// **'Axis Y'**
  String get coachAthletePlanAxisY;

  /// No description provided for @coachAthletePlanNoAnalytics.
  ///
  /// In en, this message translates to:
  /// **'No analytics for this plan'**
  String get coachAthletePlanNoAnalytics;

  /// No description provided for @coachAthletePlanSessionsCompleted.
  ///
  /// In en, this message translates to:
  /// **'{completed} / {planned} sessions'**
  String coachAthletePlanSessionsCompleted(Object completed, Object planned);

  /// No description provided for @coachAthletePlanPeriod.
  ///
  /// In en, this message translates to:
  /// **'Period: {start} – {end}'**
  String coachAthletePlanPeriod(Object start, Object end);

  /// No description provided for @coachAthletePlanNotes.
  ///
  /// In en, this message translates to:
  /// **'Notes: {notes}'**
  String coachAthletePlanNotes(Object notes);

  /// No description provided for @coachAthletePlanMassEditTooltip.
  ///
  /// In en, this message translates to:
  /// **'Mass edit athlete plan'**
  String get coachAthletePlanMassEditTooltip;

  /// No description provided for @coachAthletePlanMassEditMenu.
  ///
  /// In en, this message translates to:
  /// **'Mass edit (notes/day)'**
  String get coachAthletePlanMassEditMenu;

  /// No description provided for @coachAthletePlanWorkoutNotesHint.
  ///
  /// In en, this message translates to:
  /// **'Enter note for athlete'**
  String get coachAthletePlanWorkoutNotesHint;

  /// No description provided for @coachAthletePlanWorkoutRescheduled.
  ///
  /// In en, this message translates to:
  /// **'Workout rescheduled'**
  String get coachAthletePlanWorkoutRescheduled;

  /// No description provided for @coachAthletePlanWorkoutNotesUpdated.
  ///
  /// In en, this message translates to:
  /// **'Note updated'**
  String get coachAthletePlanWorkoutNotesUpdated;

  /// No description provided for @coachAthletePlanNoExercises.
  ///
  /// In en, this message translates to:
  /// **'No exercise data in this workout'**
  String get coachAthletePlanNoExercises;

  /// No description provided for @coachAthletePlanEditExercise.
  ///
  /// In en, this message translates to:
  /// **'Edit exercise'**
  String get coachAthletePlanEditExercise;

  /// No description provided for @coachAthletePlanAddExercise.
  ///
  /// In en, this message translates to:
  /// **'Add exercise'**
  String get coachAthletePlanAddExercise;

  /// No description provided for @coachAthletePlanDeleteExerciseConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete exercise?'**
  String get coachAthletePlanDeleteExerciseConfirmTitle;

  /// No description provided for @coachAthletePlanDeleteExerciseConfirmBody.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete {name} from workout?'**
  String coachAthletePlanDeleteExerciseConfirmBody(Object name);

  /// No description provided for @coachAthletePlanExerciseDeleted.
  ///
  /// In en, this message translates to:
  /// **'Exercise deleted'**
  String get coachAthletePlanExerciseDeleted;

  /// No description provided for @coachAthletePlanDeleteError.
  ///
  /// In en, this message translates to:
  /// **'Error while deleting: {error}'**
  String coachAthletePlanDeleteError(Object error);

  /// No description provided for @coachAthletePlanOrder.
  ///
  /// In en, this message translates to:
  /// **'Order: {order}'**
  String coachAthletePlanOrder(Object order);

  /// No description provided for @coachAthletePlanSets.
  ///
  /// In en, this message translates to:
  /// **'Sets: {count}'**
  String coachAthletePlanSets(Object count);

  /// No description provided for @coachAthletePlanNoSets.
  ///
  /// In en, this message translates to:
  /// **'No sets'**
  String get coachAthletePlanNoSets;

  /// No description provided for @coachAthletePlanAddSet.
  ///
  /// In en, this message translates to:
  /// **'Add set'**
  String get coachAthletePlanAddSet;

  /// No description provided for @coachAthletePlanMassEditErrorNoWorkouts.
  ///
  /// In en, this message translates to:
  /// **'No workouts for mass edits'**
  String get coachAthletePlanMassEditErrorNoWorkouts;

  /// No description provided for @coachAthletePlanMassEditErrorNoWorkoutsOnDay.
  ///
  /// In en, this message translates to:
  /// **'No workouts on selected day'**
  String get coachAthletePlanMassEditErrorNoWorkoutsOnDay;

  /// No description provided for @coachAthletePlanMassEditUpdateWorkouts.
  ///
  /// In en, this message translates to:
  /// **'Update workout notes'**
  String get coachAthletePlanMassEditUpdateWorkouts;

  /// No description provided for @coachAthletePlanMassEditUpdateExercises.
  ///
  /// In en, this message translates to:
  /// **'Update exercise notes'**
  String get coachAthletePlanMassEditUpdateExercises;

  /// No description provided for @coachAthletePlanMassEditNoChanges.
  ///
  /// In en, this message translates to:
  /// **'No changes to apply'**
  String get coachAthletePlanMassEditNoChanges;

  /// No description provided for @coachAthletePlanMassEditApplied.
  ///
  /// In en, this message translates to:
  /// **'Mass edit applied for selected day'**
  String get coachAthletePlanMassEditApplied;

  /// No description provided for @coachAthletePlanMassEditWorkoutHint.
  ///
  /// In en, this message translates to:
  /// **'New note for all workouts on this day'**
  String get coachAthletePlanMassEditWorkoutHint;

  /// No description provided for @planEditorMassReplaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Mass exercise replacement'**
  String get planEditorMassReplaceTitle;

  /// No description provided for @planEditorChooseTarget.
  ///
  /// In en, this message translates to:
  /// **'Choose target exercise'**
  String get planEditorChooseTarget;

  /// No description provided for @planEditorTargetPrefix.
  ///
  /// In en, this message translates to:
  /// **'Target: {name}'**
  String planEditorTargetPrefix(Object name);

  /// No description provided for @planEditorSelectAll.
  ///
  /// In en, this message translates to:
  /// **'Select all'**
  String get planEditorSelectAll;

  /// No description provided for @planEditorClearAll.
  ///
  /// In en, this message translates to:
  /// **'Clear all'**
  String get planEditorClearAll;

  /// No description provided for @planEditorOccurrences.
  ///
  /// In en, this message translates to:
  /// **'Occurrences: {count}'**
  String planEditorOccurrences(Object count);

  /// No description provided for @planEditorPreview.
  ///
  /// In en, this message translates to:
  /// **'Preview'**
  String get planEditorPreview;

  /// No description provided for @planEditorRightsCheckUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Rights check unavailable, continuing without it: {error}'**
  String planEditorRightsCheckUnavailable(Object error);

  /// No description provided for @planEditorNoAccessibleMicrocycles.
  ///
  /// In en, this message translates to:
  /// **'No accessible microcycles for replacement'**
  String get planEditorNoAccessibleMicrocycles;

  /// No description provided for @planEditorNoExercisesToReplace.
  ///
  /// In en, this message translates to:
  /// **'No exercises to replace'**
  String get planEditorNoExercisesToReplace;

  /// No description provided for @planEditorPreviewReplaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Replacement preview'**
  String get planEditorPreviewReplaceTitle;

  /// No description provided for @planEditorPreviewTarget.
  ///
  /// In en, this message translates to:
  /// **'Target: {name}'**
  String planEditorPreviewTarget(Object name);

  /// No description provided for @planEditorPreviewTotals.
  ///
  /// In en, this message translates to:
  /// **'Exercises to replace: {exercises}, sets affected: {sets}'**
  String planEditorPreviewTotals(Object exercises, Object sets);

  /// No description provided for @planEditorPreviewMicroStats.
  ///
  /// In en, this message translates to:
  /// **'Exercises: {ex} · Sets: {sets}'**
  String planEditorPreviewMicroStats(Object ex, Object sets);

  /// No description provided for @planEditorApplyReplaceResult.
  ///
  /// In en, this message translates to:
  /// **'Replacement: success {success}, failed {failed}'**
  String planEditorApplyReplaceResult(Object success, Object failed);

  /// No description provided for @workoutListTitle.
  ///
  /// In en, this message translates to:
  /// **'Workouts'**
  String get workoutListTitle;

  /// No description provided for @workoutListAddWorkout.
  ///
  /// In en, this message translates to:
  /// **'Add Workout'**
  String get workoutListAddWorkout;

  /// No description provided for @workoutListWorkoutName.
  ///
  /// In en, this message translates to:
  /// **'Workout Name'**
  String get workoutListWorkoutName;

  /// No description provided for @workoutListEnterNameError.
  ///
  /// In en, this message translates to:
  /// **'Please enter a workout name'**
  String get workoutListEnterNameError;

  /// No description provided for @workoutListCreateError.
  ///
  /// In en, this message translates to:
  /// **'Error creating workout: {error}'**
  String workoutListCreateError(Object error);

  /// No description provided for @workoutListNextWorkout.
  ///
  /// In en, this message translates to:
  /// **'Next Workout'**
  String get workoutListNextWorkout;

  /// No description provided for @workoutListEmpty.
  ///
  /// In en, this message translates to:
  /// **'No workouts in this progression'**
  String get workoutListEmpty;

  /// No description provided for @exerciseCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 exercise} other{{count} exercises}}'**
  String exerciseCount(num count);

  /// No description provided for @nutritionSessionsTitle.
  ///
  /// In en, this message translates to:
  /// **'Nutrition Sessions'**
  String get nutritionSessionsTitle;

  /// No description provided for @nutritionSessionsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No nutrition sessions yet'**
  String get nutritionSessionsEmpty;

  /// No description provided for @nutritionSessionsEmptyDesc.
  ///
  /// In en, this message translates to:
  /// **'Start tracking your nutrition by creating your first session'**
  String get nutritionSessionsEmptyDesc;

  /// No description provided for @nutritionSessionTitle.
  ///
  /// In en, this message translates to:
  /// **'Session {id}'**
  String nutritionSessionTitle(Object id);

  /// No description provided for @userIdLabel.
  ///
  /// In en, this message translates to:
  /// **'User ID: {id}'**
  String userIdLabel(Object id);

  /// No description provided for @entriesCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 entry} other{{count} entries}}'**
  String entriesCount(num count);

  /// No description provided for @nutritionEntriesLabel.
  ///
  /// In en, this message translates to:
  /// **'Entries'**
  String get nutritionEntriesLabel;

  /// No description provided for @nutritionNoEntries.
  ///
  /// In en, this message translates to:
  /// **'No entries'**
  String get nutritionNoEntries;

  /// No description provided for @dateLabel.
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get dateLabel;

  /// No description provided for @workoutIdLabel.
  ///
  /// In en, this message translates to:
  /// **'Workout ID'**
  String get workoutIdLabel;

  /// No description provided for @appliedPlanWorkoutIdLabel.
  ///
  /// In en, this message translates to:
  /// **'Applied Plan Workout ID'**
  String get appliedPlanWorkoutIdLabel;

  /// No description provided for @typeLabel.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get typeLabel;

  /// No description provided for @dosageLabel.
  ///
  /// In en, this message translates to:
  /// **'Dosage'**
  String get dosageLabel;

  /// No description provided for @nutritionEditSession.
  ///
  /// In en, this message translates to:
  /// **'Edit Nutrition Session'**
  String get nutritionEditSession;

  /// No description provided for @nutritionCreateSession.
  ///
  /// In en, this message translates to:
  /// **'Create Nutrition Session'**
  String get nutritionCreateSession;

  /// No description provided for @nutritionSessionConfig.
  ///
  /// In en, this message translates to:
  /// **'Session Configuration'**
  String get nutritionSessionConfig;

  /// No description provided for @nutritionSessionId.
  ///
  /// In en, this message translates to:
  /// **'Session ID'**
  String get nutritionSessionId;

  /// No description provided for @workoutIdOptional.
  ///
  /// In en, this message translates to:
  /// **'Workout ID (optional)'**
  String get workoutIdOptional;

  /// No description provided for @appliedPlanWorkoutIdOptional.
  ///
  /// In en, this message translates to:
  /// **'Applied Plan Workout ID (optional)'**
  String get appliedPlanWorkoutIdOptional;

  /// No description provided for @nutritionSelectedEntries.
  ///
  /// In en, this message translates to:
  /// **'Selected Entries'**
  String get nutritionSelectedEntries;

  /// No description provided for @nutritionNoEntriesSelected.
  ///
  /// In en, this message translates to:
  /// **'No entries selected'**
  String get nutritionNoEntriesSelected;

  /// No description provided for @nutritionAvailableItems.
  ///
  /// In en, this message translates to:
  /// **'Available Items'**
  String get nutritionAvailableItems;

  /// No description provided for @foodLabel.
  ///
  /// In en, this message translates to:
  /// **'Food'**
  String get foodLabel;

  /// No description provided for @supplementsLabel.
  ///
  /// In en, this message translates to:
  /// **'Supplements'**
  String get supplementsLabel;

  /// No description provided for @medicationsLabel.
  ///
  /// In en, this message translates to:
  /// **'Medications'**
  String get medicationsLabel;

  /// No description provided for @nutritionNoItemsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No items available'**
  String get nutritionNoItemsAvailable;

  /// No description provided for @updateSession.
  ///
  /// In en, this message translates to:
  /// **'Update Session'**
  String get updateSession;

  /// No description provided for @createSession.
  ///
  /// In en, this message translates to:
  /// **'Create Session'**
  String get createSession;

  /// No description provided for @exerciseListEmptyDesc.
  ///
  /// In en, this message translates to:
  /// **'Try changing the filter or add a new exercise'**
  String get exerciseListEmptyDesc;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'uk'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'uk':
      return AppLocalizationsUk();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}

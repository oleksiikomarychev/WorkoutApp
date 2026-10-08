// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Ukrainian (`uk`).
class AppLocalizationsUk extends AppLocalizations {
  AppLocalizationsUk([String locale = 'uk']) : super(locale);

  @override
  String get appTitle => 'Workout App';

  @override
  String get missingAthleteId => 'Відсутній athleteId';

  @override
  String get missingChatArguments => 'Відсутні аргументи чату';

  @override
  String get fieldRequired => 'Обовʼязково';

  @override
  String get exerciseName => 'Назва вправи';

  @override
  String get exerciseListEmptyNameError => 'Будь ласка, введіть назву вправи';

  @override
  String activePlanLoadError(Object error) {
    return 'Не вдалося завантажити план: $error';
  }

  @override
  String get activePlanNoWorkoutsOnDay => 'Немає тренувань на цей день';

  @override
  String get activePlanNotesLabel => 'Примітки';

  @override
  String get coachAthletePlanNoActivePlan => 'Немає активного плану';

  @override
  String get coachAthletePlanSetsLabel => 'Підходи';

  @override
  String get coachAthletePlanMassEditExerciseHint =>
      'Введіть примітку для вправ';

  @override
  String coachAthletePlanMassEditError(Object error) {
    return 'Помилка масового редагування: $error';
  }

  @override
  String get search => 'Пошук...';

  @override
  String get done => 'Готово';

  @override
  String get refresh => 'Оновити';

  @override
  String get edit => 'Редагувати';

  @override
  String get delete => 'Видалити';

  @override
  String get apply => 'Застосувати';

  @override
  String get cancel => 'Скасувати';

  @override
  String get retry => 'Повторити';

  @override
  String get hide => 'Приховати';

  @override
  String get noDate => 'без дати';

  @override
  String idPrefix(Object id) {
    return 'ID: $id';
  }

  @override
  String get filter => 'Фільтр';

  @override
  String get changes => 'Зміни';

  @override
  String statuses(Object statuses) {
    return 'Статуси: $statuses';
  }

  @override
  String exercises(Object exercises) {
    return 'Вправи: $exercises';
  }

  @override
  String workoutsAffected(Object count) {
    return 'Тренувань затронуто: $count';
  }

  @override
  String workoutsShifted(Object count) {
    return 'Тренувань зсунуто: $count';
  }

  @override
  String setsModified(Object count) {
    return 'Сетів змінено: $count';
  }

  @override
  String setsToBeModified(Object count) {
    return 'Сетів буде змінено: $count';
  }

  @override
  String shiftDays(Object sign, Object days) {
    return 'Зсув: $sign$days дн.';
  }

  @override
  String startingFrom(Object date) {
    return 'Починаючи з: $date';
  }

  @override
  String upToDate(Object date) {
    return 'До дати (включно): $date';
  }

  @override
  String get onlyFutureWorkouts => 'Тільки майбутні тренування';

  @override
  String dateNotEarlierThan(Object date) {
    return 'Дата не раніше $date';
  }

  @override
  String dateNotLaterThan(Object date) {
    return 'Дата не пізніше $date';
  }

  @override
  String get clampNonNegative => 'Не допускати від\'ємних значень';

  @override
  String replaceExerciseTo(Object name, Object id) {
    return 'Замінити вправу на $name (ID $id)';
  }

  @override
  String renameExerciseTo(Object name) {
    return 'Перейменувати вправу на \"$name\"';
  }

  @override
  String addNewExercises(Object count) {
    return 'Додати нових вправ: $count';
  }

  @override
  String setIntensity(Object value) {
    return 'Встановити інтенсивність = $value';
  }

  @override
  String increaseIntensityBy(Object value) {
    return 'Збільшити інтенсивність на $value';
  }

  @override
  String decreaseIntensityBy(Object value) {
    return 'Зменшити інтенсивність на $value';
  }

  @override
  String setVolume(Object value) {
    return 'Встановити повторення = $value';
  }

  @override
  String increaseVolumeBy(Object value) {
    return 'Збільшити повторення на $value';
  }

  @override
  String decreaseVolumeBy(Object value) {
    return 'Зменшити повторення на $value';
  }

  @override
  String setWeight(Object value) {
    return 'Встановити вагу = $value кг';
  }

  @override
  String increaseWeightBy(Object value) {
    return 'Збільшити вагу на $value кг';
  }

  @override
  String decreaseWeightBy(Object value) {
    return 'Зменшити вагу на $value кг';
  }

  @override
  String setEffort(Object value) {
    return 'Встановити RPE = $value';
  }

  @override
  String increaseEffortBy(Object value) {
    return 'Збільшити RPE на $value';
  }

  @override
  String decreaseEffortBy(Object value) {
    return 'Зменшити RPE на $value';
  }

  @override
  String get massEditPreviewTitle =>
      'Попередній перегляд масових змін активного плану';

  @override
  String get massEditAppliedTitle => 'Зміни активного плану застосовані';

  @override
  String get scheduleShiftPreviewTitle =>
      'Попередній перегляд зсуву розкладу активного плану';

  @override
  String get scheduleShiftTitle => 'Зсув розкладу активного плану виконано';

  @override
  String get shiftParameters => 'Параметри зсуву';

  @override
  String get modeChangeIntervals => 'Режим: змінити інтервали між тренуваннями';

  @override
  String get modeScheduleShift => 'Режим: зсув розкладу';

  @override
  String get macroActionByPercent => 'За відсотком';

  @override
  String get macroActionToTarget => 'До цільового (RPE)';

  @override
  String get macroActionByValue => 'За значенням';

  @override
  String get macroActionByTemplate => 'За шаблоном';

  @override
  String get macroActionByExisting => 'З існуючого (ID)';

  @override
  String get macroActionCreateManual => 'Створити вручну';

  @override
  String get macroActionHintPercent => 'відсоток, напр. -5 або 2.5';

  @override
  String get macroActionHintReps => 'дельта повторень, напр. +1 або -1';

  @override
  String get macroActionHintTargetRpe => 'цільовий RPE, напр. 8';

  @override
  String get macroActionHintSets => '±N підходів, напр. 1 або -2';

  @override
  String get macroActionHintGeneric => 'значення';

  @override
  String get macroActionAdjustLoad => 'Коригувати вагу';

  @override
  String get macroActionAdjustReps => 'Коригувати повторення';

  @override
  String get macroActionAdjustSets => 'Коригувати підходи';

  @override
  String get macroActionInjectMesocycle => 'Впровадити мезоцикл';

  @override
  String get macroActionTypeLabel => 'Тип дії';

  @override
  String get macroActionModeLabel => 'Режим';

  @override
  String get macroActionValueLabel => 'Значення';

  @override
  String get macroActionNoTemplates => 'Немає шаблонів мезоциклів';

  @override
  String get macroActionTemplateLabel => 'Шаблон мезоциклу';

  @override
  String macroActionLoadTemplatesError(Object error) {
    return 'Помилка завантаження шаблонів: $error';
  }

  @override
  String macroActionMesoLabel(Object index) {
    return 'Мезоцикл $index';
  }

  @override
  String get macroActionChooseMeso => 'Вибрати мезоцикл';

  @override
  String get macroActionOtherId => 'Інший (ввести ID)';

  @override
  String get macroActionExistingIdLabel => 'ID існуючого мезоцикла';

  @override
  String get macroActionEnterNumber => 'Введіть число';

  @override
  String get macroActionDurationWeeks => 'Тривалість (тижнів)';

  @override
  String get macroActionDaysInMicro => 'Днів у мікроциклі';

  @override
  String macroActionDayLabel(Object index, Object type) {
    return 'День $index: $type';
  }

  @override
  String get macroActionRest => 'вихідний';

  @override
  String get macroActionWork => 'тренування';

  @override
  String get macroActionFocusTags => 'Теги фокусу';

  @override
  String get macroActionPlacement => 'Розміщення';

  @override
  String get macroActionAppendEnd => 'В кінець плану';

  @override
  String get macroActionInsertAfterWorkout => 'Після тренування';

  @override
  String get macroActionInsertAfterMeso => 'Після мезоциклу';

  @override
  String get macroActionSelectAnchorWorkout => 'Вибрати тренування-якір';

  @override
  String get macroActionPickWorkout => 'Вибрати тренування';

  @override
  String get macroActionNotSelected => 'Не вибрано';

  @override
  String macroActionAfterAnchor(Object name) {
    return 'Після: $name';
  }

  @override
  String get macroActionNoMesoInPlan => 'В плані немає мезоциклів';

  @override
  String get macroActionMesoIndexLabel => 'Мезоцикл: ';

  @override
  String get macroActionConflicts => 'Конфлікти';

  @override
  String get macroActionReplacePlanned => 'Замінити заплановане';

  @override
  String get macroActionShiftForward => 'Зсунути вперед';

  @override
  String get macroActionSkipConflict => 'Пропустити конфлікт';

  @override
  String get macroActionTarget => 'Ціль';

  @override
  String get macroActionTargetHelp =>
      'Якщо ціль не вказана — дія застосовується до всіх вправ вибраних тренувань.';

  @override
  String get macroConditionGreater => 'більше >';

  @override
  String get macroConditionLess => 'менше <';

  @override
  String get macroConditionEqual => 'рівно =';

  @override
  String get macroConditionNotEqual => 'не рівно ≠';

  @override
  String get macroConditionInRange => 'в діапазоні';

  @override
  String get macroConditionNotInRange => 'поза діапазоном';

  @override
  String get macroConditionStagnates => 'стагнація за N вікон';

  @override
  String get macroConditionDeviates => 'відхилення від середнього';

  @override
  String get macroConditionHoldsForWorkouts =>
      'виконується N тренувань поспіль';

  @override
  String get macroConditionHoldsForSets =>
      'виконується N підходів поспіль (всередині тренування)';

  @override
  String get macroConditionOperatorLabel => 'Оператор';

  @override
  String get macroConditionRangeFrom => 'від';

  @override
  String get macroConditionNumberHint => 'число';

  @override
  String get macroConditionRangeTo => 'до';

  @override
  String get macroConditionWindowCount => 'n (вікон)';

  @override
  String get macroConditionWindowCountHint => 'ціле число, наприклад 5';

  @override
  String get macroConditionEpsilonPercent => 'epsilon_percent (поріг, %)';

  @override
  String get macroConditionValuePercent => 'value_percent (відхил., %)';

  @override
  String get macroConditionPositive => 'позитивне';

  @override
  String get macroConditionNegative => 'негативне';

  @override
  String get macroConditionDirection => 'напрямок (необов\'язково)';

  @override
  String get macroConditionGreaterEqual => 'більше або рівно ≥';

  @override
  String get macroConditionLessEqual => 'менше або рівно ≤';

  @override
  String get macroConditionRelationLabel => 'порівняння';

  @override
  String get macroConditionWorkoutCount => 'n (тренувань)';

  @override
  String get macroConditionWorkoutCountHint => 'ціле, наприклад 3';

  @override
  String get macroConditionDeltaHint => 'дельта, наприклад -2 для повторів';

  @override
  String get macroConditionSetCount => 'n (підряд підходів)';

  @override
  String get macroConditionSetCountHint => 'ціле, наприклад 12';

  @override
  String get macroConditionValueLabel => 'значення';

  @override
  String get macroDurationNextNWorkouts => 'Наступні N тренувань';

  @override
  String get macroDurationUntilLastWorkout => 'До останнього тренування';

  @override
  String get macroDurationUntilEndOfMeso => 'До кінця мезоциклу';

  @override
  String get macroDurationUntilEndOfMicro => 'До кінця мікроциклу';

  @override
  String get macroDurationUntilWorkoutX => 'До тренування X';

  @override
  String get macroDurationScopeLabel => 'Область';

  @override
  String get macroDurationCountLabel => 'Кількість';

  @override
  String get macroTargetBy => 'Ціль за:';

  @override
  String get macroTargetTags => 'Теги';

  @override
  String get macroTargetIds => 'ID';

  @override
  String get macroTargetIdsLabel => 'exercise_ids (CSV)';

  @override
  String get macroTriggerChooseExercises => 'Вибір вправ';

  @override
  String get macroTriggerMetricReadiness => 'Готовність (тренування)';

  @override
  String get macroTriggerMetricRpeSession => 'RPE сесії';

  @override
  String get macroTriggerMetricTotalReps => 'Кількість повторень';

  @override
  String get macroTriggerMetricE1rm => 'Оцінка 1ПМ (e1RM)';

  @override
  String get macroTriggerMetricPerformanceTrend => 'Тренд продуктивності';

  @override
  String get macroTriggerMetricRpeDelta => 'Дельта RPE від плану';

  @override
  String get macroTriggerMetricRepsDelta => 'Дельта повторень від плану';

  @override
  String get macroTriggerMetricLabel => 'Метрика тригера';

  @override
  String get macroWorkoutPickerTitle => 'Виберіть тренування';

  @override
  String get macroWorkoutPickerNoWorkouts =>
      'Немає тренувань в активному плані';

  @override
  String get macroWorkoutPickerNoWorkoutsOnDate => 'На цю дату немає тренувань';

  @override
  String get macroWorkoutPickerOrChooseFromList => 'Або вибрати зі списку';

  @override
  String get macroWorkoutPickerListButton => 'Список';

  @override
  String get macroWorkoutPickerWorkoutsOnDate => 'Тренування на цю дату';

  @override
  String get macroWorkoutPickerOrSelectFromList => 'Або вибрати зі списку';

  @override
  String get macroWorkoutPickerList => 'Список';

  @override
  String analyticsPlanTitle(Object planName) {
    return 'Аналітика плану $planName';
  }

  @override
  String get errorLoadingActivePlan => 'Не вдалося отримати активний план';

  @override
  String get selectTwoMetrics => 'Оберіть дві метрики';

  @override
  String get activePlanNotFound => 'Активний план не знайдено';

  @override
  String get errorLoadingData => 'Помилка завантаження даних';

  @override
  String get axisX => 'Вісь X';

  @override
  String get axisY => 'Вісь Y';

  @override
  String get showChart => 'Показати графік';

  @override
  String get selectRangeAndMetrics => 'Оберіть діапазон і метрики';

  @override
  String get noDataForSelectedMetrics => 'Немає даних для вибраних метрик';

  @override
  String get metricVolumeKg => 'Обсяг (кг)';

  @override
  String get metricEffortRpe => 'Зусилля (RPE)';

  @override
  String get metricKpsh => 'КПШ';

  @override
  String get metricReps => 'Повтори';

  @override
  String get metricOneRm => '1RM';

  @override
  String get language => 'Мова';

  @override
  String get languageSystem => 'Системна';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageUkrainian => 'Українська';

  @override
  String get accountTitle => 'Профіль';

  @override
  String get editProfileTitle => 'Редагувати профіль';

  @override
  String get displayName => 'Імʼя';

  @override
  String get bio => 'Про себе';

  @override
  String get bodyweightKg => 'Вага (кг)';

  @override
  String get heightCm => 'Зріст (см)';

  @override
  String get age => 'Вік';

  @override
  String get trainingYears => 'Стаж тренувань';

  @override
  String get publicProfile => 'Публічний профіль';

  @override
  String get units => 'Одиниці';

  @override
  String get unitsMetric => 'Метрична';

  @override
  String get unitsImperial => 'Імперська';

  @override
  String get timezone => 'Часовий пояс';

  @override
  String get notifications => 'Сповіщення';

  @override
  String get save => 'Зберегти';

  @override
  String get profileUpdated => 'Профіль оновлено';

  @override
  String get failedToUpdateProfile => 'Не вдалося оновити профіль';

  @override
  String get editProfileButton => 'Редагувати профіль';

  @override
  String get coachingSettingsButton => 'Налаштування коучингу';

  @override
  String get coachingTitle => 'Коучинг';

  @override
  String get coachingAcceptingNewClients => 'Приймає нових клієнтів';

  @override
  String get coachingNotAccepting => 'Не приймає';

  @override
  String get coachingDisabled => 'Коучинг вимкнено';

  @override
  String get coachingDisabledDescription =>
      'Користувач не ввімкнув опції коучингу.';

  @override
  String get coachingSpecializations => 'Спеціалізації';

  @override
  String get coachingLanguages => 'Мови';

  @override
  String get coachingExperience => 'Досвід';

  @override
  String get coachingTimezone => 'Часовий пояс';

  @override
  String get coachingRate => 'Тариф';

  @override
  String get coachingCustomRate => 'Індивідуальний тариф';

  @override
  String get requestCoaching => 'Запит на коучинг';

  @override
  String get statsTotalWorkouts => 'Всього тренувань';

  @override
  String get statsVolumeKg => 'Обсяг (кг)';

  @override
  String get statsActiveDays => 'Активні дні';

  @override
  String get activityTitle => 'Активність';

  @override
  String lastWeeks(Object weeks) {
    return 'Останні $weeks тижнів';
  }

  @override
  String maxKgPerDay(Object value) {
    return 'Макс: $value кг/день';
  }

  @override
  String sessionsCount(Object count) {
    return '$count сесій';
  }

  @override
  String get noActivity => 'Немає активності';

  @override
  String get less => 'Менше';

  @override
  String get more => 'Більше';

  @override
  String get completedWorkoutsTitle => 'Завершені тренування';

  @override
  String get noCompletedWorkoutsYet => 'Ще немає завершених тренувань';

  @override
  String get exerciseFormTitleAdd => 'Додати вправу';

  @override
  String get exerciseFormExerciseNameLabel => 'Назва вправи';

  @override
  String get exerciseFormPleaseEnterName => 'Будь ласка, введіть назву';

  @override
  String get exerciseFormMuscleGroupLabel => 'Група мʼязів';

  @override
  String get exerciseFormLoading => 'Завантаження...';

  @override
  String get exerciseFormSelectGroup => 'Оберіть групу';

  @override
  String get exerciseFormLoadingGroups => 'Завантаження груп...';

  @override
  String get exerciseFormPleaseSelectMuscleGroup =>
      'Будь ласка, оберіть групу мʼязів';

  @override
  String get exerciseFormProgressionTemplateOptional =>
      'Шаблон прогресії (необовʼязково)';

  @override
  String get exerciseFormSelectTemplate => 'Оберіть шаблон';

  @override
  String get exerciseFormNoTemplate => 'Без шаблону';

  @override
  String get exerciseFormSetsTitle => 'Сети';

  @override
  String get exerciseFormAddSet => 'Додати сет';

  @override
  String get exerciseFormSaveExercise => 'Зберегти вправу';

  @override
  String get exerciseFormWeightKg => 'Вага (кг)';

  @override
  String get exerciseFormReps => 'Повтори';

  @override
  String get exerciseFormRequired => 'Обовʼязково';

  @override
  String exerciseFormFailedToLoadData(Object error) {
    return 'Не вдалося завантажити дані: $error';
  }

  @override
  String exerciseFormErrorSaving(Object error) {
    return 'Помилка збереження: $error';
  }

  @override
  String get exerciseDefinitionIdRequired => 'Потрібен id визначення вправи';

  @override
  String get exerciseFormDefaultReps => '5';

  @override
  String get exerciseFormDefaultWeight => '0';

  @override
  String get exerciseListTitle => 'Вправи';

  @override
  String get exerciseListAddExerciseTitle => 'Додати вправу';

  @override
  String get exerciseListNameLabel => 'Назва';

  @override
  String get exerciseListMuscleGroupLabel => 'Група мʼязів';

  @override
  String get exerciseListEquipmentLabel => 'Обладнання';

  @override
  String get exerciseListLoading => 'Завантаження...';

  @override
  String get exerciseListSelectGroup => 'Оберіть групу';

  @override
  String get exerciseListLoadingGroups => 'Завантаження груп...';

  @override
  String get exerciseListSelectMuscleGroupValidator => 'Оберіть групу мʼязів';

  @override
  String get exerciseListEnterExerciseName => 'Введіть назву вправи';

  @override
  String get exerciseListSelectMuscleGroupSnack => 'Оберіть групу мʼязів';

  @override
  String exerciseListErrorLoadingMuscleGroups(Object error) {
    return 'Не вдалося завантажити групи мʼязів: $error';
  }

  @override
  String exerciseListErrorGeneric(Object error) {
    return 'Помилка: $error';
  }

  @override
  String get exerciseListEmpty => 'Немає вправ. Додайте нову!';

  @override
  String exerciseListMuscleGroupPrefix(Object value) {
    return 'Група мʼязів: $value';
  }

  @override
  String exerciseListEquipmentPrefix(Object value) {
    return 'Обладнання: $value';
  }

  @override
  String get exerciseListDeleteExerciseTitle => 'Видалити вправу?';

  @override
  String get exerciseListDeleteExerciseBody => 'Цю дію не можна скасувати.';

  @override
  String get exerciseListDelete => 'Видалити';

  @override
  String exerciseListErrorDeleting(Object error) {
    return 'Не вдалося видалити: $error';
  }

  @override
  String get userMaxTitle => 'Додати максимум';

  @override
  String get userMaxExerciseLabel => 'Вправа';

  @override
  String get userMaxSelectExerciseValidator => 'Оберіть вправу';

  @override
  String get userMaxWeightKgLabel => 'Вага (кг)';

  @override
  String get userMaxWeightGtZeroValidator => 'Введіть вагу > 0';

  @override
  String get userMaxRepsLabel => 'Повтори';

  @override
  String get userMaxRepsGtZeroValidator => 'Введіть повтори > 0';

  @override
  String get userMaxRepsMax12Validator => 'Максимум 12 повторів';

  @override
  String get userMaxFillAllFieldsSnack =>
      'Заповніть усі поля та оберіть вправу';

  @override
  String get userMaxSaving => 'Збереження...';

  @override
  String get userMaxSave => 'Зберегти максимум';

  @override
  String userMaxFailedToSave(Object error) {
    return 'Не вдалося зберегти максимум: $error';
  }

  @override
  String get yes => 'Так';

  @override
  String get no => 'Ні';

  @override
  String get planDraftMicrocycle => 'Мікроцикл';

  @override
  String get planDraftMesocycle => 'Мезоцикл';

  @override
  String massEditToolWorkoutsMatched(Object count) {
    return 'Тренувань затронуто: $count';
  }

  @override
  String massEditToolSetsModified(Object count) {
    return 'Сетів змінено: $count';
  }

  @override
  String massEditToolSetsToBeModified(Object count) {
    return 'Сетів буде змінено: $count';
  }

  @override
  String get workoutDetailMacrosChangesFoundTitle =>
      'Знайдено зміни по макросах';

  @override
  String workoutDetailMacrosChangesFoundBody(
    Object injectCount,
    Object hasPatches,
  ) {
    return 'Вставок мезоциклів: $injectCount\nПатчі на тренування: $hasPatches';
  }

  @override
  String get workoutDetailMacrosApplied => 'Макроси застосовано';

  @override
  String workoutDetailFailedToApplyMacros(Object error) {
    return 'Не вдалося застосувати макроси: $error';
  }

  @override
  String get workoutDetailFailedToRefreshWorkoutBeforeApplyingReadiness =>
      'Не вдалося оновити тренування перед застосуванням готовності';

  @override
  String get workoutDetailWorkoutNotReadyMissingIds =>
      'Тренування не готове до оновлення сетів (відсутні id)';

  @override
  String get workoutDetailIncreaseTooltip => 'Збільшити';

  @override
  String get workoutDetailSessionActive => 'Активна сесія';

  @override
  String get workoutDetailSessionNone => 'Немає активної сесії';

  @override
  String get workoutDetailSelectSetTypeTitle => 'Оберіть тип сета';

  @override
  String get workoutDetailSetTypeNormal => 'Звичайний сет';

  @override
  String get workoutDetailSetTypeDrop => 'Дроп-сет';

  @override
  String get workoutDetailSetTypeCluster => 'Кластерний сет';

  @override
  String get workoutDetailSetTypeRestPause => 'Rest-pause сет';

  @override
  String workoutDetailFailedToUpdateSetType(Object error) {
    return 'Не вдалося оновити тип сета: $error';
  }

  @override
  String get activePlanTitle => 'Активний план';

  @override
  String activePlanFailedToLoad(Object error) {
    return 'Не вдалося завантажити активний план: $error';
  }

  @override
  String get activePlanNone => 'Немає активного плану';

  @override
  String get activePlanAiMassEditTitle => 'AI mass edit (chat)';

  @override
  String get activePlanAiMassEditHint =>
      'Наприклад: Збільш RPE на 1 і додай по 1 підходу у всіх жимах по понеділках';

  @override
  String get activePlanAiMassEditSend => 'Надіслати';

  @override
  String activePlanAiMassEditStarted(Object taskId) {
    return 'AI mass edit запущено (task: $taskId)';
  }

  @override
  String activePlanAiMassEditFailedToSend(Object error) {
    return 'Не вдалося надіслати команду AI mass edit: $error';
  }

  @override
  String activePlanMassEditTitle(Object end, Object start) {
    return 'Масове редагування (з $start по $end)';
  }

  @override
  String get activePlanRangeLabel => 'Діапазон:';

  @override
  String get activePlanRangeFutureFromWeek => 'Майбутнє від тижня';

  @override
  String get activePlanRangeByMesoMicro => 'За мезо/мікро';

  @override
  String get activePlanIntensityLabel => 'Інтенсивність %';

  @override
  String get activePlanRpeLabel => 'RPE';

  @override
  String get activePlanRepsLabel => 'Повтори';

  @override
  String get activePlanModeSet => 'Задати';

  @override
  String get activePlanModeOffset => 'Зсув';

  @override
  String get activePlanModeScale => 'Масштаб';

  @override
  String get activePlanHintEg75 => 'напр. 75';

  @override
  String get activePlanHintPercentOffset => '+/- % (напр. -2)';

  @override
  String get activePlanHintFactor => '× коефіцієнт (напр. 1.05)';

  @override
  String get activePlanHintEg8 => 'напр. 8';

  @override
  String get activePlanHintEg5 => 'напр. 5';

  @override
  String get activePlanHintRepsOffset => '+/- повтори (напр. +1)';

  @override
  String get activePlanHintFactorReps => '× коефіцієнт (напр. 0.9)';

  @override
  String get activePlanRecalcTargetLabel => 'Перерахувати:';

  @override
  String get activePlanRecalcTargetAuto => 'Авто';

  @override
  String get activePlanRecalcTargetReps => 'Повтори';

  @override
  String get activePlanRecalcTargetRpe => 'RPE';

  @override
  String get activePlanRecalcTargetIntensity => 'Інтенсивність';

  @override
  String get activePlanValidatorLabel => 'Валідатор:';

  @override
  String get activePlanValidatorNone => 'Немає';

  @override
  String get activePlanValidatorFixReps => 'Фіксувати повтори';

  @override
  String get activePlanValidatorFixIntensity => 'Фіксувати інтенсивність';

  @override
  String get activePlanSelectAtLeastOneExercise => 'Оберіть хоча б одну вправу';

  @override
  String get activePlanSelectAtLeastOneParameter =>
      'Оберіть хоча б один параметр';

  @override
  String get activePlanPlanCancelled => 'План скасовано';

  @override
  String get activePlanFailedToCancelPlan => 'Не вдалося скасувати план';

  @override
  String activePlanExerciseIdFallback(Object id) {
    return 'Вправа $id';
  }

  @override
  String activePlanReplaceTitle(Object end, Object start) {
    return 'Заміна вправ (з $start по $end)';
  }

  @override
  String get activePlanSelectSourceExercises => 'Оберіть вправи для заміни:';

  @override
  String get activePlanSelectTargetExercise => 'Оберіть цільову вправу';

  @override
  String get activePlanPreserveIntensity => 'Зберегти інтенсивність через 1RM';

  @override
  String get activePlanSelectAtLeastOneSourceExercise =>
      'Оберіть хоча б одну вправу для заміни';

  @override
  String get activePlanSelectTargetExerciseSnack => 'Оберіть цільову вправу';

  @override
  String get activePlanPreviewReplacementTitle => 'Попередній перегляд заміни';

  @override
  String activePlanPreviewTarget(Object name) {
    return 'Ціль: $name';
  }

  @override
  String activePlanPreviewExercisesToReplace(Object count) {
    return 'Вправ до заміни: $count';
  }

  @override
  String activePlanPreviewSetsAffected(Object count) {
    return 'Зачеплено сетів: $count';
  }

  @override
  String get activePlanDropoutReasonNotEnjoyable => 'Не сподобалось';

  @override
  String get activePlanDropoutReasonOther => 'Інше / не хочу відповідати';

  @override
  String get activePlanDropoutSkip => 'Пропустити';

  @override
  String get activePlanDropoutConfirm => 'Підтвердити';

  @override
  String activePlanUpdatedSets(Object count) {
    return 'Оновлено $count сетів';
  }

  @override
  String activePlanFailed(Object error) {
    return 'Помилка: $error';
  }

  @override
  String get activePlanReplacementCancelledOneRmRequired =>
      'Заміна скасована: потрібен 1RM';

  @override
  String activePlanEnterOneRmTitle(Object exerciseName) {
    return 'Введіть 1RM для $exerciseName';
  }

  @override
  String get activePlanOneRmLabel => '1RM (кг)';

  @override
  String get activePlanOneRmHint => 'напр. 120';

  @override
  String get activePlanOneRmHelp =>
      'Введіть ваш поточний максимум для цієї вправи.';

  @override
  String get activePlanEnterNumberGtZero => 'Введіть число > 0';

  @override
  String activePlanShiftedWorkouts(Object count, Object days) {
    return 'Зміщено $count тренувань на +$days дн.';
  }

  @override
  String activePlanShiftFailed(Object error) {
    return 'Не вдалося змістити: $error';
  }

  @override
  String get activePlanKeep => 'Залишити';

  @override
  String get activePlanCancelPlan => 'Скасувати план';

  @override
  String get activePlanWhyCancelling => 'Чому ви скасовуєте?';

  @override
  String get activePlanDropoutReasonNotEnoughTime => 'Немає часу';

  @override
  String get activePlanDropoutReasonInjury => 'Травма / біль';

  @override
  String get activePlanDropoutReasonTooHard => 'Занадто складно';

  @override
  String activePlanReplaceSuccess(Object exercises, Object sets) {
    return 'Замінено $exercises вправ, оновлено $sets сетів';
  }

  @override
  String activePlanReplaceFailed(Object error) {
    return 'Помилка заміни: $error';
  }

  @override
  String get activePlanCancelConfirmTitle => 'Скасувати активний план?';

  @override
  String get activePlanCancelConfirmBody =>
      'Це припинить відстеження цього застосованого плану. Існуючі тренування залишаться.';

  @override
  String activePlanDroppedPrefix(Object reason, Object date) {
    return 'Припинено: $reason$date';
  }

  @override
  String activePlanAdherencePercent(Object value) {
    return 'Дотримання: $value%';
  }

  @override
  String activePlanFailedToLoadAnalytics(Object error) {
    return 'Не вдалося завантажити аналітику: $error';
  }

  @override
  String get activePlanStatusActive => 'Активний';

  @override
  String get coachRelationshipsTitle => 'Коуч ↔ Атлети';

  @override
  String get coachRelationshipsFilterAll => 'Усі';

  @override
  String get coachRelationshipsFilterPending => 'Очікує';

  @override
  String get coachRelationshipsFilterActive => 'Активні';

  @override
  String get coachRelationshipsFilterPaused => 'Пауза';

  @override
  String get coachRelationshipsFilterEnded => 'Завершено';

  @override
  String coachRelationshipsError(Object error) {
    return 'Помилка: $error';
  }

  @override
  String get coachRelationshipsEmpty => 'Поки що немає звʼязків';

  @override
  String coachRelationshipsAthletePrefix(Object name) {
    return 'Атлет: $name';
  }

  @override
  String coachRelationshipsStatusPrefix(Object status) {
    return 'Статус: $status';
  }

  @override
  String coachRelationshipsNotePrefix(Object note) {
    return 'Нотатка: $note';
  }

  @override
  String coachRelationshipsChannelPrefix(Object channel) {
    return 'Канал: $channel';
  }

  @override
  String get coachRelationshipsChannelNotCreated => 'не створено';

  @override
  String coachRelationshipsSessions12w(Object count) {
    return 'Сесії (12 тиж): $count';
  }

  @override
  String coachRelationshipsLastWorkout(Object date, Object suffix) {
    return 'Останнє тренування: $date$suffix';
  }

  @override
  String get coachRelationshipsLastWorkoutNA => 'н/д';

  @override
  String coachRelationshipsDaysAgoSuffix(Object days) {
    return ' · $daysд тому';
  }

  @override
  String get coachRelationshipsLoadingTrainingSummary =>
      'Завантаження підсумку...';

  @override
  String get coachRelationshipsRequestAccepted => 'Запит прийнято';

  @override
  String coachRelationshipsFailedToAccept(Object error) {
    return 'Не вдалося прийняти: $error';
  }

  @override
  String get coachRelationshipsAccept => 'Прийняти';

  @override
  String get coachRelationshipsDecline => 'Відхилити';

  @override
  String get coachRelationshipsDeclineRequestTitle => 'Відхилити запит';

  @override
  String get coachRelationshipsDeclineReasonHint => 'Причина (необовʼязково)';

  @override
  String get coachRelationshipsRequestDeclined => 'Запит відхилено';

  @override
  String coachRelationshipsFailedToDecline(Object error) {
    return 'Не вдалося відхилити: $error';
  }

  @override
  String get coachRelationshipsCoachingPaused => 'Коучинг призупинено';

  @override
  String coachRelationshipsFailedToPause(Object error) {
    return 'Не вдалося призупинити: $error';
  }

  @override
  String get coachRelationshipsCoachingResumed => 'Коучинг відновлено';

  @override
  String coachRelationshipsFailedToResume(Object error) {
    return 'Не вдалося відновити: $error';
  }

  @override
  String get coachRelationshipsChatTooltip => 'Чат';

  @override
  String get coachRelationshipsAnalyticsTooltip => 'Аналітика';

  @override
  String get coachRelationshipsNudgeTooltip => 'Нагадати';

  @override
  String get coachRelationshipsPauseCoaching => 'Призупинити коучинг';

  @override
  String get coachRelationshipsResumeCoaching => 'Відновити коучинг';

  @override
  String get coachRelationshipsEndCoaching => 'Завершити коучинг';

  @override
  String get coachRelationshipsCoachingEnded => 'Коучинг завершено';

  @override
  String coachRelationshipsFailedToEnd(Object error) {
    return 'Не вдалося завершити: $error';
  }

  @override
  String get coachRelationshipsChatChannelNotAvailable =>
      'Канал чату недоступний';

  @override
  String get coachRelationshipsNudgeSent => 'Нагадування надіслано';

  @override
  String coachRelationshipsFailedToSendNudge(Object error) {
    return 'Не вдалося надіслати нагадування: $error';
  }

  @override
  String coachRelationshipsNudgeMessageWithDays(Object athleteId, Object days) {
    return 'Привіт $athleteId, минуло $days дн. з твого останнього тренування. Давай заплануємо наступну сесію!';
  }

  @override
  String coachRelationshipsNudgeMessageNoDays(Object athleteId) {
    return 'Привіт $athleteId, давай скоро заплануємо наступне тренування!';
  }

  @override
  String coachRelationshipsVolumeAndPlan(Object volume, Object plan) {
    return 'Обсяг: $volume | Активний план: $plan';
  }

  @override
  String get coachRelationshipsVolumeDash => '-';

  @override
  String get coachRelationshipsMenuAll => 'Усі';

  @override
  String get coachRelationshipsMenuPending => 'Очікує';

  @override
  String get coachRelationshipsMenuActive => 'Активні';

  @override
  String get coachRelationshipsMenuPaused => 'Пауза';

  @override
  String get coachRelationshipsMenuEnded => 'Завершено';

  @override
  String get coachRelationshipsMenuPauseCoaching => 'Призупинити коучинг';

  @override
  String get coachRelationshipsMenuResumeCoaching => 'Відновити коучинг';

  @override
  String get coachRelationshipsMenuEndCoaching => 'Завершити коучинг';

  @override
  String planEditorTitle(Object name) {
    return 'Редактор: $name';
  }

  @override
  String get planEditorMacros => 'Макроси';

  @override
  String get planEditorNoPlanId => 'Немає ID плану';

  @override
  String planEditorBulk(Object count) {
    return 'Масово ($count)';
  }

  @override
  String get planEditorReplace => 'Заміна';

  @override
  String get planEditorSearchHint => 'Пошук вправи за назвою...';

  @override
  String get planEditorMesocycles => 'Мезоцикли';

  @override
  String get planEditorDayFilterLabel => 'Фільтр: день (число, необовʼязково)';

  @override
  String get planEditorSelectTargetError => 'Обрати цільову вправу';

  @override
  String get planEditorSelectSourceError =>
      'Оберіть хоча б одну вправу для заміни';

  @override
  String get planEditorDeleteMesocycleTitle => 'Видалити мезоцикл';

  @override
  String planEditorDeleteMesocycleBody(Object name) {
    return 'Ви впевнені, що хочете видалити мезоцикл \"$name\" та всі його мікроцикли?';
  }

  @override
  String get planEditorDeleteMesocycle => 'Видалити';

  @override
  String get planEditorMesocycleDeleted => 'Мезоцикл видалено';

  @override
  String planEditorDeleteFailed(Object error) {
    return 'Помилка видалення: $error';
  }

  @override
  String get planEditorDeleteMesocycleTooltip => 'Видалити мезоцикл';

  @override
  String planEditorMicroDays(Object count) {
    return 'Днів: $count';
  }

  @override
  String planEditorExerciseIdFallback(Object id) {
    return 'Вправа $id';
  }

  @override
  String get planEditorChangesSaved => 'Зміни збережено';

  @override
  String get planEditorMicrocycleDeleted => 'Мікроцикл видалено';

  @override
  String get planEditorDeleteMicrocycleTitle => 'Видалити мікроцикл';

  @override
  String planEditorDeleteMicrocycleBody(Object name) {
    return 'Ви впевнені, що хочете видалити мікроцикл \"$name\"?';
  }

  @override
  String get planEditorDeleteMicrocycleTooltip => 'Видалити мікроцикл';

  @override
  String get planEditorMassEditTitle => 'Масові правки: вибрані мікроцикли';

  @override
  String planEditorSkipNoRights(Object count) {
    return 'Пропущено $count мікроциклів без прав доступу';
  }

  @override
  String planEditorRightsCheckUnavailableApplyAll(Object error) {
    return 'Перевірка прав недоступна, застосовую до всіх вибраних: $error';
  }

  @override
  String planEditorMassEditsResult(Object success, Object failed) {
    return 'Масові правки: успішно $success, помилок $failed';
  }

  @override
  String coachAthletePlanTitleFallback(Object id) {
    return 'Атлет $id';
  }

  @override
  String coachAthletePlanLoadAnalyticsError(Object error) {
    return 'Не вдалося завантажити аналітику плану: $error';
  }

  @override
  String get coachAthletePlanMetricSets => 'Сети';

  @override
  String get coachAthletePlanMetricReps => 'Повторення';

  @override
  String get coachAthletePlanMetricIntensity => 'Інтенсивність (сер.)';

  @override
  String get coachAthletePlanMetricEffort => 'Зусилля (RPE сер.)';

  @override
  String get coachAthletePlanAxisX => 'Вісь X';

  @override
  String get coachAthletePlanAxisY => 'Вісь Y';

  @override
  String get coachAthletePlanNoAnalytics => 'Немає аналітики по плану';

  @override
  String coachAthletePlanSessionsCompleted(Object completed, Object planned) {
    return '$completed / $planned тренувань';
  }

  @override
  String coachAthletePlanPeriod(Object start, Object end) {
    return 'Період: $start – $end';
  }

  @override
  String coachAthletePlanNotes(Object notes) {
    return 'Примітки: $notes';
  }

  @override
  String get coachAthletePlanMassEditTooltip => 'Масові правки плану атлета';

  @override
  String get coachAthletePlanMassEditMenu =>
      'Масове редагування (нотатки/день)';

  @override
  String get coachAthletePlanWorkoutNotesHint => 'Введіть примітку для атлета';

  @override
  String get coachAthletePlanWorkoutRescheduled => 'Тренування переплановано';

  @override
  String get coachAthletePlanWorkoutNotesUpdated => 'Примітку оновлено';

  @override
  String get coachAthletePlanNoExercises =>
      'Немає даних по вправах у цьому тренуванні';

  @override
  String get coachAthletePlanEditExercise => 'Редагувати вправу';

  @override
  String get coachAthletePlanAddExercise => 'Додати вправу';

  @override
  String get coachAthletePlanDeleteExerciseConfirmTitle => 'Видалити вправу?';

  @override
  String coachAthletePlanDeleteExerciseConfirmBody(Object name) {
    return 'Ви впевнені, що хочете видалити $name з тренування?';
  }

  @override
  String get coachAthletePlanExerciseDeleted => 'Вправу видалено';

  @override
  String coachAthletePlanDeleteError(Object error) {
    return 'Помилка при видаленні: $error';
  }

  @override
  String coachAthletePlanOrder(Object order) {
    return 'Порядок: $order';
  }

  @override
  String coachAthletePlanSets(Object count) {
    return 'Сетів: $count';
  }

  @override
  String get coachAthletePlanNoSets => 'Немає сетів';

  @override
  String get coachAthletePlanAddSet => 'Додати сет';

  @override
  String get coachAthletePlanMassEditErrorNoWorkouts =>
      'Немає тренувань для масових правок';

  @override
  String get coachAthletePlanMassEditErrorNoWorkoutsOnDay =>
      'У вибраний день немає тренувань';

  @override
  String get coachAthletePlanMassEditUpdateWorkouts =>
      'Оновити нотатки тренувань (workouts)';

  @override
  String get coachAthletePlanMassEditUpdateExercises =>
      'Оновити нотатки вправ (exercise instances)';

  @override
  String get coachAthletePlanMassEditNoChanges => 'Немає змін для застосування';

  @override
  String get coachAthletePlanMassEditApplied =>
      'Mass edit застосовано для вибраного дня';

  @override
  String get coachAthletePlanMassEditWorkoutHint =>
      'Нова нотатка для всіх тренувань цього дня';

  @override
  String get planEditorMassReplaceTitle => 'Масова заміна вправ';

  @override
  String get planEditorChooseTarget => 'Обрати цільову вправу';

  @override
  String planEditorTargetPrefix(Object name) {
    return 'Ціль: $name';
  }

  @override
  String get planEditorSelectAll => 'Обрати все';

  @override
  String get planEditorClearAll => 'Зняти все';

  @override
  String planEditorOccurrences(Object count) {
    return 'Входжень: $count';
  }

  @override
  String get planEditorPreview => 'Передперегляд';

  @override
  String planEditorRightsCheckUnavailable(Object error) {
    return 'Перевірка прав недоступна, продовжую без неї: $error';
  }

  @override
  String get planEditorNoAccessibleMicrocycles =>
      'Немає доступних мікроциклів для заміни';

  @override
  String get planEditorNoExercisesToReplace => 'Немає вправ для заміни';

  @override
  String get planEditorPreviewReplaceTitle => 'Передперегляд заміни';

  @override
  String planEditorPreviewTarget(Object name) {
    return 'Ціль: $name';
  }

  @override
  String planEditorPreviewTotals(Object exercises, Object sets) {
    return 'Буде замінено вправ: $exercises, сетів зачеплено: $sets';
  }

  @override
  String planEditorPreviewMicroStats(Object ex, Object sets) {
    return 'Вправ: $ex · Сетів: $sets';
  }

  @override
  String planEditorApplyReplaceResult(Object success, Object failed) {
    return 'Заміна: успішно $success, помилок $failed';
  }

  @override
  String get workoutListTitle => 'Тренування';

  @override
  String get workoutListAddWorkout => 'Додати тренування';

  @override
  String get workoutListWorkoutName => 'Назва тренування';

  @override
  String get workoutListEnterNameError =>
      'Будь ласка, введіть назву тренування';

  @override
  String workoutListCreateError(Object error) {
    return 'Помилка створення тренування: $error';
  }

  @override
  String get workoutListNextWorkout => 'Наступне тренування';

  @override
  String get workoutListEmpty => 'У цій прогресії немає тренувань';

  @override
  String exerciseCount(num count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.compact(
      locale: localeName,
    );
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString вправ',
      many: '$countString вправ',
      few: '$countString вправи',
      one: '$countString вправа',
    );
    return '$_temp0';
  }

  @override
  String get nutritionSessionsTitle => 'Сесії харчування';

  @override
  String get nutritionSessionsEmpty => 'Сесій харчування ще немає';

  @override
  String get nutritionSessionsEmptyDesc =>
      'Почніть відстежувати харчування, створивши першу сесію';

  @override
  String nutritionSessionTitle(Object id) {
    return 'Сесія $id';
  }

  @override
  String userIdLabel(Object id) {
    return 'ID користувача: $id';
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
      other: '$countString записів',
      many: '$countString записів',
      few: '$countString записи',
      one: '$countString запис',
    );
    return '$_temp0';
  }

  @override
  String get nutritionEntriesLabel => 'Записи';

  @override
  String get nutritionNoEntries => 'Немає записів';

  @override
  String get dateLabel => 'Дата';

  @override
  String get workoutIdLabel => 'ID тренування';

  @override
  String get appliedPlanWorkoutIdLabel => 'ID тренування в плані';

  @override
  String get typeLabel => 'Тип';

  @override
  String get dosageLabel => 'Дозування';

  @override
  String get nutritionEditSession => 'Редагувати сесію';

  @override
  String get nutritionCreateSession => 'Створити сесію';

  @override
  String get nutritionSessionConfig => 'Конфігурація сесії';

  @override
  String get nutritionSessionId => 'ID сесії';

  @override
  String get workoutIdOptional => 'ID тренування (опціонально)';

  @override
  String get appliedPlanWorkoutIdOptional =>
      'ID тренування в плані (опціонально)';

  @override
  String get nutritionSelectedEntries => 'Вибрані записи';

  @override
  String get nutritionNoEntriesSelected => 'Записи не вибрані';

  @override
  String get nutritionAvailableItems => 'Доступні елементи';

  @override
  String get foodLabel => 'Їжа';

  @override
  String get supplementsLabel => 'Добавки';

  @override
  String get medicationsLabel => 'Ліки';

  @override
  String get nutritionNoItemsAvailable => 'Немає доступних елементів';

  @override
  String get updateSession => 'Оновити сесію';

  @override
  String get createSession => 'Створити сесію';

  @override
  String get exerciseListEmptyDesc =>
      'Спробуйте змінити фільтр або додайте нову вправу';
}

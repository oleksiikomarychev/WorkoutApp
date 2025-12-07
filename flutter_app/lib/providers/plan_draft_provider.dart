import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kPlanDraftPrefsKey = 'plan_draft_v1';

class DayDraft {
  String? note;

  DayDraft({this.note});

  factory DayDraft.fromJson(Map<String, dynamic> json) => DayDraft(
        note: json['note'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'note': note,
      };
}

class WeekDraft {
  String name;
  bool expanded;
  int daysCount;

  Map<int, DayDraft> days;

  double? normValue;
  String? normUnit;

  WeekDraft({required this.name, this.expanded = true, required this.daysCount, Map<int, DayDraft>? days, this.normValue, this.normUnit})
      : days = days ?? {};

  factory WeekDraft.fromJson(Map<String, dynamic> json) => WeekDraft(
        name: json['name'] as String? ?? 'Микроцикл',
        expanded: json['expanded'] as bool? ?? true,
        daysCount: json['daysCount'] as int? ?? 7,
        days: ((json['days'] as Map?)?.map((k, v) => MapEntry(int.tryParse(k.toString()) ?? 0, DayDraft.fromJson(v as Map<String, dynamic>))) ?? {})
            .map((k, v) => MapEntry(k, v)),
        normValue: (json['normValue'] as num?)?.toDouble(),
        normUnit: json['normUnit'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'expanded': expanded,
        'daysCount': daysCount,
        'days': days.map((k, v) => MapEntry(k.toString(), v.toJson())),
        if (normValue != null) 'normValue': normValue,
        if (normUnit != null) 'normUnit': normUnit,
      };
}

class PlanDraft {
  final String name;
  final int microcycleLength;
  final List<WeekDraft> weeks;
  final List<MesocycleDraft> mesocycles;

  const PlanDraft({
    required this.name,
    required this.microcycleLength,
    required this.weeks,
    required this.mesocycles,
  });

  PlanDraft copyWith({String? name, int? microcycleLength, List<WeekDraft>? weeks, List<MesocycleDraft>? mesocycles}) => PlanDraft(
        name: name ?? this.name,
        microcycleLength: microcycleLength ?? this.microcycleLength,
        weeks: weeks ?? this.weeks,
        mesocycles: mesocycles ?? this.mesocycles,
      );

  factory PlanDraft.initial() => const PlanDraft(name: '', microcycleLength: 7, weeks: [], mesocycles: []);

  factory PlanDraft.fromJson(Map<String, dynamic> json) => PlanDraft(
        name: json['name'] as String? ?? '',
        microcycleLength: json['microcycleLength'] as int? ?? 7,
        weeks: (json['weeks'] as List<dynamic>? ?? const [])
            .map((e) => WeekDraft.fromJson(e as Map<String, dynamic>))
            .toList(),
        mesocycles: (json['mesocycles'] as List<dynamic>? ?? const [])
            .map((e) => MesocycleDraft.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'microcycleLength': microcycleLength,
        'weeks': weeks.map((w) => w.toJson()).toList(),
        'mesocycles': mesocycles.map((m) => m.toJson()).toList(),
      };
}

class MesocycleDraft {
  String name;
  String? notes;
  int weeksCount;
  int microcycleLength;

  MesocycleDraft({required this.name, this.notes, required this.weeksCount, required this.microcycleLength});

  factory MesocycleDraft.fromJson(Map<String, dynamic> json) => MesocycleDraft(
        name: json['name'] as String? ?? 'Мезоцикл',
        notes: json['notes'] as String?,
        weeksCount: json['weeksCount'] as int? ?? 1,
        microcycleLength: json['microcycleLength'] as int? ?? 7,
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'notes': notes,
        'weeksCount': weeksCount,
        'microcycleLength': microcycleLength,
      };
}

class PlanDraftNotifier extends StateNotifier<PlanDraft> {
  PlanDraftNotifier() : super(PlanDraft.initial()) {
    _load();
  }

  Future<void> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_kPlanDraftPrefsKey);
      if (raw != null) {
        final jsonMap = jsonDecode(raw) as Map<String, dynamic>;
        state = PlanDraft.fromJson(jsonMap);
      }
    } catch (_) {

    }
  }

  Future<void> _save() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kPlanDraftPrefsKey, jsonEncode(state.toJson()));
    } catch (_) {

    }
  }

  void setName(String name) {
    state = state.copyWith(name: name);
    _save();
  }

  void setMicrocycleLength(int days) {
    final v = days.clamp(1, 14);
    state = state.copyWith(microcycleLength: v);
    _save();
  }

  void addWeek() {
    final idx = state.weeks.length + 1;
    final copied = List<WeekDraft>.from(state.weeks);
    copied.add(WeekDraft(name: 'Микроцикл $idx', expanded: true, daysCount: state.microcycleLength));
    state = state.copyWith(weeks: copied);
    _normalizeMesocyclesAfterWeeksChanged();
    _save();
  }


  void addWeekToMesocycle(int mesoIndex) {
    if (mesoIndex < 0 || mesoIndex >= state.mesocycles.length) return;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    final weeks = List<WeekDraft>.from(state.weeks);



    int insertIndex = 0;
    for (int i = 0; i < mesoIndex; i++) {
      insertIndex += ms[i].weeksCount;
    }
    final oldCount = ms[mesoIndex].weeksCount;
    insertIndex += oldCount;
    if (insertIndex < 0) insertIndex = 0;
    if (insertIndex > weeks.length) insertIndex = weeks.length;

    weeks.insert(
      insertIndex,
      WeekDraft(
        name: 'Микроцикл ${weeks.length + 1}',
        expanded: true,
        daysCount: ms[mesoIndex].microcycleLength,
      ),
    );
    _renumberWeeks(weeks);

    ms[mesoIndex].weeksCount = oldCount + 1;
    state = state.copyWith(weeks: weeks, mesocycles: ms);
    _save();
  }


  void removeWeekFromMesocycleEnd(int mesoIndex) {
    if (mesoIndex < 0 || mesoIndex >= state.mesocycles.length) return;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (ms[mesoIndex].weeksCount <= 0) return;
    final weeks = List<WeekDraft>.from(state.weeks);
    int start = 0;
    for (int i = 0; i < mesoIndex; i++) {
      start += ms[i].weeksCount;
    }
    final endExclusive = start + ms[mesoIndex].weeksCount;
    final removeIndex = endExclusive - 1;
    if (removeIndex >= 0 && removeIndex < weeks.length) {
      weeks.removeAt(removeIndex);
      _renumberWeeks(weeks);
      ms[mesoIndex].weeksCount -= 1;
      state = state.copyWith(weeks: weeks, mesocycles: ms);
      _save();
    }
  }

  void removeWeek(int index) {
    if (index < 0 || index >= state.weeks.length) return;
    final copied = List<WeekDraft>.from(state.weeks)..removeAt(index);
    _renumberWeeks(copied);
    state = state.copyWith(weeks: copied);
    _normalizeMesocyclesAfterWeeksChanged();
    _save();
  }

  void reorderWeeks(int oldIndex, int newIndex) {
    final copied = List<WeekDraft>.from(state.weeks);
    if (newIndex > oldIndex) newIndex -= 1;
    final item = copied.removeAt(oldIndex);
    copied.insert(newIndex, item);
    _renumberWeeks(copied);
    state = state.copyWith(weeks: copied);
    _save();
  }

  void toggleWeekExpanded(int index) {
    if (index < 0 || index >= state.weeks.length) return;
    final copied = List<WeekDraft>.from(state.weeks);
    final w = copied[index];
    copied[index] = WeekDraft(name: w.name, expanded: !w.expanded, daysCount: w.daysCount, days: w.days, normValue: w.normValue, normUnit: w.normUnit);
    state = state.copyWith(weeks: copied);
    _save();
  }

  void _renumberWeeks(List<WeekDraft> weeks) {
    for (int i = 0; i < weeks.length; i++) {
      weeks[i].name = 'Микроцикл ${i + 1}';
    }
  }

  void setDayNote(int weekIndex, int dayIndex, String? note) {
    if (weekIndex < 0 || weekIndex >= state.weeks.length) return;
    final weeks = List<WeekDraft>.from(state.weeks);
    final w = weeks[weekIndex];
    final days = Map<int, DayDraft>.from(w.days);
    final existing = days[dayIndex] ?? DayDraft();
    existing.note = note;
    days[dayIndex] = existing;
    weeks[weekIndex] = WeekDraft(name: w.name, expanded: w.expanded, daysCount: w.daysCount, days: days, normValue: w.normValue, normUnit: w.normUnit);
    state = state.copyWith(weeks: weeks);
    _save();
  }


  void setNormalizationAfterWeek(int weekIndex, double value, String unit) {
    if (weekIndex < 0 || weekIndex >= state.weeks.length) return;
    if (unit != 'kg' && unit != '%') return;
    final weeks = List<WeekDraft>.from(state.weeks);
    final w = weeks[weekIndex];
    weeks[weekIndex] = WeekDraft(
      name: w.name,
      expanded: w.expanded,
      daysCount: w.daysCount,
      days: w.days,
      normValue: value,
      normUnit: unit,
    );
    state = state.copyWith(weeks: weeks);
    _save();
  }


  void clearNormalizationAfterWeek(int weekIndex) {
    if (weekIndex < 0 || weekIndex >= state.weeks.length) return;
    final weeks = List<WeekDraft>.from(state.weeks);
    final w = weeks[weekIndex];
    weeks[weekIndex] = WeekDraft(
      name: w.name,
      expanded: w.expanded,
      daysCount: w.daysCount,
      days: w.days,
      normValue: null,
      normUnit: null,
    );
    state = state.copyWith(weeks: weeks);
    _save();
  }


  void moveNormalization(int fromWeekIndex, int toWeekIndex) {
    if (fromWeekIndex < 0 || fromWeekIndex >= state.weeks.length) return;
    if (toWeekIndex < 0 || toWeekIndex >= state.weeks.length) return;
    final weeks = List<WeekDraft>.from(state.weeks);
    final src = weeks[fromWeekIndex];
    final dst = weeks[toWeekIndex];
    final value = src.normValue;
    final unit = src.normUnit;

    weeks[fromWeekIndex] = WeekDraft(
      name: src.name,
      expanded: src.expanded,
      daysCount: src.daysCount,
      days: src.days,
      normValue: null,
      normUnit: null,
    );

    weeks[toWeekIndex] = WeekDraft(
      name: dst.name,
      expanded: dst.expanded,
      daysCount: dst.daysCount,
      days: dst.days,
      normValue: value,
      normUnit: unit,
    );
    state = state.copyWith(weeks: weeks);
    _save();
  }

  void _renumberMesocycles(List<MesocycleDraft> meso) {
    for (int i = 0; i < meso.length; i++) {
      meso[i].name = 'Мезоцикл ${i + 1}';
    }
  }

  void _normalizeMesocyclesAfterWeeksChanged() {
    final totalWeeks = state.weeks.length;
    if (state.mesocycles.isEmpty) return;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    _rebalanceMesocyclesInternal(ms, totalWeeks, exceptIndex: null);
    state = state.copyWith(mesocycles: ms);
  }

  void addMesocycle() {
    final totalWeeks = state.weeks.length;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (totalWeeks > 0 && ms.length >= totalWeeks) {

      return;
    }
    final newWeeks = totalWeeks > 0 ? 1 : 0;
    ms.add(MesocycleDraft(name: 'Мезоцикл ${ms.length + 1}', weeksCount: newWeeks, microcycleLength: state.microcycleLength));
    _rebalanceMesocyclesInternal(ms, totalWeeks, exceptIndex: ms.length - 1);
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void removeMesocycle(int index) {
    final totalWeeks = state.weeks.length;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (index < 0 || index >= ms.length) return;
    ms.removeAt(index);
    _renumberMesocycles(ms);
    _rebalanceMesocyclesInternal(ms, totalWeeks, exceptIndex: null);
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void reorderMesocycles(int oldIndex, int newIndex) {
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (newIndex > oldIndex) newIndex -= 1;
    final item = ms.removeAt(oldIndex);
    ms.insert(newIndex, item);
    _renumberMesocycles(ms);
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void setMesocycleName(int index, String name) {
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (index < 0 || index >= ms.length) return;
    ms[index].name = name;
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void setMesocycleNotes(int index, String? notes) {
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (index < 0 || index >= ms.length) return;
    ms[index].notes = notes;
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void setMesocycleMicrocycleLength(int index, int days) {
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (index < 0 || index >= ms.length) return;
    days = days.clamp(1, 14);
    final old = ms[index].microcycleLength;
    if (old == days) return;
    ms[index].microcycleLength = days;


    final weeks = List<WeekDraft>.from(state.weeks);
    int start = 0;
    for (int i = 0; i < index; i++) {
      start += ms[i].weeksCount;
    }
    final endExclusive = start + ms[index].weeksCount;
    for (int i = start; i < endExclusive && i < weeks.length; i++) {
      final w = weeks[i];
      weeks[i] = WeekDraft(name: w.name, expanded: w.expanded, daysCount: days, days: w.days, normValue: w.normValue, normUnit: w.normUnit);

      final keysToRemove = w.days.keys.where((k) => k > days).toList();
      for (final k in keysToRemove) {
        weeks[i].days.remove(k);
      }
    }
    state = state.copyWith(mesocycles: ms, weeks: weeks);
    _save();
  }

  void setMesocycleWeeksCount(int index, int weeksCount) {
    final totalWeeks = state.weeks.length;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    if (index < 0 || index >= ms.length) return;
    weeksCount = weeksCount.clamp(0, totalWeeks);
    ms[index].weeksCount = weeksCount;
    _rebalanceMesocyclesInternal(ms, totalWeeks, exceptIndex: index);
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void rebalanceMesocycles() {
    final totalWeeks = state.weeks.length;
    final ms = List<MesocycleDraft>.from(state.mesocycles);
    _rebalanceMesocyclesInternal(ms, totalWeeks, exceptIndex: null);
    state = state.copyWith(mesocycles: ms);
    _save();
  }

  void _rebalanceMesocyclesInternal(List<MesocycleDraft> ms, int totalWeeks, {int? exceptIndex}) {
    if (ms.isEmpty) return;
    if (totalWeeks <= 0) {
      for (final m in ms) {
        m.weeksCount = 0;
      }
      return;
    }


    const minPer = 1;
    if (ms.length > totalWeeks) {

      for (int i = 0; i < ms.length; i++) {
        ms[i].weeksCount = i < totalWeeks ? 1 : 0;
      }
      return;
    }


    if (exceptIndex != null) {
      ms[exceptIndex].weeksCount = ms[exceptIndex].weeksCount.clamp(minPer, totalWeeks);
    }


    final except = exceptIndex;
    int currentSum = 0;
    for (int i = 0; i < ms.length; i++) {
      currentSum += ms[i].weeksCount;
    }

    if (currentSum == totalWeeks) return;

    final others = <int>[];
    for (int i = 0; i < ms.length; i++) {
      if (i != except) others.add(i);
    }

    if (others.isEmpty) {

      ms[except ?? 0].weeksCount = totalWeeks;
      return;
    }

    int sumOthers = 0;
    for (final i in others) {
      sumOthers += ms[i].weeksCount;
    }

    final reservedForExcept = except != null ? ms[except].weeksCount : 0;
    int targetOthers = totalWeeks - reservedForExcept;
    if (targetOthers < others.length * minPer) targetOthers = others.length * minPer;


    if (sumOthers == 0) {

      for (final i in others) {
        ms[i].weeksCount = minPer;
      }
      int remaining = targetOthers - others.length * minPer;
      int k = 0;
      while (remaining > 0) {
        ms[others[k % others.length]].weeksCount += 1;
        remaining--;
        k++;
      }
    } else {
      int allocated = 0;
      for (int idx = 0; idx < others.length; idx++) {
        final i = others[idx];
        final share = (ms[i].weeksCount * targetOthers) / sumOthers;
        int val = share.floor();
        if (val < minPer) val = minPer;
        ms[i].weeksCount = val;
        allocated += val;
      }

      int diff = targetOthers - allocated;
      int t = 0;
      while (diff != 0) {
        final i = others[t % others.length];
        if (diff > 0) {
          ms[i].weeksCount += 1;
          diff--;
        } else {
          if (ms[i].weeksCount > minPer) {
            ms[i].weeksCount -= 1;
            diff++;
          }
        }
        t++;
      }
    }


    int sumAll = 0;
    for (final m in ms) {
      sumAll += m.weeksCount;
    }
    if (sumAll != totalWeeks) {
      final delta = totalWeeks - sumAll;

      if (except != null) {
        ms[except].weeksCount = (ms[except].weeksCount + delta).clamp(minPer, totalWeeks);
      } else {
        for (int i = 0; i < ms.length && sumAll != totalWeeks; i++) {
          final newVal = (ms[i].weeksCount + delta).clamp(minPer, totalWeeks);
          ms[i].weeksCount = newVal;

          sumAll = 0;
          for (final m in ms) {
            sumAll += m.weeksCount;
          }
        }
      }
    }
  }

  Future<void> resetDraft() async {
    state = PlanDraft.initial();
    await _save();
  }
}

final planDraftProvider = StateNotifierProvider<PlanDraftNotifier, PlanDraft>((ref) {
  return PlanDraftNotifier();
});

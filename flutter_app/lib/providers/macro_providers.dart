import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/macro.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/macro_service.dart';

final macroServiceProvider = Provider<MacroService>((ref) {
  return MacroService(apiClient: ApiClient());
});

class MacrosState {
  final bool loading;
  final List<PlanMacro> items;
  final String? error;
  const MacrosState({this.loading = false, this.items = const [], this.error});
  MacrosState copyWith({bool? loading, List<PlanMacro>? items, String? error}) =>
      MacrosState(loading: loading ?? this.loading, items: items ?? this.items, error: error);
}

class MacrosNotifier extends StateNotifier<MacrosState> {
  final MacroService service;
  final int calendarPlanId;
  MacrosNotifier({required this.service, required this.calendarPlanId}) : super(const MacrosState());

  Future<void> load() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final items = await service.listMacros(calendarPlanId);
      state = state.copyWith(loading: false, items: items);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<PlanMacro> create(PlanMacro macro) async {
    try {
      final created = await service.createMacro(
        calendarPlanId: calendarPlanId,
        name: macro.name,
        isActive: macro.isActive,
        priority: macro.priority,
        rule: macro.rule,
      );
      // Refresh from server to ensure canonical shape
      await load();
      return created;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<PlanMacro> update(PlanMacro macro) async {
    try {
      final updated = await service.updateMacro(
        calendarPlanId: calendarPlanId,
        macroId: macro.id!,
        name: macro.name,
        isActive: macro.isActive,
        priority: macro.priority,
        rule: macro.rule,
      );
      // Refresh from server to avoid drift and reflect backend canon
      await load();
      return updated;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> delete(int macroId) async {
    try {
      await service.deleteMacro(calendarPlanId: calendarPlanId, macroId: macroId);
      state = state.copyWith(items: state.items.where((m) => m.id != macroId).toList());
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }
}

final macrosNotifierProvider = StateNotifierProvider.family<MacrosNotifier, MacrosState, int>((ref, calendarPlanId) {
  final svc = ref.watch(macroServiceProvider);
  final notifier = MacrosNotifier(service: svc, calendarPlanId: calendarPlanId);
  notifier.load();
  return notifier;
});


import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/macro_service.dart';

class MacroPreviewState {
  final bool loading;
  final Map<String, dynamic>? preview;
  final Map<String, dynamic>? applyResult;
  final String? error;
  const MacroPreviewState({this.loading = false, this.preview, this.applyResult, this.error});
  MacroPreviewState copyWith({bool? loading, Map<String, dynamic>? preview, Map<String, dynamic>? applyResult, String? error}) =>
      MacroPreviewState(loading: loading ?? this.loading, preview: preview ?? this.preview, applyResult: applyResult ?? this.applyResult, error: error);
}

final macroPreviewServiceProvider = Provider<MacroService>((ref) => MacroService(apiClient: ApiClient()));

class MacroPreviewNotifier extends StateNotifier<MacroPreviewState> {
  final MacroService service;
  MacroPreviewNotifier(this.service) : super(const MacroPreviewState());

  Future<void> runPreview(int appliedPlanId) async {
    state = state.copyWith(loading: true, error: null, applyResult: null);
    try {
      final res = await service.runPreview(appliedPlanId: appliedPlanId);
      state = state.copyWith(loading: false, preview: res);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<void> apply(int appliedPlanId) async {
    state = state.copyWith(loading: true, error: null);
    try {
      final res = await service.applyMacros(appliedPlanId: appliedPlanId);
      state = state.copyWith(loading: false, applyResult: res);
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }
}

final macroPreviewNotifierProvider = StateNotifierProvider<MacroPreviewNotifier, MacroPreviewState>((ref) {
  final svc = ref.watch(macroPreviewServiceProvider);
  return MacroPreviewNotifier(svc);
});

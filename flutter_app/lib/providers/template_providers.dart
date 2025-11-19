import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/templates.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/templates_service.dart';

final templatesServiceProvider = Provider<TemplatesService>((ref) {
  return TemplatesService(apiClient: ApiClient());
});

final mesocycleTemplatesProvider = FutureProvider<List<MesocycleTemplateResponse>>((ref) async {
  final svc = ref.watch(templatesServiceProvider);
  return svc.listTemplates();
});

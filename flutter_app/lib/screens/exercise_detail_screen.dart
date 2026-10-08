import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import '../config/api_config.dart';
import '../models/exercise_definition.dart';
import '../providers/target_data_providers.dart';
import 'exercises_screen.dart';

class ExerciseDetailScreen extends ConsumerWidget {
  final int exerciseId;

  const ExerciseDetailScreen({super.key, required this.exerciseId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(exercisesNotifierProvider);

    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'exercise_detail',
        'entities': {'exercise_id': exerciseId},
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Exercise',
            onTitleTap: openChat,
            showBack: true,
          ),
          body: state.when(
            loading: () => const LoadingIndicator(),
            error: (e, st) =>
                ErrorMessage(message: 'Failed to load exercise: $e'),
            data: (exercises) {
              final ExerciseDefinition? current = exercises
                  .cast<ExerciseDefinition?>()
                  .firstWhere((x) => x?.id == exerciseId, orElse: () => null);

              if (current == null) {
                return const Center(child: Text('Exercise not found'));
              }

              final int? parentId = current.rootExerciseId;
              final ExerciseDefinition? parent = parentId == null
                  ? null
                  : exercises.cast<ExerciseDefinition?>().firstWhere(
                      (x) => x?.id == parentId,
                      orElse: () => null,
                    );

              final variants =
                  exercises
                      .where(
                        (e) =>
                            e.rootExerciseId != null &&
                            e.rootExerciseId == current.id,
                      )
                      .toList()
                    ..sort((a, b) => a.name.compareTo(b.name));

              final siblings =
                  parent == null
                        ? <ExerciseDefinition>[]
                        : exercises
                              .where(
                                (e) =>
                                    e.rootExerciseId != null &&
                                    e.rootExerciseId == parent.id &&
                                    e.id != current.id,
                              )
                              .toList()
                    ..sort((a, b) => a.name.compareTo(b.name));

              return ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            current.name,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          if (current.imageUrl != null &&
                              current.imageUrl!.trim().isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Text(
                              'Image',
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            const SizedBox(height: 8),
                            _ExerciseImage(imagePathOrUrl: current.imageUrl!),
                          ],
                          if (current.gifUrl != null &&
                              current.gifUrl!.trim().isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Text(
                              'GIF',
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                            const SizedBox(height: 8),
                            _ExerciseImage(imagePathOrUrl: current.gifUrl!),
                          ],
                          const SizedBox(height: 12),
                          _MetaRow(
                            label: 'Muscle group',
                            value: current.muscleGroup ?? '—',
                          ),
                          _MetaRow(
                            label: 'Equipment',
                            value: current.equipment ?? '—',
                          ),
                          _MetaRow(
                            label: 'Movement type',
                            value: current.movementType ?? '—',
                          ),
                          _MetaRow(
                            label: 'Region',
                            value: current.region ?? '—',
                          ),
                          const SizedBox(height: 12),
                          _MetaChips(
                            label: 'Target muscles',
                            values: current.targetMuscles ?? const <String>[],
                          ),
                          const SizedBox(height: 8),
                          _MetaChips(
                            label: 'Synergist muscles',
                            values:
                                current.synergistMuscles ?? const <String>[],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  if (parent != null)
                    Card(
                      child: ListTile(
                        title: const Text('Parent'),
                        subtitle: Text(parent.name),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          if (parent.id == null) return;
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) =>
                                  ExerciseDetailScreen(exerciseId: parent.id!),
                            ),
                          );
                        },
                      ),
                    ),

                  if (variants.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Variants',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    for (final v in variants)
                      Card(
                        child: ListTile(
                          leading: const Icon(Icons.fitness_center),
                          title: Text(v.name),
                          subtitle: Text(
                            '${v.muscleGroup ?? 'No muscle group'} • ${v.equipment ?? 'No equipment'}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            if (v.id == null) return;
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) =>
                                    ExerciseDetailScreen(exerciseId: v.id!),
                              ),
                            );
                          },
                        ),
                      ),
                  ],

                  if (siblings.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Other variants of parent',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    for (final s in siblings)
                      Card(
                        child: ListTile(
                          leading: const Icon(Icons.fitness_center),
                          title: Text(s.name),
                          subtitle: Text(
                            '${s.muscleGroup ?? 'No muscle group'} • ${s.equipment ?? 'No equipment'}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            if (s.id == null) return;
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) =>
                                    ExerciseDetailScreen(exerciseId: s.id!),
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ],
              );
            },
          ),
        );
      },
    );
  }
}

class _ExerciseImage extends StatelessWidget {
  final String imagePathOrUrl;

  const _ExerciseImage({required this.imagePathOrUrl});

  String _toAbsoluteUrl(String pathOrUrl) {
    final trimmed = pathOrUrl.trim();
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    if (trimmed.startsWith('api/')) {
      return ApiConfig.buildFullUrl(trimmed);
    }

    if (trimmed.startsWith('/')) {
      final endpoint = ApiConfig.buildEndpoint(trimmed);
      return ApiConfig.buildFullUrl(endpoint);
    }

    return ApiConfig.buildFullUrl(trimmed);
  }

  Future<String?> _getIdToken() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return null;
      return await user.getIdToken();
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final url = _toAbsoluteUrl(imagePathOrUrl);

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        child: FutureBuilder<String?>(
          future: _getIdToken(),
          builder: (context, snapshot) {
            final token = snapshot.data;
            final headers = (token == null || token.isEmpty)
                ? null
                : <String, String>{'Authorization': 'Bearer $token'};

            return Image.network(
              url,
              headers: headers,
              fit: BoxFit.cover,
              height: 220,
              width: double.infinity,
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return SizedBox(
                  height: 220,
                  child: Center(
                    child: CircularProgressIndicator(
                      value: loadingProgress.expectedTotalBytes != null
                          ? loadingProgress.cumulativeBytesLoaded /
                                loadingProgress.expectedTotalBytes!
                          : null,
                    ),
                  ),
                );
              },
              errorBuilder: (context, error, stackTrace) {
                return SizedBox(
                  height: 220,
                  child: Center(
                    child: Text(
                      'Failed to load image',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _MetaRow extends StatelessWidget {
  final String label;
  final String value;

  const _MetaRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: Theme.of(context).textTheme.bodySmall),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _MetaChips extends StatelessWidget {
  final String label;
  final List<String> values;

  const _MetaChips({required this.label, required this.values});

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) {
      return _MetaRow(label: label, value: '—');
    }

    final v = values.toList()..sort();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [for (final x in v) Chip(label: Text(x))],
        ),
      ],
    );
  }
}

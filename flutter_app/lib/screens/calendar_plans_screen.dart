import 'package:flutter/material.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/screens/user_profile_screen.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/plan_providers.dart';
import 'calendar_plan_create.dart';
import 'calendar_plan_detail.dart';

class CalendarPlansScreen extends ConsumerStatefulWidget {
  const CalendarPlansScreen({super.key});

  @override
  ConsumerState<CalendarPlansScreen> createState() => _CalendarPlansScreenState();
}

class _CalendarPlansScreenState extends ConsumerState<CalendarPlansScreen> {
  final ApiClient _apiClient = ApiClient.create();

  Future<Map<String, dynamic>?> _buildChatContext() async {
    final plans = (ref.read(calendarPlansProvider).value ?? const <CalendarPlan>[])
        .map(
          (p) => <String, dynamic>{
            'id': p.id,
            'name': p.name,
            'duration_weeks': p.durationWeeks,
            'is_active': p.isActive,
            'primary_goal': p.primaryGoal,
            'intended_experience_level': p.intendedExperienceLevel,
            'intended_frequency_per_week': p.intendedFrequencyPerWeek,
            'session_duration_target_min': p.sessionDurationTargetMin,
            'required_equipment': p.requiredEquipment,
            'notes': p.notes,
          },
        )
        .toList(growable: false);

    return <String, dynamic>{
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'calendar_plans',
      'timestamp': DateTime.now().toUtc().toIso8601String(),
      'entities': <String, dynamic>{
        'calendar_plans': plans,
      },
    };
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(calendarPlansProvider.notifier).load();
    });
  }

  Future<void> _deletePlan(int planId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Plan'),
        content: const Text('Are you sure you want to delete this plan?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      Future<void> performDelete({bool cascade = false}) async {
        final endpoint = ApiConfig.deleteCalendarPlanEndpoint(planId.toString());
        final queryParams = cascade ? {'cascade': 'true'} : null;
        await _apiClient.delete(
          endpoint,
          queryParams: queryParams,
          context: 'calendar_plans_delete',
        );
      }

      try {
        await performDelete();

        await _apiClient.invalidateCacheGroups([
          'plans:list',
          'plans:detail',
          'plans:detail:$planId',
          'plans:variants',
          'plans:variants:$planId',
        ]);

        setState(() {
          ref.read(calendarPlansProvider.notifier).removeLocal(planId);
        });
      } on ApiException catch (e) {
        final message = e.message;
        final isVariantsError =
            e.statusCode == 400 && message.contains('Cannot delete the original plan while variants exist');

        if (isVariantsError) {
          List<Map<String, dynamic>> variantSummaries = [];
          try {
            final variantsEndpoint = ApiConfig.listPlanVariantsEndpoint(planId.toString());
            final variantsResponse = await _apiClient.get(
              variantsEndpoint,
              context: 'calendar_plans_variants',
            );

            if (variantsResponse is List) {
              variantSummaries = variantsResponse
                  .whereType<Map<String, dynamic>>()
                  .toList();
            }
          } catch (_) {
            // Игнорируем ошибку получения списка вариантов, в этом случае покажем общее предупреждение
          }

          final cascadeConfirmed = await showDialog<bool>(
            context: context,
            builder: (context) {
              Widget content;
              if (variantSummaries.isEmpty) {
                content = const Text(
                  'This plan has variants based on it. Deleting the plan will also permanently delete all its variants and related workouts. Do you want to continue?',
                );
              } else {
                content = SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('This plan has the following variants that will be deleted:'),
                      const SizedBox(height: 8),
                      ...variantSummaries.map((v) {
                        final id = v['id'];
                        final rawName = v['name'];
                        final String name =
                            rawName is String && rawName.trim().isNotEmpty ? rawName.trim() : 'Unnamed plan';
                        final duration = v['duration_weeks'];
                        final metaParts = <String>[];
                        if (duration != null) {
                          metaParts.add('${duration} weeks');
                        }
                        final metaSuffix = metaParts.isNotEmpty ? ' • ${metaParts.join(' • ')}' : '';
                        return Text('• [$id] $name$metaSuffix');
                      }),
                      const SizedBox(height: 12),
                      const Text(
                        'Deleting the plan will permanently delete all these variants and related workouts. Do you want to continue?',
                      ),
                    ],
                  ),
                );
              }

              return AlertDialog(
                title: const Text('Delete plan with variants?'),
                content: content,
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Cancel'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Delete all'),
                  ),
                ],
              );
            },
          );

          if (cascadeConfirmed == true) {
            try {
              await performDelete(cascade: true);

              await _apiClient.invalidateCacheGroups([
                'plans:list',
                'plans:detail',
                'plans:detail:$planId',
                'plans:variants',
                'plans:variants:$planId',
                'workouts:list',
                'workouts:history_all',
              ]);

              setState(() {
                ref.read(calendarPlansProvider.notifier).removeLocal(planId);
              });
            } on ApiException catch (inner) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to delete plan: ${inner.message}')),
              );
            } catch (inner) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to delete plan: $inner')),
              );
            }
          }
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to delete plan: ${e.message}')),
          );
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete plan: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final plansAsync = ref.watch(calendarPlansProvider);

    return AssistantChatHost(
      contextBuilder: _buildChatContext,
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Training Plans',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.person),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const UserProfileScreen()),
                ),
              ),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () => ref.read(calendarPlansProvider.notifier).load(),
            child: plansAsync.when(
              loading: () => const LoadingIndicator(),
              error: (e, _) => ErrorMessage(
                message: 'Failed to load plans: $e',
                onRetry: () => ref.read(calendarPlansProvider.notifier).load(),
              ),
              data: (items) {
                if (items.isEmpty) {
                  return const EmptyState(
                    icon: Icons.calendar_today,
                    title: 'No plans available',
                    description: 'Create your first training plan',
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final plan = items[index];
                    final metaParts = <String>[];
                    if (plan.primaryGoal != null && plan.primaryGoal!.isNotEmpty) {
                      metaParts.add(plan.primaryGoal!);
                    }
                    if (plan.intendedExperienceLevel != null && plan.intendedExperienceLevel!.isNotEmpty) {
                      metaParts.add(plan.intendedExperienceLevel!);
                    }
                    if (plan.intendedFrequencyPerWeek != null) {
                      metaParts.add('${plan.intendedFrequencyPerWeek}x/week');
                    }
                    final subtitle = [
                      '${plan.durationWeeks} weeks',
                      if (plan.mesocycles.isNotEmpty) '${plan.mesocycles.length} mesocycles',
                      if (metaParts.isNotEmpty) metaParts.join(' • '),
                    ].join(' • ');

                    return Card(
                      margin: const EdgeInsets.only(bottom: 16.0),
                      child: ListTile(
                        title: Text(plan.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text(subtitle),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              plan.isActive ? Icons.check_circle : Icons.circle_outlined,
                              color: plan.isActive ? Colors.green : Colors.grey,
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.delete, color: Colors.red),
                              onPressed: () => _deletePlan(plan.id),
                            ),
                          ],
                        ),
                        onTap: () async {
                          final result = await Navigator.push<bool>(
                            context,
                            MaterialPageRoute(builder: (context) => CalendarPlanDetail(plan: plan)),
                          );
                          if (result == true) {
                            ref.read(calendarPlansProvider.notifier).load();
                          }
                        },
                      ),
                    );
                  },
                );
              },
            ),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () async {
              final result = await Navigator.push<bool>(
                context,
                MaterialPageRoute(builder: (context) => const CalendarPlanCreate()),
              );
              if (result == true) {
                ref.read(calendarPlansProvider.notifier).load();
              }
            },
            child: const Icon(Icons.add),
            tooltip: 'Create new calendar plan',
          ),
        );
      },
    );
  }
}

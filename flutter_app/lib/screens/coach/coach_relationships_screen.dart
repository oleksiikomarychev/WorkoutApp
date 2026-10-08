import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/models/crm_coach_athlete_link.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

final coachRelationshipsStatusFilterProvider = StateProvider<String?>((ref) => null);

final coachRelationshipsProvider = FutureProvider<List<CoachAthleteLink>>((ref) async {
  final svc = ref.watch(sl.crmRelationshipsServiceProvider);
  final links = await svc.getMyAthletes();
  return links;
});

final coachRelationshipsAnalyticsProvider =
    FutureProvider<Map<String, AthleteTrainingSummaryModel>>((ref) async {
  final svc = ref.watch(sl.crmAnalyticsServiceProvider);
  final analytics = await svc.getMyAthletesAnalytics();
  final map = <String, AthleteTrainingSummaryModel>{};
  for (final athlete in analytics.athletes) {
    map[athlete.athleteId] = athlete;
  }
  return map;
});

class CoachRelationshipsScreen extends ConsumerWidget {
  const CoachRelationshipsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncLinks = ref.watch(coachRelationshipsProvider);
    final analyticsAsync = ref.watch(coachRelationshipsAnalyticsProvider);
    final allUsersAsync = ref.watch(allUsersProvider(false));
    final analyticsMap = analyticsAsync.maybeWhen(
      data: (value) => value,
      orElse: () => null,
    );
    final usersMap = allUsersAsync.maybeWhen(
      data: (users) => {
        for (final u in users) u.userId: u,
      },
      orElse: () => null,
    );

    return AssistantChatHost(
      initialMessage:
          'Открываю ассистента из CoachRelationshipsScreen. Используй контекст v1, чтобы понимать фильтр по статусу и приоритетные связи.',
      contextBuilder: () => _buildCoachRelationshipsChatContext(ref),
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: l10n.coachRelationshipsTitle,
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(coachRelationshipsProvider),
              ),
              PopupMenuButton<String?>(
                onSelected: (value) {
                  ref.read(coachRelationshipsStatusFilterProvider.notifier).state = value;
                },
                itemBuilder: (context) => [
                  PopupMenuItem<String?>(
                    value: null,
                    child: Text(l10n.coachRelationshipsMenuAll),
                  ),
                  PopupMenuItem<String?>(
                    value: 'pending',
                    child: Text(l10n.coachRelationshipsMenuPending),
                  ),
                  PopupMenuItem<String?>(
                    value: 'active',
                    child: Text(l10n.coachRelationshipsMenuActive),
                  ),
                  PopupMenuItem<String?>(
                    value: 'paused',
                    child: Text(l10n.coachRelationshipsMenuPaused),
                  ),
                  PopupMenuItem<String?>(
                    value: 'ended',
                    child: Text(l10n.coachRelationshipsMenuEnded),
                  ),
                ],
              ),
            ],
          ),
          body: asyncLinks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text(l10n.coachRelationshipsError(error.toString()))),
        data: (links) {
          final filter = ref.watch(coachRelationshipsStatusFilterProvider);
          final filteredLinks = filter == null
              ? links
              : links.where((l) => l.status.toLowerCase() == filter).toList();

          if (filteredLinks.isEmpty) {
            return Center(child: Text(l10n.coachRelationshipsEmpty));
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref.refresh(coachRelationshipsProvider.future);
            },
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: filteredLinks.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final link = filteredLinks[index];
                final hasChannel = (link.channelId ?? '').isNotEmpty;
                final status = link.status.toUpperCase();
                final statusLower = link.status.toLowerCase();
                final summary = analyticsMap?[link.athleteId];
                final athleteName = usersMap?[link.athleteId]?.displayName ?? link.athleteId;
                final channelLabel = link.channelId ?? l10n.coachRelationshipsChannelNotCreated;
                return ListTile(
                  title: Text(l10n.coachRelationshipsAthletePrefix(athleteName)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(l10n.coachRelationshipsStatusPrefix(status)),
                      if ((link.note ?? '').isNotEmpty)
                        Text(l10n.coachRelationshipsNotePrefix(link.note ?? '')),
                      Text(l10n.coachRelationshipsChannelPrefix(channelLabel)),
                      if (summary != null) ...[
                        const SizedBox(height: 4),
                        Text(l10n.coachRelationshipsSessions12w(summary.sessionsCount.toString())),
                        Text(
                          l10n.coachRelationshipsLastWorkout(
                            summary.lastWorkoutAt != null
                                ? DateFormat('MMM d').format(summary.lastWorkoutAt!.toLocal())
                                : l10n.coachRelationshipsLastWorkoutNA,
                            summary.daysSinceLastWorkout != null
                                ? l10n.coachRelationshipsDaysAgoSuffix(summary.daysSinceLastWorkout.toString())
                                : '',
                          ),
                        ),
                        Text(
                          l10n.coachRelationshipsVolumeAndPlan(
                            summary.totalVolume != null
                                ? summary.totalVolume!.toStringAsFixed(1)
                                : l10n.coachRelationshipsVolumeDash,
                            summary.activePlanName ?? l10n.coachRelationshipsLastWorkoutNA,
                          ),
                        ),
                      ] else if (analyticsAsync.isLoading) ...[
                        const SizedBox(height: 4),
                        Text(l10n.coachRelationshipsLoadingTrainingSummary),
                      ],
                    ],
                  ),
                  trailing: statusLower == 'pending'
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TextButton(
                              onPressed: () async {
                                final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                try {
                                  await svc.updateStatus(
                                    id: link.id,
                                    status: 'active',
                                  );
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text(l10n.coachRelationshipsRequestAccepted)),
                                    );
                                  }
                                  ref.refresh(coachRelationshipsProvider);
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text(l10n.coachRelationshipsFailedToAccept(e.toString()))),
                                    );
                                  }
                                }
                              },
                              child: Text(l10n.coachRelationshipsAccept),
                            ),
                            TextButton(
                              onPressed: () async {
                                final controller = TextEditingController();
                                final confirmed = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) {
                                    return AlertDialog(
                                      title: Text(l10n.coachRelationshipsDeclineRequestTitle),
                                      content: TextField(
                                        controller: controller,
                                        decoration: InputDecoration(labelText: l10n.coachRelationshipsDeclineReasonHint),
                                        maxLines: 3,
                                      ),
                                      actions: [
                                        TextButton(
                                          onPressed: () => Navigator.of(ctx).pop(false),
                                          child: Text(l10n.cancel),
                                        ),
                                        ElevatedButton(
                                          onPressed: () => Navigator.of(ctx).pop(true),
                                          child: Text(l10n.coachRelationshipsDecline),
                                        ),
                                      ],
                                    );
                                  },
                                );
                                if (confirmed != true) return;
                                final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                try {
                                  final reason = controller.text.trim();
                                  await svc.updateStatus(
                                    id: link.id,
                                    status: 'ended',
                                    endedReason: reason.isEmpty ? null : reason,
                                  );
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text(l10n.coachRelationshipsRequestDeclined)),
                                    );
                                  }
                                  ref.refresh(coachRelationshipsProvider);
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text(l10n.coachRelationshipsFailedToDecline(e.toString()))),
                                    );
                                  }
                                }
                              },
                              child: Text(l10n.coachRelationshipsDecline),
                            ),
                          ],
                        )
                      : Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.chat_bubble_outline),
                              tooltip: l10n.coachRelationshipsChatTooltip,
                              onPressed: hasChannel
                                  ? () {
                                      Navigator.of(context).pushNamed(
                                        RouteNames.coachChat,
                                        arguments: CoachChatScreenArgs(
                                          channelId: link.channelId!,
                                          title: athleteName,
                                        ),
                                      );
                                    }
                                  : null,
                            ),
                            IconButton(
                              icon: const Icon(Icons.insights_outlined),
                              tooltip: l10n.coachRelationshipsAnalyticsTooltip,
                              onPressed: () {
                                Navigator.of(context).pushNamed(
                                  RouteNames.coachAthleteDetail,
                                  arguments: link.athleteId,
                                );
                              },
                            ),
                            IconButton(
                              icon: const Icon(Icons.notifications_active_outlined),
                              tooltip: l10n.coachRelationshipsNudgeTooltip,
                              onPressed: (statusLower == 'active' && hasChannel)
                                  ? () => _sendNudge(context, ref, link, summary)
                                  : null,
                            ),
                            PopupMenuButton<String>(
                              onSelected: (value) async {
                                if (value == 'pause') {
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    await svc.updateStatus(id: link.id, status: 'paused');
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsCoachingPaused)),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsFailedToPause(e.toString()))),
                                      );
                                    }
                                  }
                                } else if (value == 'resume') {
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    await svc.updateStatus(id: link.id, status: 'active');
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsCoachingResumed)),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsFailedToResume(e.toString()))),
                                      );
                                    }
                                  }
                                } else if (value == 'end') {
                                  final controller = TextEditingController();
                                  final confirmed = await showDialog<bool>(
                                    context: context,
                                    builder: (ctx) {
                                      return AlertDialog(
                                        title: Text(l10n.coachRelationshipsEndCoaching),
                                        content: TextField(
                                          controller: controller,
                                          decoration: InputDecoration(labelText: l10n.coachRelationshipsDeclineReasonHint),
                                          maxLines: 3,
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.of(ctx).pop(false),
                                            child: Text(l10n.cancel),
                                          ),
                                          ElevatedButton(
                                            onPressed: () => Navigator.of(ctx).pop(true),
                                            child: Text(l10n.coachRelationshipsEndCoaching),
                                          ),
                                        ],
                                      );
                                    },
                                  );
                                  if (confirmed != true) return;
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    final reason = controller.text.trim();
                                    await svc.updateStatus(
                                      id: link.id,
                                      status: 'ended',
                                      endedReason: reason.isEmpty ? null : reason,
                                    );
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsCoachingEnded)),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(l10n.coachRelationshipsFailedToEnd(e.toString()))),
                                      );
                                    }
                                  }
                                }
                              },
                              itemBuilder: (context) => [
                                if (statusLower == 'active')
                                  PopupMenuItem<String>(
                                    value: 'pause',
                                    child: Text(l10n.coachRelationshipsMenuPauseCoaching),
                                  ),
                                if (statusLower == 'paused')
                                  PopupMenuItem<String>(
                                    value: 'resume',
                                    child: Text(l10n.coachRelationshipsMenuResumeCoaching),
                                  ),
                                if (statusLower != 'ended')
                                  PopupMenuItem<String>(
                                    value: 'end',
                                    child: Text(l10n.coachRelationshipsMenuEndCoaching),
                                  ),
                              ],
                            ),
                          ],
                        ),
                );
              },
            ),
          );
        },
      ),
        );
      },
    );
  }
}

Future<void> _sendNudge(
  BuildContext context,
  WidgetRef ref,
  CoachAthleteLink link,
  AthleteTrainingSummaryModel? summary,
) async {
  final l10n = AppLocalizations.of(context);
  final channelId = link.channelId;
  if (channelId == null || channelId.isEmpty) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.coachRelationshipsChatChannelNotAvailable)),
      );
    }
    return;
  }

  final days = summary?.daysSinceLastWorkout;
  final message = days != null && days > 0
      ? l10n.coachRelationshipsNudgeMessageWithDays(link.athleteId, days.toString())
      : l10n.coachRelationshipsNudgeMessageNoDays(link.athleteId);

  try {
    final messaging = ref.read(sl.messagingServiceProvider);
    await messaging.sendTextMessage(channelId: channelId, content: message);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.coachRelationshipsNudgeSent)),
      );
    }
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.coachRelationshipsFailedToSendNudge(e.toString()))),
      );
    }
  }
}

Future<Map<String, dynamic>> _buildCoachRelationshipsChatContext(WidgetRef ref) async {
  try {
    final links = await ref.read(coachRelationshipsProvider.future);
    Map<String, AthleteTrainingSummaryModel>? analyticsMap;
    try {
      analyticsMap = await ref.read(coachRelationshipsAnalyticsProvider.future);
    } catch (_) {}

    final filter = ref.read(coachRelationshipsStatusFilterProvider);
    final nowIso = DateTime.now().toUtc().toIso8601String();

    final byStatus = <String, int>{};
    for (final link in links) {
      final key = link.status.toLowerCase();
      byStatus[key] = (byStatus[key] ?? 0) + 1;
    }

    final highlighted = links
        .where((l) => filter == null || l.status.toLowerCase() == filter)
        .take(3)
        .map((link) {
      final summary = analyticsMap?[link.athleteId];
      return {
        'relationship_id': link.id,
        'athlete_id': link.athleteId,
        'status': link.status,
        'channel_id': link.channelId,
        'note': link.note,
        'summary': summary == null
            ? null
            : {
                'sessions_12w': summary.sessionsCount,
                'sessions_per_week': summary.sessionsPerWeek,
                'plan_adherence': summary.planAdherence,
                'days_since_last_workout': summary.daysSinceLastWorkout,
                'active_plan_name': summary.activePlanName,
              },
      };
    }).toList();

    return {
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'coach_relationships',
      'role': 'coach',
      'timestamp': nowIso,
      'entities': {
        'relationships_summary': {
          'total': links.length,
          'by_status': byStatus,
        },
        'highlighted_relationships': highlighted,
      },
      'selection': {
        'status_filter': filter,
      },
    };
  } catch (e) {
    return {
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'coach_relationships',
      'role': 'coach',
      'timestamp': DateTime.now().toUtc().toIso8601String(),
      'error': e.toString(),
    };
  }
}

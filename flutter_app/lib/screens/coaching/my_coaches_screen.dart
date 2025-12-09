import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:workout_app/models/crm_coach_athlete_link.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/config/constants/route_names.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/services/base_api_service.dart';

final myCoachesProvider = FutureProvider<List<CoachAthleteLink>>((ref) async {
  final svc = ref.watch(sl.crmRelationshipsServiceProvider);
  final links = await svc.getMyCoaches();
  return links;
});

final coachSubscriptionStatusProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, linkId) async {
  final billing = ref.watch(sl.crmBillingServiceProvider);
  try {
    final status = await billing.getSubscriptionStatus(linkId);
    return status;
  } catch (_) {
    return const <String, dynamic>{};
  }
});

final coachDisplayNameProvider = FutureProvider.family<String, String>((ref, coachId) async {
  final profileService = ref.watch(sl.profileServiceProvider);
  try {
    final profile = await profileService.fetchProfileById(coachId);
    final displayName = profile.displayName;
    if (displayName != null && displayName.trim().isNotEmpty) {
      return displayName;
    }
  } catch (_) {}
  return coachId;
});

class MyCoachesScreen extends ConsumerWidget {
  const MyCoachesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncLinks = ref.watch(myCoachesProvider);

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'My Coaches',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(myCoachesProvider),
              ),
            ],
          ),
          body: asyncLinks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Error: $error')),
        data: (links) {
          if (links.isEmpty) {
            return const Center(child: Text('No coaches yet'));
          }
          return RefreshIndicator(
            onRefresh: () async {
              final refreshedLinks = await ref.refresh(myCoachesProvider.future);
              for (final link in refreshedLinks) {
                ref.invalidate(coachSubscriptionStatusProvider(link.id));
              }
            },
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: links.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final link = links[index];
                final hasChannel = (link.channelId ?? '').isNotEmpty;
                final status = link.status.toUpperCase();
                final displayNameAsync = ref.watch(coachDisplayNameProvider(link.coachId));
                final subscriptionAsync = ref.watch(coachSubscriptionStatusProvider(link.id));
                return ListTile(
                  title: displayNameAsync.when(
                    data: (value) => Text(value),
                    loading: () => Text(link.coachId),
                    error: (_, __) => Text(link.coachId),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Status: $status'),
                      if ((link.note ?? '').isNotEmpty)
                        Text('Note: ${link.note}'),
                      Text('Channel: ${link.channelId ?? 'not created'}'),
                      const SizedBox(height: 4),
                      subscriptionAsync.when(
                        loading: () => const Text('Subscription: loading...'),
                        error: (error, _) => Text('Subscription error: $error'),
                        data: (sub) {
                          final active = sub['active'] == true;
                          final validUntil = sub['valid_until']?.toString();
                          if (!active) {
                            return const Text('Subscription: inactive');
                          }
                          return Text('Subscription: active until ${validUntil ?? 'unknown'}');
                        },
                      ),
                    ],
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.insights_outlined),
                        tooltip: 'My analytics',
                        onPressed: () {
                          Navigator.of(context).pushNamed(
                            RouteNames.coachAthleteDetail,
                            arguments: link.athleteId,
                          );
                        },
                      ),
                      TextButton.icon(
                        icon: const Icon(Icons.chat_bubble_outline),
                        label: const Text('Chat'),
                        onPressed: hasChannel
                            ? () {
                                Navigator.of(context).pushNamed(
                                  RouteNames.coachChat,
                                  arguments: CoachChatScreenArgs(
                                    channelId: link.channelId!,
                                    title: link.coachId,
                                  ),
                                );
                              }
                            : null,
                      ),
                      const SizedBox(width: 8),
                      TextButton(
                        onPressed: link.status.toLowerCase() == 'active'
                            ? () async {
                                await _startCheckoutForLink(context, ref, link.id);
                                ref.invalidate(coachSubscriptionStatusProvider(link.id));
                              }
                            : null,
                        child: const Text('Subscribe'),
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

Future<void> _startCheckoutForLink(BuildContext context, WidgetRef ref, int linkId) async {
  try {
    final billing = ref.read(sl.crmBillingServiceProvider);
    final result = await billing.createCheckoutSession(linkId);
    final urlStr = (result['checkout_url'] ?? result['url'])?.toString();
    if (urlStr == null || urlStr.isEmpty) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to create checkout session')),
        );
      }
      return;
    }
    final uri = Uri.tryParse(urlStr);
    if (uri == null) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Invalid checkout URL')),
        );
      }
      return;
    }
    final canLaunch = await canLaunchUrl(uri);
    if (!canLaunch) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cannot open checkout URL')),
        );
      }
      return;
    }
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (e) {
    if (context.mounted) {
      String message;
      if (e is ApiException) {
        message = e.message;
      } else {
        message = 'Failed to start checkout: $e';
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    }
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_profile.dart';
import '../models/user_stats.dart';
import '../providers/providers.dart';
import '../services/service_locator.dart' as sl;
import '../widgets/user_profile_view.dart';
import '../widgets/profile_sections.dart';

class PublicUserProfileScreen extends ConsumerWidget {
  final String userId;
  final String? initialName;

  const PublicUserProfileScreen({super.key, required this.userId, this.initialName});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(publicUserProfileProvider(userId));
    final aggregatesAsync = ref.watch(publicProfileAggregatesProvider(userId));

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: initialName ?? 'Profile',
            onTitleTap: openChat,
          ),
          body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(publicUserProfileProvider(userId));
          ref.invalidate(publicProfileAggregatesProvider(userId));
          await Future.wait([
            ref.read(publicUserProfileProvider(userId).future),
            ref.read(publicProfileAggregatesProvider(userId).future),
          ]);
        },
        child: profileAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _buildErrorState(ref, error),
          data: (profile) {
            return aggregatesAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => _buildErrorState(ref, error),
              data: (stats) => _buildContent(context, ref, profile, stats),
            );
          },
        ),
      ),
    );
      },
    );
  }

  Widget _buildErrorState(WidgetRef ref, Object error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 40, color: AppColors.error),
            const SizedBox(height: 12),
            Text('Failed to load profile: $error'),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () {
                ref.invalidate(publicUserProfileProvider(userId));
                ref.invalidate(publicProfileAggregatesProvider(userId));
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, UserProfile profile, UserStats stats) {
    final currentUser = FirebaseAuth.instance.currentUser;
    final isSelf = currentUser != null && currentUser.uid == profile.userId;

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: UserProfileView(
              profile: profile,
              isOwner: false,
              subtitle: profile.userId,
              onRequestCoaching: (!isSelf && (profile.coaching?.acceptingClients ?? false))
                  ? () => _showRequestDialog(context, ref, profile)
                  : null,
              showCoachingCard: true,
              additionalSections: [
                const SizedBox(height: 24),
                ProfileStatsRow(stats: stats),
              ],
            ),
          ),
        ),
        const SizedBox(height: 32),
        ProfileActivitySection(stats: stats),
        const SizedBox(height: 32),
        ProfileCompletedWorkoutsSection(
          sessions: stats.completedSessions,
          onSessionTap: (session) {

            Navigator.of(context).pushNamed(
              '/session-log',
              arguments: session,
            );
          },
        ),
      ],
    );
  }

  Future<void> _showRequestDialog(BuildContext context, WidgetRef ref, UserProfile profile) async {
    final noteController = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Request coaching from ${profile.displayName ?? profile.userId}'),
          content: TextField(
            controller: noteController,
            decoration: const InputDecoration(
              labelText: 'Message (optional)',
            ),
            maxLines: 3,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Send'),
            ),
          ],
        );
      },
    );

    if (result != true) return;

    try {
      final svc = ref.read(sl.crmRelationshipsServiceProvider);
      await svc.requestCoaching(coachId: profile.userId, note: noteController.text.trim());
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Request sent')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send request: $e')),
        );
      }
    }
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/widgets/coach_rating_display.dart';
import 'package:workout_app/widgets/review_card.dart';
import 'package:workout_app/widgets/review_form_dialog.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_profile.dart';
import '../models/user_stats.dart';
import '../models/crm_coach_athlete_link.dart';
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
    final reviewsAsync = ref.watch(coachReviewsProvider(userId));

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
          ref.invalidate(coachReviewsProvider(userId));
          await Future.wait([
            ref.read(publicUserProfileProvider(userId).future),
            ref.read(publicProfileAggregatesProvider(userId).future),
            ref.read(coachReviewsProvider(userId).future),
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
    final coaching = profile.coaching;
    final canRequestCoaching = !isSelf && coaching != null && coaching.enabled;

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
              onRequestCoaching:
                  canRequestCoaching ? () => _showRequestDialog(context, ref, profile) : null,
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
        if (coaching != null && coaching.enabled) ...[
          const SizedBox(height: 32),
          _buildReviewsSection(context, ref, profile),
        ],
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
        String message;
        if (e is ApiException) {
          message = e.message;
        } else {
          message = 'Failed to send request: $e';
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
      }
    }
  }

  Widget _buildReviewsSection(BuildContext context, WidgetRef ref, UserProfile profile) {
    final reviewsAsync = ref.watch(coachReviewsProvider(profile.userId));
    final coaching = profile.coaching;
    final currentUser = FirebaseAuth.instance.currentUser;
    final isSelf = currentUser != null && currentUser.uid == profile.userId;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Reviews',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(width: 8),
            if (coaching != null && coaching.averageRating != null)
              CoachRatingDisplay(
                averageRating: coaching.averageRating,
                reviewCount: coaching.reviewCount,
              ),
          ],
        ),
        const SizedBox(height: 16),
        if (!isSelf && coaching != null && coaching.enabled)
          ElevatedButton.icon(
            onPressed: () => _showReviewDialog(context, ref, profile),
            icon: const Icon(Icons.star),
            label: const Text('Write a Review'),
          ),
        if (!isSelf && coaching != null && coaching.enabled) const SizedBox(height: 16),
        reviewsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => const Center(child: Text('Failed to load reviews')),
          data: (response) {
            if (response.reviews.isEmpty) {
              return const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(
                    child: Text('No reviews yet'),
                  ),
                ),
              );
            }
            return Column(
              children: response.reviews.map((review) => ReviewCard(review: review)).toList(),
            );
          },
        ),
      ],
    );
  }

  Future<void> _showReviewDialog(BuildContext context, WidgetRef ref, UserProfile profile) async {
    final currentUser = FirebaseAuth.instance.currentUser;
    if (currentUser == null) return;

    try {
      final svc = ref.read(sl.crmRelationshipsServiceProvider);
      final links = await svc.getMyCoaches(status: 'active');
      final link = links.firstWhere(
        (l) => l.coachId == profile.userId,
        orElse: () => throw Exception('No active coaching relationship found'),
      );

      if (!context.mounted) return;

      await showDialog(
        context: context,
        builder: (ctx) => ReviewFormDialog(
          linkId: link.id,
          coachName: profile.displayName ?? profile.userId,
          onSubmit: (linkId, rating, comment) async {
            final reviewSvc = ref.read(sl.crmReviewsServiceProvider);
            await reviewSvc.createReview(
              linkId: linkId,
              rating: rating,
              comment: comment,
            );
            ref.invalidate(coachReviewsProvider(profile.userId));
            ref.invalidate(publicUserProfileProvider(profile.userId));
          },
        ),
      );
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Cannot review: $e')),
        );
      }
    }
  }
}

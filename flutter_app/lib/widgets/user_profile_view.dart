import 'package:flutter/material.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_profile.dart';

class UserProfileView extends StatelessWidget {
  final UserProfile profile;
  final bool isOwner;
  final String? subtitle;
  final String? avatarUrlOverride;
  final VoidCallback? onEditProfile;
  final VoidCallback? onManageCoaching;
  final VoidCallback? onRequestCoaching;
  final List<Widget> additionalSections;
  final bool showCoachingCard;

  const UserProfileView({
    super.key,
    required this.profile,
    required this.isOwner,
    this.subtitle,
    this.avatarUrlOverride,
    this.onEditProfile,
    this.onManageCoaching,
    this.onRequestCoaching,
    this.additionalSections = const [],
    this.showCoachingCard = true,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        _buildHeader(context),
        if ((profile.bio ?? '').isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            profile.bio!,
            style: const TextStyle(fontSize: 14, color: AppColors.textSecondary),
          ),
        ],
        if (showCoachingCard) ...[
          const SizedBox(height: 24),
          _buildCoachingCard(context),
        ],
        ...additionalSections,
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    final avatarUrl = avatarUrlOverride ?? profile.photoUrl;

    return Column(
      children: [
        CircleAvatar(
          radius: 50,
          backgroundColor: AppColors.primary.withOpacity(0.15),
          backgroundImage: avatarUrl != null ? NetworkImage(avatarUrl) : null,
          child: avatarUrl == null
              ? Text(
                  (profile.displayName?.isNotEmpty ?? false)
                      ? profile.displayName!.substring(0, 1).toUpperCase()
                      : profile.userId.substring(0, 1).toUpperCase(),
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: AppColors.primary),
                )
              : null,
        ),
        const SizedBox(height: 16),
        Text(
          profile.displayName ?? 'User ${profile.userId}',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle ?? profile.userId,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
        ),
        if (isOwner && (onEditProfile != null || onManageCoaching != null)) ...[
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              if (onEditProfile != null)
                OutlinedButton.icon(
                  onPressed: onEditProfile,
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  label: const Text('Edit profile'),
                ),
              if (onManageCoaching != null)
                OutlinedButton.icon(
                  onPressed: onManageCoaching,
                  icon: const Icon(Icons.workspace_premium_outlined, size: 16),
                  label: const Text('Coaching settings'),
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildCoachingCard(BuildContext context) {
    final coaching = profile.coaching;
    final enabled = coaching?.enabled ?? false;
    final accepting = coaching?.acceptingClients ?? false;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.workspace_premium_outlined, color: AppColors.primary),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Coaching',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              if (enabled)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: accepting ? const Color(0xFFE6F4EA) : const Color(0xFFFFF3E0),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    accepting ? 'Accepting new clients' : 'Not accepting',
                    style: TextStyle(
                      fontSize: 12,
                      color: accepting ? AppColors.success : AppColors.textSecondary,
                    ),
                  ),
                )
              else
                const Text('Coaching disabled', style: TextStyle(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 16),
          if (!enabled)
            const Text(
              'This user has not enabled coaching options.',
              style: TextStyle(color: AppColors.textSecondary),
            )
          else ...[
            if ((coaching?.tagline?.isNotEmpty ?? false)) ...[
              Text(coaching!.tagline!, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
            ],
            if ((coaching?.description?.isNotEmpty ?? false)) ...[
              Text(coaching!.description!, style: const TextStyle(fontSize: 14, color: AppColors.textSecondary)),
              const SizedBox(height: 12),
            ],
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if ((coaching?.specializations ?? []).isNotEmpty)
                  _chip('Specializations', coaching!.specializations.join(', ')),
                if ((coaching?.languages ?? []).isNotEmpty)
                  _chip('Languages', coaching!.languages.join(', ')),
                if (coaching?.experienceYears != null)
                  _chip('Experience', '${coaching!.experienceYears} yrs'),
                if ((coaching?.timezone?.isNotEmpty ?? false))
                  _chip('Timezone', coaching!.timezone!),
                if (coaching?.ratePlan != null)
                  _chip(
                    'Rate',
                    coaching!.ratePlan!.amountMinor != null && coaching.ratePlan!.currency != null
                        ? '${(coaching.ratePlan!.amountMinor! / 100).toStringAsFixed(0)} ${coaching.ratePlan!.currency!.toUpperCase()} ${coaching.ratePlan!.type ?? ''}'
                        : (coaching.ratePlan!.type ?? 'Custom rate'),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (!isOwner && onRequestCoaching != null)
              ElevatedButton.icon(
                onPressed: accepting ? onRequestCoaching : null,
                icon: const Icon(Icons.handshake_outlined),
                label: const Text('Request coaching'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.textPrimary,
                  foregroundColor: Colors.white,
                  disabledBackgroundColor: AppColors.textSecondary.withOpacity(0.3),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _chip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

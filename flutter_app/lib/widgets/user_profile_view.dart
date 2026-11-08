import 'package:flutter/material.dart';
import 'package:workout_app/l10n/app_localizations.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_profile.dart';

class UserProfileView extends StatelessWidget {
  final UserProfile profile;
  final bool isOwner;
  final String? subtitle;
  final String? avatarUrlOverride;
  final VoidCallback? onEditProfile;
  final VoidCallback? onManageCoaching;
  final VoidCallback? onAvatarTool;
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
    this.onAvatarTool,
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
            style: TextStyle(
              fontSize: 14,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
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
    final l10n = AppLocalizations.of(context);
    final avatarUrl = avatarUrlOverride ?? profile.photoUrl;

    return Column(
      children: [
        Stack(
          alignment: Alignment.bottomRight,
          children: [
            CircleAvatar(
              radius: 50,
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              backgroundImage: avatarUrl != null
                  ? NetworkImage(avatarUrl)
                  : null,
              child: avatarUrl == null
                  ? Text(
                      (profile.displayName?.isNotEmpty ?? false)
                          ? profile.displayName!.substring(0, 1).toUpperCase()
                          : profile.userId.substring(0, 1).toUpperCase(),
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    )
                  : null,
            ),
            if (isOwner && onAvatarTool != null)
              Material(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                shape: const CircleBorder(),
                elevation: 2,
                child: IconButton(
                  icon: const Icon(Icons.auto_awesome, size: 18),
                  onPressed: onAvatarTool,
                  tooltip: 'Avatar',
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          profile.displayName ?? 'User ${profile.userId}',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle ?? profile.userId,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 13,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
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
                  label: Text(l10n.editProfileButton),
                ),
              if (onManageCoaching != null)
                OutlinedButton.icon(
                  onPressed: onManageCoaching,
                  icon: const Icon(Icons.workspace_premium_outlined, size: 16),
                  label: Text(l10n.coachingSettingsButton),
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildCoachingCard(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final coaching = profile.coaching;
    final enabled = coaching?.enabled ?? false;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppShadows.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.workspace_premium_outlined,
                color: AppColors.primary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  l10n.coachingTitle,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
              ),
              if (enabled)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.tertiaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    l10n.coachingAcceptingNewClients,
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).colorScheme.onTertiaryContainer,
                    ),
                  ),
                )
              else
                Text(
                  l10n.coachingDisabled,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (!enabled)
            Text(
              l10n.coachingDisabledDescription,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            )
          else ...[
            if ((coaching?.tagline?.isNotEmpty ?? false)) ...[
              Text(
                coaching!.tagline!,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 8),
            ],
            if ((coaching?.description?.isNotEmpty ?? false)) ...[
              Text(
                coaching!.description!,
                style: TextStyle(
                  fontSize: 14,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 12),
            ],
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if ((coaching?.specializations ?? []).isNotEmpty)
                  _chip(
                    context,
                    l10n.coachingSpecializations,
                    coaching!.specializations.join(', '),
                  ),
                if ((coaching?.languages ?? []).isNotEmpty)
                  _chip(
                    context,
                    l10n.coachingLanguages,
                    coaching!.languages.join(', '),
                  ),
                if (coaching?.ratePlan != null)
                  _chip(
                    context,
                    l10n.coachingRate,
                    coaching!.ratePlan!.amountMinor != null
                        ? '${(coaching.ratePlan!.amountMinor! / 100).toStringAsFixed(0)} USD / month'
                        : l10n.coachingCustomRate,
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (!isOwner && onRequestCoaching != null)
              ElevatedButton.icon(
                onPressed: enabled ? onRequestCoaching : null,
                icon: const Icon(Icons.handshake_outlined),
                label: Text(l10n.requestCoaching),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.primary,
                  foregroundColor: Theme.of(context).colorScheme.onPrimary,
                  disabledBackgroundColor: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.12),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _chip(BuildContext context, String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_summary.dart';
import '../providers/providers.dart';
import 'public_user_profile_screen.dart';
import 'user_profile_screen.dart';

class AllUsersScreen extends ConsumerWidget {
  const AllUsersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usersAsync = ref.watch(allUsersProvider);

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'All Users',
            onTitleTap: openChat,
          ),
          body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(allUsersProvider);
          await ref.read(allUsersProvider.future);
        },
        child: usersAsync.when(
          data: (users) => _buildList(users),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline, size: 40, color: AppColors.error),
                  const SizedBox(height: 12),
                  Text('Failed to load users: $error'),
                  const SizedBox(height: 12),
                  ElevatedButton(
                    onPressed: () => ref.invalidate(allUsersProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
      },
    );
  }

  Widget _buildList(List<UserSummary> users) {
    if (users.isEmpty) {
      return const Center(child: Text('No users yet'));
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemBuilder: (context, index) {
        final user = users[index];
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: AppColors.surface,
            backgroundImage: user.photoUrl != null ? NetworkImage(user.photoUrl!) : null,
            child: user.photoUrl == null
                ? Text(
                    (user.displayName?.isNotEmpty ?? false)
                        ? user.displayName!.substring(0, 1).toUpperCase()
                        : user.userId.substring(0, 1).toUpperCase(),
                  )
                : null,
          ),
          title: Text(user.displayName ?? 'User ${user.userId}'),
          subtitle: Text('Created ${user.createdAt.toLocal()}'),
          trailing: user.isPublic
              ? const Icon(Icons.lock_open, size: 18, color: AppColors.success)
              : const Icon(Icons.lock_outline, size: 18, color: AppColors.textSecondary),
          onTap: () {
            final currentUser = FirebaseAuth.instance.currentUser;
            if (currentUser != null && currentUser.uid == user.userId) {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const UserProfileScreen(),
                ),
              );
            } else {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => PublicUserProfileScreen(
                    userId: user.userId,
                    initialName: user.displayName,
                  ),
                ),
              );
            }
          },
        );
      },
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemCount: users.length,
    );
  }
}

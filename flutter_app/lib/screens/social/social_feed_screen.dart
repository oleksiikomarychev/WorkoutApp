import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/social_service.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

final socialFeedProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final svc = ref.watch(sl.socialServiceProvider);
  final posts = await svc.getWorkoutFeed(limit: 20, expand: 'reactions');

  // Collect unique author Firebase UIDs
  final authorIds = posts
      .map((p) => p['firebase_uid']?.toString())
      .whereType<String>()
      .toSet()
      .toList();

  print('DEBUG: Author Firebase UIDs from posts: $authorIds');

  // Fetch authors using Firebase UIDs
  final authors = await svc.getUsersByIds(authorIds);
  print('DEBUG: Authors response: $authors');

  final authorsMap = {for (var a in authors) a['user_id'].toString(): a};
  print('DEBUG: Authors map keys: ${authorsMap.keys}');

  return {
    'posts': posts,
    'authors': authorsMap,
  };
});

class SocialFeedScreen extends ConsumerWidget {
  const SocialFeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncFeed = ref.watch(socialFeedProvider);

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Workout Feed',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(socialFeedProvider),
              ),
            ],
          ),
          body: asyncFeed.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Center(child: Text('Error: $error')),
            data: (data) {
              final posts = data['posts'] as List<Map<String, dynamic>>;
              final authors = data['authors'] as Map<String, dynamic>;
              
              if (posts.isEmpty) {
                return const Center(child: Text('No posts yet.'));
              }
              return RefreshIndicator(
                onRefresh: () async {
                  await ref.refresh(socialFeedProvider.future);
                },
                child: ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: posts.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final post = posts[index];
                    final authorId = post['firebase_uid']?.toString();
                    final author = authors[authorId] as Map<String, dynamic>?;
                    final authorName = author?['display_name']?.toString() ?? 'Unknown';
                    final authorPhoto = author?['photo_url']?.toString();
                    final content = post['content']?.toString() ?? '';
                    final createdAt = post['created_at']?.toString();
                    final reactions = post['reactions'] as List<dynamic>? ?? [];
                    final likeReaction = reactions.firstWhere(
                      (r) => r['type'] == 'like',
                      orElse: () => {'count': 0, 'user_reacted': false},
                    );
                    final likeCount = likeReaction['count'] as int? ?? 0;
                    final userReacted = likeReaction['user_reacted'] as bool? ?? false;
                    
                    final stats = (post['attachments'] is List)
                        ? (post['attachments'] as List).whereType<Map>().firstWhere(
                            (att) => att['type'] == 'workout_stats',
                            orElse: () => const {},
                          )
                        : const {};
                    return Card(
                      elevation: 2,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                if (authorPhoto != null)
                                  CircleAvatar(
                                    backgroundImage: NetworkImage(authorPhoto),
                                    radius: 20,
                                  )
                                else
                                  const CircleAvatar(
                                    child: Icon(Icons.person),
                                    radius: 20,
                                  ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    authorName,
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(content),
                            if (stats.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text('Stats: ${stats.entries.map((e) => '${e.key}: ${e.value}').join(', ')}'),
                            ],
                            const SizedBox(height: 12),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  createdAt ?? '',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                Row(
                                  children: [
                                    Text('$likeCount'),
                                    const SizedBox(width: 4),
                                    IconButton(
                                      icon: Icon(
                                        userReacted ? Icons.favorite : Icons.favorite_border,
                                        color: userReacted ? Colors.red : null,
                                      ),
                                      onPressed: () {
                                        final socialSvc = ref.read(sl.socialServiceProvider);
                                        socialSvc.toggleReaction(
                                          postId: post['id'].toString(),
                                          reactionType: 'like',
                                        );
                                        ref.refresh(socialFeedProvider);
                                      },
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              );
            },
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () {
              _showCreatePostDialog(context, ref);
            },
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }

  void _showCreatePostDialog(BuildContext context, WidgetRef ref) {
    final contentController = TextEditingController();
    String selectedScope = 'public';
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Create Post'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: contentController,
                maxLines: 5,
                decoration: const InputDecoration(
                  hintText: 'What\'s on your mind?',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: selectedScope,
                decoration: const InputDecoration(
                  labelText: 'Scope',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'public', child: Text('Public')),
                  DropdownMenuItem(value: 'followers', child: Text('Followers')),
                  DropdownMenuItem(value: 'private', child: Text('Private')),
                ],
                onChanged: (value) {
                  setState(() {
                    selectedScope = value ?? 'public';
                  });
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final content = contentController.text.trim();
                if (content.isEmpty) return;
                
                final socialSvc = ref.read(sl.socialServiceProvider);
                try {
                  await socialSvc.createWorkoutPost(
                    content: content,
                    scope: selectedScope,
                  );
                  if (context.mounted) {
                    Navigator.pop(context);
                    ref.refresh(socialFeedProvider);
                  }
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Error creating post: $e')),
                    );
                  }
                }
              },
              child: const Text('Post'),
            ),
          ],
        ),
      ),
    );
  }
}

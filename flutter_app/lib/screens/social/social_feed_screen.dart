import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/social_service.dart';

final socialFeedProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final svc = ref.watch(sl.socialServiceProvider);
  return await svc.getWorkoutFeed(limit: 20);
});

class SocialFeedScreen extends ConsumerWidget {
  const SocialFeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncFeed = ref.watch(socialFeedProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Workout Feed'),
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
        data: (posts) {
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
                debugPrint('SOCIAL POST: $post');
                final author = post['author']?['display_name']?.toString() ?? post['author']?['id']?.toString() ?? 'Unknown';
                final content = post['content']?.toString() ?? '';
                final createdAt = post['created_at']?.toString();
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
                        Text(
                          author,
                          style: Theme.of(context).textTheme.titleMedium,
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
                            IconButton(
                              icon: const Icon(Icons.favorite_border),
                              onPressed: () {
                                final socialSvc = ref.read(sl.socialServiceProvider);
                                socialSvc.toggleReaction(
                                  postId: post['id'].toString(),
                                  reactionType: 'like',
                                );
                              },
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
    );
  }
}

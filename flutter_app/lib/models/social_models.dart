class SocialAuthor {
  final String id;
  final String? displayName;
  final String? avatarUrl;

  const SocialAuthor({
    required this.id,
    this.displayName,
    this.avatarUrl,
  });

  factory SocialAuthor.fromJson(Map<String, dynamic> json) {
    return SocialAuthor(
      id: json['id']?.toString() ?? '',
      displayName: json['display_name']?.toString(),
      avatarUrl: json['avatar_url']?.toString(),
    );
  }
}

class SocialAttachment {
  final String type;
  final Map<String, dynamic> data;

  const SocialAttachment({required this.type, required this.data});

  factory SocialAttachment.fromJson(Map<String, dynamic> json) {
    final type = json['type']?.toString() ?? 'unknown';
    final data = Map<String, dynamic>.from(json)
      ..remove('type');
    return SocialAttachment(type: type, data: data);
  }
}

class SocialComment {
  final String id;
  final String content;
  final SocialAuthor? author;
  final DateTime? createdAt;

  const SocialComment({
    required this.id,
    required this.content,
    this.author,
    this.createdAt,
  });

  factory SocialComment.fromJson(Map<String, dynamic> json) {
    return SocialComment(
      id: json['id']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      author: json['author'] is Map<String, dynamic>
          ? SocialAuthor.fromJson(json['author'] as Map<String, dynamic>)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
    );
  }
}

class SocialPost {
  final String id;
  final String content;
  final SocialAuthor? author;
  final DateTime? createdAt;
  final List<SocialAttachment> attachments;
  final List<SocialComment> comments;
  final Map<String, dynamic> metadata;

  const SocialPost({
    required this.id,
    required this.content,
    this.author,
    this.createdAt,
    this.attachments = const [],
    this.comments = const [],
    this.metadata = const {},
  });

  factory SocialPost.fromJson(Map<String, dynamic> json) {
    final attachments = <SocialAttachment>[];
    if (json['attachments'] is List) {
      for (final att in json['attachments']) {
        if (att is Map<String, dynamic>) {
          attachments.add(SocialAttachment.fromJson(att));
        }
      }
    }

    final comments = <SocialComment>[];
    if (json['comments'] is List) {
      for (final c in json['comments']) {
        if (c is Map<String, dynamic>) {
          comments.add(SocialComment.fromJson(c));
        }
      }
    }

    final metadata = <String, dynamic>{};
    if (json['metadata'] is Map) {
      metadata.addAll(Map<String, dynamic>.from(json['metadata'] as Map));
    }

    return SocialPost(
      id: json['id']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      author: json['author'] is Map<String, dynamic>
          ? SocialAuthor.fromJson(json['author'] as Map<String, dynamic>)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
      attachments: attachments,
      comments: comments,
      metadata: metadata,
    );
  }
}

class SocialFeedResponse {
  final List<SocialPost> posts;
  final String? nextCursor;
  final bool hasMore;

  const SocialFeedResponse({
    required this.posts,
    this.nextCursor,
    required this.hasMore,
  });
}

class CoachReview {
  final int id;
  final int linkId;
  final String reviewerId;
  final String? reviewerName;
  final String coachId;
  final int rating;
  final String? comment;
  final DateTime createdAt;
  final DateTime updatedAt;

  const CoachReview({
    required this.id,
    required this.linkId,
    required this.reviewerId,
    this.reviewerName,
    required this.coachId,
    required this.rating,
    this.comment,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CoachReview.fromJson(Map<String, dynamic> json) {
    return CoachReview(
      id: json['id'] as int? ?? 0,
      linkId: json['link_id'] as int? ?? 0,
      reviewerId: json['reviewer_id']?.toString() ?? '',
      reviewerName: json['reviewer_name'] as String?,
      coachId: json['coach_id']?.toString() ?? '',
      rating: json['rating'] as int? ?? 0,
      comment: json['comment'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'link_id': linkId,
        'reviewer_id': reviewerId,
        'reviewer_name': reviewerName,
        'coach_id': coachId,
        'rating': rating,
        'comment': comment,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
      };
}

class CoachReviewListResponse {
  final List<CoachReview> reviews;
  final int total;
  final int limit;
  final int offset;

  const CoachReviewListResponse({
    required this.reviews,
    required this.total,
    required this.limit,
    required this.offset,
  });

  factory CoachReviewListResponse.fromJson(Map<String, dynamic> json) {
    return CoachReviewListResponse(
      reviews: (json['reviews'] as List<dynamic>?)
              ?.map((e) => CoachReview.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      total: json['total'] as int? ?? 0,
      limit: json['limit'] as int? ?? 100,
      offset: json['offset'] as int? ?? 0,
    );
  }
}

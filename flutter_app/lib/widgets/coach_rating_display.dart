import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class CoachRatingDisplay extends StatelessWidget {
  final double? averageRating;
  final int? reviewCount;
  final bool showCount;

  const CoachRatingDisplay({
    super.key,
    this.averageRating,
    this.reviewCount,
    this.showCount = true,
  });

  @override
  Widget build(BuildContext context) {
    if (averageRating == null || reviewCount == null || reviewCount == 0) {
      return const SizedBox.shrink();
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildStarRating(averageRating!),
        const SizedBox(width: 4),
        Text(
          averageRating!.toStringAsFixed(1),
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 14,
          ),
        ),
        if (showCount) ...[
          const SizedBox(width: 4),
          Text(
            '($reviewCount)',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildStarRating(double rating) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (index) {
        if (index < rating - 0.5) {
          return const Icon(
            Icons.star,
            color: AppColors.star,
            size: 16,
          );
        } else if (index < rating) {
          return const Icon(
            Icons.star_half,
            color: AppColors.star,
            size: 16,
          );
        } else {
          return Icon(
            Icons.star_border,
            color: AppColors.textSecondary.withOpacity(0.3),
            size: 16,
          );
        }
      }),
    );
  }
}

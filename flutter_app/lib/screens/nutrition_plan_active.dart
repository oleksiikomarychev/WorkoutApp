import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/plan_providers.dart';

class NutritionPlanActive extends ConsumerWidget {
  const NutritionPlanActive({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activePlanAsync = ref.watch(activeAppliedPlanProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Nutrition Plan'),
      ),
      body: activePlanAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Text('Error: $error'),
        ),
        data: (activePlan) {
          if (activePlan == null) {
            return const Center(
              child: Text('No active calendar plan'),
            );
          }

          final nutritionPlan = activePlan.calendarPlan.nutritionPlan;
          if (nutritionPlan == null || nutritionPlan.isEmpty) {
            return const Center(
              child: Text('No nutrition plan configured'),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Plan: ${activePlan.calendarPlan.name}',
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                _buildNutritionPlanContent(nutritionPlan),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildNutritionPlanContent(Map<String, dynamic> nutritionPlan) {
    final children = <Widget>[];

    nutritionPlan.forEach((key, value) {
      children.add(
        Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  key,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                if (value is Map<String, dynamic>)
                  ...value.entries.map((entry) {
                    return Padding(
                      padding: const EdgeInsets.only(left: 8, top: 4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${entry.key}: ',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                          ),
                          Expanded(
                            child: Text(
                              entry.value?.toString() ?? 'N/A',
                              style: const TextStyle(color: Colors.grey),
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList()
                else
                  Text(
                    value?.toString() ?? 'N/A',
                    style: const TextStyle(color: Colors.grey),
                  ),
              ],
            ),
          ),
        ),
      );
    });

    return Column(children: children);
  }
}

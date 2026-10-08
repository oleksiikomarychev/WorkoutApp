import 'package:flutter/material.dart';
import 'package:workout_app/src/api/nutrition_api.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'nutrition_plan_create.dart';

class NutritionPlanDetail extends StatefulWidget {
  final Map<String, dynamic> sessionData;

  const NutritionPlanDetail({super.key, required this.sessionData});

  @override
  State<NutritionPlanDetail> createState() => _NutritionPlanDetailState();
}

class _NutritionPlanDetailState extends State<NutritionPlanDetail> {
  Future<void> _deleteSession() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Session'),
        content: const Text('Are you sure you want to delete this session?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await NutritionApi.deleteSession(widget.sessionData['session_id']);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Session deleted successfully')),
          );
          Navigator.pop(context);
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final entries = widget.sessionData['entries'] as List<dynamic>? ?? [];

    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'nutrition_plan_detail',
        'entities': {
          'session_id': widget.sessionData['session_id'],
          'user_id': widget.sessionData['user_id'],
          'entries_count': entries.length,
        },
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: l10n.nutritionSessionTitle(
              widget.sessionData['session_id'].toString(),
            ),
            onTitleTap: openChat,
            showBack: true,
            actions: [
              IconButton(
                icon: const Icon(Icons.edit),
                onPressed: () async {
                  final result = await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) =>
                          NutritionPlanCreate(initialPlan: widget.sessionData),
                    ),
                  );
                  if (result != null && mounted) {
                    Navigator.pop(context, result);
                  }
                },
              ),
              IconButton(
                icon: const Icon(Icons.delete),
                onPressed: _deleteSession,
              ),
            ],
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildInfoSection(l10n),
                const SizedBox(height: 24),
                Text(
                  l10n.nutritionEntriesLabel,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                if (entries.isEmpty)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32.0),
                      child: Text(l10n.nutritionNoEntries),
                    ),
                  )
                else
                  ...entries.map((entry) {
                    final entryMap = entry as Map<String, dynamic>;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              entryMap['name'] ?? 'Unknown',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            _buildEntryRow(
                              l10n.typeLabel,
                              entryMap['type']?.toString() ?? "Unknown",
                            ),
                            _buildEntryRow(
                              l10n.dosageLabel,
                              '${entryMap['dosage'] ?? 0} ${entryMap['unit'] ?? ""}',
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildInfoSection(AppLocalizations l10n) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            _buildInfoRow(
              l10n.userIdLabel(widget.sessionData['user_id'].toString()),
              '',
            ),
            const Divider(),
            _buildInfoRow(l10n.dateLabel, widget.sessionData['date'] ?? "N/A"),
            const Divider(),
            _buildInfoRow(
              l10n.workoutIdLabel,
              widget.sessionData['workout_id']?.toString() ?? "N/A",
            ),
            const Divider(),
            _buildInfoRow(
              l10n.appliedPlanWorkoutIdLabel,
              widget.sessionData['applied_plan_workout_id']?.toString() ??
                  "N/A",
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
          ),
          Text(value, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildEntryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
          ),
          Text(value, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:workout_app/src/api/plan_api.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/src/widgets/apply_plan_widget.dart' show ApplyPlanWidget;
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/plan_service.dart';

class CalendarPlanDetail extends StatefulWidget {
  final CalendarPlan plan;

  const CalendarPlanDetail({super.key, required this.plan});

  @override
  _CalendarPlanDetailState createState() => _CalendarPlanDetailState();
}

class _CalendarPlanDetailState extends State<CalendarPlanDetail> {
  List<UserMax> _userMaxList = [];

  Future<void> _fetchUserMaxes() async {
    try {
      final userMaxes = await PlanApi.getUserMaxes();
      setState(() => _userMaxList = userMaxes);
    } catch (e) {
      print('Failed to fetch user maxes: $e');
    }
  }

  @override
  void initState() {
    super.initState();
    _fetchUserMaxes();
  }

  Future<void> _applyPlan(BuildContext context) async {
    try {
      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (context) => ApplyPlanWidget(
          userMaxList: _userMaxList,
          onApply: (settings) async {
            try {
              await PlanApi.applyPlan(
                planId: widget.plan.id,
                userMaxIds: settings['user_max_ids'],
                computeWeights: settings['compute_weights'],
                roundingStep: settings['rounding_step'],
                roundingMode: settings['rounding_mode'],
              );
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Plan applied successfully')),
              );
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to apply plan: $e')),
              );
            }
          },
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.plan.name),
        backgroundColor: Theme.of(context).primaryColor,
        actions: [
          IconButton(
            icon: const Icon(Icons.check),
            onPressed: () => _applyPlan(context),
            tooltip: 'Apply Plan',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildPlanInfo(context),
              const SizedBox(height: 20),
              const Text('Mesocycles', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              ...widget.plan.mesocycles.map((mesocycle) => _buildMesocycleExpansionTile(mesocycle)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPlanInfo(BuildContext context) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.calendar_today, color: Theme.of(context).primaryColor),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(widget.plan.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildInfoRow('Duration', '${widget.plan.durationWeeks} weeks'),
            _buildInfoRow('Active', widget.plan.isActive ? 'Yes' : 'No'),
            if (widget.plan.startDate != null) _buildInfoRow('Start Date', widget.plan.startDate!.toLocal().toString().split(' ')[0]),
            if (widget.plan.endDate != null) _buildInfoRow('End Date', widget.plan.endDate!.toLocal().toString().split(' ')[0]),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Text('$label: ', style: const TextStyle(fontWeight: FontWeight.w500)),
          Text(value),
        ],
      ),
    );
  }

  Widget _buildMesocycleExpansionTile(Mesocycle mesocycle) {
    return Card(
      elevation: 3,
      margin: const EdgeInsets.only(bottom: 12.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ExpansionTile(
        title: Row(
          children: [
            Chip(
              label: Text('Meso ${mesocycle.orderIndex}'),
              backgroundColor: Colors.blue.shade100,
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(mesocycle.name, style: const TextStyle(fontWeight: FontWeight.w600))),
          ],
        ),
        subtitle: Text('${mesocycle.microcycles.length} microcycles'),
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (mesocycle.weeksCount != null) _buildInfoRow('Weeks', '${mesocycle.weeksCount}'),
                if (mesocycle.microcycleLengthDays != null) _buildInfoRow('Microcycle Length', '${mesocycle.microcycleLengthDays} days'),
                if (mesocycle.normalizationValue != null && mesocycle.normalizationUnit != null)
                  _buildInfoRow('Normalization', '${mesocycle.normalizationValue} ${mesocycle.normalizationUnit}'),
                if (mesocycle.notes != null) ...[
                  const SizedBox(height: 8),
                  Text('Notes: ${mesocycle.notes}', style: const TextStyle(fontStyle: FontStyle.italic)),
                ],
                const SizedBox(height: 12),
                const Text('Microcycles:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ...mesocycle.microcycles.map((microcycle) => _buildMicrocycleCard(microcycle)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMicrocycleCard(Microcycle microcycle) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 8.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: ExpansionTile(
        title: Row(
          children: [
            Chip(
              label: Text('Micro ${microcycle.orderIndex}'),
              backgroundColor: Colors.green.shade100,
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(microcycle.name)),
          ],
        ),
        subtitle: Text('${microcycle.schedule.length} days scheduled'),
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (microcycle.daysCount != null) _buildInfoRow('Days', '${microcycle.daysCount}'),
                if (microcycle.normalizationValue != null && microcycle.normalizationUnit != null)
                  _buildInfoRow('Normalization', '${microcycle.normalizationValue} ${microcycle.normalizationUnit}'),
                if (microcycle.notes != null) ...[
                  const SizedBox(height: 8),
                  Text('Notes: ${microcycle.notes}', style: const TextStyle(fontStyle: FontStyle.italic)),
                ],
                const SizedBox(height: 12),
                _buildScheduleTable(microcycle.schedule),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScheduleTable(Map<String, List<dynamic>> schedule) {
    if (schedule.isEmpty) {
      return const Text('No schedule available');
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Day')),
          DataColumn(label: Text('Exercises')),
        ],
        rows: schedule.entries.map((entry) {
          final day = entry.key;
          final exercises = entry.value;
          final exerciseText = exercises.map((e) => 'Ex ${e.exerciseId} (${e.sets.length} sets)').join('\n');
          return DataRow(cells: [
            DataCell(Text(day, style: const TextStyle(fontWeight: FontWeight.bold))),
            DataCell(Text(exerciseText)),
          ]);
        }).toList(),
      ),
    );
  }
}

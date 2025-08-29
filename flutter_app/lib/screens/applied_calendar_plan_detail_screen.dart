import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/services/applied_calendar_plan_service.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/widgets/loading_indicator.dart';

class AppliedCalendarPlanDetailScreen extends ConsumerStatefulWidget {
  final int planId;

  const AppliedCalendarPlanDetailScreen({super.key, required this.planId});

  @override
  ConsumerState<AppliedCalendarPlanDetailScreen> createState() =>
      _AppliedCalendarPlanDetailScreenState();
}

class _AppliedCalendarPlanDetailScreenState
    extends ConsumerState<AppliedCalendarPlanDetailScreen> {
  final LoggerService _logger = LoggerService('AppliedCalendarPlanDetailScreen');
  bool _isLoading = true;
  String? _errorMessage;
  AppliedCalendarPlan? _plan;

  @override
  void initState() {
    super.initState();
    _loadPlanDetails();
  }

  Future<void> _loadPlanDetails() async {
    if (!mounted) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final service = ref.read(appliedCalendarPlanServiceProvider);
      final plan = await service.getAppliedCalendarPlan(widget.planId);

      if (!mounted) return;

      setState(() {
        _plan = plan;
      });
    } catch (e, stackTrace) {
      _logger.e('Error loading plan details: $e\n$stackTrace');

      if (!mounted) return;

      setState(() {
        _errorMessage = 'Не удалось загрузить детали плана.';
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: LoadingIndicator());
    }

    if (_errorMessage != null) {
      return ErrorMessage(
        message: _errorMessage!,
        onRetry: _loadPlanDetails,
      );
    }

    if (_plan == null) {
      return const Center(child: Text('План не найден.'));
    }

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const BackButton(),
                Expanded(
                  child: Text(
                    _plan?.calendarPlan.name ?? 'Детали плана',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(width: 48), // to balance the BackButton space
              ],
            ),
            const SizedBox(height: 16),
            _PlanDetailsCard(plan: _plan!),
            const SizedBox(height: 16),
            if (_plan!.nextWorkout != null)
              _NextWorkoutCard(nextWorkout: _plan!.nextWorkout!),
            const SizedBox(height: 16),
            _MesocyclesList(mesocycles: _plan!.calendarPlan.mesocycles ?? []),
            const SizedBox(height: 16),
            _UserMaxesCard(userMaxes: _plan!.userMaxes),
          ],
        ),
      ),
    );
  }
}

class _PlanDetailsCard extends StatelessWidget {
  final AppliedCalendarPlan plan;

  const _PlanDetailsCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (plan.isActive)
                  const Chip(
                    label: Text('Активен'),
                    backgroundColor: Colors.green.withOpacity(0.2),
                  ),
              ],
            ),
            Row(
              children: [
                const Icon(Icons.date_range, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Text(
                  _formatDateRange(plan.startDate, plan.endDate),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _NextWorkoutCard extends StatelessWidget {
  final NextWorkoutSummary nextWorkout;

  const _NextWorkoutCard({required this.nextWorkout});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Ближайшая тренировка',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.fitness_center, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(child: Text(nextWorkout.name)),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.schedule, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Text(_formatDate(nextWorkout.scheduledFor)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MesocyclesList extends StatelessWidget {
  final List<Mesocycle> mesocycles;

  const _MesocyclesList({required this.mesocycles});

  @override
  Widget build(BuildContext context) {
    if (mesocycles.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Структура плана',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        ...mesocycles.map((meso) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ExpansionTile(
                title: Text('Мезоцикл ${meso.orderIndex}: ${meso.name}'),
                children: (meso.microcycles ?? []).map((micro) => ListTile(
                  title: Text('  Микроцикл ${micro.orderIndex}: ${micro.name}'),
                )).toList(),
              ),
            )),
      ],
    );
  }
}

class _UserMaxesCard extends StatelessWidget {
  final List<UserMax> userMaxes;

  const _UserMaxesCard({required this.userMaxes});

  @override
  Widget build(BuildContext context) {
    if (userMaxes.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Пользовательские максимумы',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            ...userMaxes.map((max) => ListTile(
                  title: Text('Упражнение ID: ${max.exerciseId}'),
                  subtitle: Text('${max.maxWeight} кг x ${max.repMax} ПМ'),
                )),
          ],
        ),
      ),
    );
  }
}

String _formatDateRange(DateTime? start, DateTime end) {
  final s = start != null ? _formatDate(start) : 'n/a';
  final e = _formatDate(end);
  return '$s — $e';
}

String _formatDate(DateTime? date) {
  if (date == null) return '—';
  return '${date.year}-${_two(date.month)}-${_two(date.day)}';
}

String _two(int v) => v.toString().padLeft(2, '0');
  }
}

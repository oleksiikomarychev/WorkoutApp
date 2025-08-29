import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/widgets/empty_state.dart';

class AppliedCalendarPlansScreen extends ConsumerStatefulWidget {
  const AppliedCalendarPlansScreen({super.key});

  @override
  ConsumerState<AppliedCalendarPlansScreen> createState() => _AppliedCalendarPlansScreenState();
}

import 'package:workout_app/screens/applied_calendar_plan_detail_screen.dart';

class _AppliedCalendarPlansScreenState extends ConsumerState<AppliedCalendarPlansScreen> {
  final LoggerService _logger = LoggerService('AppliedCalendarPlansScreen');
  bool _isLoading = true;
  String? _errorMessage;
  List<AppliedCalendarPlanSummary> _plans = [];

  @override
  void initState() {
    super.initState();
    _loadAppliedPlans();
  }

  Future<void> _loadAppliedPlans() async {
    if (!mounted) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final service = ref.read(appliedCalendarPlanServiceProvider);
      final plans = await service.getUserAppliedCalendarPlanSummaries();

      if (!mounted) return;

      setState(() {
        _plans = plans;
      });
    } catch (e, stackTrace) {
      _logger.e('Error loading applied plans: $e\n$stackTrace');

      if (!mounted) return;

      setState(() {
        _errorMessage = 'Не удалось загрузить данные. Пожалуйста, проверьте подключение к интернету.';
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _navigateToDetail(int planId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => AppliedCalendarPlanDetailScreen(planId: planId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16.0, 16.0, 16.0, 8.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Мои планы тренировок', style: Theme.of(context).textTheme.headlineSmall),
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: _loadAppliedPlans,
                    tooltip: 'Обновить',
                  ),
                ],
              ),
            ),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: LoadingIndicator());
    }

    if (_errorMessage != null) {
      return ErrorMessage(
        message: _errorMessage!,
        onRetry: _loadAppliedPlans,
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAppliedPlans,
      child: _plans.isEmpty
          ? const SingleChildScrollView(
              physics: AlwaysScrollableScrollPhysics(),
              child: SizedBox(
                height: 400,
                child: Center(
                  child: EmptyState(
                    icon: Icons.event_busy,
                    title: 'Нет примененных планов',
                    description: 'Примените план, чтобы он появился в этом списке.',
                  ),
                ),
              ),
            )
          : ListView.builder(
              itemCount: _plans.length,
              itemBuilder: (context, index) {
                final plan = _plans[index];
                return _PlanSummaryCard(
                  plan: plan,
                  onTap: () => _navigateToDetail(plan.id),
                );
              },
            ),
    );
  }
}

class _PlanSummaryCard extends StatelessWidget {
  final AppliedCalendarPlanSummary plan;
  final VoidCallback onTap;

  const _PlanSummaryCard({required this.plan, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      plan.calendarPlan.name,
                      style: Theme.of(context).textTheme.titleLarge,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (plan.isActive)
                    Chip(
                      label: const Text('Активен'),
                      backgroundColor: Colors.green.withOpacity(0.2),
                      padding: EdgeInsets.zero,
                    ),
                ],
              ),
              const SizedBox(height: 8),
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
      ),
    );
  }


  static String _formatDateRange(DateTime? start, DateTime end) {
    final s = start != null
        ? '${start.year}-${_two(start.month)}-${_two(start.day)}'
        : 'n/a';
    final e = '${end.year}-${_two(end.month)}-${_two(end.day)}';
    return '$s — $e';
  }

  static String _two(int v) => v.toString().padLeft(2, '0');
}

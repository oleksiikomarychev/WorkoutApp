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

class _AppliedCalendarPlansScreenState extends ConsumerState<AppliedCalendarPlansScreen> {
  final LoggerService _logger = LoggerService('AppliedCalendarPlansScreen');
  bool _isLoading = true;
  String? _errorMessage;
  AppliedCalendarPlan? _activePlan;

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
      final active = await service.getActiveAppliedCalendarPlan();
      
      if (!mounted) return;
      
      // Update state with loaded data
      setState(() {
        _activePlan = active;
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

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: LoadingIndicator());
    }
    
    if (_errorMessage != null) {
      return ErrorMessage(
        message: _errorMessage!,
        onRetry: _loadAppliedPlans,
      );
    }
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Мои планы тренировок'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAppliedPlans,
            tooltip: 'Обновить',
          )
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAppliedPlans,
        child: _activePlan == null
            ? const SingleChildScrollView(
                physics: AlwaysScrollableScrollPhysics(),
                child: SizedBox(
                  height: 400,
                  child: Center(
                    child: EmptyState(
                      icon: Icons.event_busy,
                      title: 'Нет активного плана',
                      description: 'Примените план, чтобы видеть ближайшую тренировку.',
                    ),
                  ),
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _ActivePlanCard(plan: _activePlan!),
                ],
              ),
      ),
    );
  }
}

class _ActivePlanCard extends StatelessWidget {
  final AppliedCalendarPlan plan;
  const _ActivePlanCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final next = plan.nextWorkout;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              plan.calendarPlan.name,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.date_range, size: 18),
                const SizedBox(width: 8),
                Text(
                  _formatDateRange(plan.startDate, plan.endDate),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
            const Divider(height: 24),
            Text(
              'Ближайшая тренировка',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (next == null)
              const Text('Нет запланированных тренировок')
            else ...[
              Row(
                children: [
                  const Icon(Icons.fitness_center, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(next.name)),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.schedule, size: 18),
                  const SizedBox(width: 8),
                  Text(_formatDate(next.scheduledFor)),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _formatDate(DateTime? date) {
    if (date == null) return '—';
    return '${date.year}-${_two(date.month)}-${_two(date.day)} ${_two(date.hour)}:${_two(date.minute)}';
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

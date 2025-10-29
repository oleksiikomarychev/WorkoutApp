import 'package:flutter/material.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/screens/user_profile_screen.dart';
import 'calendar_plan_create.dart';
import 'calendar_plan_detail.dart';
import 'dart:async';

class CalendarPlansScreen extends StatefulWidget {
  const CalendarPlansScreen({super.key});

  @override
  State<CalendarPlansScreen> createState() => _CalendarPlansScreenState();
}

class _CalendarPlansScreenState extends State<CalendarPlansScreen> {
  final ApiClient _apiClient = ApiClient.create();
  List<CalendarPlan> _plans = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchPlans();
  }

  Future<void> _fetchPlans() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final endpoint = ApiConfig.getAllPlansEndpoint();
      final response = await _apiClient.get('$endpoint?roots_only=true');

      if (response is List) {
        setState(() {
          _plans = response.map((json) => CalendarPlan.fromJson(json)).toList();
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Invalid response format';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load plans: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _deletePlan(int planId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Plan'),
        content: const Text('Are you sure you want to delete this plan?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _apiClient.delete(ApiConfig.deleteCalendarPlanEndpoint(planId.toString()));
        // If successful, remove the plan from the list and update the UI
        setState(() {
          _plans.removeWhere((plan) => plan.id == planId);
        });
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete plan: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Training Plans'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchPlans,
          ),
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const UserProfileScreen()),
              );
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(child: Text(_errorMessage!))
              : _plans.isEmpty
                  ? const Center(child: Text('No plans available'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(16.0),
                      itemCount: _plans.length,
                      itemBuilder: (context, index) {
                        final plan = _plans[index];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 16.0),
                          child: ListTile(
                            title: Text(plan.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text('${plan.durationWeeks} weeks • ${plan.mesocycles.length} mesocycles'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  plan.isActive ? Icons.check_circle : Icons.circle_outlined,
                                  color: plan.isActive ? Colors.green : Colors.grey,
                                ),
                                const SizedBox(width: 8),
                                IconButton(
                                  icon: const Icon(Icons.delete, color: Colors.red),
                                  onPressed: () => _deletePlan(plan.id),
                                ),
                              ],
                            ),
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(builder: (context) => CalendarPlanDetail(plan: plan)),
                              );
                            },
                          ),
                        );
                      },
                    ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const CalendarPlanCreate()),
          );
        },
        child: const Icon(Icons.add),
        tooltip: 'Create new calendar plan',
      ),
    );
  }
}

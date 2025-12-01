import 'package:flutter/material.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../config/api_config.dart';
import '../models/user_max.dart';
import '../services/api_client.dart';
import 'user_max_widget.dart';

class UserMaxScreen extends StatefulWidget {
  const UserMaxScreen({super.key});

  @override
  State<UserMaxScreen> createState() => _UserMaxScreenState();
}

class _UserMaxScreenState extends State<UserMaxScreen> {
  final ApiClient _apiClient = ApiClient.create();
  late Future<List<UserMax>> _futureMaxes;

  @override
  void initState() {
    super.initState();
    _futureMaxes = _fetchUserMaxes();
  }

  Future<List<UserMax>> _fetchUserMaxes() async {
    final response = await _apiClient.get(
      ApiConfig.getUserMaxesEndpoint(),
      context: 'UserMaxScreen',
    );

    if (response is List) {
      return response
          .map((item) => UserMax.fromJson(
                item is Map<String, dynamic>
                    ? item
                    : Map<String, dynamic>.from(item as Map),
              ))
          .toList();
    }

    throw const FormatException('Unexpected response when fetching user maxes');
  }

  Future<Map<String, dynamic>> _fetchWeakMuscleAnalysis({bool useLlm = true}) async {
    // Build base endpoint and pass query params explicitly so ApiClient preserves them
    final endpoint = ApiConfig.getWeakMuscleAnalysisEndpoint(useLlm: false);
    final response = await _apiClient.get(
      endpoint,
      queryParams: { 'use_llm': useLlm.toString() },
      context: 'UserMaxScreen.analysis',
    );
    if (response is Map<String, dynamic>) return response;
    if (response is Map) return Map<String, dynamic>.from(response);
    throw const FormatException('Unexpected response for weak muscle analysis');
  }

  Future<Map<String, dynamic>> _buildChatContext() async {
    final nowIso = DateTime.now().toUtc().toIso8601String();
    return <String, dynamic>{
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'user_max',
      'role': 'athlete',
      'timestamp': nowIso,
      'entities': <String, dynamic>{},
    };
  }

  Future<void> _showWeakMuscleAnalysis() async {
    try {
      final data = await _fetchWeakMuscleAnalysis(useLlm: true);
      if (!mounted) return;
      // Build UI bottom sheet
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (ctx) {
          final weak = (data['weak_muscles'] as List?) ?? const [];
          final muscleStrength = (data['muscle_strength'] as Map?)?.cast<String, dynamic>() ?? const {};
          final trends = (data['trend'] as Map?)?.cast<String, dynamic>() ?? const {};
          final llmEnabled = data['llm_enabled'] == true;
          final anomalies = (data['anomalies'] as List?) ?? const [];
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.75,
            minChildSize: 0.5,
            builder: (_, controller) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: ListView(
                controller: controller,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Анализ слабых мышц',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                      if (llmEnabled)
                        const Tooltip(message: 'LLM обогащение включено', child: Icon(Icons.smart_toy_outlined))
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text('Топ слабых мышц', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (weak.isEmpty)
                    const Text('Нет данных')
                  else
                    ...weak.map((w) {
                      final m = w as Map;
                      final muscle = m['muscle']?.toString() ?? '-';
                      final z = m['z']?.toString() ?? '-';
                      final score = m['score']?.toString() ?? '-';
                      final pr = m['priority']?.toString();
                      final reason = m['priority_reason']?.toString();
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(muscle),
                        subtitle: Text('z=$z, score=$score${pr != null ? ', priority=$pr' : ''}${reason != null && reason.isNotEmpty ? '\n$reason' : ''}'),
                      );
                    }),
                  const Divider(height: 24),
                  Text('Сила по мышцам', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (muscleStrength.isEmpty)
                    const Text('Нет данных')
                  else ...(
                    muscleStrength.entries
                      .toList()
                      ..sort((a, b) => (a.key).compareTo(b.key))
                  ).map((e) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 2.0),
                            child: Row(
                              children: [
                                Expanded(child: Text(e.key)),
                                Text(e.value.toString()),
                              ],
                            ),
                          )),
                  const Divider(height: 24),
                  Text('Тренды', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  if (trends.isEmpty)
                    const Text('Нет данных')
                  else
                    ...trends.entries.map((e) {
                      final v = (e.value as Map).cast<String, dynamic>();
                      final ra = v['recent_avg'];
                      final pa = v['prev_avg'];
                      final d = v['delta'];
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: Text(e.key),
                        subtitle: Text('recent=${ra ?? '-'}, prev=${pa ?? '-'}, Δ=${d ?? '-'}'),
                      );
                    }),
                  const Divider(height: 24),
                  Text('Аномалии', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(anomalies.isEmpty ? 'Не обнаружены' : anomalies.join(', ')),
                ],
              ),
            ),
          );
        },
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка анализа: $e')),
      );
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _futureMaxes = _fetchUserMaxes();
    });
    await _futureMaxes;
  }

  String _exerciseTitle(UserMax max) {
    if (max.exerciseName.isNotEmpty) return max.exerciseName;
    if (max.name.isNotEmpty) return max.name;
    return 'Упражнение ${max.exerciseId}';
  }

  Future<void> _deleteUserMax(UserMax max) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить максимум?'),
        content: Text('${_exerciseTitle(max)}\n${max.maxWeight} кг × ${max.repMax} повторений'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Удалить'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await _apiClient.delete(
        ApiConfig.deleteUserMaxEndpoint(max.id.toString()),
        context: 'UserMaxScreen.delete',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Максимум удалён')),
        );
        await _refresh();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Не удалось удалить максимум: $e')),
        );
      }
    }
  }

  Widget _buildAttemptRow(UserMax max, {required bool highlight}) {
    final textStyle = highlight
        ? Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold)
        : Theme.of(context).textTheme.bodyMedium;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${max.maxWeight} кг', style: textStyle),
                Text('Повторения: ${max.repMax}', style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Удалить максимум',
            icon: const Icon(Icons.delete_outline),
            onPressed: () => _deleteUserMax(max),
          ),
        ],
      ),
    );
  }

  Widget _buildGroupedList(List<UserMax> data) {
    final Map<int, List<UserMax>> grouped = {};
    for (final max in data) {
      grouped.putIfAbsent(max.exerciseId, () => []).add(max);
    }

    final entries = grouped.entries.toList()
      ..sort((a, b) {
        final nameA = _exerciseTitle(a.value.first);
        final nameB = _exerciseTitle(b.value.first);
        return nameA.toLowerCase().compareTo(nameB.toLowerCase());
      });

    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      itemCount: entries.length,
      separatorBuilder: (_, __) => const SizedBox(height: 16),
      itemBuilder: (context, index) {
        final entry = entries[index];
        final items = [...entry.value]
          ..sort((a, b) => b.maxWeight.compareTo(a.maxWeight));
        final top = items.first;

        return Card(
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _exerciseTitle(top),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('${top.maxWeight} кг', style: Theme.of(context).textTheme.titleMedium),
                        Text('Лучший: ${top.repMax} повторений', style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ...items.map((max) => _buildAttemptRow(max, highlight: max.id == top.id)),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AssistantChatHost(
      contextBuilder: _buildChatContext,
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'User Maxes',
            onTitleTap: openChat,
            actions: [
              IconButton(
                tooltip: 'Анализ слабых мышц',
                icon: const Icon(Icons.analytics_outlined),
                onPressed: _showWeakMuscleAnalysis,
              ),
            ],
          ),
          body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<UserMax>>(
          future: _futureMaxes,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Text('Failed to load user maxes: ${snapshot.error}'),
                  ),
                ],
              );
            }

            final data = snapshot.data ?? [];
            if (data.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Text('Нет сохранённых максимумов'),
                  ),
                ],
              );
            }

            return _buildGroupedList(data);
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final created = await showModalBottomSheet<bool>(
            context: context,
            isScrollControlled: true,
            builder: (context) => Padding(
              padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
              child: const UserMaxWidget(),
            ),
          );
          if (created == true) {
            await _refresh();
          }
        },
        child: const Icon(Icons.add),
      ),
    );
      },
    );
  }

  @override
  void dispose() {
    _apiClient.dispose();
    super.dispose();
  }
}

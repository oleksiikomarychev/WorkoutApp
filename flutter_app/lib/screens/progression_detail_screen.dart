import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progression_template.dart';
import '../services/progression_service.dart';
import '../models/user_max.dart';
import '../services/user_max_service.dart';
import 'package:intl/intl.dart';

class ProgressionDetailScreen extends StatefulWidget {
  final int templateId;
  const ProgressionDetailScreen({Key? key, required this.templateId}) : super(key: key);

  @override
  _ProgressionDetailScreenState createState() => _ProgressionDetailScreenState();
}

class _ProgressionDetailScreenState extends State<ProgressionDetailScreen> {
  late Future<ProgressionTemplate> _templateFuture;
  late Future<UserMax?> _userMaxFuture;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTemplate();
  }

  Future<void> _loadTemplate() async {
    try {
      final service = Provider.of<ProgressionService>(context, listen: false);
      final template = await service.getTemplate(widget.templateId);
      if (mounted) {
        setState(() {
          _templateFuture = Future.value(template);
          _userMaxFuture = Provider.of<UserMaxService>(context, listen: false)
              .getUserMax(template.user_max_id);
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки шаблона: $e')),
        );
        Navigator.pop(context);
      }
    }
  }

  double? _calculateWeight(ProgressionTemplate template, UserMax? userMax) {
    if (userMax == null || template.intensity == 0) return null;
    return (template.intensity / 100) * userMax.maxWeight;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
              child: Row(
                children: [
                  const BackButton(),
                  Expanded(
                    child: Text(
                      'Детали шаблона',
                      style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: _isLoading ? null : _loadTemplate,
                  ),
                ],
              ),
            ),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : FutureBuilder<ProgressionTemplate>(
                      future: _templateFuture,
                      builder: (context, templateSnapshot) {
                        if (templateSnapshot.connectionState == ConnectionState.waiting) {
                          return const Center(child: CircularProgressIndicator());
                        }

                        if (templateSnapshot.hasError) {
                          return Center(child: Text('Ошибка: ${templateSnapshot.error}'));
                        }

                        final template = templateSnapshot.data!;

                        return FutureBuilder<UserMax?>(
                          future: _userMaxFuture,
                          builder: (context, userMaxSnapshot) {
                            if (userMaxSnapshot.connectionState == ConnectionState.waiting) {
                              return const Center(child: CircularProgressIndicator());
                            }

                            if (userMaxSnapshot.hasError) {
                              return Center(child: Text('Ошибка: ${userMaxSnapshot.error}'));
                            }

                            final userMax = userMaxSnapshot.data;
                            final calculatedWeight = _calculateWeight(template, userMax);

                            return SingleChildScrollView(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Title
                                  Text(
                                    template.name,
                                    style: Theme.of(context).textTheme.headlineMedium,
                                  ),
                                  const SizedBox(height: 16),

                                  // Description
                                  if (template.description != null && template.description!.isNotEmpty)
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'Описание:',
                                          style: Theme.of(context).textTheme.titleMedium,
                                        ),
                                        const SizedBox(height: 8),
                                        Text(
                                          template.description!,
                                          style: Theme.of(context).textTheme.bodyMedium,
                                        ),
                                        const SizedBox(height: 16),
                                      ],
                                    ),

                                  // Exercise
                                  Text(
                                    'Упражнение:',
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    userMax?.exerciseId.toString() ?? 'Не указано',
                                    style: Theme.of(context).textTheme.bodyLarge,
                                  ),
                                  const SizedBox(height: 16),

                                  // Parameters
                                  Text(
                                    'Параметры:',
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 8),
                                  _buildParameterRow('Интенсивность', '${template.intensity}%'),
                                  _buildParameterRow('Усилие (RPE)', template.effort.toString()),
                                  _buildParameterRow('Объем (повторения)', template.volume?.toString() ?? 'Не указано'),
                                  _buildParameterRow('Рассчитанный вес',
                                    calculatedWeight != null ?
                                    '${calculatedWeight.toStringAsFixed(1)} кг' :
                                    'Не рассчитано'
                                  ),
                                  const SizedBox(height: 16),
                                ],
                              ),
                            );
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildParameterRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

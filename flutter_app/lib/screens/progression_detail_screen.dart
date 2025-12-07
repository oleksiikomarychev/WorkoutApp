import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progression_template.dart';
import '../services/progression_service.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/widgets/floating_header_bar.dart';
import 'package:workout_app/screens/user_profile_screen.dart';

class ProgressionDetailScreen extends StatefulWidget {
  final int templateId;
  const ProgressionDetailScreen({super.key, required this.templateId});

  @override
  _ProgressionDetailScreenState createState() => _ProgressionDetailScreenState();
}

class _ProgressionDetailScreenState extends State<ProgressionDetailScreen> {
  late Future<ProgressionTemplate> _templateFuture;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          SafeArea(
            bottom: false,
            child: Stack(
              children: [
                Column(
                  children: [
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

                        return SingleChildScrollView(
                              padding: const EdgeInsets.only(
                                top: kToolbarHeight + 16,
                                left: 16,
                                right: 16,
                                bottom: 16,
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [

                                  Text(
                                    template.name,
                                    style: Theme.of(context).textTheme.headlineMedium,
                                  ),
                                  const SizedBox(height: 16),


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



                                  Text(
                                    'Параметры:',
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 8),
                                  _buildParameterRow('Интенсивность', '${template.intensity}%'),
                                  _buildParameterRow('Усилие (RPE)', template.effort.toString()),
                                  _buildParameterRow('Объем (повторения)', template.volume?.toString() ?? 'Не указано'),
                                  const SizedBox(height: 16),
                                ],
                              ),
                            );
                      },
                    ),
            ),
          ],
        ),
                Align(
                  alignment: Alignment.topCenter,
                  child: FloatingHeaderBar(
                    title: 'Детали шаблона',
                    leading: IconButton(
                      icon: const Icon(Icons.arrow_back),
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                    actions: [
                      IconButton(
                        icon: const Icon(Icons.refresh),
                        onPressed: _isLoading ? null : _loadTemplate,
                      ),
                    ],
                    onProfileTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const UserProfileScreen()),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
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

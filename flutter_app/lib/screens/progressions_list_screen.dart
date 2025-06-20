import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progression.dart';
import '../services/progression_service.dart';

class ProgressionsListScreen extends StatefulWidget {
  const ProgressionsListScreen({Key? key}) : super(key: key);

  @override
  _ProgressionsListScreenState createState() => _ProgressionsListScreenState();
}

class _ProgressionsListScreenState extends State<ProgressionsListScreen> {
  late Future<List<ProgressionTemplate>> _progressionsFuture;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadProgressions();
  }

  Future<void> _loadProgressions() async {
    setState(() => _isLoading = true);
    try {
      final progressionService = Provider.of<ProgressionService>(context, listen: false);
      _progressionsFuture = progressionService.getTemplates();
      await _progressionsFuture;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки прогрессий: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Прогрессии'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _loadProgressions,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<List<ProgressionTemplate>>(
              future: _progressionsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return Center(child: Text('Ошибка: ${snapshot.error}'));
                }

                final progressions = snapshot.data ?? [];

                if (progressions.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.timeline_outlined,
                          size: 64,
                          color: Colors.grey,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Нет сохраненных прогрессий',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Colors.grey,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ElevatedButton.icon(
                          onPressed: _loadProgressions,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Обновить'),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: progressions.length,
                  itemBuilder: (context, index) {
                    final progression = progressions[index];
                    return ListTile(
                      title: Text(progression.name),
                      subtitle: Text('${progression.sets} подхода по ${progression.intensity}%' + 
                          (progression.calculatedWeight != null 
                              ? ' • ${progression.calculatedWeight} кг' 
                              : '')),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => Scaffold(
                              appBar: AppBar(
                                title: const Text('Детали прогрессии'),
                              ),
                              body: Center(
                                child: Text('Детали прогрессии: ${progression.name}'),
                              ),
                            ),
                          ),
                        );
                      },
                    );
                  },
                );
              },
            ),
    );
  }
}

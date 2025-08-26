import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/widgets/empty_state.dart';

class ProgressionsScreen extends ConsumerStatefulWidget {
  const ProgressionsScreen({super.key});

  @override
  ConsumerState<ProgressionsScreen> createState() => _ProgressionsScreenState();
}

class _ProgressionsScreenState extends ConsumerState<ProgressionsScreen> {
  final LoggerService _logger = LoggerService('ProgressionsScreen');
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadProgressions();
  }

  Future<void> _loadProgressions() async {
    if (!mounted) return;
    
    setState(() => _isLoading = true);
    
    try {
      // TODO: Implement progressions loading logic
      await Future.delayed(const Duration(seconds: 1));
      
      if (!mounted) return;
      
      // Update state with loaded data
    } catch (e, stackTrace) {
      _logger.e('Error loading progressions', error: e, stackTrace: stackTrace);
      
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to load progressions'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Progressions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () {
              // TODO: Navigate to create progression screen
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : const EmptyState(
              icon: Icons.timeline,
              title: 'No Progressions Yet',
              description: 'Create your first progression to track your workout journey!',
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // TODO: Navigate to create progression screen
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http_parser/http_parser.dart';
import 'package:provider/provider.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';

class SettingsImportScreen extends StatefulWidget {
  const SettingsImportScreen({super.key});

  @override
  State<SettingsImportScreen> createState() => _SettingsImportScreenState();
}

class _SettingsImportScreenState extends State<SettingsImportScreen> {
  bool _importing = false;
  String? _selectedFileName;
  PlatformFile? _selectedFile;
  _ImportResult? _result;
  String? _error;
  String? _taskId;

  Future<void> _pickFile() async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['csv'],
      allowMultiple: false,
      withData: true,
    );
    final file = picked?.files.single;
    if (file == null) return;

    setState(() {
      _selectedFile = file;
      _selectedFileName = file.name;
      _result = null;
      _error = null;
    });
  }

  Future<void> _startImport() async {
    final file = _selectedFile;
    if (file == null) return;

    final bytes = file.bytes;
    if (bytes == null || bytes.isEmpty) {
      setState(() => _error = 'Failed to read file bytes');
      return;
    }

    setState(() {
      _importing = true;
      _error = null;
      _result = null;
      _taskId = null;
    });

    try {
      final apiClient = Provider.of<ApiClient>(context, listen: false);
      final response = await apiClient.postMultipart(
        ApiConfig.importHevyCsvEndpoint,
        bytes: bytes,
        fileField: 'file',
        filename: file.name,
        contentType: MediaType('text', 'csv'),
        context: 'SettingsImport.importHevy',
        timeout: const Duration(minutes: 5),
      );

      if (response is! Map<String, dynamic>) {
        throw Exception('Invalid response: expected JSON object');
      }

      final taskId = response['task_id'];
      if (taskId is! String || taskId.isEmpty) {
        throw Exception('Missing task_id in response');
      }

      if (!mounted) return;
      setState(() => _taskId = taskId);

      await _pollTask(apiClient, taskId);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (!mounted) return;
      setState(() => _importing = false);
    }
  }

  Future<void> _pollTask(ApiClient apiClient, String taskId) async {
    const pollInterval = Duration(seconds: 2);
    final deadline = DateTime.now().add(const Duration(minutes: 60));

    while (DateTime.now().isBefore(deadline)) {
      final statusJson = await apiClient.get(
        ApiConfig.importHevyTaskStatusEndpoint(taskId),
        timeout: const Duration(seconds: 30),
        context: 'SettingsImport.importHevy.status',
      );

      if (statusJson is! Map<String, dynamic>) {
        throw Exception('Invalid task status response');
      }

      final status = (statusJson['status'] ?? '').toString().toUpperCase();
      if (status == 'SUCCESS') {
        final result = statusJson['result'];
        if (result is Map<String, dynamic>) {
          if (!mounted) return;
          setState(() {
            _result = _ImportResult(
              createdWorkouts: result['created_workouts'] ?? 0,
              totalInFile: result['total_in_file'] ?? 0,
              errors: (result['errors'] as List?)?.length ?? 0,
            );
          });
          return;
        }
        if (!mounted) return;
        setState(() {
          _result = const _ImportResult(createdWorkouts: 0, totalInFile: 0, errors: 0);
        });
        return;
      }

      if (status == 'FAILURE') {
        final err = statusJson['error']?.toString() ?? 'Import failed';
        throw Exception(err);
      }

      await Future.delayed(pollInterval);
    }

    throw Exception('Import timed out (task did not finish in time)');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Import workouts')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.fitness_center, color: colorScheme.primary),
                        const SizedBox(width: 12),
                        Text('Hevy', style: theme.textTheme.titleMedium),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Import workout history from a Hevy CSV export file. '
                      'Go to Hevy app → Settings → Export data to get the file.',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: _importing ? null : _pickFile,
                      icon: const Icon(Icons.file_upload_outlined),
                      label: Text(_selectedFileName ?? 'Select CSV file'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (_selectedFile != null && _result == null)
              FilledButton.icon(
                onPressed: _importing ? null : _startImport,
                icon: _importing
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.cloud_upload),
                label: Text(_importing ? 'Importing...' : 'Start import'),
              ),
            if (_importing)
              const Padding(
                padding: EdgeInsets.only(top: 16),
                child: Column(
                  children: [
                    LinearProgressIndicator(),
                    SizedBox(height: 8),
                    Text(
                      'This may take a few minutes for large files...',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Card(
                  color: colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.error_outline, color: colorScheme.error),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _error!,
                            style: TextStyle(color: colorScheme.onErrorContainer),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            if (_result != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Card(
                  color: colorScheme.primaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.check_circle, color: colorScheme.primary),
                            const SizedBox(width: 12),
                            Text('Import complete', style: theme.textTheme.titleMedium),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text('Created: ${_result!.createdWorkouts} workouts'),
                        Text('Total in file: ${_result!.totalInFile}'),
                        if (_result!.errors > 0)
                          Text(
                            'Errors: ${_result!.errors}',
                            style: TextStyle(color: colorScheme.error),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ImportResult {
  final int createdWorkouts;
  final int totalInFile;
  final int errors;

  const _ImportResult({
    required this.createdWorkouts,
    required this.totalInFile,
    required this.errors,
  });
}

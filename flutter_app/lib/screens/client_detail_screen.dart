import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/client_brief.dart';
import 'package:workout_app/models/accounts/tag.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/client_notes_screen.dart';

class ClientDetailScreen extends StatefulWidget {
  final ClientBrief client;
  const ClientDetailScreen({super.key, required this.client});

  @override
  State<ClientDetailScreen> createState() => _ClientDetailScreenState();
}

class _ClientDetailScreenState extends State<ClientDetailScreen> {
  bool _loading = true;
  String? _error;
  List<Tag> _clientTags = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final tags = await context.accountsService.listClientTags(widget.client.id);
      setState(() {
        _clientTags = tags;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _openManageTags() async {
    final allTags = await context.accountsService.listTags();
    final selected = Set<String>.from(_clientTags.map((t) => t.id));
    final result = await showDialog<Set<String>>(
      context: context,
      builder: (context) {
        return StatefulBuilder(builder: (context, setSt) {
          return AlertDialog(
            title: const Text('Теги клиента'),
            content: SizedBox(
              width: 400,
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: allTags.length,
                itemBuilder: (context, index) {
                  final tag = allTags[index];
                  final checked = selected.contains(tag.id);
                  return CheckboxListTile(
                    value: checked,
                    title: Text(tag.name),
                    subtitle: tag.color != null ? Text(tag.color!) : null,
                    onChanged: (v) {
                      setSt(() {
                        if (v == true) {
                          selected.add(tag.id);
                        } else {
                          selected.remove(tag.id);
                        }
                      });
                    },
                  );
                },
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.pop(context, selected),
                child: const Text('Сохранить'),
              ),
            ],
          );
        });
      },
    );

    if (result == null) return;

    // Apply diff: attach new, detach removed
    final currentIds = _clientTags.map((t) => t.id).toSet();
    final toAttach = result.difference(currentIds);
    final toDetach = currentIds.difference(result);

    try {
      setState(() => _loading = true);
      for (final id in toAttach) {
        await context.accountsService.attachTagToClient(widget.client.id, id);
      }
      for (final id in toDetach) {
        await context.accountsService.detachTagFromClient(widget.client.id, id);
      }
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Теги обновлены')),
        );
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.client;

    return Scaffold(
      appBar: AppBar(
        title: Text(c.displayName ?? c.id),
        actions: [
          IconButton(
            tooltip: 'Управлять тегами',
            icon: const Icon(Icons.label_outline),
            onPressed: _loading ? null : _openManageTags,
          ),
          IconButton(
            tooltip: 'Заметки',
            icon: const Icon(Icons.sticky_note_2_outlined),
            onPressed: _loading
                ? null
                : () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ClientNotesScreen(client: widget.client),
                      ),
                    );
                  },
          ),
          IconButton(
            tooltip: 'Обновить',
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _load,
          )
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Ошибка: $_error'))
              : Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Client ID: ${c.id}'),
                      const SizedBox(height: 8),
                      Text('Статус связи: ${c.status}'),
                      const SizedBox(height: 16),
                      const Text('Теги:'),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _clientTags.isEmpty
                            ? [const Text('нет тегов')]
                            : _clientTags
                                .map(
                                  (t) => Chip(
                                    label: Text(t.name),
                                    backgroundColor: _parseColor(t.color),
                                  ),
                                )
                                .toList(),
                      ),
                    ],
                  ),
                ),
    );
  }

  Color? _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return null;
    try {
      var value = hex.replaceFirst('#', '');
      if (value.length == 6) value = 'FF$value';
      return Color(int.parse(value, radix: 16));
    } catch (_) {
      return null;
    }
  }
}

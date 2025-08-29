import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/client_note.dart';
import 'package:workout_app/models/accounts/client_brief.dart';
import 'package:workout_app/services/service_locator.dart';

class ClientNotesScreen extends StatefulWidget {
  final ClientBrief client;
  const ClientNotesScreen({super.key, required this.client});

  @override
  State<ClientNotesScreen> createState() => _ClientNotesScreenState();
}

class _ClientNotesScreenState extends State<ClientNotesScreen> {
  bool _loading = true;
  String? _error;
  List<ClientNote> _notes = [];

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
      final res = await context.accountsService.listClientNotes(widget.client.id);
      setState(() {
        _notes = res;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _createNote() async {
    final textCtl = TextEditingController();
    String visibility = 'coach_only';
    final result = await showDialog<({String text, String visibility})>(
      context: context,
      builder: (_) => StatefulBuilder(builder: (context, setSt) {
        return AlertDialog(
          title: const Text('Новая заметка'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: textCtl,
                maxLines: 5,
                decoration: const InputDecoration(labelText: 'Текст', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: visibility,
                decoration: const InputDecoration(labelText: 'Доступ', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'coach_only', child: Text('Только коуч')),
                  DropdownMenuItem(value: 'coach_and_client', child: Text('Коуч и клиент')),
                ],
                onChanged: (v) => setSt(() => visibility = v ?? 'coach_only'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Отмена')),
            ElevatedButton(onPressed: () => Navigator.pop(context, (text: textCtl.text.trim(), visibility: visibility)), child: const Text('Создать')),
          ],
        );
      }),
    );

    if (result == null || result.text.isEmpty) return;
    try {
      setState(() => _loading = true);
      await context.accountsService.createClientNote(
        widget.client.id,
        ClientNoteCreatePayload(text: result.text, visibility: result.visibility),
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Заметка добавлена')));
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _editNote(ClientNote note) async {
    final textCtl = TextEditingController(text: note.text);
    String visibility = note.visibility;
    final result = await showDialog<({String text, String visibility})>(
      context: context,
      builder: (_) => StatefulBuilder(builder: (context, setSt) {
        return AlertDialog(
          title: const Text('Редактировать заметку'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: textCtl,
                maxLines: 5,
                decoration: const InputDecoration(labelText: 'Текст', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: visibility,
                decoration: const InputDecoration(labelText: 'Доступ', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'coach_only', child: Text('Только коуч')),
                  DropdownMenuItem(value: 'coach_and_client', child: Text('Коуч и клиент')),
                ],
                onChanged: (v) => setSt(() => visibility = v ?? 'coach_only'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Отмена')),
            ElevatedButton(onPressed: () => Navigator.pop(context, (text: textCtl.text.trim(), visibility: visibility)), child: const Text('Сохранить')),
          ],
        );
      }),
    );

    if (result == null || result.text.isEmpty) return;
    try {
      setState(() => _loading = true);
      await context.accountsService.updateNote(
        note.id,
        ClientNoteUpdatePayload(text: result.text, visibility: result.visibility),
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Заметка обновлена')));
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _deleteNote(ClientNote note) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Удалить заметку'),
        content: const Text('Вы уверены?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Отмена')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Удалить')),
        ],
      ),
    );
    if (confirm != true) return;

    try {
      setState(() => _loading = true);
      await context.accountsService.deleteNote(note.id);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Заметка удалена')));
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
        title: Text('Заметки — ${c.displayName ?? c.id}')
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Ошибка: $_error'))
              : _notes.isEmpty
                  ? const Center(child: Text('Заметок нет'))
                  : ListView.separated(
                      itemCount: _notes.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final n = _notes[index];
                        return ListTile(
                          leading: const Icon(Icons.sticky_note_2_outlined),
                          title: Text(
                            n.text,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text('Доступ: ${n.visibility}'),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.edit),
                                onPressed: _loading ? null : () => _editNote(n),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline),
                                onPressed: _loading ? null : () => _deleteNote(n),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
      floatingActionButton: FloatingActionButton(
        onPressed: _loading ? null : _createNote,
        child: const Icon(Icons.add),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/tag.dart';
import 'package:workout_app/services/service_locator.dart';

class TagsScreen extends StatefulWidget {
  const TagsScreen({super.key});

  @override
  State<TagsScreen> createState() => _TagsScreenState();
}

class _TagsScreenState extends State<TagsScreen> {
  bool _loading = true;
  String? _error;
  List<Tag> _tags = [];

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
      final res = await context.accountsService.listTags();
      setState(() {
        _tags = res;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _createTag() async {
    final nameCtl = TextEditingController();
    final colorCtl = TextEditingController();
    final result = await showDialog<({String name, String? color})>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Новый тег'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtl,
              decoration: const InputDecoration(labelText: 'Название', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: colorCtl,
              decoration: const InputDecoration(labelText: 'Цвет (#RRGGBB)', border: OutlineInputBorder()),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Отмена')),
          ElevatedButton(onPressed: () => Navigator.pop(context, (name: nameCtl.text.trim(), color: colorCtl.text.trim().isEmpty ? null : colorCtl.text.trim())), child: const Text('Создать')),
        ],
      ),
    );
    if (result == null || result.name.isEmpty) return;
    try {
      setState(() => _loading = true);
      await context.accountsService.createTag(TagCreate(name: result.name, color: result.color));
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Тег создан')));
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _editTag(Tag tag) async {
    final nameCtl = TextEditingController(text: tag.name);
    final colorCtl = TextEditingController(text: tag.color ?? '');
    final result = await showDialog<({String name, String? color})>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Редактировать тег'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtl,
              decoration: const InputDecoration(labelText: 'Название', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: colorCtl,
              decoration: const InputDecoration(labelText: 'Цвет (#RRGGBB)', border: OutlineInputBorder()),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Отмена')),
          ElevatedButton(onPressed: () => Navigator.pop(context, (name: nameCtl.text.trim(), color: colorCtl.text.trim().isEmpty ? null : colorCtl.text.trim())), child: const Text('Сохранить')),
        ],
      ),
    );
    if (result == null || result.name.isEmpty) return;

    try {
      setState(() => _loading = true);
      // Only send changed fields
      final Map<String, dynamic> payload = {};
      if (result.name != tag.name) payload['name'] = result.name;
      if (result.color != tag.color) payload['color'] = result.color;
      if (payload.isEmpty) {
        setState(() => _loading = false);
        return;
      }
      await context.accountsService.updateTag(tag.id, TagUpdate(name: payload['name'], color: payload['color']));
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Тег обновлён')));
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _deleteTag(Tag tag) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Удалить тег'),
        content: Text('Вы уверены, что хотите удалить тег "${tag.name}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Отмена')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Удалить')),
        ],
      ),
    );
    if (confirm != true) return;

    try {
      setState(() => _loading = true);
      await context.accountsService.deleteTag(tag.id);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Тег удалён')));
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Теги'),
        actions: [
          IconButton(
            tooltip: 'Создать',
            icon: const Icon(Icons.add),
            onPressed: _loading ? null : _createTag,
          ),
          IconButton(
            tooltip: 'Обновить',
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Ошибка: $_error'))
              : _tags.isEmpty
                  ? const Center(child: Text('Тегов нет'))
                  : ListView.separated(
                      itemCount: _tags.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final tag = _tags[index];
                        return ListTile(
                          leading: CircleAvatar(backgroundColor: _parseColor(tag.color), child: const Icon(Icons.label, color: Colors.white, size: 18)),
                          title: Text(tag.name),
                          subtitle: tag.color != null ? Text(tag.color!) : null,
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                tooltip: 'Редактировать',
                                icon: const Icon(Icons.edit),
                                onPressed: _loading ? null : () => _editTag(tag),
                              ),
                              IconButton(
                                tooltip: 'Удалить',
                                icon: const Icon(Icons.delete_outline),
                                onPressed: _loading ? null : () => _deleteTag(tag),
                              ),
                            ],
                          ),
                        );
                      },
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

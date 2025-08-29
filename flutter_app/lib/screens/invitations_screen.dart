import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/invitation.dart';
import 'package:workout_app/services/service_locator.dart';

class InvitationsScreen extends StatefulWidget {
  const InvitationsScreen({super.key});

  @override
  State<InvitationsScreen> createState() => _InvitationsScreenState();
}

class _InvitationsScreenState extends State<InvitationsScreen> {
  bool _loading = true;
  String? _error;
  List<Invitation> _invitations = [];

  final _acceptCodeCtl = TextEditingController();

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
      final res = await context.accountsService.listInvitations();
      setState(() {
        _invitations = res;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _createInvitation() async {
    final emailCtl = TextEditingController();
    final ttlCtl = TextEditingController(text: '24');
    final result = await showDialog<({String emailOrUserId, int? ttlHours})>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Создать инвайт'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: emailCtl,
                decoration: const InputDecoration(
                  labelText: 'Email или User ID',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: ttlCtl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'TTL часов (опционально)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Отмена'),
            ),
            ElevatedButton(
              onPressed: () {
                final ttl = int.tryParse(ttlCtl.text.trim());
                Navigator.pop(context, (emailOrUserId: emailCtl.text.trim(), ttlHours: ttl));
              },
              child: const Text('Создать'),
            ),
          ],
        );
      },
    );

    if (result == null || result.emailOrUserId.isEmpty) return;

    try {
      setState(() => _loading = true);
      await context.accountsService.createInvitation(
        InvitationCreatePayload(emailOrUserId: result.emailOrUserId, ttlHours: result.ttlHours),
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Инвайт создан')),
        );
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _acceptInvitation() async {
    final code = _acceptCodeCtl.text.trim();
    if (code.isEmpty) return;
    try {
      setState(() => _loading = true);
      await context.accountsService.acceptInvitation(code);
      _acceptCodeCtl.clear();
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Инвайт принят')),
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
  void dispose() {
    _acceptCodeCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Инвайты'),
        actions: [
          IconButton(
            tooltip: 'Создать',
            icon: const Icon(Icons.add),
            onPressed: _loading ? null : _createInvitation,
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
              : Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _acceptCodeCtl,
                              decoration: const InputDecoration(
                                labelText: 'Код инвайта',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: _loading ? null : _acceptInvitation,
                            child: const Text('Принять'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Expanded(
                        child: _invitations.isEmpty
                            ? const Center(child: Text('Инвайтов нет'))
                            : ListView.separated(
                                itemCount: _invitations.length,
                                separatorBuilder: (_, __) => const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final inv = _invitations[index];
                                  return ListTile(
                                    leading: const Icon(Icons.mail_outline),
                                    title: Text(inv.emailOrUserId),
                                    subtitle: Text('Статус: ${inv.status} — Код: ${inv.code}'),
                                    trailing: inv.expiresAt != null
                                        ? Text('до ${inv.expiresAt}')
                                        : const SizedBox.shrink(),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),
                ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/client_brief.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/client_detail_screen.dart';

class ClientsScreen extends StatefulWidget {
  const ClientsScreen({super.key});

  @override
  State<ClientsScreen> createState() => _ClientsScreenState();
}

class _ClientsScreenState extends State<ClientsScreen> {
  bool _loading = true;
  String? _error;
  List<ClientBrief> _clients = [];

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
      final res = await context.accountsService.listClients();
      setState(() {
        _clients = res;
        _loading = false;
      });
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
        title: const Text('Клиенты'),
        actions: [
          IconButton(
            tooltip: 'Обновить',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          )
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Ошибка загрузки: $_error'),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Повторить'),
                        ),
                      ],
                    ),
                  ),
                )
              : _clients.isEmpty
                  ? const Center(child: Text('Клиенты не найдены'))
                  : ListView.separated(
                      itemCount: _clients.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final c = _clients[index];
                        return ListTile(
                          leading: const Icon(Icons.person_outline),
                          title: Text(c.displayName ?? c.id),
                          subtitle: Text('Статус: ${c.status}'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => ClientDetailScreen(client: c),
                              ),
                            );
                          },
                        );
                      },
                    ),
    );
  }
}

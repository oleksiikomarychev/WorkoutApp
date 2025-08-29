import 'package:flutter/material.dart';
import 'package:workout_app/screens/clients_screen.dart';

class UserBaseScreen extends StatefulWidget {
  const UserBaseScreen({super.key});

  @override
  State<UserBaseScreen> createState() => _UserBaseScreenState();
}

class _UserBaseScreenState extends State<UserBaseScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 1, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('База пользователей'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.people_outline), text: 'Клиенты'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          ClientsScreen(),
        ],
      ),
    );
  }
}

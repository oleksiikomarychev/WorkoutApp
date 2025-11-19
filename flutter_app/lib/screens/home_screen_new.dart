import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/screens/workouts_screen.dart';
import 'package:workout_app/screens/calendar_plans_screen.dart';
import 'package:workout_app/screens/debug_screen.dart';
import 'package:workout_app/widgets/custom_bottom_nav_bar.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/chat_service.dart';

class HomeScreenNew extends StatefulWidget {
  const HomeScreenNew({super.key});

  @override
  State<HomeScreenNew> createState() => _HomeScreenNewState();
}

class _HomeScreenNewState extends State<HomeScreenNew> {
  int _selectedIndex = 0;
  
  final List<Widget> _widgetOptions = [
    const WorkoutsScreen(),  // Connected to workoutEndpoint
    const CalendarPlansScreen(), // Connected to calendarPlansEndpoint
    const DebugScreen(),
  ];

  final List<String> _appBarTitles = [
    'Тренировки',  // workoutEndpoint
    'Планы тренировок',   // calendarPlansEndpoint
    'Отладка',
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
      // Log which endpoint is being accessed
      switch (index) {
        case 0: // Workouts
          debugPrint('Accessing endpoint: ${ApiConfig.workoutsEndpoint}');
          break;
        case 1: // Plans
          debugPrint('Accessing endpoint: ${ApiConfig.calendarPlansEndpoint}');
          break;
        case 2: // Debug
          debugPrint('Navigating to DebugScreen');
          break;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mediaQuery = MediaQuery.of(context);
    final bottomPadding = mediaQuery.padding.bottom;
    
    final bool showOuterAppBar = _selectedIndex == 2;

    return Scaffold(
      appBar: !showOuterAppBar
          ? null
          : AppBar(
              title: Text(_appBarTitles[_selectedIndex]),
              actions: [
                PopupMenuButton<String>(
                  onSelected: (value) async {
                    if (value == 'logout') {
                      // Show confirmation dialog
                      final shouldLogout = await showDialog<bool>(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: const Text('Выйти из аккаунта?'),
                          content: const Text('Вы уверены, что хотите выйти?'),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(false),
                              child: const Text('Отмена'),
                            ),
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(true),
                              child: const Text('Выйти'),
                            ),
                          ],
                        ),
                      );

                      if (shouldLogout == true && mounted) {
                        try {
                          try {
                            final chat = pv.Provider.of<ChatService>(context, listen: false);
                            await chat.disconnect();
                          } catch (_) {}
                          await FirebaseAuth.instance.signOut();
                          // AuthGate will automatically redirect to SignInScreen
                        } catch (e) {
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text('Ошибка при выходе: $e'),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        }
                      }
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem<String>(
                      value: 'logout',
                      child: Row(
                        children: const [
                          Icon(Icons.logout, size: 20),
                          SizedBox(width: 12),
                          Text('Выйти'),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
      body: _widgetOptions.elementAt(_selectedIndex),
      bottomNavigationBar: CustomBottomNavBar(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        items: const [
          BottomNavBarItem(
            icon: Icons.fitness_center,
            label: 'Тренировки',
            activeLabel: 'Тренировки',
          ),
          BottomNavBarItem(
            icon: Icons.schedule,
            label: 'Планы',
            activeLabel: 'Планы',
          ),
          BottomNavBarItem(
            icon: Icons.bug_report_outlined,
            label: 'Дебаг',
            activeLabel: 'Дебаг',
          ),
        ],
      ),
    );
  }
}

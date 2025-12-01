import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/workouts_screen.dart';
import 'package:workout_app/screens/calendar_plans_screen.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/coach/coach_athletes_screen.dart';
import 'package:workout_app/screens/debug_screen.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/social/social_feed_screen.dart';
import 'package:workout_app/widgets/custom_bottom_nav_bar.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/chat_service.dart';

class HomeScreenNew extends ConsumerStatefulWidget {
  const HomeScreenNew({super.key});

  @override
  ConsumerState<HomeScreenNew> createState() => _HomeScreenNewState();
}

enum HomeTab { workouts, plans, social, crm, debug }

class _HomeScreenNewState extends ConsumerState<HomeScreenNew> {
  HomeTab _activeTab = HomeTab.workouts;

  void _onItemTapped(HomeTab tab) {
    if (_activeTab == tab) return;
    setState(() {
      _activeTab = tab;
      switch (tab) {
        case HomeTab.workouts:
          debugPrint('Accessing endpoint: ${ApiConfig.workoutsEndpoint}');
          break;
        case HomeTab.plans:
          debugPrint('Accessing endpoint: ${ApiConfig.calendarPlansEndpoint}');
          break;
        case HomeTab.social:
          debugPrint('Opening social feed');
          break;
        case HomeTab.crm:
          debugPrint('Navigating to CoachDashboardScreen');
          break;
        case HomeTab.debug:
          debugPrint('Navigating to DebugScreen');
          break;
      }
    });
  }

  Widget _tabBody(HomeTab tab) {
    switch (tab) {
      case HomeTab.workouts:
        return WorkoutsScreen();
      case HomeTab.plans:
        return CalendarPlansScreen();
      case HomeTab.social:
        return SocialFeedScreen();
      case HomeTab.crm:
        return const CoachDashboardScreen();
      case HomeTab.debug:
        return const DebugScreen();
    }
  }

  String _tabTitle(HomeTab tab) {
    switch (tab) {
      case HomeTab.workouts:
        return 'Тренировки';
      case HomeTab.plans:
        return 'Планы тренировок';
      case HomeTab.social:
        return 'Лента';
      case HomeTab.crm:
        return 'CRM';
      case HomeTab.debug:
        return 'Отладка';
    }
  }

  BottomNavBarItem _navItemFor(HomeTab tab) {
    switch (tab) {
      case HomeTab.workouts:
        return const BottomNavBarItem(
          icon: Icons.fitness_center,
          label: 'Тренировки',
          activeLabel: 'Тренировки',
        );
      case HomeTab.plans:
        return const BottomNavBarItem(
          icon: Icons.schedule,
          label: 'Планы',
          activeLabel: 'Планы',
        );
      case HomeTab.social:
        return const BottomNavBarItem(
          icon: Icons.dynamic_feed_outlined,
          label: 'Лента',
          activeLabel: 'Лента',
        );
      case HomeTab.crm:
        return const BottomNavBarItem(
          icon: Icons.analytics_outlined,
          label: 'CRM',
          activeLabel: 'CRM',
        );
      case HomeTab.debug:
        return const BottomNavBarItem(
          icon: Icons.bug_report_outlined,
          label: 'Дебаг',
          activeLabel: 'Дебаг',
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(userProfileProvider);
    final isCoach = profileAsync.maybeWhen(
      data: (profile) => profile.coaching?.enabled ?? false,
      orElse: () => false,
    );

    final tabs = <HomeTab>[
      HomeTab.workouts,
      HomeTab.plans,
      HomeTab.social,
      if (isCoach) HomeTab.crm,
      HomeTab.debug,
    ];

    if (!tabs.contains(_activeTab)) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          setState(() {
            _activeTab = HomeTab.workouts;
          });
        }
      });
    }

    final theme = Theme.of(context);
    final mediaQuery = MediaQuery.of(context);
    final bottomPadding = mediaQuery.padding.bottom;
    
    final bool showOuterAppBar = _activeTab == HomeTab.debug;

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: !showOuterAppBar
              ? null
              : PrimaryAppBar(
                  title: _tabTitle(_activeTab),
                  onTitleTap: openChat,
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
          body: _tabBody(_activeTab),
          bottomNavigationBar: CustomBottomNavBar(
        currentIndex: tabs.indexOf(_activeTab).clamp(0, tabs.length - 1),
        onTap: (index) {
          if (index < 0 || index >= tabs.length) return;
          _onItemTapped(tabs[index]);
        },
        items: tabs.map(_navItemFor).toList(),
      ),
    );
      },
    );
  }
}

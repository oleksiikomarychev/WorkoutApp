import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:animations/animations.dart';
import 'package:provider/provider.dart';
import 'dart:ui';

import '../services/progression_service.dart';
import 'workout_list_screen.dart';
import 'exercise_list_screen.dart';
import 'user_max_screen.dart';
import 'progressions_list_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {

  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final isLightMode = Theme.of(context).brightness == Brightness.light;

    final List<Widget> screens = [
      WorkoutListScreen(progressionId: 1),
      const ExerciseListScreen(),
      const UserMaxScreen(),
      const ProgressionsListScreen(),
    ];
    final Map<int, Widget> tabs = {
      0: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          HeroIcon(HeroIcons.bolt, size: 20, color: colorScheme.primary),
          const SizedBox(width: 6),
          const Text('Тренировки'),
        ],
      ),
      1: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          HeroIcon(HeroIcons.fire, size: 20, color: colorScheme.tertiary),
          const SizedBox(width: 6),
          const Text('Упражнения'),
        ],
      ),
      2: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          HeroIcon(HeroIcons.chartBar, size: 20, color: colorScheme.secondary),
          const SizedBox(width: 6),
          const Text('Максимумы'),
        ],
      ),
      3: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          HeroIcon(HeroIcons.arrowTrendingUp, size: 20, color: Colors.purple),
          const SizedBox(width: 6),
          const Text('Прогрессии'),
        ],
      ),
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Workout App'),
        centerTitle: true,
        backgroundColor: isLightMode ? colorScheme.surface : colorScheme.surfaceVariant,
        actions: [
          IconButton(
            icon: Icon(isLightMode ? Icons.dark_mode_outlined : Icons.light_mode_outlined),
            tooltip: 'Сменить тему',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Смена темы будет доступна в следующих версиях')),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Настройки',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Настройки будут доступны в следующих версиях')),
              );
            },
          ),
        ],
        elevation: 0,
      ),
      body: screens[_currentIndex],
      bottomNavigationBar: _FancyNavBar(
        currentIndex: _currentIndex,
        onTap: (int idx) {
          setState(() {
            _currentIndex = idx;
          });
        },
        colorScheme: colorScheme,
      ),
    );
  }
}

class _FancyNavBar extends StatelessWidget {
  final int currentIndex;
  final Function(int) onTap;
  final ColorScheme colorScheme;

  const _FancyNavBar({
    Key? key,
    required this.currentIndex,
    required this.onTap,
    required this.colorScheme,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final items = [
      _NavBarItem(
        icon: HeroIcons.bolt,
        label: 'Тренировки',
        color: colorScheme.primary,
      ),
      _NavBarItem(
        icon: HeroIcons.fire,
        label: 'Упражнения',
        color: colorScheme.tertiary,
      ),
      _NavBarItem(
        icon: HeroIcons.chartBar,
        label: 'Максимумы',
        color: colorScheme.secondary,
      ),
      _NavBarItem(
        icon: HeroIcons.arrowTrendingUp,
        label: 'Прогрессии',
        color: colorScheme.primaryFixedDim,
      ),
    ];
    return Padding(
      padding: const EdgeInsets.only(bottom: 18, left: 16, right: 16, top: 8),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: colorScheme.surface.withOpacity(0.70),
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: colorScheme.primary.withOpacity(0.10),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
              border: Border.all(color: colorScheme.primary.withOpacity(0.08)),
            ),
            height: 70,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(items.length, (idx) {
                final selected = idx == currentIndex;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => onTap(idx),
                    behavior: HitTestBehavior.opaque,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 350),
                      curve: Curves.easeOutQuint,
                      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                      decoration: BoxDecoration(
                        color: selected
                            ? colorScheme.primary.withOpacity(0.15)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(18),
                        boxShadow: selected
                            ? [
                                BoxShadow(
                                  color: colorScheme.primary.withOpacity(0.25),
                                  blurRadius: 14,
                                  offset: const Offset(0, 4),
                                ),
                              ]
                            : [],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          AnimatedScale(
                            scale: selected ? 1.22 : 1.0,
                            duration: const Duration(milliseconds: 350),
                            curve: Curves.easeOutBack,
                            child: HeroIcon(
                              items[idx].icon,
                              color: selected
                                  ? items[idx].color
                                  : colorScheme.onSurfaceVariant,
                              size: 28,
                            ),
                          ),
                          const SizedBox(height: 4),
                          AnimatedDefaultTextStyle(
                            style: TextStyle(
                              color: selected
                                  ? items[idx].color
                                  : colorScheme.onSurfaceVariant,
                              fontWeight: selected ? FontWeight.bold : FontWeight.w500,
                              fontSize: selected ? 14 : 12,
                              shadows: selected
                                  ? [
                                      Shadow(
                                        color: items[idx].color.withOpacity(0.18),
                                        blurRadius: 8,
                                      ),
                                    ]
                                  : [],
                            ),
                            duration: const Duration(milliseconds: 350),
                            child: Text(items[idx].label),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavBarItem {
  final HeroIcons icon;
  final String label;
  final Color color;
  const _NavBarItem({required this.icon, required this.label, required this.color});
}

// --- Остальной код ---

  Widget _buildRecentActivityCard({
    required String title,
    required String subtitle,
    required HeroIcons icon,
    required BuildContext context,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    
    return Card(
      color: colorScheme.surfaceContainerLow,
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colorScheme.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(16),
              ),
              child: HeroIcon(
                icon,
                color: colorScheme.primary,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.chevron_right),
              onPressed: () {},
            ),
          ],
        ),
      ),
    ).animate(delay: 500.ms).fadeIn(duration: 300.ms).slideX(begin: 0.2, end: 0);
  }
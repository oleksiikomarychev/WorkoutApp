import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:animations/animations.dart';

import 'workout_list_screen.dart';
import 'exercise_list_screen.dart';
import 'user_max_screen.dart';
import 'progression_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {

    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final isLightMode = Theme.of(context).brightness == Brightness.light;
    

    final menuItems = [
      MenuItemData(
        title: 'Тренировки',
        iconData: HeroIcons.bolt,
        primaryColor: colorScheme.primary,
        destinationScreen: const WorkoutListScreen(),
        subtitle: 'Управление тренировками',
      ),
      MenuItemData(
        title: 'Упражнения',
        iconData: HeroIcons.fire,
        primaryColor: colorScheme.tertiary,
        destinationScreen: const ExerciseListScreen(),
        subtitle: 'Список упражнений',
      ),
      MenuItemData(
        title: 'Мои максимумы',
        iconData: HeroIcons.chartBar,
        primaryColor: colorScheme.secondary,
        destinationScreen: const UserMaxScreen(),
        subtitle: 'Персональные рекорды',
      ),
      MenuItemData(
        title: 'Прогрессии',
        iconData: HeroIcons.arrowTrendingUp,
        primaryColor: colorScheme.error,
        destinationScreen: const ProgressionScreen(),
        subtitle: 'Схемы прогрессий',
      ),
    ];

    return Scaffold(
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [

          SliverAppBar.large(
            expandedHeight: 200.0,
            pinned: true,
            stretch: true,
            title: const Text('Workout App'),
            centerTitle: true,
            backgroundColor: isLightMode 
                ? colorScheme.surface 
                : colorScheme.surfaceVariant,
            actions: [
              IconButton(
                icon: Icon(isLightMode 
                    ? Icons.dark_mode_outlined 
                    : Icons.light_mode_outlined),
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
            flexibleSpace: FlexibleSpaceBar(
              centerTitle: true,
              background: Stack(
                children: [
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: isLightMode
                              ? [colorScheme.primaryContainer, colorScheme.surface]
                              : [colorScheme.surface, colorScheme.surfaceVariant],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    bottom: 0,
                    left: 24,
                    child: Text(
                      'Добро пожаловать!',
                      style: textTheme.headlineMedium?.copyWith(
                        color: isLightMode 
                            ? colorScheme.onPrimaryContainer
                            : colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.bold,
                      ),
                    ).animate(delay: 300.ms).fadeIn(duration: 500.ms).slideY(begin: 0.3, end: 0),
                  ),
                ],
              ),
            ),
          ),
          

          SliverPadding(
            padding: const EdgeInsets.all(16.0),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                childAspectRatio: 1.0,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
              ),
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final item = menuItems[index];
                  return _buildMenuItem(
                    context: context,
                    item: item,
                    index: index,
                  );
                },
                childCount: menuItems.length,
              ),
            ),
          ),
          

          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16.0),
                    child: Text(
                      'Последняя активность',
                      style: textTheme.titleLarge,
                    ),
                  ),
                  _buildRecentActivityCard(
                    title: 'Тренировка: Грудь и трицепс',
                    subtitle: 'Вчера, 18:30',
                    icon: HeroIcons.bolt,
                    context: context,
                  ),
                  const SizedBox(height: 12),
                  _buildRecentActivityCard(
                    title: 'Новый максимум: Жим лежа',
                    subtitle: '3 дня назад',
                    icon: HeroIcons.trophy,
                    context: context,
                  ),
                ],
              ),
            ),
          ),
          

          const SliverToBoxAdapter(
            child: SizedBox(height: 24),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem({
    required BuildContext context,
    required MenuItemData item,
    required int index,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return OpenContainer(
      transitionType: ContainerTransitionType.fadeThrough,
      openBuilder: (context, _) => item.destinationScreen,
      closedElevation: 0,
      closedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      closedColor: Theme.of(context).cardTheme.color ?? colorScheme.surface,
      closedBuilder: (context, openContainer) {
        return Card(
          color: colorScheme.surfaceContainerHigh,
          elevation: 0,
          child: InkWell(
            onTap: openContainer,
            borderRadius: BorderRadius.circular(20),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: item.primaryColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: HeroIcon(
                      item.iconData,
                      color: item.primaryColor,
                      size: 28,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    item.title,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Expanded(
                    child: Text(
                      item.subtitle,
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        )
        .animate(delay: (100 * index).ms)
        .fadeIn(duration: 300.ms)
        .slideY(begin: 0.2, end: 0);
      },
    );
  }

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
}

class MenuItemData {
  final String title;
  final String subtitle;
  final HeroIcons iconData;
  final Color primaryColor;
  final Widget destinationScreen;

  MenuItemData({
    required this.title,
    required this.iconData,
    required this.primaryColor,
    required this.destinationScreen,
    required this.subtitle,
  });
}

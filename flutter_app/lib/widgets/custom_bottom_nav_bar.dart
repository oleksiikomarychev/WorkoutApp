import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class BottomNavBarItem {
  final IconData icon;
  final String label;
  final String? activeLabel;

  const BottomNavBarItem({
    required this.icon,
    required this.label,
    this.activeLabel,
  });
}

class CustomBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<BottomNavBarItem> items;
  final Color? backgroundColor;
  final double elevation;
  final double height;
  final double iconSize;
  final double selectedFontSize;
  final double unselectedFontSize;
  final Duration animationDuration;
  final Curve animationCurve;

  const CustomBottomNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
    this.backgroundColor,
    this.elevation = 8.0,
    this.height = kBottomNavigationBarHeight,
    this.iconSize = 24.0,
    this.selectedFontSize = 12.0,
    this.unselectedFontSize = 12.0,
    this.animationDuration = const Duration(milliseconds: 200),
    this.animationCurve = Curves.easeInOut,
  }) : assert(items.length >= 2, 'BottomNavBar must have at least 2 items');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;
    final mediaQuery = MediaQuery.of(context);
    final bottomPadding = mediaQuery.padding.bottom;
    
    // Calculate available width for each item
    final screenWidth = mediaQuery.size.width;
    final itemCount = items.length.toDouble();
    final itemSpacing = 8.0; // Reduced spacing between items
    final horizontalPadding = 16.0; // Padding on the sides
    final availableWidth = screenWidth - (horizontalPadding * 2) - (itemSpacing * (itemCount - 1));
    final itemWidth = availableWidth / itemCount;

    return Material(
      color: backgroundColor ?? theme.scaffoldBackgroundColor,
      elevation: elevation,
      child: Container(
        decoration: BoxDecoration(
          boxShadow: [
            if (elevation > 0)
              BoxShadow(
                color: isDark ? Colors.black26 : Colors.grey.withOpacity(0.2),
                blurRadius: 8,
                offset: const Offset(0, -2),
              ),
          ],
        ),
        child: SafeArea(
          top: false,
          minimum: EdgeInsets.only(bottom: bottomPadding > 0 ? bottomPadding : 0),
          child: SizedBox(
            height: kBottomNavigationBarHeight,
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(
                  items.length,
                  (index) => SizedBox(
                    width: itemWidth,
                    child: _buildNavItem(
                      context: context,
                      item: items[index],
                      isSelected: index == currentIndex,
                      onTap: () => onTap(index),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem({
    required BuildContext context,
    required BottomNavBarItem item,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final textTheme = theme.textTheme;
    final label = isSelected ? (item.activeLabel ?? item.label) : item.label;
    final color = isSelected ? colorScheme.primary : colorScheme.onSurface.withOpacity(0.6);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8.0),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 2.0), // Reduced vertical padding
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Icon with animation - made more compact
              AnimatedContainer(
                duration: animationDuration,
                curve: animationCurve,
                padding: const EdgeInsets.all(4.0), // Reduced padding
                decoration: BoxDecoration(
                  color: isSelected 
                      ? colorScheme.primary.withOpacity(0.1) 
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(8.0), // Slightly smaller border radius
                ),
                child: Icon(
                  item.icon,
                  size: 20.0, // Slightly smaller icon
                  color: color,
                ),
              ),
              
              const SizedBox(height: 2.0), // Reduced spacing
              
              // Label with animation - made more compact
              AnimatedDefaultTextStyle(
                duration: animationDuration,
                curve: animationCurve,
                style: textTheme.labelSmall!.copyWith(
                  fontSize: isSelected ? 11.0 : 10.0, // Slightly smaller font
                  color: color,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  height: 1.1,
                ),
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              
              // Active indicator - made more subtle
              AnimatedContainer(
                duration: animationDuration,
                curve: animationCurve,
                margin: const EdgeInsets.only(top: 2.0),
                height: 2.0,
                width: isSelected ? 16.0 : 0.0, // Shorter indicator
                decoration: BoxDecoration(
                  color: colorScheme.primary,
                  borderRadius: BorderRadius.circular(1.0),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// Example usage with updated navigation items:
/*
int _currentIndex = 0;

CustomBottomNavBar(
  currentIndex: _currentIndex,
  onTap: (index) {
    setState(() {
      _currentIndex = index;
      // Handle navigation based on index
      switch (index) {
        case 0: // Workouts
          // Uses: ApiConfig.workoutsEndpoint
          break;
        case 1: // Exercises
          // Uses: ApiConfig.exercisesEndpoint
          break;
        case 2: // User Maxes
          // Uses: ApiConfig.userMaxesEndpoint
          break;
        case 3: // My Plans
          // Uses: ApiConfig.calendarPlansEndpoint
          break;
      }
    });
  },
  items: const [
    BottomNavBarItem(
      icon: Icons.fitness_center,
      label: 'Тренировки',
      activeLabel: 'Тренировки',
    ),
    BottomNavBarItem(
      icon: Icons.list_alt,
      label: 'Упражнения',
      activeLabel: 'Упражнения',
    ),
    BottomNavBarItem(
      icon: Icons.assessment,
      label: 'Максимумы',
      activeLabel: 'Максимумы',
    ),
    BottomNavBarItem(
      icon: Icons.assignment_turned_in,
      label: 'Мои планы',
      activeLabel: 'Мои планы',
    ),
  ],
)
*/

// API Endpoints used in navigation:
// - Workouts: ApiConfig.workoutsEndpoint
// - Exercises: ApiConfig.exercisesEndpoint
// - User Maxes: ApiConfig.userMaxesEndpoint
// - My Plans: ApiConfig.calendarPlansEndpoint

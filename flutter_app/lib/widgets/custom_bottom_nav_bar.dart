import 'dart:ui';
import 'package:flutter/material.dart';

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
    const double outerHorizontalPadding = 24.0;
    const double islandOffset = 16.0;
    final Color panelColor = backgroundColor ?? theme.scaffoldBackgroundColor;
    const List<Color> gradientColors = [
      Color(0xFF0D47A1),
      Color(0xFF1976D2),
      Color(0xFF5E35B1),
    ];

    return Material(
      color: Colors.transparent,
      elevation: 0,
      child: SizedBox(

        height: height + bottomPadding + islandOffset,
        child: SafeArea(
          top: false,
          bottom: true,
          child: Padding(
            padding: const EdgeInsets.only(
              left: outerHorizontalPadding,
              right: outerHorizontalPadding,
              bottom: islandOffset,
            ),
            child: Align(
              alignment: Alignment.bottomCenter,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: gradientColors,
                      ),
                      border: Border.all(
                        color: Colors.white.withOpacity(isDark ? 0.18 : 0.30),
                        width: 1.0,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(isDark ? 0.35 : 0.18),
                          blurRadius: 20,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: SizedBox(
                      height: height,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: List.generate(
                          items.length,
                          (index) => Expanded(
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
    final textTheme = theme.textTheme;
    final label = isSelected ? (item.activeLabel ?? item.label) : item.label;
    final Color iconColor = isSelected
        ? Colors.white
        : Colors.white.withOpacity(0.85);
    final Color textColor = iconColor;

    const borderRadius = BorderRadius.all(Radius.circular(999));

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: borderRadius,
        child: AnimatedContainer(
          duration: animationDuration,
          curve: animationCurve,
          padding: const EdgeInsets.symmetric(vertical: 6.0, horizontal: 12.0),
          decoration: BoxDecoration(
            borderRadius: borderRadius,
            color: isSelected
                ? Colors.white.withOpacity(0.18)
                : Colors.white.withOpacity(0.08),
            border: Border.all(
              color: Colors.white.withOpacity(isSelected ? 0.85 : 0.35),
              width: 1.0,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                item.icon,
                size: 20.0,
                color: iconColor,
              ),
              const SizedBox(height: 4.0),
              AnimatedDefaultTextStyle(
                duration: animationDuration,
                curve: animationCurve,
                style: textTheme.labelSmall!.copyWith(
                  fontSize: isSelected ? 11.0 : 10.0,
                  color: textColor,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  height: 1.1,
                ),
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}










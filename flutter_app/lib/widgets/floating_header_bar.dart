import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class FloatingHeaderBar extends StatelessWidget {
  final String title;
  final VoidCallback? onTitleTap;
  final VoidCallback? onProfileTap;
  final Widget? leading;
  final List<Widget>? actions;

  const FloatingHeaderBar({
    super.key,
    required this.title,
    this.onTitleTap,
    this.onProfileTap,
    this.leading,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    const gradientColors = [
      Color(0xFF0D47A1),
      Color(0xFF1976D2),
      Color(0xFF5E35B1),
    ];

    final theme = Theme.of(context);
    final textStyle = theme.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.w700,
          color: Colors.white,
        ) ??
        const TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          color: Colors.white,
        );

    final profileButton = onProfileTap == null
        ? null
        : IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            color: Colors.white,
            splashRadius: 22,
            onPressed: onProfileTap,
          );

    final effectiveActions = <Widget>[
      if (actions != null) ...actions!,
      if (profileButton != null) profileButton,
    ];

    Widget titleWidget = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withOpacity(0.08),
        boxShadow: const [
          BoxShadow(
            color: Color(0x221A1A1A),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        child: Text(title, style: textStyle, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center),
      ),
    );
    if (onTitleTap != null) {
      titleWidget = Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTitleTap,
          borderRadius: BorderRadius.circular(999),
          child: titleWidget,
        ),
      );
    }

    final decoratedActions = effectiveActions
        .map(
          (widget) => Container(
            margin: const EdgeInsets.only(left: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: Colors.white.withOpacity(0.12),
            ),
            child: IconTheme(
              data: const IconThemeData(color: Colors.white),
              child: widget,
            ),
          ),
        )
        .toList(growable: false);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Align(
        alignment: Alignment.topCenter,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(28),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
            child: Container(
              height: 56,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: gradientColors,
                ),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x331B1F3B),
                    blurRadius: 36,
                    offset: Offset(0, 22),
                    spreadRadius: 4,
                  ),
                  BoxShadow(
                    color: Color(0x14000000),
                    blurRadius: 16,
                    offset: Offset(0, 6),
                  ),
                ],
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (leading != null)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          leading!,
                          const SizedBox(width: 8),
                        ],
                      ),
                    ),
                  Center(
                    child: titleWidget,
                  ),
                  if (decoratedActions.isNotEmpty)
                    Align(
                      alignment: Alignment.centerRight,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: decoratedActions,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

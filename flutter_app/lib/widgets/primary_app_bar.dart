import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class PrimaryAppBar extends StatelessWidget implements PreferredSizeWidget {
  static const double _toolbarHeight = 72;
  static const List<Color> _gradientColors = [
    Color(0xFF0D47A1),
    Color(0xFF1976D2),
    Color(0xFF5E35B1),
  ];

  final String? title;
  final Widget? titleWidget;
  final VoidCallback? onTitleTap;
  final List<Widget>? actions;
  final bool? showBack;
  final VoidCallback? onBack;
  final Widget? leading;
  final bool centerTitle;
  final Color? backgroundColor;
  final TextStyle? titleTextStyle;
  final double elevation;
  final PreferredSizeWidget? bottom;

  const PrimaryAppBar({
    super.key,
    this.title,
    this.titleWidget,
    this.onTitleTap,
    this.actions,
    this.showBack,
    this.onBack,
    this.leading,
    this.centerTitle = false,
    this.backgroundColor,
    this.titleTextStyle,
    this.elevation = 0,
    this.bottom,
  });

  const PrimaryAppBar.main({
    super.key,
    required String this.title,
    this.onTitleTap,
    this.actions,
    this.backgroundColor,
    this.bottom,
  })  : titleWidget = null,
        showBack = null,
        onBack = null,
        leading = null,
        centerTitle = false,
        titleTextStyle = null,
        elevation = 0;

  const PrimaryAppBar.detail({
    super.key,
    required String this.title,
    this.actions,
    this.onBack,
    this.leading,
    this.centerTitle = false,
    this.backgroundColor,
    this.titleTextStyle,
    this.elevation = 0,
    this.bottom,
  })  : titleWidget = null,
        onTitleTap = null,
        showBack = true;

  @override
  Size get preferredSize {
    final double bottomHeight = bottom?.preferredSize.height ?? 0;
    return Size.fromHeight(_toolbarHeight + bottomHeight);
  }

  @override
  Widget build(BuildContext context) {
    final chipColor = backgroundColor ?? Colors.white.withOpacity(0.12);
    final TextStyle effectiveTitleStyle = titleTextStyle ??
        Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ) ??
        const TextStyle(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        );

    final bool effectiveShowBack = showBack ?? (ModalRoute.of(context)?.canPop ?? false);

    Widget? resolvedLeading = leading;
    if (resolvedLeading == null && effectiveShowBack) {
      resolvedLeading = IconButton(
        icon: const Icon(Icons.arrow_back),
        color: Colors.white,
        onPressed: onBack ?? () => Navigator.of(context).maybePop(),
      );
    }

    if (resolvedLeading != null) {
      resolvedLeading = _GlassChip(
        color: chipColor,
        margin: const EdgeInsets.only(right: 8),
        child: IconTheme(
          data: const IconThemeData(color: Colors.white),
          child: resolvedLeading!,
        ),
      );
    }

    Widget? resolvedTitle = titleWidget;
    if (resolvedTitle == null && title != null) {
      resolvedTitle = Text(title!, style: effectiveTitleStyle, overflow: TextOverflow.ellipsis);
    }

    if (resolvedTitle != null) {
      resolvedTitle = DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: Colors.white.withOpacity(0.1),
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
          child: resolvedTitle,
        ),
      );

      if (onTitleTap != null) {
        resolvedTitle = Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTitleTap,
            borderRadius: BorderRadius.circular(999),
            child: resolvedTitle,
          ),
        );
      }
    }

    final List<Widget> wrappedActions = actions != null
        ? actions!
            .map(
              (action) => _GlassChip(
                color: chipColor,
                margin: const EdgeInsets.only(left: 6),
                child: IconTheme(
                  data: const IconThemeData(color: Colors.white),
                  child: action,
                ),
              ),
            )
            .toList(growable: false)
        : const <Widget>[];

    return AppBar(
      automaticallyImplyLeading: false,
      backgroundColor: Colors.transparent,
      elevation: 0,
      toolbarHeight: _toolbarHeight,
      titleSpacing: 0,
      bottom: bottom,
      flexibleSpace: Padding(
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
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: _gradientColors,
                  ),
                  boxShadow: [
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
                    if (resolvedLeading != null)
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [resolvedLeading!],
                        ),
                      ),
                    if (wrappedActions.isNotEmpty)
                      Align(
                        alignment: Alignment.centerRight,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: wrappedActions,
                        ),
                      ),
                    if (resolvedTitle != null)
                      Center(
                        child: resolvedTitle,
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GlassChip extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? margin;
  final Color color;

  const _GlassChip({
    required this.child,
    this.margin,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color,
      ),
      child: child,
    );
  }
}

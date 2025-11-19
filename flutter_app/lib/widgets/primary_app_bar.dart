import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class PrimaryAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? title;
  final Widget? titleWidget;
  final VoidCallback? onTitleTap;
  final List<Widget>? actions;
  final bool showBack;
  final VoidCallback? onBack;
  final Widget? leading;
  final bool centerTitle;
  final Color? backgroundColor;
  final TextStyle? titleTextStyle;
  final double elevation;

  const PrimaryAppBar({
    super.key,
    this.title,
    this.titleWidget,
    this.onTitleTap,
    this.actions,
    this.showBack = false,
    this.onBack,
    this.leading,
    this.centerTitle = false,
    this.backgroundColor,
    this.titleTextStyle,
    this.elevation = 0,
  });

  const PrimaryAppBar.main({
    super.key,
    required String this.title,
    this.onTitleTap,
    this.actions,
    this.backgroundColor,
  })  : titleWidget = null,
        showBack = false,
        onBack = null,
        leading = null,
        centerTitle = false,
        titleTextStyle = null,
        elevation = 0;

  const PrimaryAppBar.detail({
    super.key,
    required String this.title,
    this.actions,
    this.showBack = true,
    this.onBack,
    this.leading,
    this.centerTitle = false,
    this.backgroundColor,
    this.titleTextStyle,
    this.elevation = 0,
  })  : titleWidget = null,
        onTitleTap = null;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final Color panelColor = theme.scaffoldBackgroundColor;
    final Color chipColor = backgroundColor ?? AppColors.surface;
    final TextStyle effectiveTitleStyle = titleTextStyle ??
        Theme.of(context).textTheme.titleLarge?.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ) ??
        const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        );

    Widget? resolvedLeading = leading;
    if (resolvedLeading == null && showBack) {
      resolvedLeading = Container(
        margin: const EdgeInsets.only(left: 12),
        decoration: BoxDecoration(
          color: chipColor,
          borderRadius: BorderRadius.circular(999),
        ),
        child: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: onBack ?? () => Navigator.of(context).maybePop(),
        ),
      );
    }

    Widget? resolvedTitle = titleWidget;
    if (resolvedTitle == null && title != null) {
      resolvedTitle = Text(title!, style: effectiveTitleStyle);
    }

    if (resolvedTitle != null) {
      resolvedTitle = Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: chipColor,
          borderRadius: BorderRadius.circular(999),
        ),
        child: resolvedTitle,
      );

      if (onTitleTap != null) {
        resolvedTitle = GestureDetector(
          onTap: onTitleTap,
          child: resolvedTitle,
        );
      }
    }

    final List<Widget>? wrappedActions = actions?.map((action) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Container(
          decoration: BoxDecoration(
            color: chipColor,
            borderRadius: BorderRadius.circular(999),
          ),
          child: action,
        ),
      );
    }).toList();

    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      leadingWidth: showBack ? 72 : null,
      leading: resolvedLeading,
      centerTitle: centerTitle,
      title: resolvedTitle,
      actions: wrappedActions,
      iconTheme: const IconThemeData(color: AppColors.textPrimary),
      flexibleSpace: IgnorePointer(
        child: ClipRect(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    panelColor.withOpacity(0.7),
                    panelColor.withOpacity(0.35),
                    panelColor.withOpacity(0.0),
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

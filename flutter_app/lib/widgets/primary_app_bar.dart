import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/config/constants/theme_constants.dart';

class PrimaryAppBar extends StatelessWidget implements PreferredSizeWidget {
  static const double _toolbarHeight = 72;

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
    this.centerTitle = true,
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
        centerTitle = true,
        titleTextStyle = null,
        elevation = 0;

  const PrimaryAppBar.detail({
    super.key,
    required String this.title,
    this.actions,
    this.onBack,
    this.leading,
    this.centerTitle = true,
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final chipColor = backgroundColor ??
        (isDark ? Colors.transparent : Colors.white.withOpacity(0.12));
    final VoidCallback? effectiveOnTitleTap = onTitleTap ?? AssistantChatHost.of(context)?.openChat;
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
      if (effectiveOnTitleTap != null) {
        resolvedTitle = Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.auto_awesome_outlined, size: 18, color: Color(0xFF9CB7B1)),
            const SizedBox(width: 8),
            Flexible(child: resolvedTitle),
          ],
        );
      }
    }

    if (resolvedTitle != null) {
      if (effectiveOnTitleTap != null) {
        resolvedTitle = Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: effectiveOnTitleTap,
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
      flexibleSpace: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          child: Align(
            alignment: Alignment.topCenter,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: BackdropFilter(
                  filter: ImageFilter.blur(
                    sigmaX: isDark ? 0 : 22,
                    sigmaY: isDark ? 0 : 22,
                  ),
                child: Container(
                  height: 56,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkChrome : null,
                    gradient: isDark ? null : AppGradients.blue,
                    boxShadow: isDark ? null : [
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
                  child: CustomMultiChildLayout(
                    delegate: _HeaderLayoutDelegate(centerTitle: centerTitle),
                    children: [
                      if (resolvedLeading != null)
                        LayoutId(id: _HeaderSlot.leading, child: resolvedLeading!),
                      if (resolvedTitle != null)
                        LayoutId(id: _HeaderSlot.title, child: resolvedTitle),
                      if (wrappedActions.isNotEmpty)
                        LayoutId(
                          id: _HeaderSlot.actions,
                          child: Row(mainAxisSize: MainAxisSize.min, children: wrappedActions),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

enum _HeaderSlot { leading, title, actions }

class _HeaderLayoutDelegate extends MultiChildLayoutDelegate {
  final bool centerTitle;

  _HeaderLayoutDelegate({required this.centerTitle});

  @override
  void performLayout(Size size) {
    Size leading = Size.zero;
    Size actions = Size.zero;
    final sideConstraints = BoxConstraints.loose(Size(size.width / 2, size.height));
    if (hasChild(_HeaderSlot.leading)) {
      leading = layoutChild(_HeaderSlot.leading, sideConstraints);
      positionChild(_HeaderSlot.leading, Offset(0, (size.height - leading.height) / 2));
    }
    if (hasChild(_HeaderSlot.actions)) {
      actions = layoutChild(_HeaderSlot.actions, sideConstraints);
      positionChild(_HeaderSlot.actions, Offset(size.width - actions.width, (size.height - actions.height) / 2));
    }
    if (hasChild(_HeaderSlot.title)) {
      final reserve = centerTitle
          ? (leading.width > actions.width ? leading.width : actions.width)
          : leading.width;
      final availableWidth = centerTitle
          ? (size.width - 2 * reserve).clamp(0.0, size.width)
          : (size.width - leading.width - actions.width).clamp(0.0, size.width);
      final title = layoutChild(
        _HeaderSlot.title,
        BoxConstraints.loose(Size(availableWidth, size.height)),
      );
      positionChild(
        _HeaderSlot.title,
        Offset(centerTitle ? (size.width - title.width) / 2 : leading.width,
            (size.height - title.height) / 2),
      );
    }
  }

  @override
  bool shouldRelayout(covariant _HeaderLayoutDelegate oldDelegate) =>
      oldDelegate.centerTitle != centerTitle;
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

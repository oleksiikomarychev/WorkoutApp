import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
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
    final VoidCallback? effectiveOnTitleTap = onTitleTap ?? AssistantChatHost.of(context)?.openChat;

    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
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

    Widget titleWidget = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (effectiveOnTitleTap != null) ...[
          const Icon(Icons.auto_awesome_outlined, size: 18, color: Color(0xFF9CB7B1)),
          const SizedBox(width: 8),
        ],
        Flexible(child: Text(title, style: textStyle, overflow: TextOverflow.ellipsis)),
      ],
    );
    if (effectiveOnTitleTap != null) {
      titleWidget = Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: effectiveOnTitleTap,
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
              color: isDark
                  ? Colors.transparent
                  : Colors.white.withOpacity(0.12),
            ),
            child: IconTheme(
              data: const IconThemeData(color: Colors.white),
              child: widget,
            ),
          ),
        )
        .toList(growable: false);

    final Widget? decoratedLeading = leading == null
        ? null
        : Container(
            margin: const EdgeInsets.only(right: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: isDark
                  ? Colors.transparent
                  : Colors.white.withOpacity(0.12),
            ),
            child: IconTheme(
              data: const IconThemeData(color: Colors.white),
              child: leading!,
            ),
          );

    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: Align(
          alignment: Alignment.topCenter,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(isDark ? 16 : 28),
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: isDark ? 0 : 22,
                sigmaY: isDark ? 0 : 22,
              ),
              child: Container(
                height: 56,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: theme.brightness == Brightness.dark
                      ? AppColors.darkChrome
                      : null,
                  gradient: theme.brightness == Brightness.dark
                      ? null
                      : AppGradients.blue,
                  boxShadow: isDark ? null : const [
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
                child: Row(
                  children: [
                    Flexible(
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: decoratedLeading ?? const SizedBox.shrink(),
                      ),
                    ),
                    Expanded(
                      flex: 2,
                      child: Center(child: titleWidget),
                    ),
                    Flexible(
                      child: Align(
                        alignment: Alignment.centerRight,
                        child: decoratedActions.isEmpty
                            ? const SizedBox.shrink()
                            : Row(
                                mainAxisSize: MainAxisSize.min,
                                children: decoratedActions,
                              ),
                      ),
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

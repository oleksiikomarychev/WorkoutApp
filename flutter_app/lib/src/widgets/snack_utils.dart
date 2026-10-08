import 'dart:async';

import 'package:flutter/material.dart';

final GlobalKey<ScaffoldMessengerState> rootScaffoldMessengerKey =
    GlobalKey<ScaffoldMessengerState>();

OverlayEntry? _activeSnackOverlay;
Timer? _activeSnackTimer;

void showAppSnackBar(
  BuildContext context,
  String message, {
  bool isError = false,
}) {
  final overlay = Overlay.of(context, rootOverlay: true);

  _activeSnackTimer?.cancel();
  _activeSnackOverlay?.remove();
  _activeSnackOverlay = null;

  final entry = OverlayEntry(
    builder: (overlayContext) {
      final media = MediaQuery.of(overlayContext);
      final bottomInset = media.viewInsets.bottom + media.padding.bottom + 16;
      return Positioned(
        bottom: bottomInset,
        left: 16,
        right: 16,
        child: Material(
          color: Colors.transparent,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: isError ? Colors.black87 : const Color(0xEE111111),
              borderRadius: BorderRadius.circular(12),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x55000000),
                  blurRadius: 12,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Text(message, style: const TextStyle(color: Colors.white)),
            ),
          ),
        ),
      );
    },
  );

  overlay.insert(entry);
  _activeSnackOverlay = entry;

  _activeSnackTimer = Timer(const Duration(seconds: 3), () {
    _activeSnackOverlay?.remove();
    _activeSnackOverlay = null;
    _activeSnackTimer = null;
  });
}

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/features/auth/auth_provider.dart';
import 'package:workout_app/features/auth/sign_in_screen.dart';
import 'package:workout_app/screens/home_screen_new.dart';
import 'package:workout_app/features/auth/auth_me_loader.dart';
import 'dart:async';

class AuthGate extends ConsumerStatefulWidget {
  const AuthGate({super.key});

  @override
  ConsumerState<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends ConsumerState<AuthGate> {
  static const _loginDelay = Duration(seconds: 1);
  Timer? _loginDelayTimer;
  bool _allowLoginScreen = false;
  bool _autoSignInAttempted = false;

  @override
  void dispose() {
    _loginDelayTimer?.cancel();
    super.dispose();
  }

  void _startLoginDelayIfNeeded() {
    if (_allowLoginScreen || _loginDelayTimer != null) {
      return;
    }
    _loginDelayTimer = Timer(_loginDelay, () {
      if (!mounted) return;
      setState(() {
        _allowLoginScreen = true;
      });
    });
  }

  Future<void> _tryAutoSignInIfPossible() async {
    if (_autoSignInAttempted) return;
    _autoSignInAttempted = true;

    if (kIsWeb) {
      return;
    }

    if (defaultTargetPlatform != TargetPlatform.android &&
        defaultTargetPlatform != TargetPlatform.iOS) {
      return;
    }

    if (FirebaseAuth.instance.currentUser != null) {
      return;
    }

    try {
      final googleUser = await GoogleSignIn(
        clientId:
            '282810209663-u4upa0psrlsd24ls422na68n1gcmlllb.apps.googleusercontent.com',
      ).signInSilently();
      if (googleUser == null) {
        return;
      }
      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );
      await FirebaseAuth.instance.signInWithCredential(credential);
    } catch (_) {
      return;
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);

    return authState.when(
      data: (user) {
        if (user != null) {
          return const AuthMeLoader(child: HomeScreenNew());
        }

        _tryAutoSignInIfPossible();

        _startLoginDelayIfNeeded();
        if (!_allowLoginScreen) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return const SignInScreen();
      },
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stackTrace) => Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 16),
              Text(
                'Authentication Error',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                error.toString(),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

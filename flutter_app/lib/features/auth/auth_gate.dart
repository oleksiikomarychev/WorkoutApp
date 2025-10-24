import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/features/auth/auth_provider.dart';
import 'package:workout_app/features/auth/sign_in_screen.dart';
import 'package:workout_app/screens/home_screen_new.dart';
import 'package:workout_app/features/auth/auth_me_loader.dart';

/// AuthGate controls the main routing based on authentication state.
/// If the user is authenticated, it shows the main app (HomeScreenNew).
/// If not authenticated, it shows the SignInScreen.
class AuthGate extends ConsumerWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);

    return authState.when(
      data: (user) {
        if (user != null) {
          return const AuthMeLoader(child: HomeScreenNew());
        } else {
          return const SignInScreen();
        }
      },
      loading: () => const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      ),
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

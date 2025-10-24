import 'package:firebase_ui_auth/firebase_ui_auth.dart' as fui;
import 'package:firebase_ui_oauth_google/firebase_ui_oauth_google.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Sign-in screen using Firebase UI Auth for simplified authentication flow.
/// Supports email/password authentication and Google Sign-In.
class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final googleClientId = dotenv.env['GOOGLE_WEB_CLIENT_ID'];
    final providers = <fui.AuthProvider>[
      fui.EmailAuthProvider(),
    ];

    if (googleClientId != null && googleClientId.isNotEmpty) {
      providers.add(
        GoogleProvider(
          clientId: googleClientId,
        ),
      );
    }

    return fui.SignInScreen(
      providers: providers,
      headerBuilder: (context, constraints, shrinkOffset) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              const FlutterLogo(size: 80),
              const SizedBox(height: 16),
              Text(
                'Workout App',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                'Войдите, чтобы продолжить',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        );
      },
      subtitleBuilder: (context, action) {
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0),
          child: action == fui.AuthAction.signIn
              ? const Text('Добро пожаловать! Войдите в свой аккаунт.')
              : const Text('Создайте аккаунт, чтобы начать тренировки.'),
        );
      },
      footerBuilder: (context, action) {
        return const Padding(
          padding: EdgeInsets.only(top: 16),
          child: Text(
            'Продолжая, вы принимаете наши условия использования.',
            style: TextStyle(color: Colors.grey),
            textAlign: TextAlign.center,
          ),
        );
      },
    );
  }
}

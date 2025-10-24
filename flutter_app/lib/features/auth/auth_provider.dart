import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Stream provider that listens to Firebase authentication state changes
final authStateProvider = StreamProvider<User?>((ref) {
  return FirebaseAuth.instance.authStateChanges();
});

/// Provider for the current user (nullable)
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authStateProvider);
  return authState.asData?.value;
});

/// Provider that indicates whether user is authenticated
final isAuthenticatedProvider = Provider<bool>((ref) {
  final user = ref.watch(currentUserProvider);
  return user != null;
});

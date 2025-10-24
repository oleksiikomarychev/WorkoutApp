import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

/// Service class wrapping Firebase Auth for centralized authentication logic.
/// Provides methods for sign-in, sign-out, and token management.
class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  /// Current authenticated user
  User? get currentUser => _auth.currentUser;

  /// Stream of authentication state changes
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  /// Get the current ID token for API requests
  /// If [forceRefresh] is true, the token will be refreshed from the server
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    final user = _auth.currentUser;
    if (user == null) {
      debugPrint('AuthService: No user logged in, cannot get ID token');
      return null;
    }

    try {
      final token = await user.getIdToken(forceRefresh);
      if (kDebugMode && !forceRefresh) {
        debugPrint('AuthService: Retrieved cached ID token');
      } else if (kDebugMode) {
        debugPrint('AuthService: Refreshed ID token from server');
      }
      return token;
    } catch (e) {
      debugPrint('AuthService: Error getting ID token: $e');
      return null;
    }
  }

  /// Sign in with email and password
  Future<UserCredential> signInWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    try {
      return await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    } catch (e) {
      debugPrint('AuthService: Sign in failed: $e');
      rethrow;
    }
  }

  /// Create a new user with email and password
  Future<UserCredential> createUserWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    try {
      return await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
    } catch (e) {
      debugPrint('AuthService: User creation failed: $e');
      rethrow;
    }
  }

  /// Send password reset email
  Future<void> sendPasswordResetEmail({required String email}) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
      debugPrint('AuthService: Password reset email sent to $email');
    } catch (e) {
      debugPrint('AuthService: Failed to send password reset email: $e');
      rethrow;
    }
  }

  /// Sign out the current user
  Future<void> signOut() async {
    try {
      await _auth.signOut();
      debugPrint('AuthService: User signed out successfully');
    } catch (e) {
      debugPrint('AuthService: Sign out failed: $e');
      rethrow;
    }
  }

  /// Check if the current user's email is verified
  bool get isEmailVerified => _auth.currentUser?.emailVerified ?? false;

  /// Send email verification to the current user
  Future<void> sendEmailVerification() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw Exception('No user is currently signed in');
    }

    try {
      await user.sendEmailVerification();
      debugPrint('AuthService: Verification email sent');
    } catch (e) {
      debugPrint('AuthService: Failed to send verification email: $e');
      rethrow;
    }
  }

  /// Reload the current user to get the latest data
  Future<void> reloadUser() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw Exception('No user is currently signed in');
    }

    try {
      await user.reload();
      debugPrint('AuthService: User data reloaded');
    } catch (e) {
      debugPrint('AuthService: Failed to reload user: $e');
      rethrow;
    }
  }

  /// Configure Firebase Auth Emulator for local development
  /// Call this before any auth operations in development mode
  void useAuthEmulator({String host = 'localhost', int port = 9099}) {
    try {
      _auth.useAuthEmulator(host, port);
      debugPrint('AuthService: Using Firebase Auth Emulator at $host:$port');
    } catch (e) {
      debugPrint('AuthService: Failed to configure Auth Emulator: $e');
    }
  }
}

import 'package:firebase_auth/firebase_auth.dart';
<<<<<<< HEAD
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
=======
// import 'package:google_sign_in/google_sign_in.dart' as gsi; // Not required when using signInWithProvider
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, TargetPlatform;
>>>>>>> 5abd336 (Resolve unmerged files: keep deletion of google-services.json; keep theirs for firebase_auth_service.dart)

class FirebaseAuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  Stream<User?> get authStateChanges => _auth.authStateChanges();

  User? get currentUser => _auth.currentUser;

  Future<String?> getIdToken() async {
    final user = _auth.currentUser;
    if (user == null) {
      return null;
    }
    return await user.getIdToken();
  }

  Future<UserCredential?> signInWithEmailAndPassword(String email, String password) async {
    try {
      return await _auth.signInWithEmailAndPassword(email: email, password: password);
    } on FirebaseAuthException catch (e) {
      // TODO: Handle errors properly
      print(e.message);
      return null;
    }
  }

  Future<UserCredential?> createUserWithEmailAndPassword(String email, String password) async {
    try {
      return await _auth.createUserWithEmailAndPassword(email: email, password: password);
    } on FirebaseAuthException catch (e) {
      // TODO: Handle errors properly
      print(e.message);
      return null;
    }
  }

  Future<UserCredential?> signInWithGoogle() async {
    try {
      // On Web, prefer Firebase's popup flow to avoid issues with google_sign_in
      if (kIsWeb) {
        final provider = GoogleAuthProvider();
        try {
          return await _auth.signInWithPopup(provider);
        } on FirebaseAuthException catch (e) {
          // If popup is blocked or not allowed, fallback to redirect
          if (e.code == 'popup-blocked' || e.code == 'popup-closed-by-user' || e.code == 'operation-not-allowed') {
            await _auth.signInWithRedirect(provider);
            // The redirect will navigate away; return null for now
            return null;
          }
          rethrow;
        }
      }

<<<<<<< HEAD
      final GoogleSignInAccount? googleUser = await GoogleSignIn.instance.authenticate();
      if (googleUser == null) {
        // The user canceled the sign-in
        return null;
      }

      final GoogleSignInAuthentication googleAuth = googleUser.authentication;

      final OAuthCredential credential = GoogleAuthProvider.credential(
        accessToken: null, // accessToken is not available on macOS
        idToken: googleAuth.idToken,
      );

      return await _auth.signInWithCredential(credential);
=======
      // Android/iOS: use Firebase Auth's native OAuth flow (no google_sign_in plugin needed)
      if (defaultTargetPlatform == TargetPlatform.android ||
          defaultTargetPlatform == TargetPlatform.iOS) {
        final provider = GoogleAuthProvider();
        return await _auth.signInWithProvider(provider);
      }

      // Desktop (e.g., macOS): fall back to manual credential flow if needed in the future.
      // For now, return null to indicate not supported on this platform.
      return null;
>>>>>>> 5abd336 (Resolve unmerged files: keep deletion of google-services.json; keep theirs for firebase_auth_service.dart)
    } on FirebaseAuthException catch (e) {
      // TODO: Handle errors properly
      print(e.message);
      return null;
    } on Exception catch (e) {
      // Handle other exceptions, like user canceling the sign-in flow
      print('Google Sign-In failed: $e');
      return null;
    }
  }

  Future<void> signOut() async {
    try {
<<<<<<< HEAD
      if (kIsWeb) {
        // On Web, google_sign_in is not used for the sign-in flow above,
        // so calling GoogleSignIn.signOut() can throw. Sign out only via Firebase.
        await _auth.signOut();
      } else {
        // Best-effort sign out from Google session; ignore errors to not block Firebase sign out
        try {
          await GoogleSignIn.instance.signOut();
        } catch (_) {}
        await _auth.signOut();
      }
=======
      // Sign out only via Firebase. When using signInWithProvider, separate Google session sign-out is unnecessary.
      await _auth.signOut();
>>>>>>> 5abd336 (Resolve unmerged files: keep deletion of google-services.json; keep theirs for firebase_auth_service.dart)
    } catch (_) {
      // Swallow errors to prevent UI from getting stuck; AuthGate will reflect the actual state
    }
  }
}

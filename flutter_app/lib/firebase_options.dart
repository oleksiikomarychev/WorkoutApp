

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;





















class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        return macos;
      case TargetPlatform.windows:
        throw UnsupportedError(
          'DefaultFirebaseOptions have not been configured for windows - '
          'you can reconfigure this by running the FlutterFire CLI again.',
        );
      case TargetPlatform.linux:
        throw UnsupportedError(
          'DefaultFirebaseOptions have not been configured for linux - '
          'you can reconfigure this by running the FlutterFire CLI again.',
        );
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not supported for this platform.',
        );
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyDZrhMZfP260kBmPE4dXCKAa5pESKGQRrI',
    appId: '1:282810209663:web:7d14d9187ca0317335364a',
    messagingSenderId: '282810209663',
    projectId: 'workout-app-auth-d49ae',
    authDomain: 'workout-app-auth-d49ae.firebaseapp.com',
    storageBucket: 'workout-app-auth-d49ae.firebasestorage.app',
    measurementId: 'G-3WDT9BKRDP',
  );



  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyASdTsNqby6t-5JglUyEnErO9RcPCSGlrc',
    appId: '1:282810209663:android:8bac6a4b60ba702535364a',
    messagingSenderId: '282810209663',
    projectId: 'workout-app-auth-d49ae',
    storageBucket: 'workout-app-auth-d49ae.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'YOUR_IOS_API_KEY',
    appId: 'YOUR_IOS_APP_ID',
    messagingSenderId: 'YOUR_MESSAGING_SENDER_ID',
    projectId: 'YOUR_PROJECT_ID',
    storageBucket: 'YOUR_PROJECT_ID.appspot.com',
    iosBundleId: 'com.example.workoutApp',
  );

  static const FirebaseOptions macos = FirebaseOptions(
    apiKey: 'AIzaSyBJsEsZdjpKaR25lQl_72c6xDBzNgyYgD0',
    appId: '1:282810209663:ios:df1e8cb4b9867e3535364a',
    messagingSenderId: '282810209663',
    projectId: 'workout-app-auth-d49ae',
    storageBucket: 'workout-app-auth-d49ae.firebasestorage.app',
    androidClientId: '282810209663-2c8gaol6ijkhp96tc1c70fuj4bdvpgse.apps.googleusercontent.com',
    iosClientId: '282810209663-psrtkj09pjudfn2ft0ifqfiugdm2oiel.apps.googleusercontent.com',
    iosBundleId: 'com.example.workoutApp',
  );

}

#!/bin/bash

# Firebase Authentication Setup Script for Workout App
# This script automates the initial setup of Firebase Authentication

set -e  # Exit on any error

echo "🔥 Firebase Authentication Setup for Workout App"
echo "=================================================="
echo ""

# Check if we're in the correct directory
if [ ! -f "pubspec.yaml" ]; then
    echo "❌ Error: Please run this script from the flutter_app directory"
    exit 1
fi

# Step 1: Install Flutter dependencies
echo "📦 Step 1: Installing Flutter dependencies..."
flutter pub get

# Step 2: Check if FlutterFire CLI is installed
echo ""
echo "🔧 Step 2: Checking FlutterFire CLI..."
if ! command -v flutterfire &> /dev/null; then
    echo "⚠️  FlutterFire CLI not found. Installing..."
    dart pub global activate flutterfire_cli
    echo "✅ FlutterFire CLI installed"
else
    echo "✅ FlutterFire CLI already installed"
fi

# Step 3: Check if Firebase CLI is installed
echo ""
echo "🔧 Step 3: Checking Firebase CLI..."
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI not found."
    echo "Please install it manually:"
    echo "  npm install -g firebase-tools"
    echo "  firebase login"
    exit 1
else
    echo "✅ Firebase CLI already installed"
fi

# Step 4: Run flutterfire configure
echo ""
echo "🔥 Step 4: Configuring Firebase for your app..."
echo "This will:"
echo "  - Connect to your Firebase project"
echo "  - Generate lib/firebase_options.dart"
echo "  - Configure platform-specific settings"
echo ""
read -p "Ready to run 'flutterfire configure'? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    flutterfire configure
    echo "✅ Firebase configuration complete!"
else
    echo "⏭️  Skipping flutterfire configure. Run it manually when ready:"
    echo "   flutterfire configure"
fi

# Step 5: Remind about Firebase Console setup
echo ""
echo "=================================================="
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. 🔐 Enable Email/Password authentication:"
echo "   - Go to https://console.firebase.google.com/"
echo "   - Select your project"
echo "   - Authentication → Sign-in method → Email/Password → Enable"
echo ""
echo "2. 🌐 For Web (optional):"
echo "   - Authentication → Settings → Authorized domains"
echo "   - Add: localhost (for development)"
echo ""
echo "3. 🚀 Run your app:"
echo "   flutter run"
echo ""
echo "4. 📖 Read the documentation:"
echo "   - AUTH_QUICKSTART.md (quick start guide)"
echo "   - FIREBASE_SETUP.md (detailed setup)"
echo ""
echo "=================================================="

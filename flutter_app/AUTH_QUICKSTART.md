# 🚀 Quick Start: Firebase Authentication

## Быстрый старт (3 шага)

### 1️⃣ Установите зависимости

```bash
# Установите Firebase CLI
npm install -g firebase-tools
firebase login

# Установите FlutterFire CLI
dart pub global activate flutterfire_cli

# Установите Flutter пакеты
cd flutter_app
flutter pub get
```

### 2️⃣ Настройте Firebase

```bash
# В директории flutter_app выполните:
flutterfire configure
```

Следуйте инструкциям:
- Выберите существующий Firebase проект или создайте новый
- Выберите платформы: Web, iOS, Android, macOS
- CLI автоматически создаст `lib/firebase_options.dart`

### 3️⃣ Включите Email/Password в Firebase Console

1. Откройте [Firebase Console](https://console.firebase.google.com/)
2. Выберите ваш проект
3. **Authentication** → **Sign-in method** → **Email/Password** → Enable

✅ **Готово!** Запустите приложение:

```bash
flutter run
```

## Что работает прямо сейчас

- ✅ **AuthGate**: Автоматический роутинг (вход/главный экран)
- ✅ **Sign In/Sign Up**: Firebase UI Auth с email/password
- ✅ **Logout**: Кнопка выхода в AppBar
- ✅ **Auth State**: Riverpod провайдеры для реактивности

## Следующие шаги (TODO)

- [ ] Запустите `flutter pub get` после добавления зависимостей
- [ ] Выполните `flutterfire configure`
- [ ] Включите Email/Password провайдер в Firebase Console
- [ ] (Опционально) Настройте Auth Emulator для локальной разработки
- [ ] Добавьте инжекцию токена в API запросы

## Локальная разработка с Emulator

Для разработки без реального Firebase:

```bash
# Запустите Auth Emulator
firebase emulators:start --only auth
```

В `lib/main.dart` раскомментируйте:
```dart
if (kDebugMode) {
  final authService = AuthService();
  authService.useAuthEmulator(host: 'localhost', port: 9099);
}
```

## Тестирование

1. Запустите приложение
2. Создайте аккаунт на экране Sign Up
3. Войдите с созданными учетными данными
4. Проверьте, что вы попали на главный экран
5. Нажмите на меню в AppBar → Выйти

## Структура кода

```
lib/features/auth/
├── auth_provider.dart       # Riverpod: authStateProvider, currentUserProvider
├── auth_gate.dart           # Роутинг: SignInScreen ↔ HomeScreenNew
├── sign_in_screen.dart      # UI: Firebase UI Auth экран
└── auth_service.dart        # Логика: wrapper для FirebaseAuth
```

## Проблемы?

Смотрите детальную документацию в [FIREBASE_SETUP.md](./FIREBASE_SETUP.md)

---

**💡 Tip:** После настройки Firebase следующий шаг — добавить инжекцию ID-токена в `ApiClient` для авторизации API запросов.

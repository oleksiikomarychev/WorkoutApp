# Firebase Authentication Setup

## Что уже сделано

✅ Добавлены зависимости Firebase в `pubspec.yaml`
✅ Создана структура `lib/features/auth/` с провайдерами и экранами
✅ Интегрирован `AuthGate` для роутинга на основе статуса авторизации
✅ Добавлена кнопка Logout в AppBar
✅ Создан `AuthService` для работы с Firebase Auth

## Что нужно сделать

### 1. Установить Firebase CLI и FlutterFire CLI

```bash
# Установите Firebase CLI (если еще не установлено)
npm install -g firebase-tools

# Войдите в Firebase
firebase login

# Установите FlutterFire CLI
dart pub global activate flutterfire_cli
```

### 2. Создать проект Firebase

1. Перейдите в [Firebase Console](https://console.firebase.google.com/)
2. Создайте новый проект (или используйте существующий)
3. Включите **Authentication** → **Sign-in method** → Email/Password

### 3. Настроить Firebase для вашего Flutter приложения

```bash
# В корне flutter_app запустите:
cd flutter_app
flutterfire configure
```

Эта команда:
- Создаст приложения для всех платформ (Web, iOS, Android, macOS)
- Сгенерирует `lib/firebase_options.dart` с реальными конфигами
- Автоматически настроит платформенные файлы

### 4. Установить зависимости

```bash
flutter pub get
```

### 5. Настроить Firebase Auth Emulator (для локальной разработки)

#### Backend (Gateway)

В `gateway/.env` добавьте:
```env
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
```

#### Frontend (Flutter)

В `lib/main.dart` раскомментируйте:
```dart
if (kDebugMode) {
  final authService = AuthService();
  authService.useAuthEmulator(host: 'localhost', port: 9099);
}
```

Запустите эмулятор:
```bash
firebase emulators:start --only auth
```

### 6. Настроить Authorized Domains (для Web)

В Firebase Console → Authentication → Settings → Authorized domains:
- Добавьте `localhost` (для разработки)
- Добавьте ваш production домен

### 7. Обновить CORS в Backend

В `gateway/gateway_app/main.py` убедитесь, что `CORS_ORIGINS` включает:
- `http://localhost:PORT` (где PORT — порт вашего Flutter Web сервера, обычно 8080)
- Ваш production домен

### 8. Протестировать аутентификацию

1. Запустите приложение: `flutter run`
2. Создайте тестового пользователя через экран регистрации
3. Войдите и проверьте, что:
   - AuthGate перенаправляет на `HomeScreenNew`
   - Кнопка Logout работает
   - После logout перенаправление на `SignInScreen`

### 9. Проверить интеграцию с Backend

После входа откройте DevTools Network и убедитесь, что:
- Все API запросы содержат заголовок `Authorization: Bearer <token>`
- Backend возвращает 200 (не 401)
- Endpoint `/api/v1/auth/me` возвращает профиль пользователя

## Структура файлов

```
lib/
├── features/
│   └── auth/
│       ├── auth_provider.dart      # Riverpod провайдеры для auth state
│       ├── auth_gate.dart          # Роутинг на основе auth state
│       ├── sign_in_screen.dart     # Экран входа (Firebase UI Auth)
│       └── auth_service.dart       # Wrapper для Firebase Auth
├── firebase_options.dart           # Сгенерированные Firebase конфиги
└── main.dart                       # Инициализация Firebase + AuthGate
```

## Следующие шаги (после текущей интеграции)

- [ ] Инжектировать ID-токен в HTTP запросы (`ApiClient._getHeaders()`)
- [ ] Обработка 401 с автоматическим refresh токена
- [ ] Добавить токен в WebSocket для чата
- [ ] Вызов `/api/v1/auth/me` после входа
- [ ] Тесты аутентификации

## Troubleshooting

### Firebase не инициализируется
- Проверьте, что `firebase_options.dart` содержит реальные значения (не `YOUR_*`)
- Убедитесь, что `Firebase.initializeApp()` вызывается в `main()`

### 401 на всех запросах
- Проверьте, что токен добавляется в заголовок `Authorization`
- Убедитесь, что backend читает и валидирует Firebase токен
- Проверьте `FIREBASE_PROJECT_ID` и `FIREBASE_CREDENTIALS_BASE64` в backend

### Web не работает
- Добавьте домен в Authorized domains (Firebase Console)
- Проверьте CORS настройки в gateway

### Emulator не работает
- Убедитесь, что порт 9099 свободен
- Проверьте, что `FIREBASE_AUTH_EMULATOR_HOST` установлена в backend
- Frontend: `authService.useAuthEmulator()` вызван до любых auth операций

## Полезные ссылки

- [FlutterFire Documentation](https://firebase.flutter.dev/)
- [Firebase UI Auth](https://pub.dev/packages/firebase_ui_auth)
- [Firebase Auth Emulator](https://firebase.google.com/docs/emulator-suite/connect_auth)

import 'package:flutter/material.dart';
import 'package:workout_app/screens/home_screen_new.dart';
import 'package:workout_app/services/logger_service.dart';

// Global navigator key for navigation from anywhere in the app
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  final LoggerService _logger = LoggerService('SplashScreen');
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _logger.i('Initializing SplashScreen');
    debugPrint('SplashScreen: initState called');
    
    _controller = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);
    
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    );

    // Simulate some initialization process
    debugPrint('SplashScreen: Starting app initialization...');
    _initializeApp().catchError((error) {
      debugPrint('SplashScreen: Error in _initializeApp: $error');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Ошибка при инициализации приложения'),
            action: SnackBarAction(
              label: 'Повторить',
              onPressed: _initializeApp,
            ),
          ),
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _initializeApp() async {
    try {
      debugPrint('SplashScreen: Starting app initialization...');
      
      // Simulate initialization process (replace with actual initialization)
      await Future.delayed(const Duration(seconds: 2));
      
      debugPrint('SplashScreen: Initialization complete, navigating to home screen...');
      
      // Ensure the widget is still mounted before navigating
      if (!mounted) {
        debugPrint('SplashScreen: Widget was disposed before navigation could complete');
        return;
      }
      
      // Navigate using the global navigator key
      navigatorKey.currentState?.pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreenNew()),
      );
      
      debugPrint('SplashScreen: Navigation completed');
    } catch (e, stackTrace) {
      debugPrint('SplashScreen: Error in _initializeApp: $e\n$stackTrace');
      
      // Fallback navigation in case of error
      if (mounted) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const HomeScreenNew()),
          );
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      home: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ScaleTransition(
                scale: _animation,
                child: const FlutterLogo(size: 100),
              ),
              const SizedBox(height: 20),
              const Text(
                'Workout App',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 20),
              const CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

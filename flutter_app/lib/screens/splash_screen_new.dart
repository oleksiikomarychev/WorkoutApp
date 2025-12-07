import 'package:flutter/material.dart';
import 'package:workout_app/screens/home_screen_new.dart';


final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

class SplashScreenNew extends StatefulWidget {
  const SplashScreenNew({super.key});

  @override
  State<SplashScreenNew> createState() => _SplashScreenNewState();
}

class _SplashScreenNewState extends State<SplashScreenNew>
    with SingleTickerProviderStateMixin {

  late AnimationController _controller;
  late Animation<double> _animation;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);

    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    );


    _initializeApp();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _initializeApp() async {
    if (_initialized) return;
    _initialized = true;

    try {
      debugPrint('SplashScreen: Starting app initialization...');


      await Future.delayed(const Duration(seconds: 2));

      debugPrint('SplashScreen: Navigation to home screen...');

      if (!mounted) return;


      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const HomeScreenNew()),
      );

    } catch (e, stackTrace) {
      debugPrint('SplashScreen: Error: $e\n$stackTrace');


      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeScreenNew()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:workout_app/screens/workouts_screen.dart';
import 'package:workout_app/screens/exercises_screen.dart';
import 'package:workout_app/screens/user_maxes_screen.dart';
import 'package:workout_app/screens/calendar_plans_screen.dart';
import 'package:workout_app/widgets/custom_bottom_nav_bar.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/config/api_config.dart';

class HomeScreenNew extends StatefulWidget {
  const HomeScreenNew({super.key});

  @override
  State<HomeScreenNew> createState() => _HomeScreenNewState();
}

class _HomeScreenNewState extends State<HomeScreenNew> {
  int _selectedIndex = 0;
  
  final List<Widget> _widgetOptions = [
    const WorkoutsScreen(),  // Connected to workoutEndpoint
    const ExercisesScreen(), // Connected to exercisesEndpoint
    const UserMaxesScreen(), // Connected to userMaxesEndpoint
    const CalendarPlansScreen(), // Connected to calendarPlansEndpoint
  ];

  final List<String> _appBarTitles = [
    'Тренировки',  // workoutEndpoint
    'Упражнения',  // exercisesEndpoint
    'Максимумы',   // userMaxesEndpoint
    'Планы тренировок',   // calendarPlansEndpoint
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
      // Log which endpoint is being accessed
      switch (index) {
        case 0: // Workouts
          debugPrint('Accessing endpoint: ${ApiConfig.workoutsEndpoint}');
          break;
        case 1: // Exercises
          debugPrint('Accessing endpoint: ${ApiConfig.exerciseDefinitionsEndpoint}');
          break;
        case 2: // User Maxes
          debugPrint('Accessing endpoint: ${ApiConfig.userMaxesEndpoint}');
          break;
        case 3: // My Plans
          debugPrint('Accessing endpoint: ${ApiConfig.calendarPlansEndpoint}');
          break;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mediaQuery = MediaQuery.of(context);
    final bottomPadding = mediaQuery.padding.bottom;
    
    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight),
        child: AppBar(
          title: Text(
            _appBarTitles[_selectedIndex],
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          centerTitle: true,
          elevation: 0,
          backgroundColor: theme.scaffoldBackgroundColor,
          foregroundColor: theme.colorScheme.onBackground,
        ),
      ),
      body: Padding(
        padding: EdgeInsets.only(bottom: kBottomNavigationBarHeight + bottomPadding),
        child: _widgetOptions.elementAt(_selectedIndex),
      ),
      bottomNavigationBar: CustomBottomNavBar(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        items: const [
          BottomNavBarItem(
            icon: Icons.fitness_center,
            label: 'Тренировки',
            activeLabel: 'Тренировки',
          ),
          BottomNavBarItem(
            icon: Icons.list_alt,
            label: 'Упражнения',
            activeLabel: 'Упражнения',
          ),
          BottomNavBarItem(
            icon: Icons.assessment,
            label: 'Максимумы',
            activeLabel: 'Максимумы',
          ),
          BottomNavBarItem(
            icon: Icons.calendar_today,
            label: 'Планы',
            activeLabel: 'Планы',
          ),
        ],
      ),
    );
  }
}

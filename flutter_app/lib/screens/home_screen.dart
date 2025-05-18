import 'package:flutter/material.dart';
import 'workout_list_screen.dart';
import 'exercise_list_screen.dart';
import 'user_max_screen.dart';
import 'progression_screen.dart';
class HomeScreen extends StatelessWidget {
  const HomeScreen({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Workout App'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          children: [
            _buildMenuCard(
              context,
              'Тренировки',
              Icons.fitness_center,
              Colors.blue,
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const WorkoutListScreen()),
              ),
            ),
            _buildMenuCard(
              context,
              'Упражнения',
              Icons.sports_gymnastics,
              Colors.green,
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ExerciseListScreen()),
              ),
            ),
            _buildMenuCard(
              context,
              'Мои максимумы',
              Icons.trending_up,
              Colors.orange,
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const UserMaxScreen()),
              ),
            ),
            _buildMenuCard(
              context,
              'Прогрессии',
              Icons.arrow_upward,
              Colors.purple,
              () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ProgressionScreen()),
              ),
            ),
          ],
        ),
      ),
    );
  }
  Widget _buildMenuCard(
    BuildContext context,
    String title,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 50,
              color: color,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

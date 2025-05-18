import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../services/workout_service.dart';
import 'workout_detail_screen.dart';
class WorkoutListScreen extends StatefulWidget {
  const WorkoutListScreen({Key? key}) : super(key: key);
  @override
  _WorkoutListScreenState createState() => _WorkoutListScreenState();
}
class _WorkoutListScreenState extends State<WorkoutListScreen> {
  late Future<List<Workout>> _workoutsFuture;
  @override
  void initState() {
    super.initState();
    _loadWorkouts();
  }
  void _loadWorkouts() {
    _workoutsFuture = Provider.of<WorkoutService>(context, listen: false).getWorkouts();
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Тренировки'),
      ),
      body: FutureBuilder<List<Workout>>(
        future: _workoutsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          } else if (snapshot.hasError) {
            return Center(
              child: Text(
                'Ошибка: ${snapshot.error}',
                style: const TextStyle(color: Colors.red),
              ),
            );
          } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return const Center(
              child: Text('Нет тренировок. Создайте новую!'),
            );
          } else {
            final workouts = snapshot.data!;
            return ListView.builder(
              itemCount: workouts.length,
              itemBuilder: (context, index) {
                final workout = workouts[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: ListTile(
                    title: Text(
                      workout.name,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: workout.description != null
                        ? Text(workout.description!)
                        : null,
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => WorkoutDetailScreen(workout: workout),
                        ),
                      );
                      setState(() {
                        _loadWorkouts();
                      });
                    },
                  ),
                );
              },
            );
          }
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const WorkoutDetailScreen(),
            ),
          );
          setState(() {
            _loadWorkouts();
          });
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}

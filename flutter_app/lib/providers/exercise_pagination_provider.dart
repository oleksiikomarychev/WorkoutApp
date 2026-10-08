import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/services/exercise_service.dart';

class PaginatedExercisesState {
  final List<ExerciseDefinition> exercises;
  final bool isLoading;
  final bool hasMore;
  final int? error;
  final int limit;
  final int offset;

  const PaginatedExercisesState({
    this.exercises = const [],
    this.isLoading = false,
    this.hasMore = true,
    this.error,
    this.limit = 50,
    this.offset = 0,
  });

  PaginatedExercisesState copyWith({
    List<ExerciseDefinition>? exercises,
    bool? isLoading,
    bool? hasMore,
    int? error,
    int? limit,
    int? offset,
  }) {
    return PaginatedExercisesState(
      exercises: exercises ?? this.exercises,
      isLoading: isLoading ?? this.isLoading,
      hasMore: hasMore ?? this.hasMore,
      error: error ?? this.error,
      limit: limit ?? this.limit,
      offset: offset ?? this.offset,
    );
  }
}

class PaginatedExercisesNotifier extends StateNotifier<PaginatedExercisesState> {
  final ExerciseService _service;

  PaginatedExercisesNotifier(this._service) : super(const PaginatedExercisesState());

  Future<void> loadMore({
    String? search,
    List<String>? muscleGroups,
    List<String>? equipment,
  }) async {
    if (state.isLoading || !state.hasMore) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final newExercises = await _service.getExerciseDefinitions(
        limit: state.limit,
        offset: state.offset,
        search: search,
        muscleGroups: muscleGroups,
        equipment: equipment,
      );

      final hasMore = newExercises.length >= state.limit;
      final allExercises = [...state.exercises, ...newExercises];

      state = state.copyWith(
        exercises: allExercises,
        isLoading: false,
        hasMore: hasMore,
        offset: state.offset + newExercises.length,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.hashCode,
      );
    }
  }

  Future<void> refresh({
    String? search,
    List<String>? muscleGroups,
    List<String>? equipment,
  }) async {
    state = const PaginatedExercisesState();

    await loadMore(
      search: search,
      muscleGroups: muscleGroups,
      equipment: equipment,
    );
  }

  void clear() {
    state = const PaginatedExercisesState();
  }
}

class ExerciseSearchState {
  final List<ExerciseDefinition> results;
  final bool isLoading;
  final String? query;
  final int? error;

  const ExerciseSearchState({
    this.results = const [],
    this.isLoading = false,
    this.query,
    this.error,
  });

  ExerciseSearchState copyWith({
    List<ExerciseDefinition>? results,
    bool? isLoading,
    String? query,
    int? error,
  }) {
    return ExerciseSearchState(
      results: results ?? this.results,
      isLoading: isLoading ?? this.isLoading,
      query: query ?? this.query,
      error: error ?? this.error,
    );
  }
}

class ExerciseSearchNotifier extends StateNotifier<ExerciseSearchState> {
  final ExerciseService _service;

  ExerciseSearchNotifier(this._service) : super(const ExerciseSearchState());

  Future<void> search(String query) async {
    if (query.trim().isEmpty) {
      state = const ExerciseSearchState();
      return;
    }

    state = state.copyWith(isLoading: true, query: query, error: null);

    try {
      final results = await _service.getExerciseDefinitions(
        limit: 20,
        search: query,
      );

      state = state.copyWith(
        results: results,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.hashCode,
      );
    }
  }

  void clear() {
    state = const ExerciseSearchState();
  }
}

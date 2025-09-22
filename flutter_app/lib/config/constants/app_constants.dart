/// App-wide constants
/// 
/// This file contains constants that are used throughout the app.
/// It helps maintain consistency and makes it easier to update values in one place.
library;

class AppConstants {
  // App info
  static const String appName = 'Workout App';
  static const String appVersion = '1.0.0';
  static const String appAuthor = 'Your Name';
  static const String appDescription = 'A workout tracking application for fitness enthusiasts';
  
  // API configuration
  static const int apiTimeout = 30; // in seconds
  static const int maxRetryAttempts = 3;
  static const int itemsPerPage = 20;
  
  // Date and time formats
  static const String dateFormat = 'MMM d, yyyy';
  static const String timeFormat = 'h:mm a';
  static const String dateTimeFormat = 'MMM d, yyyy h:mm a';
  
  // Animation durations
  static const Duration animationDuration = Duration(milliseconds: 300);
  static const Duration splashAnimationDuration = Duration(seconds: 2);
  
  // Default values
  static const int defaultWorkoutDuration = 60; // in minutes
  static const int defaultRestTime = 90; // in seconds
  static const int defaultSets = 3;
  static const int defaultReps = 10;
  
  // Pagination
  static const int defaultPageSize = 20;
  static const int defaultInitialPage = 1;
  
  // Exercise categories
  static const List<String> exerciseCategories = [
    'Chest',
    'Back',
    'Shoulders',
    'Biceps',
    'Triceps',
    'Legs',
    'Core',
    'Cardio',
    'Other',
  ];
  
  // Exercise equipment
  static const List<String> exerciseEquipment = [
    'Barbell',
    'Dumbbell',
    'Kettlebell',
    'Machine',
    'Cable',
    'Bodyweight',
    'Bands',
    'Other',
  ];
  
  // Measurement units
  static const List<String> weightUnits = ['kg', 'lb'];
  static const List<String> distanceUnits = ['km', 'mi', 'm', 'yd'];
  static const List<String> timeUnits = ['sec', 'min', 'hour'];
  
  // Difficulty levels
  static const List<String> difficultyLevels = [
    'Beginner',
    'Intermediate',
    'Advanced',
    'Expert',
  ];
  
  // RPE (Rate of Perceived Exertion) scale
  static const Map<int, String> rpeScale = {
    1: 'Very Easy',
    2: 'Easy',
    3: 'Moderate',
    4: 'Somewhat Hard',
    5: 'Hard',
    6: 'Hard',
    7: 'Very Hard',
    8: 'Very Hard',
    9: 'Very Hard',
    10: 'Max Effort',
  };
  
  // Workout types
  static const List<String> workoutTypes = [
    'Strength',
    'Hypertrophy',
    'Endurance',
    'Mobility',
    'Recovery',
    'Other',
  ];
  
  // Days of the week
  static const List<String> daysOfWeek = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];
  
  // App settings
  static const Map<String, dynamic> defaultSettings = {
    'theme': 'system', // 'light', 'dark', or 'system'
    'notifications': true,
    'sound': true,
    'vibration': true,
    'autoSave': true,
    'autoBackup': false,
    'backupFrequency': 'weekly', // 'daily', 'weekly', 'monthly'
    'weightUnit': 'kg',
    'distanceUnit': 'km',
    'language': 'en',
  };
}

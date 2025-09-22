/// Optimized RPE (Rate of Perceived Exertion) table for fast local calculations
/// This eliminates HTTP calls and provides instant RPE/reps/intensity calculations
class RpeTable {
  // Precomputed RPE table as nested maps for O(1) lookups
  // Structure: intensity -> rpe -> reps
  static const Map<int, Map<int, int>> _rpeTable = {
    100: {10: 1},
    99: {10: 1},
    98: {10: 1},
    97: {10: 1},
    96: {10: 1},
    95: {10: 2, 9: 1},
    94: {10: 2, 9: 1},
    93: {10: 3, 9: 2, 8: 1},
    92: {10: 3, 9: 2, 8: 1},
    91: {10: 4, 9: 3, 8: 2, 7: 1},
    90: {10: 4, 9: 3, 8: 2, 7: 1},
    89: {10: 5, 9: 4, 8: 3, 7: 2, 6: 1},
    88: {10: 5, 9: 4, 8: 3, 7: 2, 6: 1},
    87: {10: 6, 9: 5, 8: 4, 7: 3, 6: 2, 5: 1},
    86: {10: 6, 9: 5, 8: 4, 7: 3, 6: 2, 5: 1},
    85: {10: 6, 9: 5, 8: 4, 7: 3, 6: 2, 5: 1},
    84: {10: 7, 9: 6, 8: 5, 7: 4, 6: 3, 5: 2, 4: 1},
    83: {10: 7, 9: 6, 8: 5, 7: 4, 6: 3, 5: 2, 4: 1},
    82: {10: 8, 9: 7, 8: 6, 7: 5, 6: 4, 5: 3, 4: 2, 3: 1},
    81: {10: 8, 9: 7, 8: 6, 7: 5, 6: 4, 5: 3, 4: 2, 3: 1},
    80: {10: 8, 9: 7, 8: 6, 7: 5, 6: 4, 5: 3, 4: 2, 3: 1},
    79: {10: 9, 9: 8, 8: 7, 7: 6, 6: 5, 5: 4, 4: 3, 3: 2, 2: 1},
    78: {10: 9, 9: 8, 8: 7, 7: 6, 6: 5, 5: 4, 4: 3, 3: 2, 2: 1},
    77: {10: 10, 9: 9, 8: 8, 7: 7, 6: 6, 5: 5, 4: 4, 3: 3, 2: 2, 1: 1},
    76: {10: 10, 9: 9, 8: 8, 7: 7, 6: 6, 5: 5, 4: 4, 3: 3, 2: 2, 1: 1},
    75: {10: 10, 9: 9, 8: 8, 7: 7, 6: 6, 5: 5, 4: 4, 3: 3, 2: 2, 1: 1},
    74: {10: 11, 9: 10, 8: 9, 7: 8, 6: 7, 5: 6, 4: 5, 3: 4, 2: 3, 1: 2},
    73: {10: 11, 9: 10, 8: 9, 7: 8, 6: 7, 5: 6, 4: 5, 3: 4, 2: 3, 1: 2},
    72: {10: 12, 9: 11, 8: 10, 7: 9, 6: 8, 5: 7, 4: 6, 3: 5, 2: 4, 1: 3},
    71: {10: 12, 9: 11, 8: 10, 7: 9, 6: 8, 5: 7, 4: 6, 3: 5, 2: 4, 1: 3},
    70: {10: 12, 9: 11, 8: 10, 7: 9, 6: 8, 5: 7, 4: 6, 3: 5, 2: 4, 1: 3},
    69: {10: 13, 9: 12, 8: 11, 7: 10, 6: 9, 5: 8, 4: 7, 3: 6, 2: 5, 1: 4},
    68: {10: 14, 9: 13, 8: 12, 7: 11, 6: 10, 5: 9, 4: 8, 3: 7, 2: 6, 1: 5},
    67: {10: 15, 9: 14, 8: 13, 7: 12, 6: 11, 5: 10, 4: 9, 3: 8, 2: 7, 1: 6},
    66: {10: 16, 9: 15, 8: 14, 7: 13, 6: 12, 5: 11, 4: 10, 3: 9, 2: 8, 1: 7},
    65: {10: 17, 9: 16, 8: 15, 7: 14, 6: 13, 5: 12, 4: 11, 3: 10, 2: 9, 1: 8},
    64: {10: 18, 9: 17, 8: 16, 7: 15, 6: 14, 5: 13, 4: 12, 3: 11, 2: 10, 1: 9},
    63: {10: 19, 9: 18, 8: 17, 7: 16, 6: 15, 5: 14, 4: 13, 3: 12, 2: 11, 1: 10},
    62: {10: 20, 9: 19, 8: 18, 7: 17, 6: 16, 5: 15, 4: 14, 3: 13, 2: 12, 1: 11},
    61: {10: 21, 9: 20, 8: 19, 7: 18, 6: 17, 5: 16, 4: 15, 3: 14, 2: 13, 1: 12},
    60: {10: 22, 9: 21, 8: 20, 7: 19, 6: 18, 5: 17, 4: 16, 3: 15, 2: 14, 1: 13},
    59: {10: 23, 9: 22, 8: 21, 7: 20, 6: 19, 5: 18, 4: 17, 3: 16, 2: 15, 1: 14},
    58: {10: 24, 9: 23, 8: 22, 7: 21, 6: 20, 5: 19, 4: 18, 3: 17, 2: 16, 1: 15},
    57: {10: 25, 9: 24, 8: 23, 7: 22, 6: 21, 5: 20, 4: 19, 3: 18, 2: 17, 1: 16},
    56: {10: 26, 9: 25, 8: 24, 7: 23, 6: 22, 5: 21, 4: 20, 3: 19, 2: 18, 1: 17},
    55: {10: 27, 9: 26, 8: 25, 7: 24, 6: 23, 5: 22, 4: 21, 3: 20, 2: 19, 1: 18},
    54: {10: 28, 9: 27, 8: 26, 7: 25, 6: 24, 5: 23, 4: 22, 3: 21, 2: 20, 1: 19},
    53: {10: 29, 9: 28, 8: 27, 7: 26, 6: 25, 5: 24, 4: 23, 3: 22, 2: 21, 1: 20},
    52: {10: 30, 9: 29, 8: 28, 7: 27, 6: 26, 5: 25, 4: 24, 3: 23, 2: 22, 1: 21},
    51: {10: 31, 9: 30, 8: 29, 7: 28, 6: 27, 5: 26, 4: 25, 3: 24, 2: 23, 1: 22},
    50: {10: 32, 9: 31, 8: 30, 7: 29, 6: 28, 5: 27, 4: 26, 3: 25, 2: 24, 1: 23},
    49: {10: 33, 9: 32, 8: 31, 7: 30, 6: 29, 5: 28, 4: 27, 3: 26, 2: 25, 1: 24},
    48: {10: 34, 9: 33, 8: 32, 7: 31, 6: 30, 5: 29, 4: 28, 3: 27, 2: 26, 1: 25},
    47: {10: 35, 9: 34, 8: 33, 7: 32, 6: 31, 5: 30, 4: 29, 3: 28, 2: 27, 1: 26},
    46: {10: 36, 9: 35, 8: 34, 7: 33, 6: 32, 5: 31, 4: 30, 3: 29, 2: 28, 1: 27},
    45: {10: 37, 9: 36, 8: 35, 7: 34, 6: 33, 5: 32, 4: 31, 3: 30, 2: 29, 1: 28},
    44: {10: 38, 9: 37, 8: 36, 7: 35, 6: 34, 5: 33, 4: 32, 3: 31, 2: 30, 1: 29},
    43: {10: 39, 9: 38, 8: 37, 7: 36, 6: 35, 5: 34, 4: 33, 3: 32, 2: 31, 1: 30},
    42: {10: 40, 9: 39, 8: 38, 7: 37, 6: 36, 5: 35, 4: 34, 3: 33, 2: 32, 1: 31},
    41: {10: 41, 9: 40, 8: 39, 7: 38, 6: 37, 5: 36, 4: 35, 3: 34, 2: 33, 1: 32},
    40: {10: 42, 9: 41, 8: 40, 7: 39, 6: 38, 5: 37, 4: 36, 3: 35, 2: 34, 1: 33},
  };

  // Precomputed reverse lookup for faster calculations
  // Structure: intensity -> reps -> rpe (for calculating RPE from intensity + reps)
  static final Map<int, Map<int, int>> _intensityRepsToRpe = _buildReverseLookup();

  // Build reverse lookup table at initialization
  static Map<int, Map<int, int>> _buildReverseLookup() {
    final result = <int, Map<int, int>>{};
    _rpeTable.forEach((intensity, rpeMap) {
      result[intensity] = {};
      rpeMap.forEach((rpe, reps) {
        result[intensity]![reps] = rpe;
      });
    });
    return result;
  }

  /// Get RPE for given intensity and reps
  /// O(1) lookup time
  static int? getRpe(int intensity, int reps) {
    return _intensityRepsToRpe[intensity]?[reps];
  }

  /// Get reps for given intensity and RPE
  /// O(1) lookup time
  static int? getReps(int intensity, int rpe) {
    return _rpeTable[intensity]?[rpe];
  }

  /// Get intensity for given reps and RPE
  /// O(n) time complexity but optimized with early bounds checking
  static int? getIntensity(int reps, int rpe) {
    // Find the highest intensity that can achieve the target reps at given RPE
    for (int intensity = 100; intensity >= 40; intensity--) {
      final repsAtIntensity = _rpeTable[intensity]?[rpe];
      if (repsAtIntensity != null && repsAtIntensity >= reps) {
        return intensity;
      }
    }
    return null;
  }

  /// Calculate one rep max from RPE, reps, and weight
  static double calculateOneRepMax(int rpe, int reps, double weight) {
    final intensity = getIntensity(reps, rpe);
    if (intensity == null) return 0.0;
    return weight / (intensity / 100.0);
  }

  /// Validate intensity value
  static bool isValidIntensity(int intensity) {
    return _rpeTable.containsKey(intensity);
  }

  /// Validate RPE value
  static bool isValidRpe(int rpe) {
    return [4, 5, 6, 7, 8, 9, 10].contains(rpe);
  }

  /// Get all available intensities (sorted descending)
  static List<int> getAvailableIntensities() {
    return _rpeTable.keys.toList()..sort((a, b) => b.compareTo(a));
  }

  /// Get all available RPE values for a given intensity
  static List<int> getAvailableRpes(int intensity) {
    final rpeMap = _rpeTable[intensity];
    if (rpeMap == null) return [];
    return rpeMap.keys.toList()..sort((a, b) => b.compareTo(a));
  }

  /// Get maximum reps possible at given intensity and RPE
  static int? getMaxRepsAtIntensity(int intensity, int rpe) {
    return _rpeTable[intensity]?[rpe];
  }
}

class MuscleInfo {
  final String key;   // Enum key, e.g., "PectoralisMajor"
  final String label; // User-friendly label, e.g., "Pectoralis Major"
  final String group; // Group, e.g., "Chest"

  const MuscleInfo({
    required this.key,
    required this.label,
    required this.group,
  });

  factory MuscleInfo.fromJson(Map<String, dynamic> json) => MuscleInfo(
        key: json['key'] as String,
        label: json['label'] as String,
        group: json['group'] as String,
      );
}

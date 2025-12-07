class MuscleInfo {
  final String key;
  final String label;
  final String group;

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

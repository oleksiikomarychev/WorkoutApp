import 'dart:convert';

class MacroRule {
  final Map<String, dynamic> trigger;
  final Map<String, dynamic> condition;
  final Map<String, dynamic> action;
  final Map<String, dynamic> duration;

  const MacroRule({
    required this.trigger,
    required this.condition,
    required this.action,
    required this.duration,
  });

  factory MacroRule.empty() => const MacroRule(
        trigger: {},
        condition: {},
        action: {},
        duration: {"scope": "Next_N_Workouts", "count": 1},
      );

  factory MacroRule.fromJson(Map<String, dynamic> json) => MacroRule(
        trigger: (json['trigger'] as Map?)?.cast<String, dynamic>() ?? {},
        condition: (json['condition'] as Map?)?.cast<String, dynamic>() ?? {},
        action: (json['action'] as Map?)?.cast<String, dynamic>() ?? {},
        duration: (json['duration'] as Map?)?.cast<String, dynamic>() ?? {},
      );

  Map<String, dynamic> toJson() => {
        'trigger': trigger,
        'condition': condition,
        'action': action,
        'duration': duration,
      };
}

class PlanMacro {
  final int? id;
  final int calendarPlanId;
  final String name;
  final bool isActive;
  final int priority;
  final MacroRule rule;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const PlanMacro({
    this.id,
    required this.calendarPlanId,
    required this.name,
    required this.isActive,
    required this.priority,
    required this.rule,
    this.createdAt,
    this.updatedAt,
  });

  PlanMacro copyWith({
    int? id,
    int? calendarPlanId,
    String? name,
    bool? isActive,
    int? priority,
    MacroRule? rule,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return PlanMacro(
      id: id ?? this.id,
      calendarPlanId: calendarPlanId ?? this.calendarPlanId,
      name: name ?? this.name,
      isActive: isActive ?? this.isActive,
      priority: priority ?? this.priority,
      rule: rule ?? this.rule,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  factory PlanMacro.fromJson(Map<String, dynamic> json) {
    int asInt(dynamic v) {
      if (v is int) return v;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v) ?? 0;
      return 0;
    }
    bool asBool(dynamic v) {
      if (v is bool) return v;
      if (v is int) return v != 0;
      if (v is String) {
        final s = v.toLowerCase();
        if (s == 'true' || s == '1') return true;
        if (s == 'false' || s == '0') return false;
      }
      return false;
    }
    final cp = json['calendar_plan'];
    final cpId = json['calendar_plan_id'] ?? (cp is Map ? (cp['id']) : null) ?? json['calendarPlanId'];
    final ruleJson = (json['rule'] is String)
        ? jsonDecode(json['rule'] as String)
        : (json['rule'] as Map?)?.cast<String, dynamic>() ?? {};
    return PlanMacro(
      id: json['id'] == null ? null : asInt(json['id']),
      calendarPlanId: asInt(cpId),
      name: json['name']?.toString() ?? '',
      isActive: asBool(json['is_active'] ?? json['active'] ?? true),
      priority: asInt(json['priority'] ?? 100),
      rule: MacroRule.fromJson(ruleJson),
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at'].toString()) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      'calendar_plan_id': calendarPlanId,
      'name': name,
      'is_active': isActive,
      'priority': priority,
      'rule': rule.toJson(),
      if (createdAt != null) 'created_at': createdAt!.toIso8601String(),
      if (updatedAt != null) 'updated_at': updatedAt!.toIso8601String(),
    };
  }
}

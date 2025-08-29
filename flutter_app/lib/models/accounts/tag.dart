class Tag {
  final String id;
  final String name;
  final String? color; // hex string like #RRGGBB or #RRGGBBAA

  Tag({
    required this.id,
    required this.name,
    this.color,
  });

  factory Tag.fromJson(Map<String, dynamic> json) {
    return Tag(
      id: json['id'] as String,
      name: json['name'] as String,
      color: json['color'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        if (color != null) 'color': color,
      };
}

class TagCreate {
  final String name;
  final String? color;

  TagCreate({required this.name, this.color});

  Map<String, dynamic> toJson() => {
        'name': name,
        if (color != null) 'color': color,
      };
}

class TagUpdate {
  final String? name;
  final String? color;

  TagUpdate({this.name, this.color});

  Map<String, dynamic> toJson() => {
        if (name != null) 'name': name,
        if (color != null) 'color': color,
      };
}

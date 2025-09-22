class Client {
  final String id;
  final String name;
  final String email;
  final String? displayName;
  final String? status;

  Client({
    required this.id,
    required this.name,
    required this.email,
    this.displayName,
    this.status,
  });

  factory Client.fromJson(Map<String, dynamic> json) {
    return Client(
      id: json['id'],
      name: json['name'],
      email: json['email'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'displayName': displayName,
      'status': status,
    };
  }
}

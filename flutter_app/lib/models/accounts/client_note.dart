class ClientNote {
  final String id;
  final String coachUserId;
  final String clientUserId;
  final String visibility; // 'coach_only' | 'shared_with_client'
  final String text;
  final DateTime createdAt;
  final DateTime updatedAt;

  ClientNote({
    required this.id,
    required this.coachUserId,
    required this.clientUserId,
    required this.visibility,
    required this.text,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ClientNote.fromJson(Map<String, dynamic> json) {
    return ClientNote(
      id: json['id'] as String,
      coachUserId: json['coach_user_id'] as String,
      clientUserId: json['client_user_id'] as String,
      visibility: json['visibility'] as String,
      text: json['text'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

class ClientNoteCreatePayload {
  final String text;
  final String visibility; // 'coach_only' | 'shared_with_client'

  ClientNoteCreatePayload({required this.text, this.visibility = 'coach_only'});

  Map<String, dynamic> toJson() => {
        'text': text,
        'visibility': visibility,
      };
}

class ClientNoteUpdatePayload {
  final String? text;
  final String? visibility;

  ClientNoteUpdatePayload({this.text, this.visibility});

  Map<String, dynamic> toJson() => {
        if (text != null) 'text': text,
        if (visibility != null) 'visibility': visibility,
      };
}

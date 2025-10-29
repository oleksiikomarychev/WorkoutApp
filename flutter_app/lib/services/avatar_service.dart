import 'dart:typed_data';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/config/api_config.dart';

class AvatarService {
  Future<Uint8List> generateAvatar({required String prompt, String model = 'fofr/sdxl-emoji'}) async {
    final endpoint = ApiConfig.buildFullUrl(ApiConfig.avatarsGenerateEndpoint);
    final user = FirebaseAuth.instance.currentUser;
    String? idToken;
    if (user != null) {
      try { idToken = await user.getIdToken(); } catch (_) {}
    }

    final headers = <String, String>{
      'Content-Type': 'application/json',
      if (idToken != null) 'Authorization': 'Bearer $idToken',
      'Accept': 'image/png',
    };

    final body = json.encode({
      'prompt': prompt,
      'model': model,
    });

    final uri = Uri.parse(endpoint);
    final res = await http.post(uri, headers: headers, body: body).timeout(const Duration(seconds: 30));

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.bodyBytes;
    }

    String message = 'Avatar generation failed (${res.statusCode})';
    try {
      final parsed = json.decode(res.body);
      if (parsed is Map && parsed['detail'] != null) message = parsed['detail'].toString();
    } catch (_) {}
    throw Exception(message);
  }

  Future<String> applyAsProfile({required Uint8List pngBytes}) async {
    final endpoint = ApiConfig.buildFullUrl(ApiConfig.applyProfilePhotoEndpoint);
    final user = FirebaseAuth.instance.currentUser;
    String? idToken;
    if (user != null) {
      try { idToken = await user.getIdToken(); } catch (_) {}
    }

    final headers = <String, String>{
      'Content-Type': 'image/png',
      if (idToken != null) 'Authorization': 'Bearer $idToken',
    };
    final uri = Uri.parse(endpoint);
    final res = await http.post(uri, headers: headers, body: pngBytes).timeout(const Duration(seconds: 30));

    if (res.statusCode >= 200 && res.statusCode < 300) {
      try {
        final js = json.decode(res.body) as Map<String, dynamic>;
        final url = js['photo_url']?.toString() ?? '';
        if (url.isNotEmpty && user != null) {
          try { await user.updatePhotoURL(url); } catch (_) {}
        }
        return url;
      } catch (_) {
        return '';
      }
    }
    throw Exception('Failed to apply profile photo (${res.statusCode})');
  }
}

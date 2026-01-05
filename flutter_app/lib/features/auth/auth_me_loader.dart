import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';


class AuthMeLoader extends StatefulWidget {
  const AuthMeLoader({super.key, required this.child});

  final Widget child;

  @override
  State<AuthMeLoader> createState() => _AuthMeLoaderState();
}

class _AuthMeLoaderState extends State<AuthMeLoader> {
  bool _requested = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_requested) {
      _requested = true;
      _callAuthMe();
    }
  }

  Future<void> _callAuthMe() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        return;
      }
      try {
        final token = await user.getIdToken(true);
        if (token == null || token.isEmpty) {
          return;
        }
      } catch (_) {
        return;
      }
      final api = pv.Provider.of<ApiClient>(context, listen: false);
      await api.get(ApiConfig.buildEndpoint('/auth/me'));
    } catch (e) {
      final shouldLogout = e is ApiException && (e.statusCode == 401 || e.statusCode == 403);
      if (!shouldLogout) {
        return;
      }
      return;
    }
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

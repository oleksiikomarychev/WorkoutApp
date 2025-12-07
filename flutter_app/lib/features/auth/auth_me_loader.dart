import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';


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
      final api = pv.Provider.of<ApiClient>(context, listen: false);
      await api.get(ApiConfig.buildEndpoint('/auth/me'));
    } catch (e) {

      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        try {
          await FirebaseAuth.instance.signOut();
        } catch (_) {}
      }
    }
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/route_names.dart';

class SettingsHomeScreen extends StatelessWidget {
  const SettingsHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          ListTile(
            title: const Text('General'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context).pushNamed(RouteNames.settingsGeneral);
            },
          ),
          const Divider(height: 1),
          ListTile(
            title: const Text('Import workouts'),
            leading: const Icon(Icons.file_upload_outlined),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context).pushNamed(RouteNames.settingsImport);
            },
          ),
          const Divider(height: 1),
          ListTile(
            title: const Text('Amplitude Test'),
            leading: const Icon(Icons.analytics_outlined),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context).pushNamed(RouteNames.amplitudeTest);
            },
          ),
          const Divider(height: 1),
          ListTile(
            title: const Text('Privacy policy & Terms'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context).pushNamed(RouteNames.settingsLegal);
            },
          ),
          const Divider(height: 1),
        ],
      ),
    );
  }
}

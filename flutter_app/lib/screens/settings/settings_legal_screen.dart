import 'package:flutter/material.dart';

class SettingsLegalScreen extends StatelessWidget {
  const SettingsLegalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Legal'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          Text(
            'Privacy Policy',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          SizedBox(height: 8),
          Text(
            'This is a placeholder. Add your privacy policy text or open a web page.',
          ),
          SizedBox(height: 24),
          Text(
            'Terms of Service',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          SizedBox(height: 8),
          Text(
            'This is a placeholder. Add your terms of service text or open a web page.',
          ),
        ],
      ),
    );
  }
}

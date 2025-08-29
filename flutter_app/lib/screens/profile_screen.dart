import 'package:flutter/material.dart';
import 'package:workout_app/models/accounts/user_profile.dart';
import 'package:workout_app/services/firebase_auth_service.dart';
import 'package:workout_app/services/service_locator.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  UserProfile? _profile;
  bool _loading = true;
  String? _error;

  final _displayNameCtl = TextEditingController();
  final _avatarUrlCtl = TextEditingController();
  final _localeCtl = TextEditingController();
  final _timezoneCtl = TextEditingController();
  final _countryCtl = TextEditingController();
  bool _marketingOptIn = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final me = await context.accountsService.getMe();
      _applyToForm(me);
      setState(() {
        _profile = me;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _applyToForm(UserProfile me) {
    _displayNameCtl.text = me.displayName ?? '';
    _avatarUrlCtl.text = me.avatarUrl ?? '';
    _localeCtl.text = me.locale ?? '';
    _timezoneCtl.text = me.timezone ?? '';
    _countryCtl.text = me.country ?? '';
    _marketingOptIn = me.marketingOptIn;
  }

  Map<String, dynamic> _buildUpdatePayload() {
    final Map<String, dynamic> data = {};
    if (_displayNameCtl.text != (_profile?.displayName ?? '')) {
      data['display_name'] = _displayNameCtl.text.isEmpty ? null : _displayNameCtl.text;
    }
    if (_avatarUrlCtl.text != (_profile?.avatarUrl ?? '')) {
      data['avatar_url'] = _avatarUrlCtl.text.isEmpty ? null : _avatarUrlCtl.text;
    }
    if (_localeCtl.text != (_profile?.locale ?? '')) {
      data['locale'] = _localeCtl.text.isEmpty ? null : _localeCtl.text;
    }
    if (_timezoneCtl.text != (_profile?.timezone ?? '')) {
      data['timezone'] = _timezoneCtl.text.isEmpty ? null : _timezoneCtl.text;
    }
    if (_countryCtl.text != (_profile?.country ?? '')) {
      data['country'] = _countryCtl.text.isEmpty ? null : _countryCtl.text;
    }
    if (_marketingOptIn != (_profile?.marketingOptIn ?? false)) {
      data['marketing_opt_in'] = _marketingOptIn;
    }
    return data;
  }

  Future<void> _save() async {
    final payload = _buildUpdatePayload();
    if (payload.isEmpty) return; // nothing to update
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final updated = await context.accountsService.updateMe(payload);
      _applyToForm(updated);
      setState(() {
        _profile = updated;
        _loading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated')),
        );
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  void dispose() {
    _displayNameCtl.dispose();
    _avatarUrlCtl.dispose();
    _localeCtl.dispose();
    _timezoneCtl.dispose();
    _countryCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authService = FirebaseAuthService();
    final user = authService.currentUser;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _save,
            icon: const Icon(Icons.save),
            tooltip: 'Save',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Failed to load: $_error'),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Signed in as: ${user?.email ?? user?.uid ?? '-'}'),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _displayNameCtl,
                        decoration: const InputDecoration(
                          labelText: 'Display name',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _avatarUrlCtl,
                        decoration: const InputDecoration(
                          labelText: 'Avatar URL',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _localeCtl,
                        decoration: const InputDecoration(
                          labelText: 'Locale',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _timezoneCtl,
                        decoration: const InputDecoration(
                          labelText: 'Timezone',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _countryCtl,
                        maxLength: 2,
                        decoration: const InputDecoration(
                          labelText: 'Country (ISO-2)',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Switch(
                            value: _marketingOptIn,
                            onChanged: (v) => setState(() => _marketingOptIn = v),
                          ),
                          const SizedBox(width: 8),
                          const Text('Marketing opt-in'),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          ElevatedButton.icon(
                            onPressed: _loading ? null : _save,
                            icon: const Icon(Icons.save),
                            label: const Text('Save'),
                          ),
                          const SizedBox(width: 12),
                          OutlinedButton.icon(
                            onPressed: _loading ? null : _load,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Reload'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: () async {
                          await authService.signOut();
                          // AuthGate will handle navigation
                        },
                        child: const Text('Sign Out'),
                      ),
                    ],
                  ),
                ),
    );
  }
}


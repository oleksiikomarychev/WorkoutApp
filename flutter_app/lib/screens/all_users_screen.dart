import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/coach_rating_display.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_summary.dart';
import '../providers/providers.dart';
import 'public_user_profile_screen.dart';
import 'user_profile_screen.dart';

class AllUsersScreen extends ConsumerStatefulWidget {
  const AllUsersScreen({super.key});

  @override
  ConsumerState<AllUsersScreen> createState() => _AllUsersScreenState();
}

class _AllUsersScreenState extends ConsumerState<AllUsersScreen> {
  bool _filterCoaches = false;
  UserFilters _filters = const UserFilters();

  @override
  Widget build(BuildContext context) {
    final usersAsync = ref.watch(filteredUsersProvider(_filters.copyWith(coach: _filterCoaches)));

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'All Users',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: Icon(_filterCoaches ? Icons.person : Icons.person_outline),
                tooltip: _filterCoaches ? 'Show all users' : 'Show coaches only',
                onPressed: () {
                  setState(() {
                    _filterCoaches = !_filterCoaches;
                    _filters = const UserFilters();
                  });
                },
              ),
              if (_filterCoaches)
                IconButton(
                  icon: const Icon(Icons.filter_list),
                  tooltip: 'Filter coaches',
                  onPressed: _showFilterBottomSheet,
                ),
            ],
          ),
          body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(filteredUsersProvider);
        },
        child: usersAsync.when(
          data: (users) => _buildList(users),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline, size: 40, color: AppColors.error),
                  const SizedBox(height: 12),
                  Text('Failed to load users: $error'),
                  const SizedBox(height: 12),
                  ElevatedButton(
                    onPressed: () => ref.invalidate(filteredUsersProvider),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
      },
    );
  }

  void _showFilterBottomSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => _FilterBottomSheet(
        filters: _filters,
        onApply: (newFilters) {
          setState(() {
            _filters = newFilters;
          });
          Navigator.pop(context);
        },
        onClear: () {
          setState(() {
            _filters = const UserFilters();
          });
          Navigator.pop(context);
        },
      ),
    );
  }

  Widget _buildList(List<UserSummary> users) {
    if (users.isEmpty) {
      return const Center(child: Text('No users yet'));
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemBuilder: (context, index) {
        final user = users[index];
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: AppColors.surface,
            backgroundImage: user.photoUrl != null ? NetworkImage(user.photoUrl!) : null,
            child: user.photoUrl == null
                ? Text(
                    (user.displayName?.isNotEmpty ?? false)
                        ? user.displayName!.substring(0, 1).toUpperCase()
                        : user.userId.substring(0, 1).toUpperCase(),
                  )
                : null,
          ),
          title: Text(user.displayName ?? 'User ${user.userId}'),
          subtitle: _buildSubtitle(user),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (user.coachingEnabled == true && user.averageRating != null)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: CoachRatingDisplay(
                    averageRating: user.averageRating,
                    reviewCount: user.reviewCount,
                  ),
                ),
              user.isPublic
                  ? const Icon(Icons.lock_open, size: 18, color: AppColors.success)
                  : const Icon(Icons.lock_outline, size: 18, color: AppColors.textSecondary),
            ],
          ),
          onTap: () {
            final currentUser = FirebaseAuth.instance.currentUser;
            if (currentUser != null && currentUser.uid == user.userId) {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const UserProfileScreen(),
                ),
              );
            } else {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => PublicUserProfileScreen(
                    userId: user.userId,
                    initialName: user.displayName,
                  ),
                ),
              );
            }
          },
        );
      },
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemCount: users.length,
    );
  }

  Widget _buildSubtitle(UserSummary user) {
    final parts = <String>[];
    parts.add('Created ${user.createdAt.toLocal()}');
    
    if (user.coachingEnabled == true) {
      if (user.rateAmountMinor != null) {
        final rate = user.rateAmountMinor! / 100;
        parts.add('$rate USD/month');
      }
      if (user.specializations.isNotEmpty) {
        parts.add(user.specializations.take(2).join(', '));
      }
    }
    
    return Text(parts.join(' • '));
  }
}

class _FilterBottomSheet extends StatefulWidget {
  final UserFilters filters;
  final ValueChanged<UserFilters> onApply;
  final VoidCallback onClear;

  const _FilterBottomSheet({
    required this.filters,
    required this.onApply,
    required this.onClear,
  });

  @override
  State<_FilterBottomSheet> createState() => _FilterBottomSheetState();
}

class _FilterBottomSheetState extends State<_FilterBottomSheet> {
  late UserFilters _filters;
  final _minRateController = TextEditingController();
  final _maxRateController = TextEditingController();
  String _sortBy = 'created_at';

  static const Map<String, String> _languageOptions = {
    'en': 'English',
    'ua': 'Ukrainian',
    'ru': 'Russian',
    'pl': 'Polish',
    'de': 'German',
  };

  static const Map<String, String> _specializationOptions = {
    'strength': 'Strength Training',
    'hypertrophy': 'Hypertrophy',
    'weight_loss': 'Weight Loss',
    'endurance': 'Endurance',
    'powerlifting': 'Powerlifting',
    'bodybuilding': 'Bodybuilding',
    'functional': 'Functional Training',
    'rehabilitation': 'Rehabilitation',
    'nutrition': 'Nutrition Coaching',
    'online': 'Online Coaching',
    'in_person': 'In-Person Training',
    'youth': 'Youth Training',
    'senior': 'Senior Fitness',
    'mobility': 'Mobility/Flexibility',
  };

  late Set<String> _selectedLanguages;
  late Set<String> _selectedSpecializations;

  @override
  void initState() {
    super.initState();
    _filters = widget.filters;
    // Convert cents to dollars for display
    _minRateController.text = _filters.minRate != null ? (_filters.minRate! / 100).toString() : '';
    _maxRateController.text = _filters.maxRate != null ? (_filters.maxRate! / 100).toString() : '';
    _sortBy = _filters.sortBy ?? 'created_at';

    _selectedLanguages = <String>{
      for (final code in (_filters.languages ?? const <String>[]))
        if (_languageOptions.containsKey(code)) code,
    };

    _selectedSpecializations = <String>{
      for (final code in (_filters.specializations ?? const <String>[]))
        if (_specializationOptions.containsKey(code)) code,
    };
  }

  @override
  void dispose() {
    _minRateController.dispose();
    _maxRateController.dispose();
    super.dispose();
  }

  void _applyFilters() {
    final specializations = _selectedSpecializations.isEmpty ? null : _selectedSpecializations.toList();

    final languages = _selectedLanguages.toList();
    
    final minRate = int.tryParse(_minRateController.text);
    final maxRate = int.tryParse(_maxRateController.text);
    
    // Convert dollars to cents for backend
    final minRateCents = minRate != null ? minRate * 100 : null;
    final maxRateCents = maxRate != null ? maxRate * 100 : null;
    
    widget.onApply(UserFilters(
      coach: _filters.coach,
      specializations: specializations,
      languages: languages.isEmpty ? null : languages,
      minRate: minRateCents,
      maxRate: maxRateCents,
      sortBy: _sortBy,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Filter Coaches',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  TextButton(
                    onPressed: widget.onClear,
                    child: const Text('Clear'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Specializations',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final entry in _specializationOptions.entries)
                    FilterChip(
                      label: Text(entry.value),
                      selected: _selectedSpecializations.contains(entry.key),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedSpecializations.add(entry.key);
                          } else {
                            _selectedSpecializations.remove(entry.key);
                          }
                        });
                      },
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Languages',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final entry in _languageOptions.entries)
                    FilterChip(
                      label: Text(entry.value),
                      selected: _selectedLanguages.contains(entry.key),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _selectedLanguages.add(entry.key);
                          } else {
                            _selectedLanguages.remove(entry.key);
                          }
                        });
                      },
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _minRateController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Min Rate (\$)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _maxRateController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Max Rate (\$)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _sortBy,
                decoration: const InputDecoration(
                  labelText: 'Sort By',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'created_at', child: Text('Created At')),
                  DropdownMenuItem(value: 'rating', child: Text('Rating')),
                  DropdownMenuItem(value: 'last_active', child: Text('Last Active')),
                ],
                onChanged: (value) {
                  setState(() {
                    _sortBy = value ?? 'created_at';
                  });
                },
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _applyFilters,
                child: const Text('Apply Filters'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

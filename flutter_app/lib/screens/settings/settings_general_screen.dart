import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/providers/app_locale_provider.dart';
import 'package:workout_app/providers/app_theme_mode_provider.dart';
import 'package:workout_app/providers/profile_screen_sections_provider.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/features/auth/auth_service.dart';
import 'package:workout_app/models/user_profile.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/user_analytics_service.dart';

class SettingsGeneralScreen extends ConsumerWidget {
  const SettingsGeneralScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Track settings screen opening
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final profileAsync = ref.read(userProfileProvider);
      final profile = profileAsync.value;
      await UserAnalyticsService.instance.trackScreenOpen('settings_general', properties: {
        'coaching_enabled': profile?.coaching?.enabled ?? false,
        'coaching_eligible': profile?.coachingEligibility?.eligible ?? false,
        'has_stripe_account': profile?.coaching?.stripeConnectAccountId != null,
      });
    });
    
    final l10n = AppLocalizations.of(context);
    final profileAsync = ref.watch(userProfileProvider);
    final themeMode = ref.watch(appThemeModeProvider);
    final sectionPrefs = ref.watch(profileScreenSectionsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('General settings'),
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed to load profile: $e')),
        data: (profile) {
          final languageCode = ref.watch(appLocaleProvider)?.languageCode;
          final timezone = profile.settings.timezone ?? '';
          final coaching = profile.coaching;
          final coachingEnabled = coaching?.enabled ?? false;
          final eligibleForCoaching = profile.coachingEligibility?.eligible ?? false;

          Future<void> setLanguage(String? code) async {
            final ctrl = ref.read(appLocaleProvider.notifier);
            final svc = ref.read(sl.profileServiceProvider);

            if (code == null) {
              await ctrl.setSystemLocale();
              await svc.updateSettings(locale: null);
            } else {
              await ctrl.setLocaleCode(code);
              await svc.updateSettings(locale: code);
            }

            ref.invalidate(userProfileProvider);
          }

          Future<void> setCoachingEnabled(bool value) async {
            // Track coaching enable/disable action
            await UserAnalyticsService.instance.trackUserAction('coaching_status_change', properties: {
              'action': value ? 'enable' : 'disable',
              'previous_status': coachingEnabled ? 'enabled' : 'disabled',
              'new_status': value ? 'enabled' : 'disabled',
              'screen': 'settings_general',
            });
            
            try {
              final svc = ref.read(sl.profileServiceProvider);
              await svc.updateCoachingProfile(enabled: value);
              ref.invalidate(userProfileProvider);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(value ? 'Coaching enabled' : 'Coaching disabled')),
                );
              }
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to update coaching: $e')),
                );
              }
            }
          }

          double _calculateProfileCompletionScore(
            String tagline,
            String description,
            List<String> specializations,
            List<String> languages,
            String? rateType,
          ) {
            int score = 0;
            int maxScore = 5;
            
            if (tagline.isNotEmpty) score++;
            if (description.isNotEmpty) score++;
            if (specializations.isNotEmpty) score++;
            if (languages.isNotEmpty) score++;
            if (rateType != null) score++;
            
            return score / maxScore;
          }

          Future<void> showCoachingSettingsDialog() async {
            // Track coaching settings dialog open
            await UserAnalyticsService.instance.trackUserAction('coaching_settings_open', properties: {
              'screen': 'settings_general',
              'action': 'open_settings_dialog',
              'coaching_enabled': coachingEnabled,
            });

            const languageOptions = <String, String>{
              'en': 'English',
              'ua': 'Ukrainian',
              'ru': 'Russian',
              'pl': 'Polish',
              'de': 'German',
            };

            const specializationOptions = <String, String>{
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

            bool enabled = coaching?.enabled ?? false;
            final taglineController = TextEditingController(text: coaching?.tagline ?? '');
            final descriptionController = TextEditingController(text: coaching?.description ?? '');
            final selectedSpecializations = <String>{...?(coaching?.specializations)};
            final selectedLanguages = <String>{...?(coaching?.languages)};
            final rateAmountController = TextEditingController(
              text: coaching?.ratePlan?.amountMinor != null ? (coaching!.ratePlan!.amountMinor! / 100).toStringAsFixed(0) : '',
            );

            final result = await showDialog<bool>(
              context: context,
              builder: (ctx) {
                return StatefulBuilder(
                  builder: (ctx, setState) {
                    return AlertDialog(
                      title: const Text('Coaching settings'),
                      content: SingleChildScrollView(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Enable coaching features'),
                              value: enabled,
                              onChanged: (value) => setState(() => enabled = value),
                            ),
                            TextField(
                              controller: taglineController,
                              decoration: const InputDecoration(labelText: 'Tagline'),
                            ),
                            TextField(
                              controller: descriptionController,
                              decoration: const InputDecoration(labelText: 'Description'),
                              maxLines: 3,
                            ),
                            const SizedBox(height: 12),
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
                                for (final entry in specializationOptions.entries)
                                  FilterChip(
                                    label: Text(entry.value),
                                    selected: selectedSpecializations.contains(entry.key),
                                    onSelected: (value) {
                                      setState(() {
                                        if (value) {
                                          selectedSpecializations.add(entry.key);
                                        } else {
                                          selectedSpecializations.remove(entry.key);
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
                                for (final entry in languageOptions.entries)
                                  FilterChip(
                                    label: Text(entry.value),
                                    selected: selectedLanguages.contains(entry.key),
                                    onSelected: (selected) {
                                      setState(() {
                                        if (selected) {
                                          selectedLanguages.add(entry.key);
                                        } else {
                                          selectedLanguages.remove(entry.key);
                                        }
                                      });
                                    },
                                  ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: rateAmountController,
                              decoration: const InputDecoration(labelText: 'Rate per month (USD)'),
                              keyboardType: TextInputType.number,
                            ),
                            const SizedBox(height: 4),
                            const Align(
                              alignment: Alignment.centerLeft,
                              child: Text(
                                'Amount is entered in dollars (e.g. 120 = \$120.00).',
                                style: TextStyle(fontSize: 11),
                              ),
                            ),
                          ],
                        ),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(false),
                          child: Text(l10n.cancel),
                        ),
                        ElevatedButton(
                          onPressed: () => Navigator.of(ctx).pop(true),
                          child: Text(l10n.save),
                        ),
                      ],
                    );
                  },
                );
              },
            );

            if (result != true) return;

            int? parseInt(String text) {
              if (text.trim().isEmpty) return null;
              return int.tryParse(text.trim());
            }

            int? parseAmount(String text) {
              if (text.trim().isEmpty) return null;
              final value = double.tryParse(text.trim());
              if (value == null) return null;
              // Convert dollars to cents for backend
              return (value * 100).round();
            }

            final svc = ref.read(sl.profileServiceProvider);

            try {
              // Track coaching profile update
              await UserAnalyticsService.instance.trackUserAction('coaching_profile_update', properties: {
                'screen': 'settings_general',
                'action': 'save_coaching_settings',
                'enabled': enabled,
                'has_tagline': taglineController.text.trim().isNotEmpty,
                'has_description': descriptionController.text.trim().isNotEmpty,
                'has_specializations': selectedSpecializations.isNotEmpty,
                'has_languages': selectedLanguages.isNotEmpty,
                'has_rate_plan': rateAmountController.text.trim().isNotEmpty,
              });
              
              await svc.updateCoachingProfile(
                enabled: enabled,
                tagline: taglineController.text.trim(),
                description: descriptionController.text.trim(),
                specializations: selectedSpecializations.toList(),
                languages: selectedLanguages.toList(),
                ratePlan: (rateAmountController.text.trim().isNotEmpty)
                    ? CoachingRatePlan(
                        amountMinor: parseAmount(rateAmountController.text),
                      )
                    : null,
              );
              ref.invalidate(userProfileProvider);
              
              // Track trainer profile published if this is first time enabling coaching
              final currentCoaching = profile.coaching;
              final wasPreviouslyEnabled = currentCoaching?.enabled ?? false;
              final isNowEnabled = enabled;
              final hasCompleteProfile = taglineController.text.trim().isNotEmpty &&
                  descriptionController.text.trim().isNotEmpty &&
                  selectedSpecializations.isNotEmpty;
                  
              if (!wasPreviouslyEnabled && isNowEnabled && hasCompleteProfile) {
                await UserAnalyticsService.instance.trackTrainerProfilePublished(properties: {
                  'has_tagline': taglineController.text.trim().isNotEmpty,
                  'has_description': descriptionController.text.trim().isNotEmpty,
                  'has_specializations': selectedSpecializations.isNotEmpty,
                  'has_languages': selectedLanguages.isNotEmpty,
                  'has_rate_plan': rateAmountController.text.trim().isNotEmpty,
                  'profile_completion_score': _calculateProfileCompletionScore(
                    taglineController.text.trim(),
                    descriptionController.text.trim(),
                    selectedSpecializations.toList(),
                    selectedLanguages.toList(),
                    rateAmountController.text.trim().isNotEmpty ? 'per_month' : null,
                  ),
                });
              }
              
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Coaching profile updated')),
                );
              }
            } catch (e) {
              String message;
              if (e is ApiException) {
                message = e.message;
              } else {
                message = 'Failed to update coaching profile: $e';
              }
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(message)),
              );
            }  
          }

          Future<void> setTimezone(String? value) async {
            final svc = ref.read(sl.profileServiceProvider);
            final trimmed = (value ?? '').trim();
            await svc.updateSettings(timezone: trimmed.isEmpty ? null : trimmed);
            ref.invalidate(userProfileProvider);
          }

          Future<void> setPublicProfile(bool value) async {
            final svc = ref.read(sl.profileServiceProvider);
            await svc.updateProfile(isPublic: value);
            ref.invalidate(userProfileProvider);
          }

          String languageSubtitle() {
            if (languageCode == null) return l10n.languageSystem;
            switch (languageCode) {
              case 'en':
                return l10n.languageEnglish;
              case 'uk':
                return l10n.languageUkrainian;
              default:
                return languageCode;
            }
          }

          String themeSubtitle() {
            switch (themeMode) {
              case ThemeMode.system:
                return 'System';
              case ThemeMode.light:
                return 'Light';
              case ThemeMode.dark:
                return 'Dark';
            }
          }

          Future<void> pickThemeMode() async {
            final selected = await showModalBottomSheet<ThemeMode>(
              context: context,
              builder: (ctx) {
                return SafeArea(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ListTile(
                        title: const Text('System'),
                        trailing: themeMode == ThemeMode.system ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop(ThemeMode.system),
                      ),
                      ListTile(
                        title: const Text('Light'),
                        trailing: themeMode == ThemeMode.light ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop(ThemeMode.light),
                      ),
                      ListTile(
                        title: const Text('Dark'),
                        trailing: themeMode == ThemeMode.dark ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop(ThemeMode.dark),
                      ),
                    ],
                  ),
                );
              },
            );
            if (selected == null) return;
            await ref.read(appThemeModeProvider.notifier).setThemeMode(selected);
          }

          Future<void> pickLanguage() async {
            final selected = await showModalBottomSheet<String?>(
              context: context,
              builder: (ctx) {
                final current = languageCode;
                return SafeArea(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ListTile(
                        title: Text(l10n.languageSystem),
                        trailing: current == null ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop(null),
                      ),
                      ListTile(
                        title: Text(l10n.languageEnglish),
                        trailing: current == 'en' ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop('en'),
                      ),
                      ListTile(
                        title: Text(l10n.languageUkrainian),
                        trailing: current == 'uk' ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop('uk'),
                      ),
                    ],
                  ),
                );
              },
            );

            if (selected == languageCode) return;
            await setLanguage(selected);
          }

          Future<void> editTimezone() async {
            final controller = TextEditingController(text: timezone);
            final result = await showDialog<String?>(
              context: context,
              builder: (ctx) {
                return AlertDialog(
                  title: Text(l10n.timezone),
                  content: TextField(
                    controller: controller,
                    decoration: const InputDecoration(hintText: 'e.g. Europe/Kyiv'),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.of(ctx).pop(null),
                      child: Text(l10n.cancel),
                    ),
                    ElevatedButton(
                      onPressed: () => Navigator.of(ctx).pop(controller.text),
                      child: Text(l10n.save),
                    ),
                  ],
                );
              },
            );
            if (result == null) return;
            await setTimezone(result);
          }

          Future<void> signOut() async {
            final ok = await showDialog<bool>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Sign out'),
                content: const Text('Are you sure you want to sign out?'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(false),
                    child: Text(l10n.cancel),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(true),
                    child: const Text('Sign out'),
                  ),
                ],
              ),
            );
            if (ok != true) return;
            await AuthService().signOut();
          }

          Future<void> deleteAccount() async {
            final ok = await showDialog<bool>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Delete account'),
                content: const Text('This will schedule deletion of your account data. Continue?'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(false),
                    child: Text(l10n.cancel),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(true),
                    child: const Text('Delete'),
                  ),
                ],
              ),
            );
            if (ok != true) return;

            try {
              final svc = ref.read(sl.accountServiceProvider);
              await svc.purgeAccount();
              await AuthService().signOut();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Account deletion scheduled')),
                );
              }
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to delete account: $e')),
                );
              }
            }
          }

          Future<void> connectStripe() async {
            // Track Stripe connection attempt
            await UserAnalyticsService.instance.trackUserAction('stripe_connect_attempt', properties: {
              'screen': 'settings_general',
              'action': 'connect_stripe',
              'has_existing_account': coaching?.stripeConnectAccountId != null,
            });
            
            try {
              final svc = ref.read(sl.profileServiceProvider);
              final response = await svc.createStripeConnectOnboardingLink();
              final url = response['onboarding_url'] as String?;
              
              if (url != null && await canLaunchUrl(Uri.parse(url))) {
                // Track successful Stripe redirect
                await UserAnalyticsService.instance.trackUserAction('stripe_connect_redirect', properties: {
                  'screen': 'settings_general',
                  'action': 'redirect_to_stripe',
                  'onboarding_url': url,
                });
                
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Opening Stripe setup...'),
                    ),
                  );
                }
              } else {
                // Track Stripe connection failure
                await UserAnalyticsService.instance.trackUserAction('stripe_connect_failed', properties: {
                  'screen': 'settings_general',
                  'action': 'stripe_redirect_failed',
                  'has_url': url != null,
                });
                
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Failed to open Stripe setup'),
                    ),
                  );
                }
              }
            } catch (e) {
              // Track Stripe connection error
              await UserAnalyticsService.instance.trackUserAction('stripe_connect_error', properties: {
                'screen': 'settings_general',
                'action': 'stripe_connect_error',
                'error_message': e.toString(),
              });
              
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to connect Stripe: $e')),
                );
              }
            }
          }

          return ListView(
            children: [
              ListTile(
                title: const Text('Theme'),
                subtitle: Text(themeSubtitle()),
                trailing: const Icon(Icons.chevron_right),
                onTap: pickThemeMode,
              ),
              const Divider(height: 1),
              ListTile(
                title: Text(l10n.language),
                subtitle: Text(languageSubtitle()),
                trailing: const Icon(Icons.chevron_right),
                onTap: pickLanguage,
              ),
              const Divider(height: 1),
              ListTile(
                title: Text(l10n.timezone),
                subtitle: Text(timezone.isEmpty ? 'Not set' : timezone),
                trailing: const Icon(Icons.chevron_right),
                onTap: editTimezone,
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: Text(l10n.publicProfile),
                value: profile.isPublic,
                onChanged: (v) => setPublicProfile(v),
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Show activity chart'),
                value: sectionPrefs.showActivityChart,
                onChanged: (v) => ref.read(profileScreenSectionsProvider.notifier).setShowActivityChart(v),
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Show workout history'),
                value: sectionPrefs.showWorkoutHistory,
                onChanged: (v) => ref.read(profileScreenSectionsProvider.notifier).setShowWorkoutHistory(v),
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Show workout analytics'),
                value: sectionPrefs.showWorkoutAnalytics,
                onChanged: (v) => ref.read(profileScreenSectionsProvider.notifier).setShowWorkoutAnalytics(v),
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Show all time'),
                value: sectionPrefs.workoutAnalyticsShowAllTime,
                onChanged: sectionPrefs.showWorkoutAnalytics
                    ? (v) => ref
                        .read(profileScreenSectionsProvider.notifier)
                        .setWorkoutAnalyticsShowAllTime(v)
                    : null,
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Use horizontal scroll'),
                value: sectionPrefs.workoutAnalyticsUseHorizontalScroll,
                onChanged: sectionPrefs.showWorkoutAnalytics
                    ? (v) => ref
                        .read(profileScreenSectionsProvider.notifier)
                        .setWorkoutAnalyticsUseHorizontalScroll(v)
                    : null,
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Enable coaching'),
                value: coachingEnabled,
                onChanged: eligibleForCoaching ? (v) => setCoachingEnabled(v) : null,
              ),
              const Divider(height: 1),
              ListTile(
                title: const Text('Coaching settings'),
                subtitle: eligibleForCoaching ? null : const Text('Not available for this account'),
                trailing: const Icon(Icons.chevron_right),
                onTap: (coachingEnabled || eligibleForCoaching) ? showCoachingSettingsDialog : null,
              ),
              const Divider(height: 1),
              if (coachingEnabled && (coaching?.stripeConnectAccountId == null))
                ListTile(
                  title: const Text('Connect Stripe payouts'),
                  subtitle: const Text('Set up payment processing for coaching'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: connectStripe,
                ),
              if (coachingEnabled && (coaching?.stripeConnectAccountId != null))
                ListTile(
                  title: const Text('Stripe connected'),
                  subtitle: const Text('Payment processing is set up'),
                  trailing: const Icon(Icons.check_circle, color: Colors.green),
                  onTap: connectStripe,
                ),
              const Divider(height: 1),
              ListTile(
                title: const Text('Sign out'),
                onTap: signOut,
              ),
              const Divider(height: 1),
              ListTile(
                title: const Text('Delete account'),
                textColor: Theme.of(context).colorScheme.error,
                onTap: deleteAccount,
              ),
              const Divider(height: 1),
            ],
          );
        },
      ),
    );
  }
}

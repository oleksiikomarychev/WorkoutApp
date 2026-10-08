import 'package:flutter/material.dart';
import 'package:workout_app/src/api/nutrition_api.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'nutrition_plan_detail.dart';
import 'nutrition_plan_create.dart';

class NutritionPlansList extends StatefulWidget {
  const NutritionPlansList({super.key});

  @override
  State<NutritionPlansList> createState() => _NutritionPlansListState();
}

class _NutritionPlansListState extends State<NutritionPlansList> {
  List<Map<String, dynamic>> _sessions = [];
  bool _isLoading = true;

  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final sessions = await NutritionApi.getAllSessions();
      if (mounted) {
        setState(() {
          _sessions = sessions;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  Future<void> _refreshSessions() async {
    await _loadSessions();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'nutrition_plans_list',
        'entities': {'sessions_count': _sessions.length},
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: l10n.nutritionSessionsTitle,
            onTitleTap: openChat,
          ),
          body: RefreshIndicator(
            onRefresh: _refreshSessions,
            child: _buildBody(l10n),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () async {
              final result = await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const NutritionPlanCreate(),
                ),
              );
              if (result != null) {
                _refreshSessions();
              }
            },
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }

  Widget _buildBody(AppLocalizations l10n) {
    if (_isLoading) {
      return const LoadingIndicator();
    }

    if (_errorMessage != null) {
      return ErrorMessage(
        message: 'Failed to load nutrition sessions: $_errorMessage',
        onRetry: _loadSessions,
      );
    }

    if (_sessions.isEmpty) {
      return EmptyState(
        icon: Icons.restaurant,
        title: l10n.nutritionSessionsEmpty,
        description: l10n.nutritionSessionsEmptyDesc,
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 12),
      itemCount: _sessions.length,
      itemBuilder: (context, index) {
        final session = _sessions[index];
        final entries = session['entries'] as List<dynamic>? ?? [];
        return ListTile(
          title: Text(
            l10n.nutritionSessionTitle(session['session_id'].toString()),
          ),
          subtitle: Text(l10n.userIdLabel(session['user_id'].toString())),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(l10n.entriesCount(entries.length)),
              const Icon(Icons.chevron_right),
            ],
          ),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => NutritionPlanDetail(sessionData: session),
              ),
            ).then((_) => _refreshSessions());
          },
        );
      },
    );
  }
}

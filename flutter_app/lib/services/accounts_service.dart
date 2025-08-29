import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/api_client.dart';

import 'package:workout_app/models/accounts/user_profile.dart';
import 'package:workout_app/models/accounts/client_brief.dart';
import 'package:workout_app/models/accounts/client_note.dart';
import 'package:workout_app/models/accounts/tag.dart';

class AccountsService extends BaseApiService {
  AccountsService(ApiClient apiClient) : super(apiClient);

  // --- Me ---
  Future<UserProfile> getMe() async {
    return await get<UserProfile>(
      ApiConfig.accountsMe,
      (json) => UserProfile.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<UserProfile> updateMe(Map<String, dynamic> payload) async {
    return await patch<UserProfile>(
      ApiConfig.accountsMe,
      payload,
      (json) => UserProfile.fromJson(json as Map<String, dynamic>),
    );
  }

  // --- Clients ---
  Future<List<ClientBrief>> listClients() async {
    final resp = await apiClient.get(
      ApiConfig.accountsClients,
      context: 'AccountsService.listClients',
    );
    if (resp is Map<String, dynamic>) {
      final items = (resp['items'] as List?) ?? [];
      return items
          .whereType<Map<String, dynamic>>()
          .map((e) => ClientBrief.fromJson(e))
          .toList();
    }
    throw Exception('Unexpected response for clients list');
  }

  // --- Notes ---
  Future<List<ClientNote>> listClientNotes(String clientUserId) async {
    final resp = await apiClient.get(
      ApiConfig.accountsClientNotes(clientUserId),
      context: 'AccountsService.listClientNotes',
    );
    if (resp is Map<String, dynamic>) {
      final items = (resp['items'] as List?) ?? [];
      return items
          .whereType<Map<String, dynamic>>()
          .map((e) => ClientNote.fromJson(e))
          .toList();
    }
    throw Exception('Unexpected response for client notes list');
  }

  Future<ClientNote> createClientNote(String clientUserId, ClientNoteCreatePayload payload) async {
    final resp = await apiClient.post(
      ApiConfig.accountsClientNotes(clientUserId),
      payload.toJson(),
      context: 'AccountsService.createClientNote',
    );
    if (resp is Map<String, dynamic>) {
      return ClientNote.fromJson(resp);
    }
    throw Exception('Unexpected response for create client note');
  }

  Future<ClientNote> updateNote(String noteId, ClientNoteUpdatePayload payload) async {
    final resp = await apiClient.put(
      ApiConfig.accountsNoteById(noteId),
      payload.toJson(),
      context: 'AccountsService.updateNote',
    );
    if (resp is Map<String, dynamic>) {
      return ClientNote.fromJson(resp);
    }
    throw Exception('Unexpected response for update note');
  }

  Future<bool> deleteNote(String noteId) async {
    await apiClient.delete(
      ApiConfig.accountsNoteById(noteId),
      context: 'AccountsService.deleteNote',
    );
    return true;
  }

  // --- Tags ---
  Future<List<Tag>> listTags() async {
    final resp = await apiClient.get(
      ApiConfig.accountsTags,
      context: 'AccountsService.listTags',
    );
    if (resp is Map<String, dynamic>) {
      final items = (resp['items'] as List?) ?? [];
      return items
          .whereType<Map<String, dynamic>>()
          .map((e) => Tag.fromJson(e))
          .toList();
    }
    throw Exception('Unexpected response for tags list');
  }

  Future<List<Tag>> listClientTags(String clientUserId) async {
    final resp = await apiClient.get(
      ApiConfig.accountsClientTags(clientUserId),
      context: 'AccountsService.listClientTags',
    );
    if (resp is Map<String, dynamic>) {
      final items = (resp['items'] as List?) ?? [];
      return items
          .whereType<Map<String, dynamic>>()
          .map((e) => Tag.fromJson(e))
          .toList();
    }
    throw Exception('Unexpected response for client tags list');
  }

  Future<bool> attachTagToClient(String clientUserId, String tagId) async {
    await apiClient.post(
      ApiConfig.accountsClientTagById(clientUserId, tagId),
      {},
      context: 'AccountsService.attachTagToClient',
    );
    return true;
  }

  Future<bool> detachTagFromClient(String clientUserId, String tagId) async {
    await apiClient.delete(
      ApiConfig.accountsClientTagById(clientUserId, tagId),
      context: 'AccountsService.detachTagFromClient',
    );
    return true;
  }
}

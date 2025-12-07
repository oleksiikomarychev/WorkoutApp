import 'package:freezed_annotation/freezed_annotation.dart';

part 'base_model.freezed.dart';
part 'base_model.g.dart';

@immutable
abstract class BaseModel with _$BaseModel {
  const BaseModel._();

  Map<String, dynamic> toJson();


  int? get id;


  static T? fromJson<T extends BaseModel>(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) fromJsonT,
  ) {
    try {
      return fromJsonT(json);
    } catch (e) {
      print('Error parsing $T from JSON: $e');
      return null;
    }
  }
}

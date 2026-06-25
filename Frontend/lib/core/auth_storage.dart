import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final _storage = FlutterSecureStorage();

class AuthStorage {
  static Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  static Future<void> saveUserInfo({
    required String userId,
    required String fullName,
    required String role,
    String? classId,
    String? className,
  }) async {
    await _storage.write(key: 'user_id', value: userId);
    await _storage.write(key: 'full_name', value: fullName);
    await _storage.write(key: 'role', value: role);
    if (classId != null) await _storage.write(key: 'class_id', value: classId);
    if (className != null) await _storage.write(key: 'class_name', value: className);
  }

  static Future<String?> getAccessToken() => _storage.read(key: 'access_token');
  static Future<String?> getRefreshToken() => _storage.read(key: 'refresh_token');
  static Future<String?> getRole() => _storage.read(key: 'role');
  static Future<String?> getClassId() => _storage.read(key: 'class_id');
  static Future<String?> getClassName() => _storage.read(key: 'class_name');
  static Future<String?> getUserId() => _storage.read(key: 'user_id');
  static Future<String?> getFullName() => _storage.read(key: 'full_name');

  static Future<void> clear() => _storage.deleteAll();
}

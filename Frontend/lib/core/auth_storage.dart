import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _storage = FlutterSecureStorage(
  aOptions: AndroidOptions(
    encryptedSharedPreferences: true,
  ),
);

class AuthStorage {
  static Future<void> saveTokens(String access, String refresh) async {
    try {
      await _storage.write(key: 'access_token', value: access);
      await _storage.write(key: 'refresh_token', value: refresh);
    } catch (_) {
      await clear();
    }
  }

  static Future<void> saveUserInfo({
    required String userId,
    required String fullName,
    required String role,
    String? classId,
    String? className,
  }) async {
    try {
      await _storage.write(key: 'user_id', value: userId);
      await _storage.write(key: 'full_name', value: fullName);
      await _storage.write(key: 'role', value: role);
      if (classId != null)
        await _storage.write(key: 'class_id', value: classId);
      if (className != null)
        await _storage.write(key: 'class_name', value: className);
    } catch (_) {
      await clear();
    }
  }

  static Future<String?> getAccessToken() async {
    try {
      return await _storage.read(key: 'access_token');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getRefreshToken() async {
    try {
      return await _storage.read(key: 'refresh_token');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getRole() async {
    try {
      return await _storage.read(key: 'role');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getClassId() async {
    try {
      return await _storage.read(key: 'class_id');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getClassName() async {
    try {
      return await _storage.read(key: 'class_name');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getUserId() async {
    try {
      return await _storage.read(key: 'user_id');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<String?> getFullName() async {
    try {
      return await _storage.read(key: 'full_name');
    } catch (_) {
      await clear();
      return null;
    }
  }

  static Future<void> clear() async {
    try {
      await _storage.deleteAll();
    } catch (_) {}
  }
}

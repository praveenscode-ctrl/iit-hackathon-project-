import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../core/auth_storage.dart';

final _svc = AuthService();

final authProvider = StateNotifierProvider<AuthNotifier, UserModel?>((ref) {
  return AuthNotifier();
});

class AuthNotifier extends StateNotifier<UserModel?> {
  AuthNotifier() : super(null);

  Future<UserModel> login({
    required String email,
    required String password,
    required String registrationId,
    String fcmToken = '',
  }) async {
    final user = await _svc.login(
      email: email,
      password: password,
      registrationId: registrationId,
      fcmToken: fcmToken,
    );
    state = user;
    return user;
  }

  Future<UserModel> restoreFromStorage() async {
    final user = await _svc.getMe();
    state = user;
    return user;
  }

  Future<void> logout() async {
    await _svc.logout();
    state = null;
  }

  void setUser(UserModel user) => state = user;
}

import '../core/api_client.dart';
import '../core/auth_storage.dart';
import '../models/user_model.dart';

class AuthService {
  Future<UserModel> login({
    required String email,
    required String password,
    required String registrationId,
    String fcmToken = '',
  }) async {
    final data = await apiPost('/auth/login', data: {
      'email': email,
      'password': password,
      'registration_id': registrationId,
      'fcm_token': fcmToken,
    });

    await AuthStorage.saveTokens(
      data['access_token'] as String,
      data['refresh_token'] as String,
    );

    final user = UserModel.fromJson(data['user'] as Map<String, dynamic>);
    await AuthStorage.saveUserInfo(
      userId: user.id,
      fullName: user.fullName,
      role: user.role,
      classId: user.classId,
      className: user.className,
    );
    return user;
  }

  Future<void> adminSignup({
    required String fullName,
    required String email,
    required String password,
  }) async {
    await apiPost('/auth/admin/signup', data: {
      'full_name': fullName,
      'email': email,
      'password': password,
    });
  }

  Future<UserModel> verifyOtp({
    required String email,
    required String otp,
  }) async {
    final data = await apiPost('/auth/admin/verify-otp', data: {
      'email': email,
      'otp': otp,
    });

    await AuthStorage.saveTokens(
      data['access_token'] as String,
      data['refresh_token'] as String,
    );

    final user = UserModel.fromJson(data['user'] as Map<String, dynamic>);
    await AuthStorage.saveUserInfo(
      userId: user.id,
      fullName: user.fullName,
      role: user.role,
    );
    return user;
  }

  Future<UserModel> getMe() async {
    final data = await apiGet('/auth/me');
    return UserModel.fromJson(data as Map<String, dynamic>);
  }

  Future<void> logout() async {
    final refresh = await AuthStorage.getRefreshToken();
    try {
      await apiPost('/auth/logout', data: {'refresh_token': refresh});
    } catch (_) {}
    await AuthStorage.clear();
  }
}

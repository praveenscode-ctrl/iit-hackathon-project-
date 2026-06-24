import 'package:dio/dio.dart';
import 'constants.dart';
import 'auth_storage.dart';
import 'exceptions.dart';

final dio = _buildDio();

Dio _buildDio() {
  final d = Dio(BaseOptions(
    baseUrl: kBaseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
    contentType: 'application/json',
  ));

  d.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final token = await AuthStorage.getAccessToken();
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    },
    onError: (err, handler) async {
      if (err.response?.statusCode == 401) {
        // try refresh
        final refreshed = await _tryRefresh();
        if (refreshed) {
          // retry with new token
          final token = await AuthStorage.getAccessToken();
          err.requestOptions.headers['Authorization'] = 'Bearer $token';
          try {
            final resp = await dio.fetch(err.requestOptions);
            return handler.resolve(resp);
          } catch (_) {}
        }
        // refresh failed — clear and let caller handle
        await AuthStorage.clear();
      }
      handler.next(err);
    },
  ));

  return d;
}

Future<bool> _tryRefresh() async {
  final refresh = await AuthStorage.getRefreshToken();
  if (refresh == null) return false;

  try {
    final resp = await Dio().post(
      '$kBaseUrl/auth/refresh',
      data: {'refresh_token': refresh},
    );
    final newToken = resp.data['access_token'] as String;
    await AuthStorage.saveTokens(newToken, refresh);
    return true;
  } catch (_) {
    return false;
  }
}

// helper for GET
Future<dynamic> apiGet(String path, {Map<String, dynamic>? params}) async {
  try {
    final resp = await dio.get(path, queryParameters: params);
    return resp.data;
  } on DioException catch (e) {
    _throwApiError(e);
  }
}

// helper for POST
Future<dynamic> apiPost(String path, {dynamic data}) async {
  try {
    final resp = await dio.post(path, data: data);
    return resp.data;
  } on DioException catch (e) {
    _throwApiError(e);
  }
}

// helper for PATCH
Future<dynamic> apiPatch(String path, {dynamic data}) async {
  try {
    final resp = await dio.patch(path, data: data);
    return resp.data;
  } on DioException catch (e) {
    _throwApiError(e);
  }
}

void _throwApiError(DioException e) {
  final status = e.response?.statusCode ?? 0;
  final detail = e.response?.data?['detail'] ?? e.message ?? 'Something went wrong';
  throw ApiException(status, detail.toString());
}

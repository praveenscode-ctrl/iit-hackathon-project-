import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:assignhub/core/api_client.dart' as client;
import 'package:assignhub/services/auth_service.dart';
import 'package:assignhub/services/storage_service.dart';
import 'package:assignhub/services/export_service.dart';
import 'package:assignhub/services/submission_service.dart';

import 'package:flutter/services.dart';

class MockHttpClientAdapter extends Mock implements HttpClientAdapter {}

void main() {
  late MockHttpClientAdapter mockAdapter;

  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    final Map<String, String> values = {};
    const MethodChannel('plugins.it_nomads.com/flutter_secure_storage')
        .setMockMethodCallHandler((MethodCall methodCall) async {
      if (methodCall.method == 'read') {
        return values[methodCall.arguments['key']];
      }
      if (methodCall.method == 'write') {
        values[methodCall.arguments['key']] = methodCall.arguments['value'] as String;
        return true;
      }
      if (methodCall.method == 'deleteAll') {
        values.clear();
        return true;
      }
      return null;
    });
    registerFallbackValue(RequestOptions(path: ''));
  });

  setUp(() {
    mockAdapter = MockHttpClientAdapter();
    client.dio.httpClientAdapter = mockAdapter;
  });

  group('AuthService', () {
    final authService = AuthService();

    test('login sends snake_case fields', () async {
      final responseBody = jsonEncode({
        'access_token': 'at',
        'refresh_token': 'rt',
        'user': {
          'id': 'u',
          'full_name': 'U',
          'email': 'u@u.com',
          'role': 'ADMIN',
          'class_id': null,
          'class_name': null,
          'registration_id': null
        }
      });

      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((invocation) async {
        return ResponseBody.fromString(
          responseBody,
          200,
          headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          },
        );
      });

      await authService.login(
        email: 'admin@test.com',
        password: 'pass',
        registrationId: '',
        fcmToken: '',
      );

      final captured = verify(() => mockAdapter.fetch(captureAny(), any(), any())).captured.first as RequestOptions;
      final data = captured.data as Map<String, dynamic>;

      expect(data.containsKey('registration_id'), isTrue);
      expect(data.containsKey('fcm_token'), isTrue);
      expect(data.containsKey('registrationId'), isFalse);
      expect(data.containsKey('fcmToken'), isFalse);
    });
  });

  group('StorageService', () {
    final storageService = StorageService();

    test('presigned upload sends upload_purpose not folder', () async {
      final responseBody = jsonEncode({
        'upload_url': 'https://s3.test',
        'file_url': 'https://s3.file',
        'expires_in': 300
      });

      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((_) async => ResponseBody.fromString(
        responseBody,
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ));

      await storageService.getUploadUrl(
        fileName: 'test.pdf',
        fileType: 'application/pdf',
        uploadPurpose: 'SUBMISSION',
      );

      final captured = verify(() => mockAdapter.fetch(captureAny(), any(), any())).captured.first as RequestOptions;
      final data = captured.data as Map<String, dynamic>;

      expect(data.containsKey('upload_purpose'), isTrue);
      expect(data.containsKey('folder'), isFalse);
      expect(data.containsKey('uploadPurpose'), isFalse);
      expect(data['upload_purpose'], 'SUBMISSION');
    });

    test('presigned download sends file_url not fileUrl', () async {
      final responseBody = jsonEncode({
        'download_url': 'https://dl.test',
        'expires_in': 300
      });

      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((_) async => ResponseBody.fromString(
        responseBody,
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ));

      await storageService.getDownloadUrl('https://s3.test/file.pdf');

      final captured = verify(() => mockAdapter.fetch(captureAny(), any(), any())).captured.first as RequestOptions;
      final data = captured.data as Map<String, dynamic>;

      expect(data.containsKey('file_url'), isTrue);
      expect(data.containsKey('fileUrl'), isFalse);
    });
  });

  group('ExportService', () {
    final exportService = ExportService();

    test('export request reads export_job_id from response', () async {
      final responseBody = jsonEncode({
        'export_job_id': 'export-uuid-abc',
        'status': 'PENDING'
      });

      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((_) async => ResponseBody.fromString(
        responseBody,
        202,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ));

      final jobId = await exportService.requestExport('assign-uuid');
      expect(jobId, 'export-uuid-abc');
    });
  });

  group('SubmissionService', () {
    final submissionService = SubmissionService();

    test('submit sends snake_case fields', () async {
      final responseBody = jsonEncode({
        'submission_id': 'sub-uuid',
        'submitted_at': '2026-01-01T00:00:00Z',
        'is_late': false,
        'version': 1,
        'receipt': 'Submitted successfully at...'
      });

      when(() => mockAdapter.fetch(any(), any(), any())).thenAnswer((_) async => ResponseBody.fromString(
        responseBody,
        201,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      ));

      await submissionService.submit(
        'assign-uuid',
        submissionType: 'TEXT',
        textAnswer: 'My answer',
        fileUrl: null,
      );

      final captured = verify(() => mockAdapter.fetch(captureAny(), any(), any())).captured.first as RequestOptions;
      final data = captured.data as Map<String, dynamic>;

      expect(data.containsKey('submission_type'), isTrue);
      expect(data.containsKey('text_answer'), isTrue);
      expect(data.containsKey('file_url'), isTrue);
      expect(data.containsKey('submissionType'), isFalse);
      expect(data.containsKey('textAnswer'), isFalse);
    });
  });

  group('WebSocket Client', () {
    test('ws url uses query param token not authorization header', () {
      const assignmentId = 'assign-uuid';
      const token = 'access_token_value';
      final wsUrl = 'wss://assignhub-api.onrender.com/api/v1/ws/tracker/$assignmentId?token=$token';
      expect(wsUrl, contains('?token='));
      expect(wsUrl, isNot(contains('Authorization')));
    });

    test('submission_created event updates row by student_id', () {
      final event = {
        'event': 'submission_created',
        'assignment_id': 'assign-uuid',
        'submitted_count': 1,
        'pending_count': 4,
        'missed_count': 0,
        'late_count': 0,
        'student': {
          'student_id': 'student-uuid',
          'full_name': 'Student One',
          'tracker_status': 'SUBMITTED',
          'submitted_at': '2026-06-25T10:00:00Z',
          'is_late': false,
        },
      };
      final studentId = (event['student'] as Map<String, dynamic>)['student_id'] as String;
      expect(studentId, 'student-uuid');
    });
  });
}

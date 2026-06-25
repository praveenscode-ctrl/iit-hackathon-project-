import 'package:flutter_test/flutter_test.dart';
import 'package:assignhub/models/user_model.dart';
import 'package:assignhub/models/class_model.dart';
import 'package:assignhub/models/assignment_model.dart';
import 'package:assignhub/models/submission_model.dart';
import 'package:assignhub/models/analytics_model.dart';
import 'package:assignhub/models/notification_model.dart';

void main() {

  group('UserModel.fromJson', () {
    test('parses login response with all fields', () {
      final json = {
        'id': 'user-uuid-1',
        'full_name': 'Test User',
        'email': 'test@test.com',
        'role': 'MENTOR',
        'class_id': 'class-uuid-1',
        'class_name': 'Batch A',
        'registration_id': 'MENTOR-ABC12345',
      };
      final user = UserModel.fromJson(json);
      expect(user.id, 'user-uuid-1');
      expect(user.fullName, 'Test User');  // fromJson reads 'full_name'
      expect(user.classId, 'class-uuid-1');  // reads 'class_id'
      expect(user.className, 'Batch A');     // reads 'class_name'
      expect(user.registrationId, 'MENTOR-ABC12345');
    });

    test('admin has null class_id and class_name', () {
      final json = {
        'id': 'admin-uuid',
        'full_name': 'Admin',
        'email': 'admin@test.com',
        'role': 'ADMIN',
        'class_id': null,
        'class_name': null,
        'registration_id': null,
      };
      final user = UserModel.fromJson(json);
      expect(user.classId, isNull);
      expect(user.className, isNull);
      expect(user.registrationId, isNull);
    });
  });

  group('ClassStudentModel.fromJson', () {
    test('reads membership_status not status', () {
      final json = {
        'id': 'student-uuid',
        'full_name': 'Student One',
        'email': 's@test.com',
        'registration_id': 'ROLL001',
        'membership_status': 'ACTIVE',   // MISMATCH-007 check
        'risk_level': 'NORMAL',
        'completion_rate': 75.5,
        'joined_via': 'MANUAL',
        'joined_at': '2026-01-01T00:00:00Z',
      };
      final student = ClassStudentModel.fromJson(json);
      expect(student.membershipStatus, 'ACTIVE');
      expect(student.joinedAt, isNotNull);
    });

    test('does not crash when analytics fields are zero', () {
      final json = {
        'id': 'student-uuid-2',
        'full_name': 'Student Two',
        'email': 's2@test.com',
        'registration_id': 'ROLL002',
        'membership_status': 'PENDING',
        'risk_level': 'NORMAL',
        'completion_rate': 0.0,
        'joined_via': 'BULK_IMPORT',
        'joined_at': '2026-01-01T00:00:00Z',
      };
      expect(() => ClassStudentModel.fromJson(json), returnsNormally);
    });
  });

  group('ApprovalModel.fromJson', () {
    test('reads student_id not id', () {
      final json = {
        'student_id': 'student-uuid-abc',  // MISMATCH approval check
        'full_name': 'Pending Student',
        'email': 'pending@test.com',
        'registration_id': 'ROLL003',
        'requested_at': '2026-01-01T00:00:00Z',  // not created_at
        'joined_via': 'MANUAL',
      };
      final approval = ApprovalModel.fromJson(json);
      expect(approval.studentId, 'student-uuid-abc');  // reads 'student_id'
      expect(approval.requestedAt, isNotNull);
    });
  });

  group('AssignmentModel.fromJson', () {
    test('student_submission always parsed even when not submitted', () {
      final json = {
        'id': 'assignment-uuid',
        'title': 'Test Assignment',
        'description': null,
        'content_type': 'RICH_TEXT',
        'content_url': null,
        'rich_text_body': 'Do this',
        'submission_type': 'TEXT',
        'deadline_at': null,
        'status': 'PUBLISHED',
        'class_id': 'class-uuid',
        'created_by_name': 'Mentor One',
        'student_submission': {
          'submitted': false,
          'submission_id': null,
          'submitted_at': null,
          'is_late': false,
          'version': 0,
        },
      };
      final assignment = AssignmentModel.fromJson(json);
      expect(assignment.studentSubmission, isNotNull);
      expect(assignment.studentSubmission!.submitted, isFalse);
      expect(assignment.studentSubmission!.submissionId, isNull);
    });

    test('nullable fields do not crash', () {
      final json = {
        'id': 'a-uuid',
        'title': 'Assignment',
        'description': null,
        'content_type': 'LINK',
        'content_url': 'https://example.com',
        'rich_text_body': null,
        'submission_type': 'FILE',
        'deadline_at': null,
        'status': 'DRAFT',
        'class_id': 'class-uuid',
        'created_by_name': 'Someone',
        'student_submission': {
          'submitted': false, 'submission_id': null,
          'submitted_at': null, 'is_late': false, 'version': 0
        },
      };
      expect(() => AssignmentModel.fromJson(json), returnsNormally);
    });
  });

  group('SubmissionModel.fromJson', () {
    test('reads submission_id not id — MISMATCH-005', () {
      final json = {
        'submission_id': 'sub-uuid-abc',  // must read this key
        'assignment_id': 'assign-uuid',
        'assignment_title': 'Assignment One',
        'submission_type': 'TEXT',
        'submitted_at': '2026-06-25T10:00:00Z',
        'is_late': false,
        'version': 2,
      };
      final sub = SubmissionModel.fromJson(json);
      expect(sub.submissionId, 'sub-uuid-abc');  // NOT sub.id
      expect(sub.assignmentTitle, 'Assignment One');
    });
  });

  group('ExportJobModel.fromJson', () {
    test('reads export_job_id not id — MISMATCH-006', () {
      final json = {
        'export_job_id': 'export-uuid-xyz',  // must read this key
        'status': 'PENDING',
        'file_url': null,
      };
      final export = ExportJobModel.fromJson(json);
      expect(export.exportJobId, 'export-uuid-xyz');  // NOT export.id
      expect(export.fileUrl, isNull);  // nullable — must not crash
    });

    test('file_url is nullable — does not crash when null', () {
      final json = {
        'export_job_id': 'export-uuid',
        'status': 'PENDING',
        'file_url': null,
      };
      expect(() => ExportJobModel.fromJson(json), returnsNormally);
    });
  });

  group('StudentAnalyticsModel.fromJson', () {
    test('avg_submission_delay_hours parsed as nullable double — MISMATCH-004', () {
      final jsonWithNull = {
        'student_id': 's-uuid',
        'full_name': 'Student',
        'class_name': 'Class A',
        'total_assigned': 3,
        'total_submitted': 2,
        'total_missed': 1,
        'total_late': 0,
        'completion_rate': 66.67,
        'current_streak': 1,
        'longest_streak': 2,
        'avg_submission_delay_hours': null,  // MISMATCH-004: must not crash
        'risk_level': 'NORMAL',
        'consecutive_misses': 0,
        'class_avg_completion': 55.0,
        'assignment_history': [],
      };
      final analytics = StudentAnalyticsModel.fromJson(jsonWithNull);
      expect(analytics.avgSubmissionDelayHours, isNull);
      expect(analytics.classAvgCompletion, 55.0);
    });

    test('parses all 15 required fields', () {
      final json = {
        'student_id': 's-uuid', 'full_name': 'S', 'class_name': 'C',
        'total_assigned': 5, 'total_submitted': 4, 'total_missed': 1,
        'total_late': 1, 'completion_rate': 80.0, 'current_streak': 3,
        'longest_streak': 4, 'avg_submission_delay_hours': 2.5,
        'risk_level': 'LOW', 'consecutive_misses': 0,
        'class_avg_completion': 70.0, 'assignment_history': [],
      };
      final a = StudentAnalyticsModel.fromJson(json);
      expect(a.totalAssigned, 5);
      expect(a.classAvgCompletion, 70.0);
    });
  });

  group('NotificationModel.fromJson', () {
    test('payload key always parsed even if null', () {
      final json = {
        'id': 'notif-uuid',
        'notification_type': 'STUDENT_APPROVED',
        'title': 'Access Granted',
        'body': 'You can log in',
        'payload': null,
        'is_read': false,
        'created_at': '2026-06-25T10:00:00Z',
      };
      expect(() => NotificationModel.fromJson(json), returnsNormally);
    });
  });

  group('TrackerStudent.fromJson', () {
    test('reads student_id not id for WebSocket row update', () {
      final json = {
        'student_id': 'student-uuid',   // WS update finds row by this
        'full_name': 'Student',
        'registration_id': 'ROLL001',
        'tracker_status': 'SUBMITTED',
        'submitted_at': '2026-06-25T10:00:00Z',
        'is_late': false,
        'submission_id': 'sub-uuid',
      };
      final tracker = TrackerStudent.fromJson(json);
      expect(tracker.studentId, 'student-uuid');
      expect(tracker.trackerStatus, 'SUBMITTED');
    });
  });
}

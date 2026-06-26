import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'auth_storage.dart';

// auth screens
import '../screens/auth/splash_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/admin_signup_screen.dart';
import '../screens/auth/otp_verify_screen.dart';

// admin screens
import '../screens/admin/admin_dashboard_screen.dart';
import '../screens/admin/class_list_screen.dart';
import '../screens/admin/create_class_screen.dart';
import '../screens/admin/class_detail_screen.dart';
import '../screens/admin/class_students_screen.dart';
import '../screens/admin/approvals_screen.dart';
import '../screens/admin/student_profile_screen.dart';
import '../screens/admin/bulk_import_screen.dart';
import '../screens/admin/add_co_mentor_screen.dart';
import '../screens/admin/analytics_overview_screen.dart';
import '../screens/admin/class_analytics_drill_screen.dart';
import '../screens/admin/ai_query_screen.dart';

// mentor screens
import '../screens/mentor/mentor_dashboard_screen.dart';
import '../screens/mentor/student_list_screen.dart';
import '../screens/mentor/student_profile_screen.dart';
import '../screens/mentor/approvals_screen.dart';
import '../screens/mentor/assignment_list_screen.dart';
import '../screens/mentor/create_assignment_screen.dart';
import '../screens/mentor/assignment_tracker_screen.dart';
import '../screens/mentor/submissions_view_screen.dart';
import '../screens/mentor/class_analytics_screen.dart';
import '../screens/mentor/assignment_analytics_screen.dart';

// student screens
import '../screens/student/student_dashboard_screen.dart';
import '../screens/student/student_assignment_detail_screen.dart';
import '../screens/student/student_submissions_screen.dart';
import '../screens/student/student_analytics_screen.dart';

final router = GoRouter(
  initialLocation: '/',
  redirect: (context, state) async {
    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (_, __) => const SplashScreen()),
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(
        path: '/admin/signup', builder: (_, __) => const AdminSignupScreen()),
    GoRoute(
      path: '/admin/otp',
      builder: (_, state) => OtpVerifyScreen(email: state.extra as String),
    ),

    // ── admin ──
    GoRoute(
        path: '/admin/dashboard',
        builder: (_, __) => const AdminDashboardScreen()),
    GoRoute(
        path: '/admin/classes', builder: (_, __) => const ClassListScreen()),
    GoRoute(
        path: '/admin/classes/new',
        builder: (_, __) => const CreateClassScreen()),
    GoRoute(
      path: '/admin/classes/:classId',
      builder: (_, state) =>
          ClassDetailScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/admin/classes/:classId/students',
      builder: (_, state) =>
          ClassStudentsScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/admin/classes/:classId/approvals',
      builder: (_, state) =>
          AdminApprovalsScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/admin/classes/:classId/co-mentor',
      builder: (_, state) =>
          AddCoMentorScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/admin/students/:studentId',
      builder: (_, state) => AdminStudentProfileScreen(
          studentId: state.pathParameters['studentId']!),
    ),
    GoRoute(
        path: '/admin/bulk-import',
        builder: (_, __) => const BulkImportScreen()),
    GoRoute(
        path: '/admin/analytics',
        builder: (_, __) => const AnalyticsOverviewScreen()),
    GoRoute(
      path: '/admin/analytics/:classId',
      builder: (_, state) =>
          ClassAnalyticsDrillScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/admin/ai',
      builder: (_, state) => const AdminAiQueryScreen(),
    ),

    // ── mentor ──
    GoRoute(
        path: '/mentor/dashboard',
        builder: (_, __) => const MentorDashboardScreen()),
    GoRoute(
      path: '/mentor/classes/:classId/students',
      builder: (_, state) =>
          MentorStudentListScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/mentor/students/:studentId',
      builder: (_, state) => MentorStudentProfileScreen(
          studentId: state.pathParameters['studentId']!),
    ),
    GoRoute(
      path: '/mentor/classes/:classId/approvals',
      builder: (_, state) =>
          MentorApprovalsScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/mentor/classes/:classId/assignments',
      builder: (_, state) =>
          MentorAssignmentListScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/mentor/classes/:classId/assignments/new',
      builder: (_, state) =>
          CreateAssignmentScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/mentor/assignments/:assignmentId/tracker',
      builder: (_, state) => AssignmentTrackerScreen(
          assignmentId: state.pathParameters['assignmentId']!),
    ),
    GoRoute(
      path: '/mentor/assignments/:assignmentId/submissions',
      builder: (_, state) => SubmissionsViewScreen(
        assignmentId: state.pathParameters['assignmentId']!,
      ),
    ),
    GoRoute(
      path: '/mentor/classes/:classId/analytics',
      builder: (_, state) =>
          MentorClassAnalyticsScreen(classId: state.pathParameters['classId']!),
    ),
    GoRoute(
      path: '/mentor/assignments/:assignmentId/analytics',
      builder: (_, state) => MentorAssignmentAnalyticsScreen(
          assignmentId: state.pathParameters['assignmentId']!),
    ),

    // ── student ──
    GoRoute(
        path: '/student/dashboard',
        builder: (_, __) => const StudentDashboardScreen()),
    GoRoute(
      path: '/student/assignments/:assignmentId',
      builder: (_, state) => StudentAssignmentDetailScreen(
          assignmentId: state.pathParameters['assignmentId']!),
    ),
    GoRoute(
        path: '/student/submissions',
        builder: (_, __) => const StudentSubmissionsScreen()),
    GoRoute(
      path: '/student/analytics',
      builder: (_, state) => const StudentAnalyticsScreen(),
    ),
  ],
);

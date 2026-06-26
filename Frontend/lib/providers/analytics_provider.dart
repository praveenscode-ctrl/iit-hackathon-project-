import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/analytics_model.dart';
import '../services/analytics_service.dart';

final _svc = AnalyticsService();

final adminOverviewProvider = FutureProvider<Map<String, dynamic>>((ref) {
  return _svc.getAdminOverview();
});

final classAnalyticsProvider =
    FutureProvider.family<ClassAnalyticsModel, String>((ref, classId) {
  return _svc.getClassAnalytics(classId);
});

final classStudentsAnalyticsProvider =
    FutureProvider.family<List<Map<String, dynamic>>, String>((ref, classId) {
  return _svc.getClassStudentsAnalytics(classId);
});

final studentAnalyticsProvider =
    FutureProvider.family<StudentAnalyticsModel, String>((ref, studentId) {
  return _svc.getStudentAnalytics(studentId);
});

final riskStudentsProvider =
    FutureProvider.family<List<Map<String, dynamic>>, String>((ref, classId) {
  return _svc.getRiskStudents(classId);
});

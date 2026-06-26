import '../core/api_client.dart';
import '../models/analytics_model.dart';

class AnalyticsService {
  Future<Map<String, dynamic>> getAdminOverview() async {
    final data = await apiGet('/analytics/admin/overview');
    return data as Map<String, dynamic>;
  }

  Future<ClassAnalyticsModel> getClassAnalytics(String classId) async {
    final data = await apiGet('/analytics/classes/$classId');
    return ClassAnalyticsModel.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getClassStudentsAnalytics(
      String classId) async {
    final data = await apiGet('/analytics/classes/$classId/students');
    return List<Map<String, dynamic>>.from(data['students'] as List);
  }

  Future<StudentAnalyticsModel> getStudentAnalytics(String studentId) async {
    final data = await apiGet('/analytics/students/$studentId');
    return StudentAnalyticsModel.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getRiskStudents(String classId) async {
    final data =
        await apiGet('/analytics/risk/students', params: {'class_id': classId});
    return List<Map<String, dynamic>>.from(data['at_risk_students'] as List);
  }

  Future<Map<String, dynamic>> getAssignmentAnalytics(
      String assignmentId) async {
    final data = await apiGet('/analytics/assignments/$assignmentId');
    return data as Map<String, dynamic>;
  }
}

import '../core/api_client.dart';
import '../models/assignment_model.dart';
import '../models/analytics_model.dart';

class AssignmentService {
  Future<List<AssignmentModel>> getAssignments(String classId) async {
    final data = await apiGet('/assignments', params: {'class_id': classId});
    final list = data['assignments'] as List;
    return list.map((e) => AssignmentModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<AssignmentModel> getAssignment(String assignmentId) async {
    final data = await apiGet('/assignments/$assignmentId');
    return AssignmentModel.fromJson(data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> createAssignment(Map<String, dynamic> body) async {
    final data = await apiPost('/assignments', data: body);
    return data as Map<String, dynamic>;
  }

  Future<void> publish(String assignmentId) async {
    await apiPost('/assignments/$assignmentId/publish', data: {});
  }

  Future<void> close(String assignmentId) async {
    await apiPost('/assignments/$assignmentId/close', data: {});
  }

  Future<TrackerModel> getTracker(String assignmentId) async {
    final data = await apiGet('/assignments/$assignmentId/tracker');
    return TrackerModel.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getSubmissions(String assignmentId) async {
    final data = await apiGet('/assignments/$assignmentId/submissions');
    return List<Map<String, dynamic>>.from(data['submissions'] as List);
  }
}

import '../core/api_client.dart';
import '../models/submission_model.dart';

class SubmissionService {
  Future<Map<String, dynamic>> submit(
    String assignmentId, {
    required String submissionType,
    String? fileUrl,
    String? textAnswer,
    String? lateReason,
  }) async {
    final data = await apiPost('/assignments/$assignmentId/submit', data: {
      'submission_type': submissionType,
      'file_url': fileUrl,
      'text_answer': textAnswer,
      'late_reason': lateReason,
    });
    return data as Map<String, dynamic>;
  }

  Future<List<SubmissionModel>> getMySubmissions() async {
    final data = await apiGet('/submissions/my');
    final list = data['submissions'] as List;
    return list
        .map((e) => SubmissionModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> requestExtension(
    String assignmentId, {
    required String reason,
  }) async {
    final data = await apiPost('/assignments/$assignmentId/extension-request', data: {
      'reason': reason,
    });
    return data as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getExtensionRequests(String assignmentId) async {
    final data = await apiGet('/assignments/$assignmentId/extension-requests');
    return List<Map<String, dynamic>>.from(data['requests'] as List);
  }

  Future<void> approveExtension(String requestId) async {
    await apiPost('/extension-requests/$requestId/approve');
  }

  Future<void> rejectExtension(String requestId) async {
    await apiPost('/extension-requests/$requestId/reject');
  }
}

import '../core/api_client.dart';
import '../models/submission_model.dart';

class SubmissionService {
  Future<Map<String, dynamic>> submit(
    String assignmentId, {
    required String submissionType,
    String? fileUrl,
    String? textAnswer,
  }) async {
    final data = await apiPost('/assignments/$assignmentId/submit', data: {
      'submission_type': submissionType,
      'file_url': fileUrl,
      'text_answer': textAnswer,
    });
    return data as Map<String, dynamic>;
  }

  Future<List<SubmissionModel>> getMySubmissions() async {
    final data = await apiGet('/submissions/my');
    final list = data['submissions'] as List;
    return list.map((e) => SubmissionModel.fromJson(e as Map<String, dynamic>)).toList();
  }
}

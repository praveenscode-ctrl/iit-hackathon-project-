import '../core/api_client.dart';
import '../models/ai_response_model.dart';

class AiService {
  Future<AiResponseModel> query({
    String? classId,
    required String queryText,
  }) async {
    final data = await apiPost('/ai/query', data: {
      'class_id': classId,
      'query_text': queryText,
    });
    return AiResponseModel.fromJson(data as Map<String, dynamic>);
  }
}

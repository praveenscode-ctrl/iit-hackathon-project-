import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/ai_response_model.dart';
import '../services/ai_service.dart';

final _svc = AiService();

final aiProvider = StateNotifierProvider<AiNotifier, AsyncValue<AiResponseModel?>>((ref) {
  return AiNotifier();
});

class AiNotifier extends StateNotifier<AsyncValue<AiResponseModel?>> {
  AiNotifier() : super(const AsyncValue.data(null));

  Future<void> ask({String? classId, required String queryText}) async {
    state = const AsyncValue.loading();
    try {
      final result = await _svc.query(classId: classId, queryText: queryText);
      state = AsyncValue.data(result);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void clear() => state = const AsyncValue.data(null);
}

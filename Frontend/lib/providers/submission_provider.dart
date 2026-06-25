import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/submission_model.dart';
import '../services/submission_service.dart';

final _svc = SubmissionService();

final mySubmissionsProvider = FutureProvider<List<SubmissionModel>>((ref) {
  return _svc.getMySubmissions();
});

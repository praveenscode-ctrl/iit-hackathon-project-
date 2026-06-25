import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/assignment_model.dart';
import '../services/submission_service.dart';
import '../models/analytics_model.dart';
import '../services/assignment_service.dart';

final _svc = AssignmentService();

final assignmentsProvider = FutureProvider.family<List<AssignmentModel>, String>((ref, classId) {
  return _svc.getAssignments(classId);
});

final assignmentDetailProvider = FutureProvider.family<AssignmentModel, String>((ref, assignmentId) {
  return _svc.getAssignment(assignmentId);
});

final trackerProvider = FutureProvider.family<TrackerModel, String>((ref, assignmentId) {
  return _svc.getTracker(assignmentId);
});

final submissionsForAssignmentProvider = FutureProvider.family<List<Map<String, dynamic>>, String>((ref, assignmentId) {
  return _svc.getSubmissions(assignmentId);
});

final mySubmissionsProvider = FutureProvider<List<dynamic>>((ref) async {
  final data = await SubmissionService().getMySubmissions();
  return data;
});

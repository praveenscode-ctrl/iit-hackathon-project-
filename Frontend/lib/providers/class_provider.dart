import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/class_model.dart';
import '../services/class_service.dart';

final _svc = ClassService();

final classListProvider = FutureProvider<List<ClassModel>>((ref) {
  return _svc.getClasses();
});

final myClassesProvider = FutureProvider<List<Map<String, dynamic>>>((ref) {
  return _svc.getMyClasses();
});

final classDetailProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, classId) {
  return _svc.getClassDetail(classId);
});

final classStudentsProvider = FutureProvider.family<List<Map<String, dynamic>>, String>((ref, classId) {
  return _svc.getStudents(classId);
});

final approvalsProvider = FutureProvider.family<List<Map<String, dynamic>>, String>((ref, classId) {
  return _svc.getApprovals(classId);
});

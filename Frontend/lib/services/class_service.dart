import '../core/api_client.dart';
import '../models/class_model.dart';

class ClassService {
  Future<List<ClassModel>> getClasses() async {
    final data = await apiGet('/classes');
    final list = data['classes'] as List;
    return list.map((e) => ClassModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Map<String, dynamic>>> getMyClasses() async {
    final data = await apiGet('/classes/my-classes');
    return List<Map<String, dynamic>>.from(data['classes'] as List);
  }

  Future<Map<String, dynamic>> getClassDetail(String classId) async {
    final data = await apiGet('/classes/$classId');
    return data as Map<String, dynamic>;
  }

  Future<ClassModel> createClass({
    required String className,
    String? description,
    String? academicYear,
  }) async {
    final data = await apiPost('/classes', data: {
      'class_name': className,
      'description': description,
      'academic_year': academicYear,
    });
    return ClassModel.fromJson(data as Map<String, dynamic>);
  }

  Future<void> updateClass(String classId, Map<String, dynamic> fields) async {
    await apiPatch('/classes/$classId', data: fields);
  }

  Future<List<Map<String, dynamic>>> getStudents(String classId) async {
    final data = await apiGet('/classes/$classId/students');
    return List<Map<String, dynamic>>.from(data['students'] as List);
  }

  Future<List<Map<String, dynamic>>> getApprovals(String classId) async {
    final data = await apiGet('/classes/$classId/approvals');
    return List<Map<String, dynamic>>.from(data['pending'] as List);
  }

  Future<void> approveStudent(String classId, String studentId) async {
    await apiPatch('/classes/$classId/students/$studentId/approve', data: {});
  }

  Future<void> rejectStudent(String classId, String studentId, {String? reason}) async {
    await apiPatch('/classes/$classId/students/$studentId/reject', data: {
      'reason': reason,
    });
  }

  Future<void> addCoMentor(String classId, {required String fullName, required String email}) async {
    await apiPost('/classes/$classId/co-mentors', data: {
      'full_name': fullName,
      'email': email,
    });
  }
}

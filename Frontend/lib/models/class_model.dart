class ClassModel {
  final String id;
  final String className;
  final String? description;
  final String? academicYear;
  final String status;
  final int studentCount;
  final int mentorCount;
  final String createdAt;

  ClassModel({
    required this.id,
    required this.className,
    this.description,
    this.academicYear,
    required this.status,
    required this.studentCount,
    required this.mentorCount,
    required this.createdAt,
  });

  factory ClassModel.fromJson(Map<String, dynamic> j) => ClassModel(
        id: j['id'] as String? ?? '',
        className: j['class_name'] as String? ?? '',
        description: j['description'] as String?,
        academicYear: j['academic_year'] as String?,
        status: j['status'] as String? ?? 'ACTIVE',
        studentCount: (j['student_count'] as num?)?.toInt() ?? 0,
        mentorCount: (j['mentor_count'] as num?)?.toInt() ?? 0,
        createdAt: j['created_at'] as String? ?? '',
      );
}

class ClassStudentModel {
  final String id;
  final String fullName;
  final String email;
  final String registrationId;
  final String membershipStatus;
  final String riskLevel;
  final double completionRate;
  final String joinedVia;
  final DateTime joinedAt;

  ClassStudentModel({
    required this.id,
    required this.fullName,
    required this.email,
    required this.registrationId,
    required this.membershipStatus,
    required this.riskLevel,
    required this.completionRate,
    required this.joinedVia,
    required this.joinedAt,
  });

  factory ClassStudentModel.fromJson(Map<String, dynamic> j) =>
      ClassStudentModel(
        id: j['id'] as String,
        fullName: j['full_name'] as String,
        email: j['email'] as String,
        registrationId: j['registration_id'] as String,
        membershipStatus: j['membership_status'] as String,
        riskLevel: j['risk_level'] as String,
        completionRate: (j['completion_rate'] as num).toDouble(),
        joinedVia: j['joined_via'] as String,
        joinedAt: DateTime.parse(j['joined_at'] as String),
      );
}

class ApprovalModel {
  final String studentId;
  final String fullName;
  final String email;
  final String registrationId;
  final DateTime requestedAt;
  final String joinedVia;

  ApprovalModel({
    required this.studentId,
    required this.fullName,
    required this.email,
    required this.registrationId,
    required this.requestedAt,
    required this.joinedVia,
  });

  factory ApprovalModel.fromJson(Map<String, dynamic> j) => ApprovalModel(
        studentId: j['student_id'] as String,
        fullName: j['full_name'] as String,
        email: j['email'] as String,
        registrationId: j['registration_id'] as String,
        requestedAt: DateTime.parse(j['requested_at'] as String),
        joinedVia: j['joined_via'] as String,
      );
}

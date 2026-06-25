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
        id: j['id'] as String,
        className: j['class_name'] as String,
        description: j['description'] as String?,
        academicYear: j['academic_year'] as String?,
        status: j['status'] as String,
        studentCount: (j['student_count'] as num).toInt(),
        mentorCount: (j['mentor_count'] as num?)?.toInt() ?? 0,
        createdAt: j['created_at'] as String,
      );
}

class StudentSubmissionInfo {
  final bool submitted;
  final String? submissionId;
  final DateTime? submittedAt;
  final bool isLate;
  final int version;

  StudentSubmissionInfo({
    required this.submitted,
    this.submissionId,
    this.submittedAt,
    required this.isLate,
    required this.version,
  });

  factory StudentSubmissionInfo.fromJson(Map<String, dynamic> j) =>
      StudentSubmissionInfo(
        submitted: j['submitted'] as bool,
        submissionId: j['submission_id'] as String?,
        submittedAt: j['submitted_at'] != null
            ? DateTime.parse(j['submitted_at'] as String)
            : null,
        isLate: j['is_late'] as bool,
        version: (j['version'] as num).toInt(),
      );
}

class AssignmentModel {
  final String id;
  final String title;
  final String? description;
  final String contentType;
  final String? contentUrl;
  final String? richTextBody;
  final String submissionType;
  final DateTime? deadlineAt;
  final String status;
  final String classId;
  final String createdByName;
  final DateTime createdAt;
  final StudentSubmissionInfo? studentSubmission;
  final String? extensionStatus;
  final String? extensionReason;

  AssignmentModel({
    required this.id,
    required this.title,
    this.description,
    required this.contentType,
    this.contentUrl,
    this.richTextBody,
    required this.submissionType,
    this.deadlineAt,
    required this.status,
    required this.classId,
    required this.createdByName,
    required this.createdAt,
    this.studentSubmission,
    this.extensionStatus,
    this.extensionReason,
  });

  factory AssignmentModel.fromJson(Map<String, dynamic> j) => AssignmentModel(
        id: j['id'] as String,
        title: j['title'] as String,
        description: j['description'] as String?,
        contentType: j['content_type'] as String,
        contentUrl: j['content_url'] as String?,
        richTextBody: j['rich_text_body'] as String?,
        submissionType: j['submission_type'] as String,
        deadlineAt: j['deadline_at'] != null
            ? DateTime.parse(j['deadline_at'] as String)
            : null,
        status: j['status'] as String,
        classId: j['class_id'] as String,
        createdByName: j['created_by_name'] as String,
        createdAt: j['created_at'] != null
            ? DateTime.parse(j['created_at'] as String)
            : DateTime.now(),
        studentSubmission: j['student_submission'] != null
            ? StudentSubmissionInfo.fromJson(
                j['student_submission'] as Map<String, dynamic>)
            : null,
        extensionStatus: j['extension_status'] as String?,
        extensionReason: j['extension_reason'] as String?,
      );
}

class SubmissionModel {
  final String submissionId;
  final String assignmentId;
  final String assignmentTitle;
  final String submissionType;
  final DateTime submittedAt;
  final bool isLate;
  final int version;

  SubmissionModel({
    required this.submissionId,
    required this.assignmentId,
    required this.assignmentTitle,
    required this.submissionType,
    required this.submittedAt,
    required this.isLate,
    required this.version,
  });

  factory SubmissionModel.fromJson(Map<String, dynamic> j) => SubmissionModel(
        submissionId: j['submission_id'] as String,
        assignmentId: j['assignment_id'] as String,
        assignmentTitle: j['assignment_title'] as String,
        submissionType: j['submission_type'] as String,
        submittedAt: DateTime.parse(j['submitted_at'] as String),
        isLate: j['is_late'] as bool,
        version: (j['version'] as num).toInt(),
      );
}

class ExportJobModel {
  final String exportJobId;
  final String status;
  final String? fileUrl;

  ExportJobModel({
    required this.exportJobId,
    required this.status,
    this.fileUrl,
  });

  factory ExportJobModel.fromJson(Map<String, dynamic> j) => ExportJobModel(
        exportJobId: j['export_job_id'] as String,
        status: j['status'] as String,
        fileUrl: j['file_url'] as String?,
      );
}

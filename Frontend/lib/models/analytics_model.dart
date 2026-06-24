class AssignmentHistoryItem {
  final String assignmentId;
  final String title;
  final DateTime? deadlineAt;
  final String trackerStatus;
  final DateTime? submittedAt;
  final bool isLate;

  AssignmentHistoryItem({
    required this.assignmentId,
    required this.title,
    this.deadlineAt,
    required this.trackerStatus,
    this.submittedAt,
    required this.isLate,
  });

  factory AssignmentHistoryItem.fromJson(Map<String, dynamic> j) =>
      AssignmentHistoryItem(
        assignmentId: j['assignment_id'] as String,
        title: j['title'] as String,
        deadlineAt: j['deadline_at'] != null
            ? DateTime.parse(j['deadline_at'] as String)
            : null,
        trackerStatus: j['tracker_status'] as String,
        submittedAt: j['submitted_at'] != null
            ? DateTime.parse(j['submitted_at'] as String)
            : null,
        isLate: j['is_late'] as bool,
      );
}

class StudentAnalyticsModel {
  final String studentId;
  final String fullName;
  final String className;
  final int totalAssigned;
  final int totalSubmitted;
  final int totalMissed;
  final int totalLate;
  final double completionRate;
  final int currentStreak;
  final int longestStreak;
  final double? avgSubmissionDelayHours;
  final String riskLevel;
  final int consecutiveMisses;
  final double classAvgCompletion;
  final List<AssignmentHistoryItem> assignmentHistory;

  StudentAnalyticsModel({
    required this.studentId,
    required this.fullName,
    required this.className,
    required this.totalAssigned,
    required this.totalSubmitted,
    required this.totalMissed,
    required this.totalLate,
    required this.completionRate,
    required this.currentStreak,
    required this.longestStreak,
    this.avgSubmissionDelayHours,
    required this.riskLevel,
    required this.consecutiveMisses,
    required this.classAvgCompletion,
    required this.assignmentHistory,
  });

  factory StudentAnalyticsModel.fromJson(Map<String, dynamic> j) =>
      StudentAnalyticsModel(
        studentId: j['student_id'] as String,
        fullName: j['full_name'] as String,
        className: j['class_name'] as String,
        totalAssigned: (j['total_assigned'] as num).toInt(),
        totalSubmitted: (j['total_submitted'] as num).toInt(),
        totalMissed: (j['total_missed'] as num).toInt(),
        totalLate: (j['total_late'] as num).toInt(),
        completionRate: (j['completion_rate'] as num).toDouble(),
        currentStreak: (j['current_streak'] as num).toInt(),
        longestStreak: (j['longest_streak'] as num).toInt(),
        avgSubmissionDelayHours:
            (j['avg_submission_delay_hours'] as num?)?.toDouble(),
        riskLevel: j['risk_level'] as String,
        consecutiveMisses: (j['consecutive_misses'] as num).toInt(),
        classAvgCompletion: (j['class_avg_completion'] as num).toDouble(),
        assignmentHistory: (j['assignment_history'] as List)
            .map((e) => AssignmentHistoryItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class BottleneckAssignment {
  final String assignmentId;
  final String title;
  final double completionRate;

  BottleneckAssignment({
    required this.assignmentId,
    required this.title,
    required this.completionRate,
  });

  factory BottleneckAssignment.fromJson(Map<String, dynamic> j) =>
      BottleneckAssignment(
        assignmentId: j['assignment_id'] as String,
        title: j['title'] as String,
        completionRate: (j['completion_rate'] as num).toDouble(),
      );
}

class ClassAnalyticsModel {
  final String classId;
  final String className;
  final int totalStudents;
  final int totalAssignments;
  final double avgCompletion;
  final double avgMissRate;
  final double avgLateRate;
  final int highRiskCount;
  final List<BottleneckAssignment> bottleneckAssignments;
  final Map<String, int> riskDistribution;

  ClassAnalyticsModel({
    required this.classId,
    required this.className,
    required this.totalStudents,
    required this.totalAssignments,
    required this.avgCompletion,
    required this.avgMissRate,
    required this.avgLateRate,
    required this.highRiskCount,
    required this.bottleneckAssignments,
    required this.riskDistribution,
  });

  factory ClassAnalyticsModel.fromJson(Map<String, dynamic> j) =>
      ClassAnalyticsModel(
        classId: j['class_id'] as String,
        className: j['class_name'] as String,
        totalStudents: (j['total_students'] as num).toInt(),
        totalAssignments: (j['total_assignments'] as num).toInt(),
        avgCompletion: (j['avg_completion'] as num).toDouble(),
        avgMissRate: (j['avg_miss_rate'] as num).toDouble(),
        avgLateRate: (j['avg_late_rate'] as num).toDouble(),
        highRiskCount: (j['high_risk_count'] as num).toInt(),
        bottleneckAssignments: (j['bottleneck_assignments'] as List)
            .map((e) => BottleneckAssignment.fromJson(e as Map<String, dynamic>))
            .toList(),
        riskDistribution: Map<String, int>.from(
          (j['risk_distribution'] as Map).map(
            (k, v) => MapEntry(k as String, (v as num).toInt()),
          ),
        ),
      );
}

class TrackerStudent {
  final String studentId;
  final String fullName;
  final String registrationId;
  final String trackerStatus;
  final DateTime? submittedAt;
  final bool isLate;
  final String? submissionId;

  TrackerStudent({
    required this.studentId,
    required this.fullName,
    required this.registrationId,
    required this.trackerStatus,
    this.submittedAt,
    required this.isLate,
    this.submissionId,
  });

  factory TrackerStudent.fromJson(Map<String, dynamic> j) => TrackerStudent(
        studentId: j['student_id'] as String,
        fullName: j['full_name'] as String,
        registrationId: j['registration_id'] as String,
        trackerStatus: j['tracker_status'] as String,
        submittedAt: j['submitted_at'] != null
            ? DateTime.parse(j['submitted_at'] as String)
            : null,
        isLate: j['is_late'] as bool,
        submissionId: j['submission_id'] as String?,
      );
}

class TrackerModel {
  final String assignmentId;
  final String title;
  final DateTime? deadlineAt;
  final String status;
  final int submittedCount;
  final int pendingCount;
  final int missedCount;
  final int lateCount;
  final List<TrackerStudent> students;

  TrackerModel({
    required this.assignmentId,
    required this.title,
    this.deadlineAt,
    required this.status,
    required this.submittedCount,
    required this.pendingCount,
    required this.missedCount,
    required this.lateCount,
    required this.students,
  });

  factory TrackerModel.fromJson(Map<String, dynamic> j) => TrackerModel(
        assignmentId: j['assignment_id'] as String,
        title: j['title'] as String,
        deadlineAt: j['deadline_at'] != null
            ? DateTime.parse(j['deadline_at'] as String)
            : null,
        status: j['status'] as String,
        submittedCount: (j['submitted_count'] as num).toInt(),
        pendingCount: (j['pending_count'] as num).toInt(),
        missedCount: (j['missed_count'] as num).toInt(),
        lateCount: (j['late_count'] as num).toInt(),
        students: (j['students'] as List)
            .map((e) => TrackerStudent.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

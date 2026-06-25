import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/risk_badge_widget.dart';
import 'package:intl/intl.dart';

class AdminStudentProfileScreen extends ConsumerWidget {
  final String studentId;
  const AdminStudentProfileScreen({super.key, required this.studentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(studentAnalyticsProvider(studentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Student Profile')),
      body: analytics.when(
        loading: () => const LoadingWidget(message: 'Loading profile...'),
        error: (e, _) => AppErrorWidget(
          message: e.toString(),
          onRetry: () => ref.invalidate(studentAnalyticsProvider(studentId)),
        ),
        data: (a) {
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(studentAnalyticsProvider(studentId)),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // profile header
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 28,
                          backgroundColor: const Color(0xFF1A56DB).withOpacity(0.1),
                          child: Text(
                            a.fullName.isNotEmpty ? a.fullName[0].toUpperCase() : '?',
                            style: const TextStyle(fontSize: 22, color: Color(0xFF1A56DB), fontWeight: FontWeight.bold),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(a.fullName, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
                              const SizedBox(height: 2),
                              Text(a.className, style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
                              const SizedBox(height: 6),
                              RiskBadge(riskLevel: a.riskLevel),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // analytics summary cards
                const Text('Performance', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _statTile('Assigned', '${a.totalAssigned}', Colors.blue)),
                    const SizedBox(width: 8),
                    Expanded(child: _statTile('Submitted', '${a.totalSubmitted}', Colors.green)),
                    const SizedBox(width: 8),
                    Expanded(child: _statTile('Missed', '${a.totalMissed}', Colors.red)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _statTile('Late', '${a.totalLate}', Colors.orange)),
                    const SizedBox(width: 8),
                    Expanded(child: _statTile('Streak', '${a.currentStreak}🔥', Colors.purple)),
                    const SizedBox(width: 8),
                    Expanded(child: _statTile('Completion', '${a.completionRate.toStringAsFixed(0)}%', Colors.teal)),
                  ],
                ),

                if (a.avgSubmissionDelayHours != null) ...[
                  const SizedBox(height: 8),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      child: Row(
                        children: [
                          const Icon(Icons.access_time, size: 16, color: Color(0xFF6B7280)),
                          const SizedBox(width: 8),
                          Text(
                            'Avg submission delay: ${a.avgSubmissionDelayHours!.toStringAsFixed(1)} hrs',
                            style: const TextStyle(fontSize: 13, color: Color(0xFF374151)),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 16),

                // assignment history — NOT from /notifications, from analytics
                const Text('Assignment History', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                if (a.assignmentHistory.isEmpty)
                  const Text('No assignment history yet', style: TextStyle(fontSize: 13, color: Color(0xFF9CA3AF)))
                else
                  ...a.assignmentHistory.map((h) {
                    final statusColor = switch (h.trackerStatus) {
                      'SUBMITTED' => Colors.green.shade600,
                      'LATE' => Colors.orange.shade600,
                      'MISSED' => Colors.red.shade600,
                      _ => Colors.grey.shade500,
                    };
                    final deadlineStr = h.deadlineAt != null
                        ? DateFormat('d MMM yyyy').format(h.deadlineAt!.toLocal())
                        : 'No deadline';

                    return Card(
                      margin: const EdgeInsets.only(bottom: 6),
                      child: ListTile(
                        title: Text(h.title, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                        subtitle: Text(deadlineStr, style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                        trailing: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: statusColor.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(h.trackerStatus, style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600)),
                        ),
                      ),
                    );
                  }),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _statTile(String label, String val, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        children: [
          Text(val, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/assignment_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/analytics_chart_widget.dart';

class MentorAssignmentAnalyticsScreen extends ConsumerWidget {
  final String assignmentId;
  const MentorAssignmentAnalyticsScreen(
      {super.key, required this.assignmentId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tracker = ref.watch(trackerProvider(assignmentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Assignment Analytics')),
      body: tracker.when(
        loading: () => const LoadingWidget(message: 'Loading analytics...'),
        error: (e, _) => AppErrorWidget(
            message: e.toString(),
            onRetry: () => ref.invalidate(trackerProvider(assignmentId))),
        data: (data) {
          int submitted = 0, pending = 0, missed = 0, late = 0;
          for (var s in data.students) {
            switch (s.trackerStatus) {
              case 'SUBMITTED':
                submitted++;
                break;
              case 'PENDING':
                pending++;
                break;
              case 'MISSED':
                missed++;
                break;
              case 'LATE':
                late++;
                break;
            }
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const Text('Submission Status Distribution',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 16),
                      StatusDonutChart(
                          submitted: submitted,
                          pending: pending,
                          missed: missed,
                          late: late),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                      child: _stat('Submitted', '$submitted', Colors.green)),
                  Expanded(child: _stat('Pending', '$pending', Colors.grey)),
                  Expanded(child: _stat('Missed', '$missed', Colors.red)),
                  Expanded(child: _stat('Late', '$late', Colors.orange)),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _stat(String label, String val, Color color) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8)),
      child: Column(
        children: [
          Text(val,
              style: TextStyle(
                  fontSize: 18, fontWeight: FontWeight.bold, color: color)),
          Text(label,
              style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
        ],
      ),
    );
  }
}

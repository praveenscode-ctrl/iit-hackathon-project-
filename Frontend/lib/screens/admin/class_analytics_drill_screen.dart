import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/risk_badge_widget.dart';
import '../../widgets/analytics_chart_widget.dart';

class ClassAnalyticsDrillScreen extends ConsumerWidget {
  final String classId;
  const ClassAnalyticsDrillScreen({super.key, required this.classId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final classAnalytics = ref.watch(classAnalyticsProvider(classId));
    final studentsAnalytics =
        ref.watch(classStudentsAnalyticsProvider(classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Class Analytics')),
      body: classAnalytics.when(
        loading: () => const LoadingWidget(message: 'Loading analytics...'),
        error: (e, _) => AppErrorWidget(
            message: e.toString(),
            onRetry: () => ref.invalidate(classAnalyticsProvider(classId))),
        data: (a) => RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(classAnalyticsProvider(classId));
            ref.invalidate(classStudentsAnalyticsProvider(classId));
          },
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // class summary
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(a.className,
                          style: const TextStyle(
                              fontSize: 17, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                              child: _stat('Students', '${a.totalStudents}',
                                  Colors.blue)),
                          Expanded(
                              child: _stat('Assignments',
                                  '${a.totalAssignments}', Colors.teal)),
                          Expanded(
                              child: _stat('High Risk', '${a.highRiskCount}',
                                  Colors.red)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                              child: _stat(
                                  'Completion',
                                  '${a.avgCompletion.toStringAsFixed(1)}%',
                                  Colors.green)),
                          Expanded(
                              child: _stat(
                                  'Miss Rate',
                                  '${a.avgMissRate.toStringAsFixed(1)}%',
                                  Colors.orange)),
                          Expanded(
                              child: _stat(
                                  'Late Rate',
                                  '${a.avgLateRate.toStringAsFixed(1)}%',
                                  Colors.purple)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // risk distribution if available
              if (a.riskDistribution.isNotEmpty) ...[
                const Text('Risk Distribution',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      children: a.riskDistribution.entries
                          .map((e) => Padding(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 4),
                                child: Row(
                                  children: [
                                    RiskBadge(riskLevel: e.key),
                                    const Spacer(),
                                    Text('${e.value} students',
                                        style: const TextStyle(
                                            fontSize: 13,
                                            color: Color(0xFF374151))),
                                  ],
                                ),
                              ))
                          .toList(),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // bottleneck assignments
              if (a.bottleneckAssignments.isNotEmpty) ...[
                const Text('Bottleneck Assignments',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                const Text('Assignments with lowest completion rates',
                    style: TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                const SizedBox(height: 8),
                ...a.bottleneckAssignments.map((b) => Card(
                      margin: const EdgeInsets.only(bottom: 6),
                      child: ListTile(
                        title: Text(b.title,
                            style: const TextStyle(
                                fontWeight: FontWeight.w500, fontSize: 14)),
                        trailing: Text(
                            '${b.completionRate.toStringAsFixed(1)}%',
                            style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.red)),
                      ),
                    )),
                const SizedBox(height: 16),
              ],

              // student breakdown
              const Text('Student Breakdown',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              studentsAnalytics.when(
                loading: () => const LoadingWidget(),
                error: (_, __) => const Text('Could not load student data',
                    style: TextStyle(color: Color(0xFF9CA3AF))),
                data: (list) {
                  if (list.isEmpty)
                    return const Text('No students',
                        style: TextStyle(color: Color(0xFF9CA3AF)));
                  return Column(
                    children: list.map((s) {
                      final name = s['full_name'] as String? ?? '';
                      final risk = s['risk_level'] as String? ?? 'NORMAL';
                      final completion =
                          (s['completion_rate'] as num?)?.toDouble() ?? 0.0;
                      final studentId = s['student_id'] as String? ?? '';
                      return Card(
                        margin: const EdgeInsets.only(bottom: 6),
                        child: ListTile(
                          title: Text(name,
                              style: const TextStyle(
                                  fontWeight: FontWeight.w500, fontSize: 14)),
                          subtitle: Text(
                              '${completion.toStringAsFixed(0)}% completion'),
                          trailing: RiskBadge(riskLevel: risk),
                          onTap: studentId.isNotEmpty
                              ? () => context.push('/admin/students/$studentId')
                              : null,
                        ),
                      );
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _stat(String label, String val, Color color) {
    return Column(
      children: [
        Text(val,
            style: TextStyle(
                fontSize: 15, fontWeight: FontWeight.bold, color: color)),
        Text(label,
            style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
      ],
    );
  }
}

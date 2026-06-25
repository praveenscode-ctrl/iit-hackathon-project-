import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/analytics_provider.dart';
import '../../providers/class_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/analytics_chart_widget.dart';

class AnalyticsOverviewScreen extends ConsumerWidget {
  const AnalyticsOverviewScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overview = ref.watch(adminOverviewProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Analytics Overview')),
      body: overview.when(
        loading: () => const LoadingWidget(message: 'Loading analytics...'),
        error: (e, _) => AppErrorWidget(message: e.toString(), onRetry: () => ref.invalidate(adminOverviewProvider)),
        data: (data) {
          final totalClasses = data['total_classes'] ?? 0;
          final totalStudents = data['total_students'] ?? 0;
          final highRisk = data['total_high_risk_students'] ?? 0;
          final avgCompletion = (data['avg_completion_rate'] as num?)?.toDouble() ?? 0.0;
          final classesList = data['classes'] as List? ?? [];

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(adminOverviewProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // institution cards
                const Text('Institution Overview', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: _card('Total Classes', '$totalClasses', Icons.school_outlined, Colors.blue)),
                    const SizedBox(width: 10),
                    Expanded(child: _card('Total Students', '$totalStudents', Icons.people_outline, Colors.teal)),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: _card('High Risk', '$highRisk', Icons.warning_amber_outlined, Colors.red)),
                    const SizedBox(width: 10),
                    Expanded(child: _card('Avg Completion', '${avgCompletion.toStringAsFixed(1)}%', Icons.check_circle_outline, Colors.green)),
                  ],
                ),

                if (classesList.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  const Text('Class Completion', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: CompletionBarChart(
                        labels: classesList.map((c) => c['class_name'] as String).toList(),
                        values: classesList.map((c) => (c['avg_completion'] as num?)?.toDouble() ?? 0.0).toList(),
                        caption: 'avg_completion per class — from GET /analytics/admin/overview',
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),
                  const Text('Miss Rate by Class', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: CompletionBarChart(
                        labels: classesList.map((c) => c['class_name'] as String).toList(),
                        values: classesList.map((c) => (c['avg_miss_rate'] as num?)?.toDouble() ?? 0.0).toList(),
                        caption: 'avg_miss_rate per class — from GET /analytics/admin/overview',
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),
                  const Text('Drill Down by Class', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  ...classesList.map((c) {
                    final classId = c['class_id'] as String? ?? '';
                    final className = c['class_name'] as String? ?? '';
                    final highRiskCount = c['high_risk_count'] ?? 0;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(className, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text('$highRiskCount high risk students'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: classId.isNotEmpty ? () => context.push('/admin/analytics/$classId') : null,
                      ),
                    );
                  }),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _card(String label, String val, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 5)]),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 10),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(val, style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: color)),
            Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
          ]),
        ],
      ),
    );
  }
}

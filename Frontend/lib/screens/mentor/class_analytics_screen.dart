import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

class MentorClassAnalyticsScreen extends ConsumerWidget {
  final String classId;
  const MentorClassAnalyticsScreen({super.key, required this.classId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(classAnalyticsProvider(classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Class Analytics')),
      body: analytics.when(
        loading: () =>
            const LoadingWidget(message: 'Loading class analytics...'),
        error: (e, _) => AppErrorWidget(
            message: e.toString(),
            onRetry: () => ref.invalidate(classAnalyticsProvider(classId))),
        data: (a) {
          return RefreshIndicator(
            onRefresh: () async =>
                ref.invalidate(classAnalyticsProvider(classId)),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(a.className,
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 16),
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
                                    Colors.red)),
                            Expanded(
                                child: _stat(
                                    'Late Rate',
                                    '${a.avgLateRate.toStringAsFixed(1)}%',
                                    Colors.orange)),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('Bottleneck Assignments',
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                if (a.bottleneckAssignments.isEmpty)
                  const Text('No bottlenecks detected',
                      style: TextStyle(color: Color(0xFF9CA3AF)))
                else
                  ...a.bottleneckAssignments.map((b) => Card(
                        child: ListTile(
                          title: Text(b.title),
                          trailing: Text(
                              '${b.completionRate.toStringAsFixed(1)}%',
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.red)),
                        ),
                      )),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _stat(String label, String val, Color color) {
    return Column(
      children: [
        Text(val,
            style: TextStyle(
                fontSize: 18, fontWeight: FontWeight.bold, color: color)),
        Text(label,
            style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280))),
      ],
    );
  }
}

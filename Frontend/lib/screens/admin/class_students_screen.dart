import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/class_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/risk_badge_widget.dart';

class ClassStudentsScreen extends ConsumerWidget {
  final String classId;
  const ClassStudentsScreen({super.key, required this.classId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(classStudentsProvider(classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Students')),
      body: students.when(
        loading: () => const LoadingWidget(message: 'Loading students...'),
        error: (e, _) => AppErrorWidget(
          message: e.toString(),
          onRetry: () => ref.invalidate(classStudentsProvider(classId)),
        ),
        data: (list) {
          if (list.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.people_outline, size: 56, color: Color(0xFFD1D5DB)),
                  SizedBox(height: 12),
                  Text('No students in this class', style: TextStyle(fontSize: 15, color: Color(0xFF9CA3AF))),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(classStudentsProvider(classId)),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final s = list[i];
                final name = s['full_name'] as String? ?? '';
                final regId = s['registration_id'] as String? ?? '';
                final membershipStatus = s['membership_status'] as String? ?? '';
                final riskLevel = s['risk_level'] as String? ?? 'NORMAL';
                final completion = (s['completion_rate'] as num?)?.toDouble() ?? 0.0;
                final studentId = s['student_id'] as String? ?? '';

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: const Color(0xFF1A56DB).withOpacity(0.1),
                      child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Color(0xFF1A56DB), fontWeight: FontWeight.bold)),
                    ),
                    title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(regId, style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: membershipStatus == 'APPROVED' ? Colors.green.shade50 : Colors.orange.shade50,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(membershipStatus, style: TextStyle(fontSize: 10, color: membershipStatus == 'APPROVED' ? Colors.green.shade700 : Colors.orange.shade700)),
                            ),
                            const SizedBox(width: 8),
                            Text('${completion.toStringAsFixed(0)}%', style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
                          ],
                        ),
                      ],
                    ),
                    trailing: RiskBadge(riskLevel: riskLevel),
                    onTap: studentId.isNotEmpty ? () => context.push('/admin/students/$studentId') : null,
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

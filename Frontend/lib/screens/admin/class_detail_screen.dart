import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/class_provider.dart';
import '../../providers/analytics_provider.dart';
import '../../services/class_service.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

class ClassDetailScreen extends ConsumerStatefulWidget {
  final String classId;
  const ClassDetailScreen({super.key, required this.classId});

  @override
  ConsumerState<ClassDetailScreen> createState() => _ClassDetailScreenState();
}

class _ClassDetailScreenState extends ConsumerState<ClassDetailScreen> {
  final _svc = ClassService();

  Future<void> _archiveClass() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Archive Class'),
        content: const Text('This will archive the class. Students will no longer have access. Continue?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Archive', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _svc.updateClass(widget.classId, {'status': 'ARCHIVED'});
      ref.invalidate(classDetailProvider(widget.classId));
      ref.invalidate(classListProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Class archived')));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(classDetailProvider(widget.classId));
    final analytics = ref.watch(classAnalyticsProvider(widget.classId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Class Detail'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (val) {
              if (val == 'archive') _archiveClass();
              if (val == 'co-mentor') context.push('/admin/classes/${widget.classId}/co-mentor');
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'co-mentor', child: Text('Add Co-Mentor')),
              const PopupMenuItem(value: 'archive', child: Text('Archive Class', style: TextStyle(color: Colors.red))),
            ],
          ),
        ],
      ),
      body: detail.when(
        loading: () => const LoadingWidget(message: 'Loading class...'),
        error: (e, _) => AppErrorWidget(message: e.toString(), onRetry: () => ref.invalidate(classDetailProvider(widget.classId))),
        data: (data) {
          final className = data['class_name'] as String? ?? '';
          final description = data['description'] as String?;
          final academicYear = data['academic_year'] as String?;
          final status = data['status'] as String? ?? '';
          final mentors = data['mentors'] as List? ?? [];

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(classDetailProvider(widget.classId));
              ref.invalidate(classAnalyticsProvider(widget.classId));
            },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // class header card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(child: Text(className, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold))),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: status == 'ACTIVE' ? Colors.green.shade50 : Colors.grey.shade100,
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(status, style: TextStyle(fontSize: 11, color: status == 'ACTIVE' ? Colors.green.shade700 : Colors.grey.shade600, fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ),
                        if (description != null) ...[
                          const SizedBox(height: 8),
                          Text(description, style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
                        ],
                        if (academicYear != null) ...[
                          const SizedBox(height: 4),
                          Text('Academic Year: $academicYear', style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                // mentors section
                if (mentors.isNotEmpty) ...[
                  const Text('Mentors', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  ...mentors.map((m) => Card(
                    margin: const EdgeInsets.only(bottom: 6),
                    child: ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.person)),
                      title: Text(m['full_name'] as String? ?? ''),
                      subtitle: Text(m['email'] as String? ?? ''),
                    ),
                  )),
                  const SizedBox(height: 12),
                ],

                // quick nav actions
                const Text('Manage', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _navCard(context, 'Students', Icons.people_outline, () => context.push('/admin/classes/${widget.classId}/students'))),
                    const SizedBox(width: 10),
                    Expanded(child: _navCard(context, 'Approvals', Icons.how_to_reg_outlined, () => context.push('/admin/classes/${widget.classId}/approvals'))),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: _navCard(context, 'Analytics', Icons.bar_chart, () => context.push('/admin/analytics/${widget.classId}'))),
                    const SizedBox(width: 10),
                    Expanded(child: _navCard(context, 'Bulk Import', Icons.upload_file_outlined, () => context.push('/admin/bulk-import'))),
                  ],
                ),

                const SizedBox(height: 16),

                // analytics preview
                analytics.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (a) => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Analytics Snapshot', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(child: _miniStat('Completion', '${a.avgCompletion.toStringAsFixed(1)}%', Colors.green)),
                          const SizedBox(width: 10),
                          Expanded(child: _miniStat('Miss Rate', '${a.avgMissRate.toStringAsFixed(1)}%', Colors.red)),
                          const SizedBox(width: 10),
                          Expanded(child: _miniStat('High Risk', '${a.highRiskCount}', Colors.orange)),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _navCard(BuildContext context, String label, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Column(
          children: [
            Icon(icon, color: const Color(0xFF1A56DB), size: 22),
            const SizedBox(height: 6),
            Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFF374151))),
          ],
        ),
      ),
    );
  }

  Widget _miniStat(String label, String val, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        children: [
          Text(val, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: color)),
          Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
        ],
      ),
    );
  }
}

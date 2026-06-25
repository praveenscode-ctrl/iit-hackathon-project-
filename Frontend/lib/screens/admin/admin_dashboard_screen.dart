import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/analytics_provider.dart';
import '../../providers/notification_provider.dart';
import '../../providers/class_provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/analytics_chart_widget.dart';
import '../../widgets/notification_tile_widget.dart';
import '../../services/auth_service.dart';
import '../../core/auth_storage.dart';

class AdminDashboardScreen extends ConsumerStatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  ConsumerState<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends ConsumerState<AdminDashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(notificationsProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final overview = ref.watch(adminOverviewProvider);
    final classes = ref.watch(classListProvider);
    final notifs = ref.watch(notificationsProvider);
    final user = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Dashboard'),
        actions: [
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () {},
              ),
              if (ref.read(notificationsProvider.notifier).unreadCount > 0)
                Positioned(
                  right: 8, top: 8,
                  child: Container(
                    width: 8, height: 8,
                    decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(adminOverviewProvider);
          ref.invalidate(classListProvider);
          ref.read(notificationsProvider.notifier).load();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // greeting
            Text(
              'Hi, ${user?.fullName ?? 'Admin'} 👋',
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF111827)),
            ),
            const SizedBox(height: 4),
            const Text('Here\'s your institution overview', style: TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
            const SizedBox(height: 20),

            // overview stats
            overview.when(
              loading: () => const LoadingWidget(message: 'Loading overview...'),
              error: (e, _) => AppErrorWidget(message: e.toString(), onRetry: () => ref.invalidate(adminOverviewProvider)),
              data: (data) => _buildOverviewSection(context, data),
            ),

            const SizedBox(height: 20),

            // quick actions
            _buildQuickActions(context),

            const SizedBox(height: 20),

            // class list summary
            classes.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (cls) {
                if (cls.isEmpty) return const SizedBox.shrink();
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Classes', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                        TextButton(onPressed: () => context.push('/admin/classes'), child: const Text('View all')),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...cls.take(3).map((c) => Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(c.className, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text('${c.studentCount} students · ${c.mentorCount} mentors'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/admin/classes/${c.id}'),
                      ),
                    )),
                  ],
                );
              },
            ),

            const SizedBox(height: 20),

            // recent notifications
            const Text('Recent Notifications', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            notifs.when(
              loading: () => const LoadingWidget(),
              error: (_, __) => const Text('Could not load notifications', style: TextStyle(color: Color(0xFF9CA3AF))),
              data: (list) {
                if (list.isEmpty) return const Text('No notifications yet', style: TextStyle(color: Color(0xFF9CA3AF), fontSize: 13));
                return Card(
                  child: Column(
                    children: list.take(5).map((n) => NotificationTile(
                      notification: n,
                      onTap: () => ref.read(notificationsProvider.notifier).markRead(n.id),
                    )).toList(),
                  ),
                );
              },
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: const Color(0xFF1A56DB),
        onPressed: () => context.push('/admin/classes/new'),
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  Widget _buildOverviewSection(BuildContext context, Map<String, dynamic> data) {
    final totalClasses = data['total_classes'] ?? 0;
    final totalStudents = data['total_students'] ?? 0;
    final highRiskTotal = data['total_high_risk_students'] ?? 0;
    final avgCompletion = (data['avg_completion_rate'] as num?)?.toDouble() ?? 0.0;
    final classesList = data['classes'] as List? ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: _statCard('Classes', '$totalClasses', Icons.school_outlined, Colors.blue)),
            const SizedBox(width: 12),
            Expanded(child: _statCard('Students', '$totalStudents', Icons.people_outline, Colors.teal)),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _statCard('High Risk', '$highRiskTotal', Icons.warning_amber_outlined, Colors.red)),
            const SizedBox(width: 12),
            Expanded(child: _statCard('Avg Completion', '${avgCompletion.toStringAsFixed(1)}%', Icons.check_circle_outline, Colors.green)),
          ],
        ),
        if (classesList.isNotEmpty) ...[
          const SizedBox(height: 20),
          const Text('Class Completion Comparison', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          CompletionBarChart(
            labels: classesList.map((c) => c['class_name'] as String).toList(),
            values: classesList.map((c) => (c['avg_completion'] as num?)?.toDouble() ?? 0.0).toList(),
            caption: 'Average assignment completion rate per class (from backend analytics)',
          ),
        ],
      ],
    );
  }

  Widget _statCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 6, offset: const Offset(0, 2))],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF111827))),
                Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280), overflow: TextOverflow.ellipsis)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Quick Actions', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: _actionBtn(context, 'Classes', Icons.school_outlined, '/admin/classes')),
            const SizedBox(width: 10),
            Expanded(child: _actionBtn(context, 'Analytics', Icons.bar_chart, '/admin/analytics')),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: _actionBtn(context, 'Bulk Import', Icons.upload_file_outlined, '/admin/bulk-import')),
            const SizedBox(width: 10),
            Expanded(child: _actionBtn(context, 'AI Query', Icons.psychology_outlined, '/admin/ai')),
          ],
        ),
      ],
    );
  }

  Widget _actionBtn(BuildContext context, String label, IconData icon, String route) {
    return GestureDetector(
      onTap: () => context.push(route),
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
}

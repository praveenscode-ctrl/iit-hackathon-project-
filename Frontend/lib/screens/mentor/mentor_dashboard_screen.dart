import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notification_provider.dart';
import '../../providers/class_provider.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/notification_tile_widget.dart';

class MentorDashboardScreen extends ConsumerStatefulWidget {
  const MentorDashboardScreen({super.key});

  @override
  ConsumerState<MentorDashboardScreen> createState() => _MentorDashboardScreenState();
}

class _MentorDashboardScreenState extends ConsumerState<MentorDashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(notificationsProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider);
    final myClasses = ref.watch(myClassesProvider);
    final notifs = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mentor Dashboard'),
        actions: [
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
          ref.invalidate(myClassesProvider);
          ref.read(notificationsProvider.notifier).load();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Hi, ${user?.fullName ?? 'Mentor'} 👋',
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF111827)),
            ),
            const SizedBox(height: 4),
            const Text('Manage your classes and assignments', style: TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
            const SizedBox(height: 20),

            const Text('My Classes', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            myClasses.when(
              loading: () => const LoadingWidget(message: 'Loading classes...'),
              error: (e, _) => TextButton(onPressed: () => ref.invalidate(myClassesProvider), child: const Text('Retry')),
              data: (list) {
                if (list.isEmpty) return const Text('No classes assigned yet', style: TextStyle(color: Color(0xFF9CA3AF), fontSize: 13));
                return Column(
                  children: list.map((c) {
                    final classId = c['id'] as String? ?? c['class_id'] as String? ?? '';
                    final className = c['class_name'] as String? ?? '';
                    final studentCount = c['student_count'] ?? 0;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: const Icon(Icons.school_outlined, color: Color(0xFF1A56DB)),
                        title: Text(className, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text('$studentCount students'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: classId.isNotEmpty ? () => _openClassMenu(context, classId, className) : null,
                      ),
                    );
                  }).toList(),
                );
              },
            ),

            const SizedBox(height: 20),
            const Text('Recent Alerts', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            notifs.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (list) {
                if (list.isEmpty) return const Text('No notifications', style: TextStyle(color: Color(0xFF9CA3AF), fontSize: 13));
                return Card(
                  child: Column(
                    children: list.take(4).map((n) => NotificationTile(
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
    );
  }

  void _openClassMenu(BuildContext context, String classId, String className) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Text(className, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
            const Divider(),
            ListTile(leading: const Icon(Icons.people_outline), title: const Text('Students'), onTap: () { Navigator.pop(context); context.push('/mentor/classes/$classId/students'); }),
            ListTile(leading: const Icon(Icons.how_to_reg_outlined), title: const Text('Approvals'), onTap: () { Navigator.pop(context); context.push('/mentor/classes/$classId/approvals'); }),
            ListTile(leading: const Icon(Icons.assignment_outlined), title: const Text('Assignments'), onTap: () { Navigator.pop(context); context.push('/mentor/classes/$classId/assignments'); }),
            ListTile(leading: const Icon(Icons.bar_chart), title: const Text('Analytics'), onTap: () { Navigator.pop(context); context.push('/mentor/classes/$classId/analytics'); }),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/analytics_provider.dart';
import '../../providers/assignment_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/risk_badge_widget.dart';
import '../../widgets/assignment_card_widget.dart';
import '../../widgets/notification_tile_widget.dart';

class StudentDashboardScreen extends ConsumerStatefulWidget {
  const StudentDashboardScreen({super.key});

  @override
  ConsumerState<StudentDashboardScreen> createState() => _StudentDashboardScreenState();
}

class _StudentDashboardScreenState extends ConsumerState<StudentDashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(notificationsProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider);
    if (user == null) return const SizedBox.shrink();

    final analytics = ref.watch(studentAnalyticsProvider(user.id));
    final assignments = user.classId != null ? ref.watch(assignmentsProvider(user.classId!)) : null;
    final notifs = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Dashboard'),
        actions: [
          Stack(
            children: [
              IconButton(icon: const Icon(Icons.notifications_outlined), onPressed: () {}),
              if (ref.read(notificationsProvider.notifier).unreadCount > 0)
                Positioned(right: 8, top: 8, child: Container(width: 8, height: 8, decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle))),
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
          ref.invalidate(studentAnalyticsProvider(user.id));
          if (user.classId != null) ref.invalidate(assignmentsProvider(user.classId!));
          ref.read(notificationsProvider.notifier).load();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Hi, ${user.fullName} 👋', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF111827))),
            const SizedBox(height: 20),

            // Profile snapshot
            analytics.when(
              loading: () => const LoadingWidget(message: 'Loading profile...'),
              error: (e, _) => AppErrorWidget(message: e.toString(), onRetry: () => ref.invalidate(studentAnalyticsProvider(user.id))),
              data: (a) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Your Performance', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                          RiskBadge(riskLevel: a.riskLevel),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(child: _stat('Completion', '${a.completionRate.toStringAsFixed(0)}%', Colors.green)),
                          Expanded(child: _stat('Streak', '${a.currentStreak}🔥', Colors.purple)),
                          Expanded(child: _stat('Late', '${a.totalLate}', Colors.orange)),
                        ],
                      ),
                      const SizedBox(height: 16),
                      OutlinedButton(
                        onPressed: () => context.push('/student/analytics'),
                        style: OutlinedButton.styleFrom(minimumSize: const Size(double.infinity, 40)),
                        child: const Text('View Full Analytics'),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Pending Assignments', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                TextButton(onPressed: () => context.push('/student/submissions'), child: const Text('Past Submissions')),
              ],
            ),
            const SizedBox(height: 8),

            // Pending assignments
            if (user.classId == null)
              const Text('You are not assigned to a class yet.', style: TextStyle(color: Color(0xFF9CA3AF)))
            else if (assignments != null)
              assignments.when(
                loading: () => const LoadingWidget(),
                error: (e, _) => Text(e.toString(), style: const TextStyle(color: Colors.red)),
                data: (list) {
                  final pending = list.where((a) => a.status == 'PUBLISHED').toList();
                  if (pending.isEmpty) return const Text('Hooray! No pending assignments.', style: TextStyle(color: Color(0xFF9CA3AF)));
                  return Column(
                    children: pending.map((a) => AssignmentCard(
                      assignment: a,
                      onTap: () => context.push('/student/assignments/${a.id}'),
                    )).toList(),
                  );
                },
              ),

            const SizedBox(height: 24),
            const Text('Recent Alerts', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            notifs.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (list) {
                if (list.isEmpty) return const Text('No notifications', style: TextStyle(color: Color(0xFF9CA3AF), fontSize: 13));
                return Card(
                  child: Column(
                    children: list.take(3).map((n) => NotificationTile(
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

  Widget _stat(String label, String val, Color color) => Column(children: [
    Text(val, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
    Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280))),
  ]);
}

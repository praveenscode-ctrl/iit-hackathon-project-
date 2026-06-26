import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/class_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';

class ClassListScreen extends ConsumerWidget {
  const ClassListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final classes = ref.watch(classListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Classes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context.push('/admin/classes/new'),
          ),
        ],
      ),
      body: classes.when(
        loading: () => const LoadingWidget(message: 'Loading classes...'),
        error: (e, _) => AppErrorWidget(
          message: e.toString(),
          onRetry: () => ref.invalidate(classListProvider),
        ),
        data: (list) {
          if (list.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.school_outlined,
                      size: 56, color: Color(0xFFD1D5DB)),
                  SizedBox(height: 12),
                  Text('No classes yet',
                      style: TextStyle(fontSize: 15, color: Color(0xFF9CA3AF))),
                  SizedBox(height: 4),
                  Text('Tap + to create one',
                      style: TextStyle(fontSize: 13, color: Color(0xFFD1D5DB))),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(classListProvider),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final c = list[i];
                return Card(
                  margin:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
                  child: ListTile(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    title: Text(c.className,
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 15)),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (c.academicYear != null)
                          Text(c.academicYear!,
                              style: const TextStyle(
                                  fontSize: 12, color: Color(0xFF9CA3AF))),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.people_outline,
                                size: 13, color: Color(0xFF6B7280)),
                            const SizedBox(width: 4),
                            Text('${c.studentCount} students',
                                style: const TextStyle(
                                    fontSize: 12, color: Color(0xFF6B7280))),
                            const SizedBox(width: 12),
                            const Icon(Icons.person_outline,
                                size: 13, color: Color(0xFF6B7280)),
                            const SizedBox(width: 4),
                            Text('${c.mentorCount} mentors',
                                style: const TextStyle(
                                    fontSize: 12, color: Color(0xFF6B7280))),
                          ],
                        ),
                      ],
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: c.status == 'ACTIVE'
                                ? Colors.green.shade50
                                : Colors.grey.shade100,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            c.status,
                            style: TextStyle(
                              fontSize: 11,
                              color: c.status == 'ACTIVE'
                                  ? Colors.green.shade700
                                  : Colors.grey.shade600,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Icon(Icons.chevron_right,
                            color: Color(0xFF9CA3AF)),
                      ],
                    ),
                    onTap: () => context.push('/admin/classes/${c.id}'),
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

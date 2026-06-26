import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/assignment_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/assignment_card_widget.dart';

class MentorAssignmentListScreen extends ConsumerStatefulWidget {
  final String classId;
  const MentorAssignmentListScreen({super.key, required this.classId});

  @override
  ConsumerState<MentorAssignmentListScreen> createState() =>
      _MentorAssignmentListScreenState();
}

class _MentorAssignmentListScreenState
    extends ConsumerState<MentorAssignmentListScreen> {
  String _filter = 'ALL';

  @override
  Widget build(BuildContext context) {
    final assignments = ref.watch(assignmentsProvider(widget.classId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Assignments'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context
                .push('/mentor/classes/${widget.classId}/assignments/new'),
          ),
        ],
      ),
      body: Column(
        children: [
          // filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: ['ALL', 'DRAFT', 'PUBLISHED', 'CLOSED']
                  .map((f) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(f),
                          selected: _filter == f,
                          onSelected: (_) => setState(() => _filter = f),
                          selectedColor:
                              const Color(0xFF1A56DB).withOpacity(0.15),
                        ),
                      ))
                  .toList(),
            ),
          ),
          Expanded(
            child: assignments.when(
              loading: () =>
                  const LoadingWidget(message: 'Loading assignments...'),
              error: (e, _) => AppErrorWidget(
                  message: e.toString(),
                  onRetry: () =>
                      ref.invalidate(assignmentsProvider(widget.classId))),
              data: (list) {
                final filtered = _filter == 'ALL'
                    ? list
                    : list.where((a) => a.status == _filter).toList();
                if (filtered.isEmpty) {
                  return Center(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.assignment_outlined,
                        size: 56, color: Color(0xFFD1D5DB)),
                    const SizedBox(height: 12),
                    Text(
                        _filter == 'ALL'
                            ? 'No assignments yet'
                            : 'No ${_filter.toLowerCase()} assignments',
                        style: const TextStyle(
                            fontSize: 15, color: Color(0xFF9CA3AF))),
                  ]));
                }
                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(assignmentsProvider(widget.classId)),
                  child: ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (_, i) => AssignmentCard(
                      assignment: filtered[i],
                      onTap: () => context.push(
                          '/mentor/assignments/${filtered[i].id}/tracker'),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

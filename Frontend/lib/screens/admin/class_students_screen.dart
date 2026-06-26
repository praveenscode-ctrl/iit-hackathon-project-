import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/class_provider.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/risk_badge_widget.dart';

class ClassStudentsScreen extends ConsumerStatefulWidget {
  final String classId;
  const ClassStudentsScreen({super.key, required this.classId});

  @override
  ConsumerState<ClassStudentsScreen> createState() =>
      _ClassStudentsScreenState();
}

class _ClassStudentsScreenState extends ConsumerState<ClassStudentsScreen> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final students = ref.watch(classStudentsProvider(widget.classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Students')),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              controller: _searchCtrl,
              onChanged: (val) =>
                  setState(() => _query = val.trim().toLowerCase()),
              decoration: InputDecoration(
                hintText: 'Search by name, email or reg. no.',
                hintStyle:
                    const TextStyle(fontSize: 13, color: Color(0xFF9CA3AF)),
                prefixIcon: const Icon(Icons.search, color: Color(0xFF9CA3AF)),
                suffixIcon: _query.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 20),
                        onPressed: () {
                          _searchCtrl.clear();
                          setState(() => _query = '');
                        },
                      )
                    : null,
                filled: true,
                fillColor: Colors.white,
                contentPadding:
                    const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFE5E7EB))),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFE5E7EB))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        const BorderSide(color: Color(0xFF1A56DB), width: 1.5)),
              ),
            ),
          ),
          // Student List
          Expanded(
            child: students.when(
              loading: () =>
                  const LoadingWidget(message: 'Loading students...'),
              error: (e, _) => AppErrorWidget(
                message: e.toString(),
                onRetry: () =>
                    ref.invalidate(classStudentsProvider(widget.classId)),
              ),
              data: (list) {
                final filtered = _query.isEmpty
                    ? list
                    : list.where((s) {
                        final name =
                            (s['full_name'] as String? ?? '').toLowerCase();
                        final email =
                            (s['email'] as String? ?? '').toLowerCase();
                        final regId = (s['registration_id'] as String? ?? '')
                            .toLowerCase();
                        return name.contains(_query) ||
                            email.contains(_query) ||
                            regId.contains(_query);
                      }).toList();

                if (filtered.isEmpty) {
                  return Center(
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(
                          _query.isNotEmpty
                              ? Icons.search_off
                              : Icons.people_outline,
                          size: 56,
                          color: const Color(0xFFD1D5DB)),
                      const SizedBox(height: 12),
                      Text(
                        _query.isNotEmpty
                            ? 'No students match "$_query"'
                            : 'No students in this class',
                        style: const TextStyle(
                            fontSize: 15, color: Color(0xFF9CA3AF)),
                      ),
                    ]),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(classStudentsProvider(widget.classId)),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: filtered.length,
                    itemBuilder: (_, i) {
                      final s = filtered[i];
                      final name = s['full_name'] as String? ?? '';
                      final regId = s['registration_id'] as String? ?? '';
                      final email = s['email'] as String? ?? '';
                      final membershipStatus =
                          s['membership_status'] as String? ?? '';
                      final riskLevel = s['risk_level'] as String? ?? 'NORMAL';
                      final completion =
                          (s['completion_rate'] as num?)?.toDouble() ?? 0.0;
                      final studentId = s['student_id'] as String? ??
                          s['id'] as String? ??
                          '';

                      return Card(
                        margin: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 5),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 8),
                          leading: CircleAvatar(
                            backgroundColor:
                                const Color(0xFF1A56DB).withOpacity(0.1),
                            child: Text(
                                name.isNotEmpty ? name[0].toUpperCase() : '?',
                                style: const TextStyle(
                                    color: Color(0xFF1A56DB),
                                    fontWeight: FontWeight.bold)),
                          ),
                          title: Text(name,
                              style: const TextStyle(
                                  fontWeight: FontWeight.w600, fontSize: 14)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(regId,
                                  style: const TextStyle(
                                      fontSize: 12, color: Color(0xFF9CA3AF))),
                              if (email.isNotEmpty)
                                Text(email,
                                    style: const TextStyle(
                                        fontSize: 11,
                                        color: Color(0xFF9CA3AF))),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: membershipStatus == 'APPROVED'
                                          ? Colors.green.shade50
                                          : Colors.orange.shade50,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(membershipStatus,
                                        style: TextStyle(
                                            fontSize: 10,
                                            color:
                                                membershipStatus == 'APPROVED'
                                                    ? Colors.green.shade700
                                                    : Colors.orange.shade700)),
                                  ),
                                  const SizedBox(width: 8),
                                  Text('${completion.toStringAsFixed(0)}%',
                                      style: const TextStyle(
                                          fontSize: 11,
                                          color: Color(0xFF6B7280))),
                                ],
                              ),
                            ],
                          ),
                          trailing: RiskBadge(riskLevel: riskLevel),
                          onTap: studentId.isNotEmpty
                              ? () => context.push('/admin/students/$studentId')
                              : null,
                        ),
                      );
                    },
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

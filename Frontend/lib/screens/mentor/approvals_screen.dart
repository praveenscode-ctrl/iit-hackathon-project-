import 'package:flutter/material.dart';
import '../../services/class_service.dart';
import '../../core/exceptions.dart';

class MentorApprovalsScreen extends StatefulWidget {
  final String classId;
  const MentorApprovalsScreen({super.key, required this.classId});

  @override
  State<MentorApprovalsScreen> createState() => _MentorApprovalsScreenState();
}

class _MentorApprovalsScreenState extends State<MentorApprovalsScreen> {
  final _svc = ClassService();
  List<Map<String, dynamic>> _pending = [];
  bool _loading = true;
  String? _loadError;
  final Set<String> _busy = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final list = await _svc.getApprovals(widget.classId);
      setState(() => _pending = list);
    } catch (e) {
      setState(() => _loadError = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _approve(String studentId) async {
    setState(() => _busy.add(studentId));
    try {
      await _svc.approveStudent(widget.classId, studentId);
      setState(() => _pending.removeWhere((s) => s['student_id'] == studentId));
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Student approved')));
    } on ApiException catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      setState(() => _busy.remove(studentId));
    }
  }

  Future<void> _reject(String studentId) async {
    final ctrl = TextEditingController();
    String? reason;
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Reject'),
        content: TextField(
            controller: ctrl,
            decoration: const InputDecoration(labelText: 'Reason (optional)')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () {
                reason = ctrl.text.trim();
                Navigator.pop(context);
              },
              child: const Text('Reject', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (reason == null) return;

    setState(() => _busy.add(studentId));
    try {
      await _svc.rejectStudent(widget.classId, studentId,
          reason: reason!.isEmpty ? null : reason);
      setState(() => _pending.removeWhere((s) => s['student_id'] == studentId));
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Student rejected')));
    } on ApiException catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      setState(() => _busy.remove(studentId));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pending Approvals')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _loadError != null
              ? Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(_loadError!,
                      style: const TextStyle(color: Color(0xFF6B7280))),
                  const SizedBox(height: 12),
                  TextButton(onPressed: _load, child: const Text('Retry')),
                ]))
              : _pending.isEmpty
                  ? const Center(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.check_circle_outline,
                          size: 56, color: Color(0xFFD1D5DB)),
                      SizedBox(height: 12),
                      Text('No pending approvals',
                          style: TextStyle(
                              fontSize: 15, color: Color(0xFF9CA3AF))),
                    ]))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        itemCount: _pending.length,
                        itemBuilder: (_, i) {
                          final s = _pending[i];
                          final id = s['student_id'] as String? ?? '';
                          final name = s['full_name'] as String? ?? '';
                          final regId = s['registration_id'] as String? ?? '';
                          final busy = _busy.contains(id);
                          return Card(
                            margin: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 5),
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Row(children: [
                                CircleAvatar(
                                  backgroundColor:
                                      const Color(0xFF1A56DB).withOpacity(0.1),
                                  child: Text(
                                      name.isNotEmpty
                                          ? name[0].toUpperCase()
                                          : '?',
                                      style: const TextStyle(
                                          color: Color(0xFF1A56DB),
                                          fontWeight: FontWeight.bold)),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                    child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                      Text(name,
                                          style: const TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: 14)),
                                      Text(regId,
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: Color(0xFF9CA3AF))),
                                    ])),
                                busy
                                    ? const SizedBox(
                                        width: 24,
                                        height: 24,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2))
                                    : Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                            IconButton(
                                                icon: const Icon(
                                                    Icons.check_circle_outline,
                                                    color: Colors.green),
                                                onPressed: () => _approve(id)),
                                            IconButton(
                                                icon: const Icon(
                                                    Icons.cancel_outlined,
                                                    color: Colors.red),
                                                onPressed: () => _reject(id)),
                                          ]),
                              ]),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}

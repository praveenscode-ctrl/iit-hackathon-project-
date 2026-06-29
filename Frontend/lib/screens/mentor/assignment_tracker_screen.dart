import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/assignment_provider.dart';
import '../../services/export_service.dart';
import '../../services/storage_service.dart';
import '../../services/assignment_service.dart';
import '../../core/ws_client.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/tracker_card_widget.dart';
import '../../services/submission_service.dart';
import 'package:url_launcher/url_launcher.dart';

class AssignmentTrackerScreen extends ConsumerStatefulWidget {
  final String assignmentId;
  const AssignmentTrackerScreen({super.key, required this.assignmentId});

  @override
  ConsumerState<AssignmentTrackerScreen> createState() =>
      _AssignmentTrackerScreenState();
}

class _AssignmentTrackerScreenState
    extends ConsumerState<AssignmentTrackerScreen> {
  final _exportSvc = ExportService();
  final _storageSvc = StorageService();
  final _wsClient = WsClient();
  final _subSvc = SubmissionService();
  bool _exporting = false;
  bool _publishing = false;
  List<Map<String, dynamic>> _extensionRequests = [];
  bool _loadingRequests = false;

  Future<void> _publishAssignment(String classId) async {
    setState(() => _publishing = true);
    try {
      final assignmentSvc = AssignmentService();
      await assignmentSvc.publish(widget.assignmentId);
      
      ref.invalidate(assignmentDetailProvider(widget.assignmentId));
      ref.invalidate(trackerProvider(widget.assignmentId));
      ref.invalidate(assignmentsProvider(classId));
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Assignment published successfully!')));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to publish: $e')));
      }
    } finally {
      if (mounted) setState(() => _publishing = false);
    }
  }

  Future<void> _loadRequests() async {
    setState(() => _loadingRequests = true);
    try {
      final reqs = await _subSvc.getExtensionRequests(widget.assignmentId);
      if (mounted) {
        setState(() {
          _extensionRequests = reqs;
        });
      }
    } catch (_) {
      // ignore
    } finally {
      if (mounted) setState(() => _loadingRequests = false);
    }
  }

  Future<void> _approveRequest(String requestId) async {
    try {
      await _subSvc.approveExtension(requestId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Extension request approved successfully!')));
      }
      _loadRequests();
      ref.invalidate(trackerProvider(widget.assignmentId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to approve extension: $e')));
      }
    }
  }

  Future<void> _rejectRequest(String requestId) async {
    try {
      await _subSvc.rejectExtension(requestId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Extension request put on wait / rejected!')));
      }
      _loadRequests();
      ref.invalidate(trackerProvider(widget.assignmentId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to reject extension: $e')));
      }
    }
  }

  @override
  void initState() {
    super.initState();
    // listen to WebSocket 'tracker_refresh' to auto-reload
    _wsClient.onTrackerRefresh = _onWsRefresh;
    _wsClient.connect(widget.assignmentId);
    _loadRequests();
  }

  @override
  void dispose() {
    _wsClient.disconnect();
    super.dispose();
  }

  void _onWsRefresh(dynamic payload) {
    // if payload contains assignment_id and it matches, or no payload, invalidate
    if (payload == null || payload['assignment_id'] == widget.assignmentId) {
      ref.invalidate(trackerProvider(widget.assignmentId));
    }
  }

  Future<void> _exportCsv() async {
    setState(() => _exporting = true);
    try {
      final jobId = await _exportSvc.requestExport(widget.assignmentId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Export started, please wait...')));

      final fileUrl = await _exportSvc.pollUntilDone(jobId);
      final downloadUrl = await _storageSvc.getDownloadUrl(fileUrl);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Export ready! Opening...')));

      final uri = Uri.parse(downloadUrl);
      try {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } catch (e) {
        await Clipboard.setData(ClipboardData(text: downloadUrl));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
              content:
                  Text('Could not open browser. Link copied to clipboard!')));
        }
      }
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Export failed: $e')));
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final assignment = ref.watch(assignmentDetailProvider(widget.assignmentId));
    final tracker = ref.watch(trackerProvider(widget.assignmentId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Live Tracker'),
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics_outlined),
            tooltip: 'Analytics',
            onPressed: () => context
                .push('/mentor/assignments/${widget.assignmentId}/analytics'),
          ),
          IconButton(
            icon: const Icon(Icons.list_alt_outlined),
            tooltip: 'Submissions',
            onPressed: () => context
                .push('/mentor/assignments/${widget.assignmentId}/submissions'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(assignmentDetailProvider(widget.assignmentId));
          ref.invalidate(trackerProvider(widget.assignmentId));
          await _loadRequests();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // assignment info
            assignment.when(
              loading: () => const LoadingWidget(),
              error: (e, _) => AppErrorWidget(message: e.toString()),
              data: (a) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                              child: Text(a.title,
                                  style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold))),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                                color: Colors.blue.shade50,
                                borderRadius: BorderRadius.circular(20)),
                            child: Text(a.status,
                                style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.blue.shade700,
                                    fontWeight: FontWeight.w600)),
                          ),
                        ],
                      ),
                      if (a.description != null) ...[
                        const SizedBox(height: 8),
                        Text(a.description!,
                            style: const TextStyle(
                                fontSize: 13, color: Color(0xFF6B7280))),
                      ],
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          const Icon(Icons.sync, size: 14, color: Colors.green),
                          const SizedBox(width: 4),
                          const Text('Live via WebSocket',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.green,
                                  fontWeight: FontWeight.w500)),
                          const Spacer(),
                          TextButton.icon(
                            onPressed: _exporting ? null : _exportCsv,
                            icon: _exporting
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2))
                                : const Icon(Icons.download_outlined, size: 16),
                            label: Text(
                                _exporting ? 'Exporting...' : 'Export CSV',
                                style: const TextStyle(fontSize: 13)),
                          ),
                        ],
                      ),
                      if (a.status == 'DRAFT') ...[
                        const Divider(height: 24),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(
                              backgroundColor: const Color(0xFF1A56DB),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                            icon: _publishing
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2))
                                : const Icon(Icons.publish_outlined, size: 18),
                            label: Text(_publishing ? 'Publishing...' : 'Publish Assignment Now',
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                            onPressed: _publishing ? null : () => _publishAssignment(a.classId),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),

            if (_extensionRequests.any((r) => r['status'] == 'PENDING')) ...[
              const SizedBox(height: 16),
              const Text(
                'Pending Extension Requests',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ..._extensionRequests.where((r) => r['status'] == 'PENDING').map((req) {
                final studentName = req['student_name'] as String? ?? 'Student';
                final regId = req['registration_id'] as String? ?? '';
                final reason = req['reason'] as String? ?? '';
                final reqId = req['id'] as String;
                return Card(
                  color: Colors.orange.shade50,
                  margin: const EdgeInsets.symmetric(vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                    side: BorderSide(color: Colors.orange.shade200),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: Colors.orange.shade100,
                              radius: 18,
                              child: Text(
                                studentName.isNotEmpty ? studentName[0].toUpperCase() : '?',
                                style: TextStyle(
                                    color: Colors.orange.shade800,
                                    fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    studentName,
                                    style: const TextStyle(
                                        fontSize: 14, fontWeight: FontWeight.bold),
                                  ),
                                  if (regId.isNotEmpty)
                                    Text(
                                      regId,
                                      style: TextStyle(
                                          fontSize: 11, color: Colors.grey.shade600),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Reason: "$reason"',
                          style: const TextStyle(
                              fontSize: 13, fontStyle: FontStyle.italic),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.green,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 8),
                              ),
                              onPressed: () => _approveRequest(reqId),
                              icon: const Icon(Icons.check, size: 16),
                              label: const Text('Accept'),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.red,
                                side: const BorderSide(color: Colors.red),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 8),
                              ),
                              onPressed: () => _rejectRequest(reqId),
                              icon: const Icon(Icons.close, size: 16),
                              label: const Text('Wait'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],

            const SizedBox(height: 16),

            // tracker list or draft placeholder
            assignment.when(
              loading: () => const SizedBox.shrink(),
              error: (e, _) => const SizedBox.shrink(),
              data: (a) {
                if (a.status == 'DRAFT') {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 40, horizontal: 16),
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.hourglass_empty_rounded,
                              size: 48, color: Color(0xFF9CA3AF)),
                          SizedBox(height: 12),
                          Text(
                            'Assignment is in draft status.\nPublish it to start tracking student submissions.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: Color(0xFF6B7280),
                                fontSize: 14,
                                height: 1.4),
                          ),
                        ],
                      ),
                    ),
                  );
                }
                return tracker.when(
                  loading: () => const LoadingWidget(message: 'Loading tracker...'),
                  error: (e, _) => AppErrorWidget(
                      message: e.toString(),
                      onRetry: () =>
                          ref.invalidate(trackerProvider(widget.assignmentId))),
                  data: (data) {
                    if (data.students.isEmpty)
                      return const Text('No students tracking this assignment.',
                          style: TextStyle(color: Color(0xFF9CA3AF)));
                    return Column(
                      children: data.students
                          .map((s) => TrackerCard(
                                studentName: s.fullName,
                                registrationId: s.registrationId,
                                trackerStatus: s.trackerStatus,
                                submittedAt: s.submittedAt != null
                                    ? s.submittedAt!
                                        .toLocal()
                                        .toString()
                                        .substring(0, 16)
                                    : null,
                              ))
                          .toList(),
                    );
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

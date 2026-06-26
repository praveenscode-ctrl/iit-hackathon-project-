import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/assignment_provider.dart';
import '../../services/export_service.dart';
import '../../services/storage_service.dart';
import '../../core/ws_client.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../widgets/tracker_card_widget.dart';
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
  bool _exporting = false;

  @override
  void initState() {
    super.initState();
    // listen to WebSocket 'tracker_refresh' to auto-reload
    _wsClient.onTrackerRefresh = _onWsRefresh;
    _wsClient.connect(widget.assignmentId);
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
                    ],
                  ),
                ),
              ),
            ),

            const SizedBox(height: 16),

            // tracker list
            tracker.when(
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
            ),
          ],
        ),
      ),
    );
  }
}

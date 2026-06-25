import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/assignment_provider.dart';
import '../../services/storage_service.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

class SubmissionsViewScreen extends ConsumerStatefulWidget {
  final String assignmentId;
  const SubmissionsViewScreen({super.key, required this.assignmentId});

  @override
  ConsumerState<SubmissionsViewScreen> createState() => _SubmissionsViewScreenState();
}

class _SubmissionsViewScreenState extends ConsumerState<SubmissionsViewScreen> {
  final _storageSvc = StorageService();
  final Set<String> _downloading = {};

  Future<void> _downloadFile(String submissionId, String fileUrl) async {
    setState(() => _downloading.add(submissionId));
    try {
      final downloadUrl = await _storageSvc.getDownloadUrl(fileUrl);
      final uri = Uri.parse(downloadUrl);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        throw Exception('Could not open browser');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to download: $e')));
    } finally {
      if (mounted) setState(() => _downloading.remove(submissionId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final submissions = ref.watch(submissionsForAssignmentProvider(widget.assignmentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Submissions')),
      body: submissions.when(
        loading: () => const LoadingWidget(message: 'Loading submissions...'),
        error: (e, _) => AppErrorWidget(message: e.toString(), onRetry: () => ref.invalidate(submissionsForAssignmentProvider(widget.assignmentId))),
        data: (list) {
          if (list.isEmpty) {
            return const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.assignment_turned_in_outlined, size: 56, color: Color(0xFFD1D5DB)),
              SizedBox(height: 12),
              Text('No submissions yet', style: TextStyle(fontSize: 15, color: Color(0xFF9CA3AF))),
            ]));
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(submissionsForAssignmentProvider(widget.assignmentId)),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final sub = list[i];
                final subId = sub['id'] as String;
                final student = sub['student'] as Map<String, dynamic>? ?? {};
                final name = student['full_name'] as String? ?? 'Unknown Student';
                final regId = student['registration_id'] as String? ?? '';
                final type = sub['submission_type'] as String? ?? 'TEXT';
                final text = sub['text_answer'] as String?;
                final fileUrl = sub['file_url'] as String?;
                final time = sub['submitted_at'] != null ? DateFormat('d MMM yyyy, h:mm a').format(DateTime.parse(sub['submitted_at']).toLocal()) : '';

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              radius: 16,
                              backgroundColor: const Color(0xFF1A56DB).withOpacity(0.1),
                              child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Color(0xFF1A56DB), fontWeight: FontWeight.bold, fontSize: 14)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                Text('$regId · $time', style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280))),
                              ],
                            )),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(20)),
                              child: Text(type, style: TextStyle(fontSize: 10, color: Colors.grey.shade700, fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ),
                        if (text != null && text.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(color: const Color(0xFFF9FAFB), borderRadius: BorderRadius.circular(8), border: Border.all(color: const Color(0xFFE5E7EB))),
                            child: Text(text, style: const TextStyle(fontSize: 13, color: Color(0xFF374151))),
                          ),
                        ],
                        if (fileUrl != null && fileUrl.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _downloading.contains(subId) ? null : () => _downloadFile(subId, fileUrl),
                            icon: _downloading.contains(subId) ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.download_outlined, size: 16),
                            label: Text(_downloading.contains(subId) ? 'Downloading...' : 'Download Attached File', style: const TextStyle(fontSize: 13)),
                          ),
                        ],
                      ],
                    ),
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

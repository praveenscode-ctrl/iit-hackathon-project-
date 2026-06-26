import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/assignment_provider.dart';
import '../../services/storage_service.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

class StudentSubmissionsScreen extends ConsumerStatefulWidget {
  const StudentSubmissionsScreen({super.key});

  @override
  ConsumerState<StudentSubmissionsScreen> createState() =>
      _StudentSubmissionsScreenState();
}

class _StudentSubmissionsScreenState
    extends ConsumerState<StudentSubmissionsScreen> {
  final _storageSvc = StorageService();
  final Set<String> _downloading = {};

  Future<void> _downloadFile(String submissionId, String fileUrl) async {
    setState(() => _downloading.add(submissionId));
    try {
      final downloadUrl = await _storageSvc.getDownloadUrl(fileUrl);
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
            .showSnackBar(SnackBar(content: Text('Failed to download: $e')));
    } finally {
      if (mounted) setState(() => _downloading.remove(submissionId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final mySubs = ref.watch(mySubmissionsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Submissions')),
      body: mySubs.when(
        loading: () => const LoadingWidget(message: 'Loading submissions...'),
        error: (e, _) => AppErrorWidget(
            message: e.toString(),
            onRetry: () => ref.invalidate(mySubmissionsProvider)),
        data: (list) {
          if (list.isEmpty) {
            return const Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
              Icon(Icons.history, size: 56, color: Color(0xFFD1D5DB)),
              SizedBox(height: 12),
              Text('No submissions found',
                  style: TextStyle(fontSize: 15, color: Color(0xFF9CA3AF))),
            ]));
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(mySubmissionsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final sub = list[i];
                final subId = sub.submissionId;
                final title = sub.assignmentTitle;
                final type = sub.submissionType;
                final text = sub.textAnswer;
                final fileUrl = sub.fileUrl;
                final time = DateFormat('d MMM yyyy, h:mm a')
                    .format(sub.submittedAt.toLocal());

                return Card(
                  margin:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.assignment_turned_in,
                                color: Colors.green, size: 20),
                            const SizedBox(width: 10),
                            Expanded(
                                child: Text(title,
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 15))),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                  color: Colors.grey.shade100,
                                  borderRadius: BorderRadius.circular(20)),
                              child: Text(type,
                                  style: TextStyle(
                                      fontSize: 10,
                                      color: Colors.grey.shade700,
                                      fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text('Submitted on: $time',
                            style: const TextStyle(
                                fontSize: 12, color: Color(0xFF6B7280))),
                        if (text != null && text.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                                color: const Color(0xFFF9FAFB),
                                borderRadius: BorderRadius.circular(8),
                                border:
                                    Border.all(color: const Color(0xFFE5E7EB))),
                            child: Text(text,
                                style: const TextStyle(
                                    fontSize: 13, color: Color(0xFF374151))),
                          ),
                        ],
                        if (fileUrl != null && fileUrl.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _downloading.contains(subId)
                                ? null
                                : () => _downloadFile(subId, fileUrl),
                            icon: _downloading.contains(subId)
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2))
                                : const Icon(Icons.download_outlined, size: 16),
                            label: Text(
                                _downloading.contains(subId)
                                    ? 'Downloading...'
                                    : 'Download My File',
                                style: const TextStyle(fontSize: 13)),
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

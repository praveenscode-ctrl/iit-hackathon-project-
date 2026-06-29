import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';
import 'dart:io' as io;
import '../../providers/assignment_provider.dart';
import '../../services/submission_service.dart';
import '../../services/storage_service.dart';
import '../../services/notification_service.dart';
import '../../widgets/loading_widget.dart';
import '../../widgets/error_widget.dart';
import '../../core/exceptions.dart';

class StudentAssignmentDetailScreen extends ConsumerStatefulWidget {
  final String assignmentId;
  const StudentAssignmentDetailScreen({super.key, required this.assignmentId});

  @override
  ConsumerState<StudentAssignmentDetailScreen> createState() =>
      _StudentAssignmentDetailScreenState();
}

class _StudentAssignmentDetailScreenState
    extends ConsumerState<StudentAssignmentDetailScreen> {
  final _subSvc = SubmissionService();
  final _storageSvc = StorageService();
  final _notifSvc = NotificationService();
  final _textCtrl = TextEditingController();
  final _reasonCtrl = TextEditingController();

  bool _submitting = false;
  String? _error;

  String? _uploadedFileUrl;
  bool _fileUploading = false;
  String? _fileName;

  bool _downloadingQ = false;
  bool _reminding = false;

  @override
  void dispose() {
    _textCtrl.dispose();
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _downloadQuestion(String fileUrl) async {
    setState(() => _downloadingQ = true);
    try {
      final url = await _storageSvc.getDownloadUrl(fileUrl);
      final uri = Uri.parse(url);
      try {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } catch (e) {
        await Clipboard.setData(ClipboardData(text: url));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
              content:
                  Text('Could not open browser. Link copied to clipboard!')));
        }
      }
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to get download link: $e')));
    } finally {
      if (mounted) setState(() => _downloadingQ = false);
    }
  }

  Future<void> _pickAndUploadSubmission() async {
    final result = await FilePicker.platform.pickFiles(type: FileType.any);
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;

    var bytes = file.bytes;
    if (bytes == null && file.path != null) {
      bytes = await io.File(file.path!).readAsBytes();
    }
    if (bytes == null) {
      setState(() => _error = 'Could not read selected file');
      return;
    }

    setState(() {
      _fileUploading = true;
      _error = null;
    });
    try {
      // 1. presigned url
      final urlData = await _storageSvc.getUploadUrl(
          fileName: file.name,
          fileType: 'application/octet-stream',
          uploadPurpose: 'SUBMISSION');
      final uploadUrl = urlData['upload_url'] as String;
      final fileUrl = urlData['file_url'] as String;

      // 2. put
      await _storageSvc.uploadToS3(
          uploadUrl, bytes!, 'application/octet-stream');

      setState(() {
        _uploadedFileUrl = fileUrl;
        _fileName = file.name;
      });
    } catch (e) {
      setState(() => _error = 'File upload failed: $e');
    } finally {
      setState(() => _fileUploading = false);
    }
  }

  Future<void> _submit(String type, bool isLate) async {
    final text = _textCtrl.text.trim();

    if (type == 'TEXT' && text.isEmpty) {
      setState(() => _error = 'Please enter your answer');
      return;
    }
    if (type == 'FILE' && _uploadedFileUrl == null) {
      setState(() => _error = 'Please upload a file');
      return;
    }
    if (type == 'BOTH' && text.isEmpty && _uploadedFileUrl == null) {
      setState(() => _error = 'Please enter your answer or upload a file');
      return;
    }

    final reason = _reasonCtrl.text.trim();
    if (isLate && reason.isEmpty) {
      setState(() => _error = 'Please enter a reason for late submission');
      return;
    }

    final submitType =
        type == 'BOTH' ? (_uploadedFileUrl != null ? 'FILE' : 'TEXT') : type;

    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await _subSvc.submit(
        widget.assignmentId,
        submissionType: submitType,
        textAnswer: text.isEmpty ? null : text,
        fileUrl: _uploadedFileUrl,
        lateReason: isLate ? reason : null,
      );
      ref.invalidate(assignmentDetailProvider(widget.assignmentId));
      ref.invalidate(mySubmissionsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Assignment submitted successfully!')));
        context.pop();
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Failed to submit');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _setReminder() async {
    final now = DateTime.now();
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: now.add(const Duration(hours: 1)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 30)),
    );
    if (pickedDate == null) return;

    if (!mounted) return;
    final pickedTime = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(now.add(const Duration(hours: 1))),
    );
    if (pickedTime == null) return;

    final remindDateTime = DateTime(
      pickedDate.year,
      pickedDate.month,
      pickedDate.day,
      pickedTime.hour,
      pickedTime.minute,
    );

    if (remindDateTime.isBefore(DateTime.now())) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Reminder time must be in the future')),
        );
      }
      return;
    }

    setState(() => _reminding = true);
    try {
      final time = remindDateTime.toUtc().toIso8601String();
      await _notifSvc.setReminder(
          assignmentId: widget.assignmentId, remindAt: time);
      if (mounted) {
        final formatted =
            DateFormat('d MMM yyyy, h:mm a').format(remindDateTime);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Reminder set successfully for $formatted')),
        );
      }
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to set reminder: $e')));
    } finally {
      if (mounted) setState(() => _reminding = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final assignment = ref.watch(assignmentDetailProvider(widget.assignmentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Assignment Detail')),
      body: assignment.when(
        loading: () => const LoadingWidget(message: 'Loading...'),
        error: (e, _) => AppErrorWidget(
            message: e.toString(),
            onRetry: () =>
                ref.invalidate(assignmentDetailProvider(widget.assignmentId))),
        data: (a) {
          final type = a.submissionType; // TEXT, FILE, or BOTH
          final deadlineStr = a.deadlineAt != null
              ? DateFormat('d MMM yyyy, h:mm a').format(a.deadlineAt!.toLocal())
              : 'No deadline';
          final info = a.studentSubmission;
          final alreadySubmitted = info != null && info.submitted == true;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // header card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(a.title,
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                        if (a.description != null) ...[
                          const SizedBox(height: 8),
                          Text(a.description!,
                              style: const TextStyle(
                                  fontSize: 14, color: Color(0xFF374151))),
                        ],
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            const Icon(Icons.schedule,
                                size: 16, color: Color(0xFF6B7280)),
                            const SizedBox(width: 6),
                            Text('Due: $deadlineStr',
                                style: const TextStyle(
                                    fontSize: 13, color: Color(0xFF6B7280))),
                          ],
                        ),
                        if (a.contentUrl != null) ...[
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _downloadingQ
                                ? null
                                : () => _downloadQuestion(a.contentUrl!),
                            icon: _downloadingQ
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2))
                                : const Icon(Icons.download_outlined, size: 16),
                            label: Text(
                                _downloadingQ
                                    ? 'Opening...'
                                    : 'View Attached Question (PDF)',
                                style: const TextStyle(fontSize: 13)),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // actions row
                if (!alreadySubmitted)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton.icon(
                        onPressed: _reminding ? null : _setReminder,
                        icon: _reminding
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.notification_add_outlined),
                        label:
                            Text(_reminding ? 'Setting...' : 'Remind Me Later'),
                      ),
                    ],
                  ),

                const SizedBox(height: 8),

                // submission area
                if (alreadySubmitted)
                  Card(
                    color: Colors.green.shade50,
                    child: const Padding(
                      padding: EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green),
                          SizedBox(width: 12),
                          Expanded(
                              child: Text(
                                  'You have already submitted this assignment. Check the Submissions tab for details.',
                                  style: TextStyle(
                                      color: Colors.green,
                                      fontWeight: FontWeight.w500))),
                        ],
                      ),
                    ),
                  )
                else
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Your Submission',
                              style: TextStyle(
                                  fontSize: 16, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 16),
                          if (type == 'TEXT' || type == 'BOTH') ...[
                            TextField(
                              controller: _textCtrl,
                              maxLines: 5,
                              decoration: const InputDecoration(
                                  labelText: 'Text Answer',
                                  alignLabelWithHint: true),
                            ),
                            const SizedBox(height: 16),
                          ],
                          if (type == 'FILE' || type == 'BOTH') ...[
                            const Text('File Upload',
                                style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                    color: Color(0xFF374151))),
                            const SizedBox(height: 8),
                            OutlinedButton.icon(
                              onPressed: _fileUploading
                                  ? null
                                  : _pickAndUploadSubmission,
                              icon: _fileUploading
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2))
                                  : const Icon(Icons.upload_file),
                              label: Text(_fileUploading
                                  ? 'Uploading...'
                                  : _fileName ?? 'Select File'),
                            ),
                            if (_uploadedFileUrl != null)
                              Padding(
                                padding: const EdgeInsets.only(top: 8),
                                child: Text('✓ Uploaded: $_fileName',
                                    style: TextStyle(
                                        fontSize: 12,
                                        color: Colors.green.shade700)),
                              ),
                            const SizedBox(height: 16),
                          ],
                          final isLate = a.status == 'CLOSED' || (a.deadlineAt != null && a.deadlineAt!.isBefore(DateTime.now()));
                          if (isLate) ...[
                            const Text(
                              'This assignment is past its deadline or closed. A reason is required to submit.',
                              style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.red,
                                  fontWeight: FontWeight.w500),
                            ),
                            const SizedBox(height: 8),
                            TextField(
                              controller: _reasonCtrl,
                              maxLines: 2,
                              decoration: const InputDecoration(
                                  labelText: 'Reason for late submission *',
                                  alignLabelWithHint: true),
                            ),
                            const SizedBox(height: 16),
                          ],
                          if (_error != null) ...[
                            Container(
                              padding: const EdgeInsets.all(12),
                              margin: const EdgeInsets.only(bottom: 16),
                              decoration: BoxDecoration(
                                  color: Colors.red.shade50,
                                  borderRadius: BorderRadius.circular(8),
                                  border:
                                      Border.all(color: Colors.red.shade200)),
                              child: Text(_error!,
                                  style: TextStyle(
                                      fontSize: 13,
                                      color: Colors.red.shade700)),
                            ),
                          ],
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: (_submitting || _fileUploading)
                                  ? null
                                  : () => _submit(type, isLate),
                              child: _submitting
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2, color: Colors.white))
                                  : const Text('Submit Assignment',
                                      style: TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

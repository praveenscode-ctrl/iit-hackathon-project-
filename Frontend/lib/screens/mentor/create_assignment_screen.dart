import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io' as io;
import '../../services/assignment_service.dart';
import '../../services/storage_service.dart';
import '../../core/exceptions.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/assignment_provider.dart';

class CreateAssignmentScreen extends ConsumerStatefulWidget {
  final String classId;
  const CreateAssignmentScreen({super.key, required this.classId});

  @override
  ConsumerState<CreateAssignmentScreen> createState() =>
      _CreateAssignmentScreenState();
}

class _CreateAssignmentScreenState
    extends ConsumerState<CreateAssignmentScreen> {
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _assignmentSvc = AssignmentService();
  final _storageSvc = StorageService();

  String _submissionType = 'TEXT';
  bool _publishNow = false;
  bool _loading = false;
  String? _error;
  DateTime? _deadline;

  // for PDF file upload
  String? _uploadedFileUrl;
  bool _fileUploading = false;
  String? _fileName;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickAndUploadPdf() async {
    final result = await FilePicker.platform
        .pickFiles(type: FileType.custom, allowedExtensions: ['pdf']);
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;

    var bytes = file.bytes;
    if (bytes == null && file.path != null) {
      bytes = await io.File(file.path!).readAsBytes();
    }
    if (bytes == null) {
      setState(() => _error = 'Could not read selected PDF file');
      return;
    }

    setState(() {
      _fileUploading = true;
      _error = null;
    });
    try {
      // step 1: get presigned upload URL from backend
      final urlData = await _storageSvc.getUploadUrl(
          fileName: file.name,
          fileType: 'application/pdf',
          uploadPurpose: 'ASSIGNMENT');
      final uploadUrl = urlData['upload_url'] as String;
      final fileUrl = urlData['file_url'] as String;

      // step 2: PUT directly to S3
      await _storageSvc.uploadToS3(uploadUrl, bytes!, 'application/pdf');

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

  Future<void> _pickDeadline() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
        context: context,
        initialDate: now.add(const Duration(days: 7)),
        firstDate: now,
        lastDate: now.add(const Duration(days: 365)));
    if (picked == null) return;
    final time =
        await showTimePicker(context: context, initialTime: TimeOfDay.now());
    if (time == null) return;
    setState(() => _deadline = DateTime(
        picked.year, picked.month, picked.day, time.hour, time.minute));
  }

  Future<void> _create() async {
    final title = _titleCtrl.text.trim();
    if (title.isEmpty) {
      setState(() => _error = 'Title is required');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final body = <String, dynamic>{
        'class_id': widget.classId,
        'title': title,
        'description':
            _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        'content_type': _uploadedFileUrl != null ? 'PDF' : 'RICH_TEXT',
        'content_url': _uploadedFileUrl,
        'submission_type': _submissionType,
        'deadline_at': _deadline?.toUtc().toIso8601String(),
      };

      final data = await _assignmentSvc.createAssignment(body);
      final assignmentId = data['id'] as String;

      if (_publishNow) {
        await _assignmentSvc.publish(assignmentId);
      }

      ref.invalidate(assignmentsProvider(widget.classId));

      if (!mounted) return;
      context.pop();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Failed to create assignment');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Assignment')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _titleCtrl,
              decoration: const InputDecoration(
                  labelText: 'Title *', prefixIcon: Icon(Icons.title)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _descCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                  labelText: 'Description',
                  alignLabelWithHint: true,
                  prefixIcon: Icon(Icons.notes_outlined)),
            ),
            const SizedBox(height: 16),
            const Text('Submission Type',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF374151))),
            const SizedBox(height: 6),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'TEXT', label: Text('Text')),
                ButtonSegment(value: 'FILE', label: Text('File')),
                ButtonSegment(value: 'BOTH', label: Text('Both')),
              ],
              selected: {_submissionType},
              onSelectionChanged: (s) =>
                  setState(() => _submissionType = s.first),
            ),
            const SizedBox(height: 16),

            // question file upload (PDF)
            const Text('Question File (PDF)',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF374151))),
            const SizedBox(height: 6),
            OutlinedButton.icon(
              onPressed: _fileUploading ? null : _pickAndUploadPdf,
              icon: _fileUploading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.upload_file_outlined),
              label: Text(
                  _fileUploading ? 'Uploading...' : _fileName ?? 'Attach PDF'),
            ),
            if (_uploadedFileUrl != null)
              Text('✓ Uploaded: $_fileName',
                  style: TextStyle(fontSize: 12, color: Colors.green.shade700)),

            const SizedBox(height: 16),
            // deadline picker
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.schedule, color: Color(0xFF1A56DB)),
              title: Text(_deadline == null
                  ? 'Set Deadline (optional)'
                  : _deadline!.toLocal().toString().substring(0, 16)),
              trailing: _deadline == null
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () => setState(() => _deadline = null)),
              onTap: _pickDeadline,
              shape: RoundedRectangleBorder(
                  side: const BorderSide(color: Color(0xFFE5E7EB)),
                  borderRadius: BorderRadius.circular(8)),
            ),

            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Publish immediately',
                  style: TextStyle(fontSize: 14)),
              subtitle: const Text('Leave off to save as DRAFT',
                  style: TextStyle(fontSize: 12)),
              value: _publishNow,
              onChanged: (v) => setState(() => _publishNow = v),
              contentPadding: EdgeInsets.zero,
            ),

            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200)),
                child: Text(_error!,
                    style: TextStyle(fontSize: 13, color: Colors.red.shade700)),
              ),
            ],
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: (_loading || _fileUploading) ? null : _create,
              child: _loading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : Text(_publishNow ? 'Create & Publish' : 'Save as Draft',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }
}

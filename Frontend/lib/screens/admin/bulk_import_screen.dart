import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/api_client.dart';
import '../../core/exceptions.dart';
import 'package:dio/dio.dart';
import 'dart:io' as io;

import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

class BulkImportScreen extends StatefulWidget {
  const BulkImportScreen({super.key});

  @override
  State<BulkImportScreen> createState() => _BulkImportScreenState();
}

class _BulkImportScreenState extends State<BulkImportScreen> {
  bool _uploading = false;
  String? _error;
  Map<String, dynamic>? _batchResult;
  String? _batchId;
  bool _polling = false;

  Future<void> _downloadTemplate() async {
    try {
      final data = await apiGet('/provision/bulk-import/template');
      final url = data['download_url'] as String?;
      if (url != null) {
        final uri = Uri.parse(url);
        try {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        } catch (e) {
          await Clipboard.setData(ClipboardData(text: url));
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Could not launch browser. Link copied to clipboard!'),
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }

  Future<void> _pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xlsx'],
    );
    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    if (file.extension?.toLowerCase() != 'xlsx') {
      setState(() => _error = 'Only .xlsx files are supported');
      return;
    }

    setState(() {
      _uploading = true;
      _error = null;
      _batchResult = null;
    });

    try {
      var bytes = file.bytes;
      if (bytes == null && file.path != null) {
        bytes = await io.File(file.path!).readAsBytes();
      }
      if (bytes == null) {
        setState(() => _error = 'Could not read file');
        return;
      }

      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(bytes, filename: file.name),
      });

      final resp = await dio.post('/provision/bulk-import', data: formData);
      final batchId = resp.data['batch_id'] as String;
      setState(() {
        _batchId = batchId;
        _polling = true;
      });
      await _pollStatus(batchId);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Upload failed: $e');
    } finally {
      if (mounted)
        setState(() {
          _uploading = false;
          _polling = false;
        });
    }
  }

  Future<void> _pollStatus(String batchId) async {
    while (true) {
      await Future.delayed(const Duration(seconds: 2));
      try {
        final data = await apiGet('/provision/bulk-import/$batchId');
        final status = data['status'] as String?;
        if (status == 'COMPLETED' ||
            status == 'PARTIAL' ||
            status == 'FAILED') {
          if (mounted)
            setState(() => _batchResult = data as Map<String, dynamic>);
          break;
        }
      } catch (_) {
        break;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Bulk Import')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Import Classes, Mentors & Students',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            const Text(
              'Download the template, fill in the 3 sheets (Classes → Mentors → Students), then upload.',
              style: TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: _downloadTemplate,
              icon: const Icon(Icons.download_outlined),
              label: const Text('Download Template'),
              style: OutlinedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 46)),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.shade200),
              ),
              child: const Text(
                  '⚠️ Only .xlsx files are accepted. Large files may take longer to process.',
                  style: TextStyle(fontSize: 12)),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: (_uploading || _polling) ? null : _pickAndUpload,
              icon: const Icon(Icons.upload_file_outlined),
              label: Text(_uploading
                  ? 'Uploading...'
                  : _polling
                      ? 'Processing...'
                      : 'Select & Upload File'),
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
            if (_polling && _batchResult == null) ...[
              const SizedBox(height: 20),
              const Row(children: [
                CircularProgressIndicator(),
                SizedBox(width: 16),
                Text('Processing your file...')
              ]),
            ],
            if (_batchResult != null) ...[
              const SizedBox(height: 20),
              _buildBatchResult(_batchResult!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildBatchResult(Map<String, dynamic> data) {
    final status = data['status'] as String? ?? '';
    final errors = data['errors'] as List? ?? [];
    final summary = data['summary'] as Map? ?? {};
    final isSuccess = status == 'COMPLETED' || status == 'PARTIAL';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(isSuccess ? Icons.check_circle : Icons.error,
                color: isSuccess ? Colors.green : Colors.red),
            const SizedBox(width: 8),
            Text('Import $status',
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: isSuccess ? Colors.green : Colors.red)),
          ],
        ),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
              'Classes: ${summary['classes_created'] ?? 0} · Mentors: ${summary['mentors_created'] ?? 0} · Students: ${summary['students_created'] ?? 0}',
              style: const TextStyle(fontSize: 13, color: Color(0xFF374151))),
        ],
        if (errors.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Errors',
              style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.red)),
          const SizedBox(height: 6),
          ...errors.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                    '• Sheet: ${e['sheet']} Row: ${e['row']} — ${e['message']}',
                    style: const TextStyle(
                        fontSize: 12, color: Color(0xFF374151))),
              )),
        ],
      ],
    );
  }
}

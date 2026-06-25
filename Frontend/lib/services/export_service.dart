import 'dart:async';
import '../core/api_client.dart';
class ExportService {
  Future<String> requestExport(String assignmentId) async {
    final data = await apiPost('/exports/assignment-tracker', data: {
      'assignment_id': assignmentId,
    });
    return data['export_job_id'] as String;
  }
  Future<String> pollUntilDone(String exportJobId) async {
    while (true) {
      final data = await apiGet('/exports/$exportJobId');
      final status = data['status'] as String;
      if (status == 'DONE') {
        return data['file_url'] as String;
      } else if (status == 'FAILED') {
        throw Exception('Export failed');
      }
      await Future.delayed(const Duration(seconds: 3));
    }
  }
}

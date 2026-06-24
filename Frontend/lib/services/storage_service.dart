import 'package:dio/dio.dart';
import '../core/api_client.dart';

class StorageService {
  // step 1: get presigned upload URL
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String fileType,
    required String uploadPurpose, // 'ASSIGNMENT' or 'SUBMISSION'
  }) async {
    final data = await apiPost('/storage/presigned-upload', data: {
      'file_name': fileName,
      'file_type': fileType,
      'upload_purpose': uploadPurpose,
    });
    return data as Map<String, dynamic>;
  }

  // step 2: PUT file bytes directly to S3
  Future<void> uploadToS3(String uploadUrl, List<int> bytes, String fileType) async {
    final plain = Dio();
    await plain.put(
      uploadUrl,
      data: Stream.fromIterable(bytes.map((b) => [b])),
      options: Options(
        headers: {
          'Content-Type': fileType,
          'Content-Length': bytes.length,
        },
      ),
    );
  }

  // get a presigned download URL for a private S3 file
  Future<String> getDownloadUrl(String fileUrl) async {
    final data = await apiPost('/storage/presigned-download', data: {
      'file_url': fileUrl,
    });
    return data['download_url'] as String;
  }
}

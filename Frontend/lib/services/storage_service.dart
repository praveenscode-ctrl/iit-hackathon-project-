import 'package:dio/dio.dart';
import '../core/api_client.dart';

class StorageService {
 
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String fileType,
    required String uploadPurpose, 
  }) async {
    final data = await apiPost('/storage/presigned-upload', data: {
      'file_name': fileName,
      'file_type': fileType,
      'upload_purpose': uploadPurpose,
    });
    return data as Map<String, dynamic>;
  }
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
  Future<String> getDownloadUrl(String fileUrl) async {
    final data = await apiPost('/storage/presigned-download', data: {
      'file_url': fileUrl,
    });
    return data['download_url'] as String;
  }
}

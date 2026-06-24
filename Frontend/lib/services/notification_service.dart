import '../core/api_client.dart';
import '../models/notification_model.dart';

class NotificationService {
  Future<Map<String, dynamic>> getNotifications() async {
    final data = await apiGet('/notifications');
    return data as Map<String, dynamic>;
  }

  Future<void> markRead(String notificationId) async {
    await apiPatch('/notifications/$notificationId/read');
  }

  Future<void> markAllRead() async {
    await apiPatch('/notifications/read-all');
  }

  Future<Map<String, dynamic>> setReminder({
    required String assignmentId,
    required String remindAt,
  }) async {
    final data = await apiPost('/notifications/reminder', data: {
      'assignment_id': assignmentId,
      'remind_at': remindAt,
    });
    return data as Map<String, dynamic>;
  }
}

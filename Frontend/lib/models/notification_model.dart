class NotificationModel {
  final String id;
  final String notificationType;
  final String title;
  final String body;
  final Map<String, dynamic>? payload;
  final bool isRead;
  final DateTime createdAt;

  NotificationModel({
    required this.id,
    required this.notificationType,
    required this.title,
    required this.body,
    this.payload,
    required this.isRead,
    required this.createdAt,
  });

  factory NotificationModel.fromJson(Map<String, dynamic> j) =>
      NotificationModel(
        id: j['id'] as String,
        notificationType: j['notification_type'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        payload: j['payload'] as Map<String, dynamic>?,
        isRead: j['is_read'] as bool,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

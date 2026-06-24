import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/notification_model.dart';
import '../services/notification_service.dart';

final _svc = NotificationService();

final notificationsProvider = StateNotifierProvider<NotificationNotifier, AsyncValue<List<NotificationModel>>>((ref) {
  return NotificationNotifier();
});

class NotificationNotifier extends StateNotifier<AsyncValue<List<NotificationModel>>> {
  NotificationNotifier() : super(const AsyncValue.loading());

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final data = await _svc.getNotifications();
      final list = (data['notifications'] as List)
          .map((e) => NotificationModel.fromJson(e as Map<String, dynamic>))
          .toList();
      state = AsyncValue.data(list);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markRead(String id) async {
    await _svc.markRead(id);
    state.whenData((list) {
      state = AsyncValue.data(
        list.map((n) => n.id == id ? _markOne(n) : n).toList(),
      );
    });
  }

  Future<void> markAllRead() async {
    await _svc.markAllRead();
    state.whenData((list) {
      state = AsyncValue.data(list.map(_markOne).toList());
    });
  }

  int get unreadCount =>
      state.valueOrNull?.where((n) => !n.isRead).length ?? 0;

  NotificationModel _markOne(NotificationModel n) => NotificationModel(
        id: n.id,
        notificationType: n.notificationType,
        title: n.title,
        body: n.body,
        payload: n.payload,
        isRead: true,
        createdAt: n.createdAt,
      );
}

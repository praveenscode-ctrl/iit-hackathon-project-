import 'dart:developer' as dev;
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
    dev.log("Handling background message: ${message.messageId}");
  } catch (e) {
    dev.log("Error in background message handler: $e");
  }
}

class FcmService {
  static final FcmService instance = FcmService._();
  FcmService._();

  bool _initialized = false;
  String? _fcmToken;

  Future<void> init() async {
    if (_initialized) return;
    try {
      await Firebase.initializeApp();

      final messaging = FirebaseMessaging.instance;

      // Request permission
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      // Get token
      _fcmToken = await messaging.getToken();
      dev.log("FCM Token: $_fcmToken");

      // Listen for token refreshes
      messaging.onTokenRefresh.listen((token) {
        _fcmToken = token;
      });

      // Handle background messages when app is closed
      FirebaseMessaging.onBackgroundMessage(
          _firebaseMessagingBackgroundHandler);

      _initialized = true;
    } catch (e) {
      dev.log("Firebase initialization failed/skipped: $e");
    }
  }

  String get fcmToken => _fcmToken ?? '';
}

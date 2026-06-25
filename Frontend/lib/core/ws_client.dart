import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'constants.dart';
import 'auth_storage.dart';

// only used for tracker screen
class WsClient {
  WebSocketChannel? _channel;
  StreamSubscription? _sub;

  int _retries = 0;
  bool _intentionalClose = false;

  String? _assignmentId;

  // callbacks set by the tracker screen
  Function(Map<String, dynamic>)? onSubmissionCreated;
  Function(Map<String, dynamic>)? onTrackerRefresh;
  Function()? onDisconnected;
  Function()? onReconnectFailed;

  Future<void> connect(String assignmentId) async {
    _assignmentId = assignmentId;
    _intentionalClose = false;
    _retries = 0;
    await _doConnect();
  }

  Future<void> _doConnect() async {
    final token = await AuthStorage.getAccessToken();
    if (token == null) return;

    final uri = Uri.parse('$kWsUrl/ws/tracker/$_assignmentId?token=$token');

    try {
      _channel = WebSocketChannel.connect(uri);
      _sub = _channel!.stream.listen(
        _onMessage,
        onDone: _onClose,
        onError: (_) => _onClose(),
        cancelOnError: true,
      );
      _retries = 0; // reset on successful connect
    } catch (_) {
      _onClose();
    }
  }

  void _onMessage(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      final event = data['event'] as String?;

      if (event == 'submission_created') {
        onSubmissionCreated?.call(data);
      } else if (event == 'tracker_refresh') {
        onTrackerRefresh?.call(data);
      }
      // 'connected' ping — no action needed
    } catch (_) {}
  }

  void _onClose() {
    _sub?.cancel();
    _channel = null;

    if (_intentionalClose) return;

    onDisconnected?.call();

    // backoff: 2s, 4s, 8s — max 3 attempts
    if (_retries < 3) {
      final delay = Duration(seconds: [2, 4, 8][_retries]);
      _retries++;
      Timer(delay, _doConnect);
    } else {
      onReconnectFailed?.call();
    }
  }

  void disconnect() {
    _intentionalClose = true;
    _sub?.cancel();
    _channel?.sink.close();
    _channel = null;
  }
}

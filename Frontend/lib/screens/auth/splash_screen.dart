import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/constants.dart';
import '../../core/auth_storage.dart';
import '../../core/api_client.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/server_wakeup_widget.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  bool _showWakeup = false;
  String _statusText = 'Starting up...';

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    // show wakeup banner if server is slow
    final wakeupTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) setState(() => _showWakeup = true);
    });

    try {
      // wake the server
      final plain = Dio();
      await plain.get('https://assignhub-api.onrender.com/health');
    } catch (_) {
      // cold start — keep waiting
    }

    wakeupTimer.cancel();
    if (mounted) setState(() { _showWakeup = false; _statusText = 'Checking session...'; });

    final token = await AuthStorage.getAccessToken();
    if (token == null) {
      if (mounted) context.go('/login');
      return;
    }

    try {
      final user = await ref.read(authProvider.notifier).restoreFromStorage();
      if (!mounted) return;
      switch (user.role) {
        case 'ADMIN':
          context.go('/admin/dashboard');
        case 'MENTOR':
          context.go('/mentor/dashboard');
        default:
          context.go('/student/dashboard');
      }
    } catch (_) {
      await AuthStorage.clear();
      if (mounted) context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A56DB),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.assignment_turned_in, size: 72, color: Colors.white),
              const SizedBox(height: 16),
              const Text(
                'AssignHub',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 4),
              Text(
                'Assignment Management Platform',
                style: TextStyle(fontSize: 13, color: Colors.white.withOpacity(0.75)),
              ),
              const SizedBox(height: 48),
              if (_showWakeup)
                const ServerWakeupWidget()
              else
                Column(
                  children: [
                    const CircularProgressIndicator(color: Colors.white),
                    const SizedBox(height: 16),
                    Text(_statusText, style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 13)),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}

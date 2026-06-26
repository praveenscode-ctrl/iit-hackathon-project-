import 'package:flutter/material.dart';

// shown on splash if server takes more than 5 seconds to respond
class ServerWakeupWidget extends StatelessWidget {
  const ServerWakeupWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const CircularProgressIndicator(color: Colors.white),
        const SizedBox(height: 20),
        const Text(
          'Server is starting up...',
          style: TextStyle(
              color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 6),
        Text(
          'This may take up to 60 seconds on first launch.',
          style: TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 12),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

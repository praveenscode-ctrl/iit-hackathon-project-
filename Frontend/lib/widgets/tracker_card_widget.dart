import 'package:flutter/material.dart';

class TrackerCard extends StatelessWidget {
  final String studentName;
  final String registrationId;
  final String trackerStatus;
  final String? submittedAt;

  const TrackerCard({
    super.key,
    required this.studentName,
    required this.registrationId,
    required this.trackerStatus,
    this.submittedAt,
  });

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (trackerStatus) {
      'SUBMITTED' => (Colors.green.shade600, Icons.check_circle_outline),
      'LATE' => (Colors.orange.shade600, Icons.watch_later_outlined),
      'MISSED' => (Colors.red.shade600, Icons.cancel_outlined),
      _ => (Colors.grey.shade500, Icons.hourglass_empty),
    };

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(studentName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                Text(registrationId, style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(trackerStatus, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
              ),
              if (submittedAt != null)
                Text(submittedAt!, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF))),
            ],
          ),
        ],
      ),
    );
  }
}

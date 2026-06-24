import 'package:flutter/material.dart';

class RiskBadge extends StatelessWidget {
  final String riskLevel;
  const RiskBadge({super.key, required this.riskLevel});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (riskLevel) {
      'HIGH' => (Colors.red.shade600, 'High Risk'),
      'MEDIUM' => (Colors.orange.shade600, 'Medium'),
      'LOW' => (Colors.yellow.shade700, 'Low'),
      'RECOVERING' => (Colors.blue.shade400, 'Recovering'),
      _ => (Colors.green.shade600, 'Normal'),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

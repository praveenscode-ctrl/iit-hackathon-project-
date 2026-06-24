import 'package:flutter/material.dart';
import '../models/assignment_model.dart';
import 'package:intl/intl.dart';

class AssignmentCard extends StatelessWidget {
  final AssignmentModel assignment;
  final VoidCallback onTap;

  const AssignmentCard({super.key, required this.assignment, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final statusColor = switch (assignment.status) {
      'PUBLISHED' => Colors.green.shade600,
      'CLOSED' => Colors.grey.shade600,
      _ => Colors.orange.shade600, // DRAFT
    };

    String deadline = 'No deadline';
    if (assignment.deadlineAt != null) {
      deadline = DateFormat('d MMM yyyy, h:mm a').format(assignment.deadlineAt!.toLocal());
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      assignment.title,
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      assignment.status,
                      style: TextStyle(fontSize: 11, color: statusColor, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
              if (assignment.description != null) ...[
                const SizedBox(height: 6),
                Text(
                  assignment.description!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280)),
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.schedule, size: 14, color: Color(0xFF9CA3AF)),
                  const SizedBox(width: 4),
                  Text(deadline, style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                  const Spacer(),
                  Text(
                    assignment.submissionType,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

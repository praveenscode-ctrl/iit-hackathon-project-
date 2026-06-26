import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class CompletionBarChart extends StatelessWidget {
  final List<String> labels;
  final List<double> values;
  final String caption;

  const CompletionBarChart({
    super.key,
    required this.labels,
    required this.values,
    required this.caption,
  });

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 180,
          child: BarChart(
            BarChartData(
              maxY: 100,
              gridData: const FlGridData(show: false),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                leftTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (val, _) {
                      final i = val.toInt();
                      if (i < 0 || i >= labels.length) return const SizedBox();
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          labels[i].length > 8
                              ? '${labels[i].substring(0, 7)}…'
                              : labels[i],
                          style: const TextStyle(
                              fontSize: 10, color: Color(0xFF6B7280)),
                        ),
                      );
                    },
                  ),
                ),
              ),
              barGroups: List.generate(values.length, (i) {
                return BarChartGroupData(x: i, barRods: [
                  BarChartRodData(
                    toY: values[i],
                    color: const Color(0xFF1A56DB),
                    width: 18,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ]);
              }),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          caption,
          style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF)),
        ),
      ],
    );
  }
}

class StatusDonutChart extends StatelessWidget {
  final int submitted;
  final int pending;
  final int missed;
  final int late;

  const StatusDonutChart({
    super.key,
    required this.submitted,
    required this.pending,
    required this.missed,
    required this.late,
  });

  @override
  Widget build(BuildContext context) {
    final total = submitted + pending + missed + late;
    if (total == 0) return const SizedBox.shrink();

    return Column(
      children: [
        SizedBox(
          height: 150,
          child: PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: 35,
              sections: [
                PieChartSectionData(
                    value: submitted.toDouble(),
                    color: Colors.green.shade500,
                    title: '',
                    radius: 28),
                PieChartSectionData(
                    value: pending.toDouble(),
                    color: Colors.grey.shade400,
                    title: '',
                    radius: 28),
                PieChartSectionData(
                    value: missed.toDouble(),
                    color: Colors.red.shade400,
                    title: '',
                    radius: 28),
                PieChartSectionData(
                    value: late.toDouble(),
                    color: Colors.orange.shade400,
                    title: '',
                    radius: 28),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _dot(Colors.green.shade500, 'Submitted $submitted'),
            const SizedBox(width: 12),
            _dot(Colors.grey.shade400, 'Pending $pending'),
            const SizedBox(width: 12),
            _dot(Colors.red.shade400, 'Missed $missed'),
            const SizedBox(width: 12),
            _dot(Colors.orange.shade400, 'Late $late'),
          ],
        ),
      ],
    );
  }

  Widget _dot(Color c, String label) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
          const SizedBox(width: 4),
          Text(label,
              style: const TextStyle(fontSize: 10, color: Color(0xFF6B7280))),
        ],
      );
}

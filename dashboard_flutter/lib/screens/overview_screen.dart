part of '../main.dart';

class _Overview extends StatelessWidget {
  const _Overview({required this.store});
  final DashboardStore store;
  String val(String k, String fallback) => store._summary(k, fallback);
  @override
  Widget build(BuildContext context) {
    final latest = store.steps.reversed.take(24).toList().reversed.toList();
    final total = store.summaries.isEmpty ? '—' : val('n_tls_controlled', '—');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(
          builder: (c, box) {
            final n = box.maxWidth > 1150
                ? 6
                : box.maxWidth > 850
                ? 3
                : 2;
            return GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: n,
              childAspectRatio: 1.7,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              children: [
                _Metric(
                  title: 'SIMULATION STATUS',
                  value: store.runState.toUpperCase(),
                  icon: Icons.play_circle_outline,
                  color: _green,
                  sub: '${store.controller.toUpperCase()} controller',
                ),
                _Metric(
                  title: 'CONTROLLED JUNCTIONS',
                  value: total,
                  icon: Icons.alt_route,
                  color: _cyan,
                  sub: store.family == 'network'
                      ? 'Network-wide family'
                      : 'Single junction',
                ),
                _Metric(
                  title: 'ACTIVE VEHICLES',
                  value: _snapshotTotal(store.steps, 'vehicles'),
                  icon: Icons.directions_car_outlined,
                  color: _green,
                  sub: 'latest recorded network snapshot',
                ),
                _Metric(
                  title: 'WAITING VEHICLES',
                  value: _snapshotTotal(store.steps, 'halting'),
                  icon: Icons.hourglass_bottom,
                  color: _amber,
                  sub: 'sum of latest approach queues',
                ),
                _Metric(
                  title: 'AVG WAITING TIME',
                  value: '${val('avg_wait', '—')} s',
                  icon: Icons.hourglass_bottom,
                  color: _amber,
                  sub: 'recorded summary',
                ),
                _Metric(
                  title: 'THROUGHPUT',
                  value: val('throughput_veh_per_min', '—'),
                  icon: Icons.speed,
                  color: _cyan,
                  sub: 'vehicles / minute',
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: _Panel(
                title: 'NETWORK TRAFFIC FLOW',
                subtitle: 'Recorded approach telemetry across the selected run',
                child: latest.isEmpty
                    ? const _Empty(text: 'No steps.csv telemetry found')
                    : SizedBox(
                        height: 205,
                        child: LineChart(_lineData(latest)),
                      ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: _Panel(
                title: 'RUN INFORMATION',
                subtitle: store.runId,
                child: Column(
                  children: [
                    _Info('Family', store.family.toUpperCase()),
                    _Info('Controller', store.controller.toUpperCase()),
                    _Info('Scenario', store.scenario),
                    _Info(
                      'Seed',
                      store.status?['seed']?.toString() ?? val('seed', '—'),
                    ),
                    _Info(
                      'Simulated time',
                      '${store.status?['sim_time'] ?? val('sim_end_time', '—')} s',
                    ),
                    _Info('Simulation limit', '${store.status?['max_sim_s'] ?? '—'} s'),
                    _Info('Last update', store.status?['updated_utc']?.toString() ?? '—'),
                    _Info('Data source', store.mode),
                    _Info('Selected folder', store.root ?? 'No folder selected'),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _Panel(
                title: 'NETWORK CONGESTION',
                subtitle: 'Latest recorded junction observations',
                child: latest.isEmpty
                    ? const _Empty(text: 'No congestion telemetry')
                    : _TrafficMap(rows: latest),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _Panel(
                title: 'QUEUE SNAPSHOT',
                subtitle: 'Worst observed records in the loaded step sample',
                child: _QueueList(rows: latest),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

String _latest(List<Map<String, String>> rows, String key, String fallback) =>
    rows.isEmpty ? fallback : (rows.last[key] ?? fallback);

String _snapshotTotal(List<Map<String, String>> rows, String key) {
  if (rows.isEmpty) return '—';
  final times = rows
      .map((row) => double.tryParse(row['sim_time'] ?? ''))
      .whereType<double>();
  if (times.isEmpty) return _latest(rows, key, '—');
  final latestTime = times.reduce((a, b) => a > b ? a : b);
  final total = rows
      .where((row) => double.tryParse(row['sim_time'] ?? '') == latestTime)
      .map((row) => int.tryParse(row[key] ?? '') ?? 0)
      .fold<int>(0, (sum, value) => sum + value);
  return total.toString();
}

LineChartData _lineData(List<Map<String, String>> rows) {
  final points = <FlSpot>[];
  for (var i = 0; i < rows.length; i++) {
    final y = double.tryParse(rows[i]['halting'] ?? '');
    if (y != null) points.add(FlSpot(i.toDouble(), y));
  }
  return LineChartData(
    minY: 0,
    gridData: FlGridData(
      show: true,
      drawVerticalLine: false,
      getDrawingHorizontalLine: (_) =>
          const FlLine(color: _border, strokeWidth: .6),
    ),
    borderData: FlBorderData(show: false),
    titlesData: const FlTitlesData(
      leftTitles: AxisTitles(
        sideTitles: SideTitles(showTitles: true, reservedSize: 30),
      ),
      bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
    ),
    lineBarsData: [
      LineChartBarData(
        spots: points,
        isCurved: true,
        color: _cyan,
        barWidth: 2,
        dotData: const FlDotData(show: false),
        belowBarData: BarAreaData(
          show: true,
          color: _cyan.withValues(alpha: .10),
        ),
      ),
    ],
  );
}

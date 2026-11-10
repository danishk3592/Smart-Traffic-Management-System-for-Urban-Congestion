part of '../main.dart';

class _Monitoring extends StatefulWidget {
  const _Monitoring({required this.store});
  final DashboardStore store;
  @override
  State<_Monitoring> createState() => _MonitoringState();
}

class _MonitoringState extends State<_Monitoring> {
  String? selected;
  @override
  Widget build(BuildContext context) {
    final rows = widget.store.steps;
    final ids =
        rows
            .map((r) => r['intersection_id'] ?? '')
            .where((s) => s.isNotEmpty)
            .toSet()
            .toList()
          ..sort();
    selected = ids.contains(selected)
        ? selected
        : (ids.isEmpty ? null : ids.first);
    final chosen = rows.where((r) => r['intersection_id'] == selected).toList();
    final sampleTimes = chosen
        .map((r) => double.tryParse(r['sim_time'] ?? ''))
        .whereType<double>();
    final latestSimTime = sampleTimes.isEmpty
        ? null
        : sampleTimes.reduce((a, b) => a > b ? a : b);
    final latestApproaches = latestSimTime == null
        ? (chosen.isEmpty ? <Map<String, String>>[] : [chosen.last])
        : chosen
              .where(
                (r) => double.tryParse(r['sim_time'] ?? '') == latestSimTime,
              )
              .toList();
    final current = latestApproaches.isEmpty ? null : latestApproaches.last;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _Badge(label: 'READ ONLY', color: _green),
            const SizedBox(width: 12),
            if (ids.isNotEmpty)
              DropdownButton<String>(
                value: selected,
                dropdownColor: _panel2,
                underline: const SizedBox(),
                items: ids
                    .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                    .toList(),
                onChanged: (v) => setState(() => selected = v),
              ),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 2,
              child: _Panel(
                title: 'SIGNAL STATE',
                subtitle: selected ?? 'No junction selected',
                child: current == null
                    ? const _Empty(
                        text: 'Load step telemetry to inspect signal state',
                      )
                    : Row(
                        children: [
                          _TrafficLight(state: current['signal_state'] ?? '—'),
                          const SizedBox(width: 20),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _Info('Current phase', current['phase'] ?? '—'),
                                _Info(
                                  'Phase elapsed',
                                  '${current['phase_elapsed'] ?? '—'} s',
                                ),
                                _Info('Last action', current['action'] ?? '—'),
                                _Info(
                                  'Safety accepted',
                                  current['action_accepted'] ?? '—',
                                ),
                                _Info(
                                  'Congestion',
                                  current['congestion'] ?? '—',
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 3,
              child: _Panel(
                title: 'APPROACH TELEMETRY',
                subtitle: latestSimTime == null
                    ? 'Latest recorded approach sample'
                    : 'Latest sample • sim time ${latestSimTime.toStringAsFixed(1)} s',
                child: chosen.isEmpty
                    ? const _Empty(text: 'No approach rows for this junction')
                    : _DataTable(
                        columns: const [
                          'Approach',
                          'Vehicles',
                          'Queue',
                          'Mean speed',
                          'Wait',
                        ],
                        rows: latestApproaches
                            .map(
                              (r) => [
                                r['approach'] ?? '—',
                                r['vehicles'] ?? '—',
                                r['halting'] ?? '—',
                                '${r['mean_speed'] ?? '—'} m/s',
                                '${r['wait_time'] ?? '—'} s',
                              ],
                            )
                            .toList(),
                      ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _Panel(
          title: 'RECENT SIGNAL ACTIVITY',
          subtitle: 'Latest recorded phase and action events',
          child: rows.isEmpty
              ? const _Empty(text: 'No steps.csv history')
              : _DataTable(
                  columns: const [
                    'Time',
                    'Junction',
                    'Approach',
                    'Phase',
                    'Signal',
                    'Action',
                    'Accepted',
                  ],
                  rows: rows.reversed
                      .take(12)
                      .map(
                        (r) => [
                          r['sim_time'] ?? '—',
                          r['intersection_id'] ?? '—',
                          r['approach'] ?? '—',
                          r['phase'] ?? '—',
                          r['signal_state'] ?? '—',
                          r['action'] ?? '—',
                          r['action_accepted'] ?? '—',
                        ],
                      )
                      .toList(),
                ),
        ),
      ],
    );
  }
}

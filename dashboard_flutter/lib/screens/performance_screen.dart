part of '../main.dart';

class _Evaluation extends StatefulWidget {
  const _Evaluation({required this.store});
  final DashboardStore store;
  @override
  State<_Evaluation> createState() => _EvaluationState();
}

class _EvaluationState extends State<_Evaluation> {
  String milestone = 'M2', seedSet = 'final';
  String aggregation = 'headline', metric = 'travel_time';
  @override
  Widget build(BuildContext context) {
    final source = widget.store.comparisons
        .where(
          (r) =>
              (r['milestone'] ?? '').toUpperCase() == milestone &&
              (r['seed_set'] ?? '').toLowerCase() == seedSet,
        )
        .toList();
    final eligible = source.where((r) =>
      r['aggregation'] == aggregation && r['metric'] == metric && r['scope'] == 'all'
    ).toList();
    final actual = eligible.isNotEmpty && widget.store.mode == 'REAL FILES';
    final rows = eligible.where((r) => r['trip_basis'] == 'all').toList();
    final commonRows = metric == 'travel_time'
        ? eligible.where((r) => r['trip_basis'] == 'common').toList()
        : <Map<String, String>>[];
    final selected = rows.where((r) => r['controller'] == 'rl').firstOrNull ??
        rows.where((r) => r['controller'] == 'hybrid').firstOrNull;
    final targetStatus = selected?['target_met']?.toLowerCase();
    final coverage = widget.store.evaluationSummary(milestone, seedSet);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            _Filter(
              label: 'Milestone',
              value: milestone,
              values: const ['M1', 'M2'],
              onChanged: (v) => setState(() => milestone = v),
            ),
            const SizedBox(width: 12),
            _Filter(
              label: 'Evaluation set',
              value: seedSet,
              values: const ['dev', 'final'],
              onChanged: (v) => setState(() => seedSet = v),
            ),
            const SizedBox(width: 12),
            _Filter(
              label: 'Result row',
              value: aggregation,
              values: const ['headline', 'primary', 'scenario'],
              onChanged: (v) => setState(() => aggregation = v),
            ),
            const SizedBox(width: 12),
            _Filter(
              label: 'Metric',
              value: metric,
              values: const ['travel_time', 'waiting_time', 'time_loss', 'completion_rate', 'queue', 'throughput', 'teleports'],
              onChanged: (v) => setState(() => metric = v),
            ),
            const Spacer(),
            if (!actual) _Badge(label: 'SAVED FILES ONLY', color: _amber),
          ],
        ),
        const SizedBox(height: 14),
        if (milestone == 'M1')
          const _Notice(
            text:
                'Single-Junction Milestone — Not the Final Result. Provisional until metric confirmation.',
            warning: true,
          ),
        if (milestone == 'M2' && coverage != null)
          _Notice(
            text:
                'AI coverage: ${coverage['n_tls_ai']}/${coverage['n_tls_controlled']} (${coverage['ai_coverage']}) • provisional until P1',
            warning: false,
          ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (c, b) => GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: b.maxWidth > 1000 ? 6 : 3,
            childAspectRatio: 1.8,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            children: [
              _Metric(
                title: metric.toUpperCase(),
                value: '${selected?['mean'] ?? '—'} s',
                icon: Icons.schedule,
                color: _cyan,
                sub: 'selected evaluation row',
              ),
              _Metric(
                title: 'IMPROVEMENT VS FIXED',
                value: '${selected?['improvement_vs_fixed_pct'] ?? '—'}%',
                icon: Icons.trending_down,
                color: _green,
                sub: 'recorded comparison value',
              ),
              _Metric(
                title: 'AVG WAITING',
                value: '${widget.store._summary('avg_wait', '—')} s',
                icon: Icons.hourglass_bottom,
                color: _amber,
                sub: 'saved summary',
              ),
              _Metric(
                title: 'AVG QUEUE',
                value: widget.store._summary('avg_queue', '—'),
                icon: Icons.queue,
                color: _amber,
                sub: 'saved summary',
              ),
              _Metric(
                title: 'THROUGHPUT',
                value: widget.store._summary('throughput_veh_per_min', '—'),
                icon: Icons.speed,
                color: _cyan,
                sub: 'vehicles / minute',
              ),
              _Metric(
                title: '10% TARGET',
                value: targetStatus == null || targetStatus.isEmpty ? '—' : (targetStatus == 'true' ? 'MET' : 'NOT MET'),
                icon: Icons.flag_outlined,
                color: targetStatus == 'true'
                    ? _green
                    : _red,
                sub: 'target is not assumed',
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: _Panel(
                title: 'CONTROLLER COMPARISON',
                subtitle: 'Travel-time records as saved in comparison.csv',
                child: actual
                    ? _ComparisonChart(rows: rows)
                    : const _Empty(text: 'Run evaluation before comparison data is available'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: _Panel(
                title: 'EVALUATION RESULTS',
                subtitle: actual
                    ? 'Recorded outcome'
                    : 'No matching saved comparison rows',
                child: rows.isEmpty ? const _Empty(text: 'Load results/summary/comparison.csv to see evaluation results') : _DataTable(
                  columns: metric == 'travel_time'
                      ? const ['Controller', 'Censored mean', '95% CI', 'Common mean', 'Common set', 'Completion', 'Target']
                      : const ['Controller', 'Mean', '95% CI', 'Completion', 'Target'],
                  rows: rows
                      .map((r) {
                        final common = commonRows.where((c) =>
                          c['controller'] == r['controller'] &&
                          c['scenario'] == r['scenario'] &&
                          c['aggregation'] == r['aggregation']
                        ).firstOrNull;
                        final targetRaw = r['target_met']?.toLowerCase();
                        final target = targetRaw == null || targetRaw.isEmpty
                            ? '—'
                            : targetRaw == 'true' ? 'Met' : 'Not met';
                        if (metric != 'travel_time') {
                          return [
                            r['controller'] ?? '—',
                            r['mean'] ?? '—',
                            '${r['ci95_low'] ?? '—'} – ${r['ci95_high'] ?? '—'}',
                            r['completion_rate_mean'] ?? '—',
                            target,
                          ];
                        }
                        return [
                          r['controller'] ?? '—',
                          r['mean'] ?? '—',
                          '${r['ci95_low'] ?? '—'} – ${r['ci95_high'] ?? '—'}',
                          common?['mean'] ?? '—',
                          common?['n_trips_basis'] ?? '—',
                          r['completion_rate_mean'] ?? '—',
                          target,
                        ];
                      })
                      .toList(),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (milestone == 'M2')
          _Panel(
            title: 'JUNCTION AI COVERAGE & CONGESTION',
            subtitle: 'Per-junction records from junctions.csv',
            child: widget.store.junctions.isEmpty
                ? const _Empty(text: 'No junction-level evaluation data')
                : _DataTable(
                    columns: const [
                      'Junction',
                      'Controller',
                      'Avg queue',
                      'Avg wait',
                      'High congestion',
                      'PPO share',
                    ],
                    rows: widget.store.junctions
                        .map(
                          (r) => [
                            r['tls_id'] ?? '—',
                            r['controlled_by'] ?? '—',
                            r['avg_queue'] ?? '—',
                            r['avg_wait'] ?? '—',
                            r['frac_time_high_congestion'] ?? '—',
                            r['ppo_tick_share'] ?? '—',
                          ],
                        )
                        .toList(),
                  ),
          ),
      ],
    );
  }
}

class _ComparisonChart extends StatelessWidget {
  const _ComparisonChart({required this.rows});
  final List<Map<String, String>> rows;

  @override
  Widget build(BuildContext context) {
    final vals = rows
        .map((r) => double.tryParse(r['mean'] ?? '') ?? 0)
        .toList();
    return SizedBox(
      height: 220,
      child: BarChart(
        BarChartData(
          maxY:
              (vals.isEmpty ? 100 : vals.reduce((a, b) => a > b ? a : b)) * 1.2,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) =>
                const FlLine(color: _border, strokeWidth: .6),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: true, reservedSize: 36),
            ),
            rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (x, _) {
                  final i = x.toInt();
                  if (i < 0 || i >= rows.length) return const SizedBox();
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      (rows[i]['controller'] ?? '').toUpperCase(),
                      style: const TextStyle(fontSize: 9, color: _muted),
                    ),
                  );
                },
              ),
            ),
          ),
          barGroups: List.generate(
            rows.length,
            (i) => BarChartGroupData(
              x: i,
              barRods: [
                BarChartRodData(
                  toY: vals[i],
                  width: 22,
                  color: [_muted, _amber, _cyan][i % 3],
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(3),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

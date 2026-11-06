part of '../main.dart';

class _History extends StatelessWidget {
  const _History({required this.store});
  final DashboardStore store;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Panel(
        title: 'SAVED EXPERIMENT RUNS',
        subtitle: 'Discovered from results/raw/*/summary.csv',
        child: store.summaries.isEmpty
            ? const _Empty(
                text:
                    'No run summaries found. Choose the STMS project folder to load saved experiments.',
              )
            : _DataTable(
                columns: const [
                  'Run ID',
                  'Family',
                  'Controller',
                  'Scenario',
                  'Seed',
                  'Avg wait',
                  'Queue',
                  'Throughput',
                  'Commit',
                  'Metrics',
                ],
                rows: store.summaries
                    .map(
                      (r) => [
                        r['run_id'] ?? '—',
                        r['family'] ?? '—',
                        r['controller'] ?? '—',
                        r['scenario'] ?? '—',
                        r['seed'] ?? '—',
                        r['avg_wait'] ?? '—',
                        r['avg_queue'] ?? '—',
                        r['throughput_veh_per_min'] ?? '—',
                        r['git_commit'] ?? '—',
                        r['metrics_version'] ?? '—',
                      ],
                    )
                    .toList(),
              ),
      ),
      const SizedBox(height: 12),
      _Panel(
        title: 'MODEL CONFIGURATIONS',
        subtitle: 'Model config.json files are read from Ai/rl/models/',
        child: store.modelConfigs.isEmpty
            ? const _Empty(text: 'No model config.json files found under Ai/rl/models/')
            : _DataTable(
                columns: const ['Config file', 'Seeds', 'Reward weights', 'Git commit', 'Wall clock', 'TLS hash'],
                rows: store.modelConfigs.map((m) => [
                  m['path']?.toString() ?? '—',
                  m['seeds']?.toString() ?? '—',
                  m['reward_weights']?.toString() ?? '—',
                  m['git_commit']?.toString() ?? '—',
                  m['training_wall_clock_s']?.toString() ?? m['wall_clock_s']?.toString() ?? '—',
                  m['intended_tls_list_hash']?.toString() ?? '—',
                ]).toList(),
              ),
      ),
    ],
  );
}

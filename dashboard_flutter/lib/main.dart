import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:csv/csv.dart';
import 'package:file_picker/file_picker.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:path/path.dart' as p;

part 'screens/overview_screen.dart';
part 'screens/live_monitoring_screen.dart';
part 'screens/performance_screen.dart';
part 'screens/experiment_history_screen.dart';

const _bg = Color(0xff0d1322);
const _shell = Color(0xff080e1d);
const _panel = Color(0xff151b2b);
const _panel2 = Color(0xff191f2f);
const _border = Color(0xff303a4e);
const _cyan = Color(0xff00d2ff);
const _green = Color(0xff48d99e);
const _amber = Color(0xffffb547);
const _red = Color(0xffff6b6b);
const _muted = Color(0xff94a3b8);

final Stopwatch _processStartup = Stopwatch()..start();

void main(List<String> args) {
  _processStartup.start();
  final measurement = DashboardLoadMeasurement.fromArgs(args);
  final freshnessMeasurement = DashboardFreshnessMeasurement.fromArgs(args);
  if (measurement != null && freshnessMeasurement != null) {
    throw ArgumentError(
      'Page-load and live-freshness measurement modes are exclusive.',
    );
  }
  runApp(
    StmsApp(
      measurement: measurement,
      freshnessMeasurement: freshnessMeasurement,
    ),
  );
}

Future<File> _createSafeMeasurementFile(String outputPath) async {
  final requested = File(outputPath).absolute;
  final tempPath = p
      .normalize(await Directory.systemTemp.resolveSymbolicLinks())
      .toLowerCase();
  final parentPath = p
      .normalize(await requested.parent.resolveSymbolicLinks())
      .toLowerCase();
  final parentIsTemp = parentPath == tempPath;
  final parentIsUnderTemp = parentPath.startsWith('$tempPath${p.separator}');
  final filename = p.basename(requested.path);
  if ((!parentIsTemp && !parentIsUnderTemp) ||
      !filename.startsWith('stms_t54_') ||
      !filename.endsWith('.json')) {
    throw ArgumentError(
      'Measurement reports must be new stms_t54_*.json files under the OS temporary directory.',
    );
  }
  return requested.create(exclusive: true);
}

class DashboardLoadMeasurement {
  const DashboardLoadMeasurement(this.root, this.outputPath);

  final String root;
  final String outputPath;

  static DashboardLoadMeasurement? fromArgs(List<String> args) {
    String? value(String name) {
      final prefix = '$name=';
      for (final arg in args) {
        if (arg.startsWith(prefix)) return arg.substring(prefix.length);
      }
      return null;
    }

    final root = value('--t54-measure-root');
    final output = value('--t54-measure-output');
    if (root == null && output == null) return null;
    if (root == null || output == null || root.isEmpty || output.isEmpty) {
      throw ArgumentError(
        'Measurement mode requires both --t54-measure-root and --t54-measure-output.',
      );
    }
    return DashboardLoadMeasurement(root, output);
  }

  Future<File> createNewReportFile() async {
    return _createSafeMeasurementFile(outputPath);
  }
}

class DashboardFreshnessMeasurement {
  const DashboardFreshnessMeasurement(this.root, this.runId, this.outputPath);

  final String root;
  final String runId;
  final String outputPath;
  static const sampleTarget = 30;

  static DashboardFreshnessMeasurement? fromArgs(List<String> args) {
    String? value(String name) {
      final prefix = '$name=';
      for (final arg in args) {
        if (arg.startsWith(prefix)) return arg.substring(prefix.length);
      }
      return null;
    }

    final root = value('--t54-freshness-root');
    final runId = value('--t54-freshness-run-id');
    final output = value('--t54-freshness-output');
    if (root == null && runId == null && output == null) return null;
    if (root == null ||
        root.isEmpty ||
        runId == null ||
        runId.isEmpty ||
        output == null ||
        output.isEmpty) {
      throw ArgumentError(
        'Freshness mode requires --t54-freshness-root, --t54-freshness-run-id, and --t54-freshness-output.',
      );
    }
    return DashboardFreshnessMeasurement(root, runId, output);
  }

  Future<File> createNewReportFile() => _createSafeMeasurementFile(outputPath);
}

class StmsApp extends StatefulWidget {
  const StmsApp({
    super.key,
    this.initialStore,
    this.measurement,
    this.freshnessMeasurement,
  });
  final DashboardStore? initialStore;
  final DashboardLoadMeasurement? measurement;
  final DashboardFreshnessMeasurement? freshnessMeasurement;
  @override
  State<StmsApp> createState() => _StmsAppState();
}

class _StmsAppState extends State<StmsApp> {
  int _page = 0;
  late final DashboardStore _store;

  @override
  void initState() {
    super.initState();
    _store = widget.initialStore ?? DashboardStore();
    _store.addListener(_refresh);
    if (_store.root == null && !_store.hasData) _store.clearData();
    final measurement = widget.measurement;
    if (measurement != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) unawaited(_measureRealResultsLoad(measurement));
      });
    }
    final freshnessMeasurement = widget.freshnessMeasurement;
    if (freshnessMeasurement != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          unawaited(_startFreshnessMeasurement(freshnessMeasurement));
        }
      });
    }
  }

  Future<void> _measureRealResultsLoad(
    DashboardLoadMeasurement measurement,
  ) async {
    final startupMs = _processStartup.elapsedMicroseconds / 1000;
    final loadClock = Stopwatch()..start();
    try {
      await _store.loadFolder(measurement.root);
      if (_store.availableRuns.isEmpty || _store.summaries.isEmpty) {
        throw StateError('No real run summaries were loaded.');
      }
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        final report = {
          'schema_version': 1,
          'measurement': 'windows_release_real_results_first_data_frame',
          'root': measurement.root,
          'startup_to_initial_frame_ms': startupMs,
          'load_request_to_data_frame_ms': loadClock.elapsedMicroseconds / 1000,
          'run_count': _store.availableRuns.length,
          'summary_count': _store.summaries.length,
          'selected_run_id': _store.selectedRunId,
          'selected_summary_loaded': _store.selectedSummary != null,
          'load_error': _store.error,
        };
        await _writeMeasurementReport(measurement, report, successExitCode: 0);
      });
    } catch (error) {
      await _writeMeasurementReport(measurement, {
        'schema_version': 1,
        'error': error.toString(),
      }, successExitCode: 2);
    }
  }

  final List<Map<String, Object?>> _freshnessSamples = [];
  final Set<String> _freshnessSeen = {};
  bool _writingFreshnessReport = false;

  Future<void> _startFreshnessMeasurement(
    DashboardFreshnessMeasurement measurement,
  ) async {
    try {
      await _store.loadFolder(measurement.root);
      if (!_store.runIds.contains(measurement.runId)) {
        throw StateError(
          'Expected live run ${measurement.runId} was not discovered.',
        );
      }
      if (_store.selectedRunId != measurement.runId) {
        await _store.selectRun(measurement.runId);
      }
    } catch (error) {
      await _writeFreshnessReport(measurement, {
        'schema_version': 1,
        'error': error.toString(),
      }, successExitCode: 2);
    }
  }

  void _recordFreshnessAfterFrame() {
    final measurement = widget.freshnessMeasurement;
    final status = _store.status;
    if (measurement == null ||
        status == null ||
        _store.selectedRunId != measurement.runId ||
        status['run_id'] != measurement.runId ||
        status['state'] != 'running') {
      return;
    }
    final updatedUtc = status['updated_utc']?.toString() ?? '';
    if (updatedUtc.isEmpty || !_freshnessSeen.add(updatedUtc)) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final sourceUtc = DateTime.tryParse(updatedUtc)?.toUtc();
      if (sourceUtc == null) return;
      final renderedUtc = DateTime.now().toUtc();
      final ageMs = renderedUtc.difference(sourceUtc).inMicroseconds / 1000;
      _freshnessSamples.add({
        'source_updated_utc': updatedUtc,
        'rendered_frame_utc': renderedUtc.toIso8601String(),
        'rendered_last_update_text': status['updated_utc']?.toString() ?? '—',
        'sim_time': status['sim_time'],
        'age_ms': ageMs,
      });
      if (_freshnessSamples.length >=
              DashboardFreshnessMeasurement.sampleTarget &&
          !_writingFreshnessReport) {
        _writingFreshnessReport = true;
        unawaited(_finishFreshnessMeasurement(measurement));
      }
    });
  }

  Future<void> _finishFreshnessMeasurement(
    DashboardFreshnessMeasurement measurement,
  ) async {
    final ages =
        _freshnessSamples
            .map((sample) => sample['age_ms']! as num)
            .map((age) => age.toDouble())
            .toList()
          ..sort();
    final median = ages.length.isEven
        ? (ages[ages.length ~/ 2 - 1] + ages[ages.length ~/ 2]) / 2
        : ages[ages.length ~/ 2];
    await _writeFreshnessReport(measurement, {
      'schema_version': 1,
      'measurement': 'windows_release_live_status_post_frame_freshness',
      'run_id': measurement.runId,
      'sample_target': DashboardFreshnessMeasurement.sampleTarget,
      'sample_count': ages.length,
      'median_age_ms': median,
      'max_age_ms': ages.last,
      'samples': _freshnessSamples,
    }, successExitCode: 0);
  }

  Future<void> _writeFreshnessReport(
    DashboardFreshnessMeasurement measurement,
    Map<String, Object?> report, {
    required int successExitCode,
  }) async {
    try {
      final output = await measurement.createNewReportFile();
      await output.writeAsString(jsonEncode(report), flush: true);
      exit(successExitCode);
    } catch (error) {
      stderr.writeln('Could not write safe T5.4 freshness report: $error');
      exit(2);
    }
  }

  Future<void> _writeMeasurementReport(
    DashboardLoadMeasurement measurement,
    Map<String, Object?> report, {
    required int successExitCode,
  }) async {
    try {
      final output = await measurement.createNewReportFile();
      await output.writeAsString(jsonEncode(report), flush: true);
      exit(successExitCode);
    } catch (error) {
      stderr.writeln('Could not write safe T5.4 measurement report: $error');
      exit(2);
    }
  }

  void _refresh() {
    setState(() {});
    _recordFreshnessAfterFrame();
  }

  @override
  void dispose() {
    _store.removeListener(_refresh);
    _store.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'STMS Traffic Operations',
    theme: ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: _bg,
      colorScheme: const ColorScheme.dark(primary: _cyan, surface: _panel),
      fontFamily: 'Segoe UI',
      cardTheme: const CardThemeData(color: _panel, elevation: 0),
      dividerColor: _border,
      useMaterial3: true,
    ),
    home: Scaffold(
      body: Row(
        children: [
          _Sidebar(selected: _page, onSelect: (i) => setState(() => _page = i)),
          Expanded(
            child: Column(
              children: [
                _TopBar(store: _store, page: _page),
                Expanded(
                  child: Column(
                    children: [
                      if (_store.loading)
                        const LinearProgressIndicator(minHeight: 2),
                      Expanded(
                        child: _PageView(index: _page, store: _store),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

typedef DashboardSnapshotLoader =
    Future<Map<String, dynamic>> Function(
      String root,
      String? selectedRunId,
      Map<String, String> summaryFingerprints,
      Map<String, String> selectedFingerprints,
    );

class DashboardStore extends ChangeNotifier {
  DashboardStore({DashboardSnapshotLoader? snapshotLoader})
    : _snapshotLoader = snapshotLoader ?? _readDashboardSnapshotInIsolate;

  final DashboardSnapshotLoader _snapshotLoader;
  String? root;
  String mode = 'NO DATA';
  bool loading = false;
  String? error;
  List<Map<String, String>> steps = [];
  List<Map<String, String>> summaries = [];
  List<Map<String, String>> junctions = [];
  List<Map<String, String>> comparisons = [];
  List<Map<String, String>> evaluationSummaries = [];
  List<Map<String, dynamic>> modelConfigs = [];
  List<String> availableRuns = [];
  Map<String, dynamic>? status;
  bool invalidStatus = false;
  String? selectedRunId;
  Timer? _timer;
  bool _refreshing = false;
  bool _refreshQueued = false;
  bool _disposed = false;
  final Map<String, String> _summaryFingerprints = {};
  final Map<String, List<Map<String, String>>> _summariesByRun = {};
  final Map<String, String> _selectedFingerprints = {};
  String? _selectedFilesRunId;

  bool get hasData => steps.isNotEmpty || summaries.isNotEmpty;
  String get runId => status?['run_id']?.toString() ?? _summary('run_id', '—');
  String get family => status?['family']?.toString() ?? _summary('family', '—');
  String get controller =>
      status?['controller']?.toString() ?? _summary('controller', '—');
  String get scenario =>
      status?['scenario']?.toString() ?? _summary('scenario', '—');
  Map<String, String>? get selectedSummary {
    final runId = selectedRunId;
    if (runId == null) return null;
    for (final row in summaries) {
      if (row['run_id'] == runId) return row;
    }
    return null;
  }

  String _summary(String key, String fallback) =>
      selectedSummary?[key] ?? fallback;
  List<String> get runIds => availableRuns;

  Future<void> selectRun(String runId) async {
    selectedRunId = runId;
    _clearSelectedRunData();
    _selectedFilesRunId = runId;
    _selectedFingerprints.clear();
    notifyListeners();
    await refreshNow();
  }

  void _clearSelectedRunData() {
    status = null;
    invalidStatus = false;
    steps = [];
    junctions = [];
    summaries = summaries
        .where((row) => row['run_id'] != selectedRunId)
        .toList();
  }

  void clearData() {
    mode = 'NO DATA';
    root = null;
    error = null;
    status = null;
    invalidStatus = false;
    steps = [];
    summaries = [];
    junctions = [];
    comparisons = [];
    evaluationSummaries = [];
    modelConfigs = [];
    availableRuns = [];
    notifyListeners();
  }

  Future<void> chooseFolder() async {
    final selected = await FilePicker.platform.getDirectoryPath(
      dialogTitle: 'Select STMS project or results folder',
    );
    if (selected == null) return;
    await loadFolder(selected);
  }

  Future<void> loadFolder(String folder) async {
    final changedRoot = root != folder;
    if (changedRoot) {
      selectedRunId = null;
      steps = [];
      summaries = [];
      junctions = [];
      status = null;
      invalidStatus = false;
      _summaryFingerprints.clear();
      _summariesByRun.clear();
      _selectedFingerprints.clear();
      _selectedFilesRunId = null;
    }
    loading = true;
    error = null;
    root = folder;
    mode = 'REAL FILES';
    notifyListeners();
    try {
      await refreshNow();
      _timer ??= Timer.periodic(
        const Duration(seconds: 1),
        (_) => refreshNow(),
      );
      if (!hasData) {
        error ??=
            'No compatible STMS CSV/JSON data found under ${p.join(folder, 'results')}.';
      }
    } catch (e) {
      error = 'Could not read selected folder: $e';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> refreshNow() async {
    if (_disposed || root == null) return;
    if (_refreshing) {
      _refreshQueued = true;
      return;
    }
    _refreshing = true;
    try {
      final requestedRunId = selectedRunId;
      if (_selectedFilesRunId != requestedRunId) {
        _selectedFilesRunId = requestedRunId;
        _selectedFingerprints.clear();
        steps = [];
        junctions = [];
      }
      final snapshotRoot = root!;
      final summaryFingerprints = Map<String, String>.from(
        _summaryFingerprints,
      );
      final selectedFingerprints = Map<String, String>.from(
        _selectedFingerprints,
      );
      final snapshot = await _snapshotLoader(
        snapshotRoot,
        requestedRunId,
        summaryFingerprints,
        selectedFingerprints,
      );
      if (_disposed) return;
      availableRuns = List<String>.from(snapshot['runIds'] as List);
      selectedRunId = snapshot['selectedRunId'] as String?;
      if (_selectedFilesRunId != selectedRunId) {
        _selectedFilesRunId = selectedRunId;
        _selectedFingerprints.clear();
        steps = [];
        junctions = [];
      }
      final fingerprints = Map<String, String>.from(
        snapshot['fingerprints'] as Map,
      );
      final changed = Map<String, dynamic>.from(
        snapshot['changedSummaries'] as Map,
      );
      _summaryFingerprints
        ..clear()
        ..addAll(fingerprints);
      _summariesByRun.removeWhere((id, _) => !fingerprints.containsKey(id));
      for (final entry in changed.entries) {
        _summariesByRun[entry.key] = (entry.value as List)
            .cast<Map<String, String>>();
      }
      summaries = [for (final id in availableRuns) ...?_summariesByRun[id]];
      _selectedFingerprints
        ..clear()
        ..addAll(
          Map<String, String>.from(snapshot['selectedFingerprints'] as Map),
        );
      if (snapshot['stepsChanged'] as bool) {
        steps = (snapshot['steps'] as List).cast<Map<String, String>>();
      }
      if (snapshot['junctionsChanged'] as bool) {
        junctions = (snapshot['junctions'] as List).cast<Map<String, String>>();
      }
      status = snapshot['status'] as Map<String, dynamic>?;
      invalidStatus = snapshot['invalidStatus'] as bool;
      comparisons = (snapshot['comparisons'] as List)
          .cast<Map<String, String>>();
      evaluationSummaries = (snapshot['evaluationSummaries'] as List)
          .cast<Map<String, String>>();
      modelConfigs = (snapshot['modelConfigs'] as List)
          .cast<Map<String, dynamic>>();
      error = snapshot['error'] as String?;
    } catch (e) {
      error = 'Some data could not be parsed: $e';
      // Never leave the previous run's metrics on screen after a failed scan.
      steps = [];
      junctions = [];
      status = null;
      invalidStatus = true;
      summaries = summaries
          .where((row) => row['run_id'] != selectedRunId)
          .toList();
      _summariesByRun.remove(selectedRunId);
    } finally {
      _refreshing = false;
      if (!_disposed) notifyListeners();
      if (!_disposed && _refreshQueued) {
        _refreshQueued = false;
        unawaited(refreshNow());
      }
    }
  }

  String get runState {
    if (invalidStatus) return 'no data';
    if (status == null) return hasData ? 'finished' : 'no data';
    final state = status!['state']?.toString() ?? 'no data';
    if (state == 'running') {
      final updated = DateTime.tryParse(
        status!['updated_utc']?.toString() ?? '',
      );
      if (updated != null &&
          DateTime.now().toUtc().difference(updated).inSeconds > 15) {
        return 'stale';
      }
    }
    return state;
  }

  Map<String, String>? evaluationSummary(String milestone, String seedSet) =>
      evaluationSummaries
          .where(
            (row) =>
                row['milestone'] == milestone && row['seed_set'] == seedSet,
          )
          .firstOrNull;

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    super.dispose();
  }
}

Future<Map<String, dynamic>> _readDashboardSnapshotInIsolate(
  String root,
  String? requestedRunId,
  Map<String, String> previousFingerprints,
  Map<String, String> previousSelectedFingerprints,
) => Isolate.run(
  () => _readDashboardSnapshot(
    root,
    requestedRunId,
    previousFingerprints,
    previousSelectedFingerprints,
  ),
);

Future<Map<String, dynamic>> _readDashboardSnapshot(
  String root,
  String? requestedRunId,
  Map<String, String> previousFingerprints,
  Map<String, String> previousSelectedFingerprints,
) async {
  final raw = Directory(p.join(root, 'results', 'raw'));
  final runs = <({String id, String path, DateTime modified})>[];
  if (await raw.exists()) {
    final directories = <Directory>[];
    await for (final entity in raw.list(followLinks: false)) {
      if (entity is Directory) directories.add(entity);
    }
    for (var offset = 0; offset < directories.length; offset += 64) {
      final batch = directories.skip(offset).take(64);
      final discovered = await Future.wait(batch.map(_describeRun));
      runs.addAll(
        discovered.whereType<({String id, String path, DateTime modified})>(),
      );
    }
  }
  runs.sort((a, b) {
    final byModified = b.modified.compareTo(a.modified);
    return byModified != 0 ? byModified : b.id.compareTo(a.id);
  });
  final runIds = runs.map((run) => run.id).toList();
  final selectedId = runIds.contains(requestedRunId)
      ? requestedRunId
      : (runs.isEmpty ? null : runs.first.id);

  final fingerprints = <String, String>{};
  final changedSummaries = <String, List<Map<String, String>>>{};
  for (var offset = 0; offset < runs.length; offset += 64) {
    final batch = runs.skip(offset).take(64);
    final summaries = await Future.wait(
      batch.map((run) async {
        final file = File(p.join(run.path, 'summary.csv'));
        try {
          final stat = await file.stat();
          if (stat.type != FileSystemEntityType.file) return null;
          final fingerprint =
              '${stat.modified.microsecondsSinceEpoch}:${stat.size}';
          final rows = previousFingerprints[run.id] == fingerprint
              ? null
              : await _readCsvSafely(file);
          return (run.id, fingerprint, rows);
        } on FileSystemException {
          // Missing or locked files are retried on the next scan.
          return null;
        }
      }),
    );
    for (final entry
        in summaries
            .whereType<(String, String, List<Map<String, String>>?)>()) {
      fingerprints[entry.$1] = entry.$2;
      if (entry.$3 != null) changedSummaries[entry.$1] = entry.$3!;
    }
  }

  var steps = <Map<String, String>>[];
  var junctions = <Map<String, String>>[];
  var stepsChanged = false;
  var junctionsChanged = false;
  final selectedFingerprints = <String, String>{};
  Map<String, dynamic>? status;
  var invalidStatus = false;
  String? error;
  if (selectedId != null) {
    final selected = runs.firstWhere((run) => run.id == selectedId);
    for (final name in ['steps.csv', 'junctions.csv']) {
      final file = File(p.join(selected.path, name));
      final cacheKey = '$selectedId/$name';
      try {
        final before = await file.stat();
        if (before.type != FileSystemEntityType.file) continue;
        final fingerprint =
            '${before.modified.microsecondsSinceEpoch}:${before.size}';
        selectedFingerprints[cacheKey] = fingerprint;
        if (previousSelectedFingerprints[cacheKey] == fingerprint) continue;
        final rows = await _readCsvSafely(file);
        final after = await file.stat();
        if (before.size != after.size || before.modified != after.modified) {
          selectedFingerprints.remove(cacheKey);
        }
        if (name == 'steps.csv') {
          steps = rows;
          stepsChanged = true;
        } else {
          junctions = rows;
          junctionsChanged = true;
        }
      } on FileSystemException {
        selectedFingerprints.remove(cacheKey);
        if (name == 'steps.csv') {
          stepsChanged = true;
        } else {
          junctionsChanged = true;
        }
      }
    }
    final statusFile = File(p.join(selected.path, 'status.json'));
    try {
      if (await statusFile.exists()) {
        final decoded = jsonDecode(await statusFile.readAsString());
        const required = {
          'schema_version',
          'run_id',
          'state',
          'family',
          'controller',
          'scenario',
          'seed',
          'sim_time',
          'max_sim_s',
          'n_tls_controlled',
          'started_utc',
          'updated_utc',
          'error',
        };
        if (decoded is Map<String, dynamic> &&
            decoded.keys.toSet().containsAll(required) &&
            decoded['schema_version'] == 1 &&
            decoded['run_id'] == selectedId &&
            const {
              'running',
              'finished',
              'failed',
            }.contains(decoded['state'])) {
          status = decoded;
        } else {
          invalidStatus = true;
          error = 'The selected run has an invalid or mismatched status.json.';
        }
      }
    } on FormatException {
      invalidStatus = true;
      error = 'The selected run has an incomplete status.json file.';
    } on FileSystemException {
      invalidStatus = true;
      error = 'The selected run status file is being updated; retrying.';
    }
    if (error == null && status == null && steps.isEmpty && junctions.isEmpty) {
      error = 'The selected run is incomplete; waiting for readable telemetry.';
    }
  }

  final comparisons = await _readCsvSafely(
    File(p.join(root, 'results', 'summary', 'comparison.csv')),
  );
  final evaluationSummaries = await _readCsvSafely(
    File(p.join(root, 'results', 'summary', 'summary.csv')),
  );
  final modelConfigs = <Map<String, dynamic>>[];
  final modelRoot = Directory(p.join(root, 'Ai', 'rl', 'models'));
  try {
    if (await modelRoot.exists()) {
      await for (final entity in modelRoot.list(followLinks: false)) {
        if (entity is! Directory) continue;
        final configFile = File(p.join(entity.path, 'config.json'));
        try {
          final config = jsonDecode(await configFile.readAsString());
          if (config is Map<String, dynamic>) {
            modelConfigs.add({
              'path': p.relative(configFile.path, from: root),
              ...config,
            });
          }
        } on FileSystemException {
          // A partially written config is ignored until a later refresh.
        } on FormatException {
          // A partially written config is ignored until a later refresh.
        }
      }
    }
  } on FileSystemException {
    error ??= 'Model configuration files are temporarily unavailable.';
  }

  return {
    'runIds': runIds,
    'selectedRunId': selectedId,
    'fingerprints': fingerprints,
    'changedSummaries': changedSummaries,
    'selectedFingerprints': selectedFingerprints,
    'steps': steps,
    'junctions': junctions,
    'stepsChanged': stepsChanged,
    'junctionsChanged': junctionsChanged,
    'status': status,
    'invalidStatus': invalidStatus,
    'comparisons': comparisons,
    'evaluationSummaries': evaluationSummaries,
    'modelConfigs': modelConfigs,
    'error': error,
  };
}

Future<({String id, String path, DateTime modified})?> _describeRun(
  Directory directory,
) async {
  try {
    final stat = await directory.stat();
    return (
      id: p.basename(directory.path),
      path: directory.path,
      modified: stat.modified,
    );
  } on FileSystemException {
    // Ignore a folder that is being created or removed during discovery.
    return null;
  }
}

Future<List<Map<String, String>>> _readCsvSafely(File file) async {
  try {
    if (!await file.exists()) return [];
    return await _parseCsv(file);
  } on FileSystemException {
    return [];
  } on FormatException {
    return [];
  }
}

Future<List<Map<String, String>>> _parseCsv(File file) async {
  var text = await file.readAsString();
  if (!text.endsWith('\n')) {
    final lastNewline = text.lastIndexOf('\n');
    if (lastNewline < 0) return [];
    text = text.substring(0, lastNewline + 1);
  }
  final rows = const CsvToListConverter(
    shouldParseNumbers: false,
    eol: '\n',
  ).convert(text);
  if (rows.isEmpty) return [];
  final headers = rows.first.map((e) => e.toString().trim()).toList();
  final aggregateSummary =
      p.basename(file.path) == 'summary.csv' &&
      p.basename(p.dirname(file.path)) == 'summary';
  final required = aggregateSummary
      ? {
          'milestone',
          'seed_set',
          'n_rl_cells',
          'n_tls_ai',
          'n_tls_controlled',
          'ai_coverage',
          'model_sha256',
        }
      : switch (p.basename(file.path)) {
          'steps.csv' => {
            'run_id',
            'controller',
            'scenario',
            'seed',
            'sim_time',
            'intersection_id',
            'approach',
            'vehicles',
            'halting',
            'mean_speed',
            'wait_time',
            'phase',
            'phase_elapsed',
            'signal_state',
            'action',
            'action_accepted',
            'congestion',
          },
          'junctions.csv' => {
            'run_id',
            'controller',
            'scenario',
            'seed',
            'tls_id',
            'controlled_by',
            'avg_queue',
            'max_queue',
            'avg_wait',
            'frac_time_high_congestion',
            'throughput_veh_per_min',
            'n_switches',
            'n_forced_max_green',
            'n_illegal_actions',
            'n_hold_overridden',
            'fallback_activations',
            'n_ticks',
            'ppo_tick_share',
          },
          'comparison.csv' => {
            'milestone',
            'scenario',
            'aggregation',
            'controller',
            'metric',
            'scope',
            'trip_basis',
            'mean',
            'std',
            'ci95_low',
            'ci95_high',
            'n_seeds',
            'n_trips_basis',
            'completion_rate_mean',
            'seed_set',
            'improvement_vs_fixed_pct',
            'improvement_vs_rule_pct',
            'target_met',
          },
          'summary.csv' => {
            'run_id',
            'controller',
            'scenario',
            'seed',
            'git_commit',
            'config_hash',
            'metrics_version',
            'n_trips',
            'n_trips_junction',
            'n_completed',
            'n_unfinished',
            'completion_rate',
            'completion_rate_junction',
            'avg_travel_time_completed',
            'avg_travel_time_censored',
            'avg_travel_time_junction_completed',
            'avg_travel_time_junction_censored',
            'avg_wait',
            'avg_time_loss',
            'avg_depart_delay',
            'avg_queue',
            'avg_speed',
            'throughput_veh_per_min',
            'frac_time_high_congestion',
            'teleports',
            'sim_end_time',
            'wall_clock_s',
            'family',
            'n_tls_controlled',
            'n_tls_ai',
            'ai_coverage',
            'avg_junction_queue_mean',
            'worst_junction_avg_queue',
          },
          _ => <String>{},
        };
  if (!headers.toSet().containsAll(required)) {
    throw FormatException(
      'Unexpected ${p.basename(file.path)} schema; required columns are missing.',
    );
  }
  final records = rows
      .skip(1)
      .where((row) => row.length == headers.length)
      .map(
        (row) => Map<String, String>.fromIterables(
          headers,
          row.map((e) => e.toString().trim()),
        ),
      )
      .toList();
  if (p.basename(file.path) == 'summary.csv' &&
      !aggregateSummary &&
      records.any((record) => record['metrics_version'] != '1')) {
    throw FormatException('Unsupported metrics_version in ${file.path}.');
  }
  return records;
}

const _titles = [
  'Traffic Operations Overview',
  'Live Signal & Traffic Monitoring',
  'Performance & Controller Evaluation',
  'Experiment History',
];

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.selected, required this.onSelect});
  final int selected;
  final ValueChanged<int> onSelect;
  static const _icons = [
    Icons.dashboard_outlined,
    Icons.traffic_outlined,
    Icons.query_stats,
    Icons.history,
  ];
  @override
  Widget build(BuildContext context) => Container(
    width: 224,
    color: _shell,
    padding: const EdgeInsets.fromLTRB(14, 18, 14, 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: _cyan.withValues(alpha: .14),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.alt_route, color: _cyan),
            ),
            const SizedBox(width: 6),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'STMS',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.5,
                  ),
                ),
                Text(
                  'TRAFFIC SYSTEMS',
                  style: TextStyle(
                    fontSize: 8,
                    color: _muted,
                    letterSpacing: .8,
                  ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 32),
        const Text(
          'OPERATIONS',
          style: TextStyle(
            fontSize: 10,
            color: _muted,
            letterSpacing: 1.4,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 10),
        ...List.generate(
          4,
          (i) => Padding(
            padding: const EdgeInsets.only(bottom: 5),
            child: InkWell(
              borderRadius: BorderRadius.circular(6),
              onTap: () => onSelect(i),
              child: Container(
                height: 42,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: selected == i
                      ? const Color(0xff18283a)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                  border: selected == i
                      ? const Border(left: BorderSide(color: _cyan, width: 2))
                      : null,
                ),
                child: Row(
                  children: [
                    Icon(
                      _icons[i],
                      size: 18,
                      color: selected == i ? _cyan : _muted,
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: Text(
                        [
                          'Overview',
                          'Live Monitoring',
                          'Performance',
                          'Experiment History',
                        ][i],
                        style: TextStyle(
                          fontSize: 12,
                          color: selected == i ? Colors.white : _muted,
                          fontWeight: selected == i
                              ? FontWeight.w600
                              : FontWeight.w400,
                        ),
                      ),
                    ),
                    if (i == 1) const _Dot(color: _green),
                  ],
                ),
              ),
            ),
          ),
        ),
        const Spacer(),
        Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
            color: _panel,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: _border),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'READ-ONLY MODE',
                style: TextStyle(
                  color: _green,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1,
                ),
              ),
              SizedBox(height: 5),
              Text(
                'Connected to local result files',
                style: TextStyle(color: _muted, fontSize: 10),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'STMS DASHBOARD  •  v1.0',
          style: TextStyle(
            color: Color(0xff536176),
            fontSize: 9,
            letterSpacing: .7,
          ),
        ),
      ],
    ),
  );
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.store, required this.page});
  final DashboardStore store;
  final int page;
  @override
  Widget build(BuildContext context) => Container(
    height: 62,
    padding: const EdgeInsets.symmetric(horizontal: 24),
    decoration: const BoxDecoration(
      color: _shell,
      border: Border(bottom: BorderSide(color: _border)),
    ),
    child: Row(
      children: [
        Icon(Icons.grid_view_rounded, size: 15, color: _muted),
        const SizedBox(width: 10),
        Text(
          'CONTROL ROOM  /  ${_titles[page].toUpperCase()}',
          style: const TextStyle(
            fontSize: 10,
            letterSpacing: 1.1,
            color: _muted,
          ),
        ),
        const Spacer(),
        _Badge(
          label: store.mode,
          color: store.mode == 'NO DATA' ? _amber : _cyan,
        ),
        if (store.runIds.isNotEmpty) ...[
          const SizedBox(width: 10),
          DropdownButton<String>(
            value: store.runIds.contains(store.selectedRunId)
                ? store.selectedRunId
                : null,
            hint: const Text(
              'Select run',
              style: TextStyle(fontSize: 10, color: _muted),
            ),
            underline: const SizedBox(),
            dropdownColor: _panel2,
            items: store.runIds
                .map(
                  (id) => DropdownMenuItem(
                    value: id,
                    child: SizedBox(
                      width: 170,
                      child: Text(
                        id,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ),
                )
                .toList(),
            onChanged: (id) {
              if (id != null) store.selectRun(id);
            },
          ),
        ],
        const SizedBox(width: 12),
        Text(
          DateFormat('MMM d, yyyy  •  HH:mm:ss').format(DateTime.now()),
          style: const TextStyle(
            fontFamily: 'Consolas',
            fontSize: 11,
            color: _muted,
          ),
        ),
        const SizedBox(width: 12),
        IconButton(
          tooltip: 'Choose project folder',
          onPressed: store.chooseFolder,
          icon: const Icon(Icons.folder_open_outlined, size: 19, color: _cyan),
        ),
      ],
    ),
  );
}

class _PageView extends StatelessWidget {
  const _PageView({required this.index, required this.store});
  final int index;
  final DashboardStore store;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(24, 22, 24, 28),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _titles[index],
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -.4,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    [
                      'Network status, congestion, and traffic flow at a glance.',
                      'Inspect recorded signal phases and approach-level telemetry.',
                      'Recorded controller performance and evaluation outcomes.',
                      'Browse saved simulation runs and controller configurations.',
                    ][index],
                    style: const TextStyle(color: _muted, fontSize: 12),
                  ),
                ],
              ),
            ),
            if (index == 0 || index == 1)
              _Badge(
                label:
                    '${store.family.toUpperCase()}  •  ${store.runState.toUpperCase()}',
                color: store.runState == 'finished' ? _green : _amber,
              ),
          ],
        ),
        const SizedBox(height: 20),
        if (store.error != null) _Notice(text: store.error!, warning: true),
        if (store.loading)
          const LinearProgressIndicator(
            minHeight: 2,
            color: _cyan,
            backgroundColor: _panel,
          ),
        if (index == 0)
          _Overview(store: store)
        else if (index == 1)
          _Monitoring(store: store)
        else if (index == 2)
          _Evaluation(store: store)
        else
          _History(store: store),
      ],
    ),
  );
}

class _TrafficMap extends StatelessWidget {
  const _TrafficMap({required this.rows});
  final List<Map<String, String>> rows;
  @override
  Widget build(BuildContext context) {
    final ids = rows.map((r) => r['intersection_id'] ?? '').toSet().toList();
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: ids.take(24).map((id) {
        final r = rows.lastWhere((e) => e['intersection_id'] == id);
        final con = (r['congestion'] ?? '').toLowerCase();
        final col = con == 'high'
            ? _red
            : con == 'medium'
            ? _amber
            : _green;
        return Container(
          width: 92,
          height: 62,
          decoration: BoxDecoration(
            color: _bg,
            border: Border.all(color: col.withValues(alpha: .55)),
            borderRadius: BorderRadius.circular(5),
          ),
          padding: const EdgeInsets.all(8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                id,
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                softWrap: false,
                overflow: TextOverflow.ellipsis,
              ),
              const Spacer(),
              Row(
                children: [
                  _Dot(color: col),
                  const SizedBox(width: 5),
                  Expanded(
                    child: Text(
                      '${r['halting'] ?? '—'} queued',
                      style: const TextStyle(fontSize: 9, color: _muted),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _QueueList extends StatelessWidget {
  const _QueueList({required this.rows});
  final List<Map<String, String>> rows;

  @override
  Widget build(BuildContext context) {
    final list = [...rows]
      ..sort(
        (a, b) => (int.tryParse(b['halting'] ?? '0') ?? 0).compareTo(
          int.tryParse(a['halting'] ?? '0') ?? 0,
        ),
      );
    return Column(
      children: list
          .take(5)
          .map(
            (r) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      r['intersection_id'] ?? '—',
                      style: const TextStyle(fontSize: 11),
                    ),
                  ),
                  Expanded(
                    flex: 2,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value:
                            ((double.tryParse(r['halting'] ?? '0') ?? 0) / 20)
                                .clamp(0, 1),
                        color: _amber,
                        backgroundColor: _border,
                        minHeight: 5,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    r['halting'] ?? '—',
                    style: const TextStyle(fontFamily: 'Consolas'),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}

class _TrafficLight extends StatelessWidget {
  const _TrafficLight({required this.state});
  final String state;

  @override
  Widget build(BuildContext context) {
    final s = state.toLowerCase();
    final lamps = [('r', _red), ('y', _amber), ('g', _green)];
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: _shell,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: _border),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final lamp in lamps)
            Padding(
              padding: const EdgeInsets.all(4),
              child: Container(
                width: 23,
                height: 23,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: s.contains(lamp.$1)
                      ? lamp.$2
                      : lamp.$2.withValues(alpha: .15),
                  border: Border.all(color: lamp.$2.withValues(alpha: .6)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    required this.sub,
  });
  final String title, value, sub;
  final IconData icon;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(
      color: _panel,
      borderRadius: BorderRadius.circular(6),
      border: Border.all(color: _border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 15, color: color),
            const SizedBox(width: 7),
            Expanded(
              child: Text(
                title,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 9,
                  color: _muted,
                  letterSpacing: .8,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const Spacer(),
        Text(
          value,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: value.length > 12 ? 16 : 22,
            fontFamily: 'Consolas',
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
        const SizedBox(height: 3),
        Text(
          sub,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 9, color: _muted),
        ),
      ],
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.subtitle});
  final String title;
  final String? subtitle;
  final Widget child;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: _panel,
      borderRadius: BorderRadius.circular(6),
      border: Border.all(color: _border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .7,
                ),
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: const TextStyle(color: _muted, fontSize: 9),
              ),
          ],
        ),
        const SizedBox(height: 4),
        const Divider(height: 12),
        child,
      ],
    ),
  );
}

class _Info extends StatelessWidget {
  const _Info(this.label, this.value);
  final String label, value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 11, color: _muted),
          ),
        ),
        Flexible(
          child: Text(
            value,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.right,
            style: const TextStyle(fontSize: 11, fontFamily: 'Consolas'),
          ),
        ),
      ],
    ),
  );
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});
  final String label;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .10),
      borderRadius: BorderRadius.circular(4),
      border: Border.all(color: color.withValues(alpha: .35)),
    ),
    child: Text(
      label,
      style: TextStyle(
        fontFamily: 'Consolas',
        fontSize: 9,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: .5,
      ),
    ),
  );
}

class _Dot extends StatelessWidget {
  const _Dot({required this.color});
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    width: 7,
    height: 7,
    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
  );
}

class _Empty extends StatelessWidget {
  const _Empty({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 12),
    child: Center(
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: const TextStyle(color: _muted, fontSize: 11),
      ),
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, required this.warning});
  final String text;
  final bool warning;
  @override
  Widget build(BuildContext context) {
    final c = warning ? _amber : _cyan;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: c.withValues(alpha: .08),
        border: Border.all(color: c.withValues(alpha: .3)),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(text, style: TextStyle(color: c, fontSize: 11)),
    );
  }
}

class _DataTable extends StatelessWidget {
  const _DataTable({required this.columns, required this.rows});
  final List<String> columns;
  final List<List<String>> rows;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, box) {
      final colWidth = (box.maxWidth / columns.length)
          .clamp(80, 210)
          .toDouble();
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columnSpacing: 14,
          horizontalMargin: 6,
          dataRowMinHeight: 34,
          dataRowMaxHeight: 42,
          headingRowHeight: 32,
          columns: columns
              .map(
                (c) => DataColumn(
                  label: SizedBox(
                    width: colWidth,
                    child: Text(
                      c.toUpperCase(),
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                        letterSpacing: .5,
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
          rows: rows
              .map(
                (row) => DataRow(
                  cells: List.generate(
                    columns.length,
                    (i) => DataCell(
                      SizedBox(
                        width: colWidth,
                        child: Text(
                          i < row.length ? row[i] : '—',
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 10,
                            fontFamily: 'Consolas',
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      );
    },
  );
}

class _Filter extends StatelessWidget {
  const _Filter({
    required this.label,
    required this.value,
    required this.values,
    required this.onChanged,
  });
  final String label, value;
  final List<String> values;
  final ValueChanged<String> onChanged;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Text('$label  ', style: const TextStyle(color: _muted, fontSize: 10)),
      DropdownButton<String>(
        value: value,
        dropdownColor: _panel2,
        underline: const SizedBox(),
        items: values
            .map(
              (v) => DropdownMenuItem(
                value: v,
                child: Text(
                  v.toUpperCase(),
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            )
            .toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    ],
  );
}

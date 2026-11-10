import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:stms_dashboard/main.dart';

const _summaryHeader =
    'run_id,controller,scenario,seed,git_commit,config_hash,metrics_version,n_trips,n_trips_junction,n_completed,n_unfinished,completion_rate,completion_rate_junction,avg_travel_time_completed,avg_travel_time_censored,avg_travel_time_junction_completed,avg_travel_time_junction_censored,avg_wait,avg_time_loss,avg_depart_delay,avg_queue,avg_speed,throughput_veh_per_min,frac_time_high_congestion,teleports,sim_end_time,wall_clock_s,family,n_tls_controlled,n_tls_ai,ai_coverage,avg_junction_queue_mean,worst_junction_avg_queue\n';

Future<void> _writeRun(Directory root, String id, String avgWait) async {
  final file = File('${root.path}/results/raw/$id/summary.csv');
  await file.parent.create(recursive: true);
  await file.writeAsString(
    '$_summaryHeader$id,rule,net_medium,8000,abc,hash,1,1,1,1,0,1,1,10,10,10,10,$avgWait,0,0,1,5,12,0,0,10,1,network,12,0,none,1,1\n',
  );
}

void main() {
  final current = Directory.current.path;
  final projectRoot = p.basename(current) == 'dashboard_flutter'
      ? Directory(current).parent.path
      : current;
  final hasRealResults = File(
    p.join(projectRoot, 'results', 'summary', 'comparison.csv'),
  ).existsSync();
  DashboardStore? realProjectStore;

  setUpAll(() async {
    if (hasRealResults) {
      realProjectStore = DashboardStore();
      await realProjectStore!.loadFolder(projectRoot);
    }
  });

  test('ordinary launch arguments do not enable measurement mode', () {
    expect(DashboardLoadMeasurement.fromArgs([]), isNull);
    expect(DashboardFreshnessMeasurement.fromArgs([]), isNull);
    expect(
      () =>
          DashboardLoadMeasurement.fromArgs(['--t54-measure-root=D:/project']),
      throwsArgumentError,
    );
    expect(
      () => DashboardFreshnessMeasurement.fromArgs([
        '--t54-freshness-root=D:/project',
      ]),
      throwsArgumentError,
    );
    expect(
      DashboardFreshnessMeasurement.fromArgs([
        '--t54-freshness-root=D:/project',
        '--t54-freshness-run-id=live_run',
        '--t54-freshness-output=D:/temp/stms_t54_live.json',
      ])?.runId,
      'live_run',
    );
  });

  test(
    'measurement reports cannot overwrite results and are exclusive',
    () async {
      final project = await Directory.systemTemp.createTemp(
        'stms-measurement-safety-',
      );
      addTearDown(() => project.delete(recursive: true));
      final resultFile = File(
        p.join(project.path, 'results', 'raw', 'run-a', 'summary.csv'),
      );
      await resultFile.parent.create(recursive: true);
      await resultFile.writeAsString('preserve-this-result');
      await expectLater(
        DashboardLoadMeasurement(
          project.path,
          resultFile.path,
        ).createNewReportFile(),
        throwsArgumentError,
      );
      expect(await resultFile.readAsString(), 'preserve-this-result');

      final outputDir = await Directory.systemTemp.createTemp(
        'stms-measurement-output-',
      );
      addTearDown(() => outputDir.delete(recursive: true));
      final safeReport = p.join(outputDir.path, 'stms_t54_test.json');
      final measurement = DashboardLoadMeasurement(project.path, safeReport);
      final output = await measurement.createNewReportFile();
      await output.writeAsString('first report');
      await expectLater(
        measurement.createNewReportFile(),
        throwsA(isA<FileSystemException>()),
      );
      expect(await File(safeReport).readAsString(), 'first report');
    },
  );

  test(
    'freshness reports are exclusive and restricted to the OS temp folder',
    () async {
      final project = await Directory.systemTemp.createTemp(
        'stms-freshness-project-',
      );
      addTearDown(() => project.delete(recursive: true));
      final resultFile = File(
        p.join(project.path, 'results', 'raw', 'run-a', 'status.json'),
      );
      await resultFile.parent.create(recursive: true);
      await resultFile.writeAsString('preserve-this-status');
      final unsafe = DashboardFreshnessMeasurement(
        project.path,
        'run-a',
        resultFile.path,
      );
      await expectLater(unsafe.createNewReportFile(), throwsArgumentError);
      expect(await resultFile.readAsString(), 'preserve-this-status');

      final outputDir = await Directory.systemTemp.createTemp(
        'stms-freshness-output-',
      );
      addTearDown(() => outputDir.delete(recursive: true));
      final safePath = p.join(outputDir.path, 'stms_t54_live.json');
      final measurement = DashboardFreshnessMeasurement(
        project.path,
        'run-a',
        safePath,
      );
      final output = await measurement.createNewReportFile();
      await output.writeAsString('freshness report');
      await expectLater(
        measurement.createNewReportFile(),
        throwsA(isA<FileSystemException>()),
      );
      expect(await File(safePath).readAsString(), 'freshness report');
    },
  );

  testWidgets('starts in an explicit no-data state', (tester) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const StmsApp());
    expect(find.text('NO DATA'), findsWidgets);
    expect(find.text('DEMO DATA'), findsNothing);
    expect(find.text('486.2'), findsNothing);
    for (final icon in [
      Icons.traffic_outlined,
      Icons.query_stats,
      Icons.history,
    ]) {
      await tester.tap(find.byIcon(icon).first);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('shows summary metrics for the selected run only', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final store = DashboardStore()
      ..mode = 'REAL FILES'
      ..selectedRunId = 'run-active'
      ..status = {
        'run_id': 'run-active',
        'state': 'running',
        'family': 'network',
        'controller': 'rule',
        'scenario': 'net_medium',
        'seed': 8000,
        'sim_time': 10,
        'max_sim_s': 7200,
        'n_tls_controlled': 12,
      }
      ..summaries = [
        {
          'run_id': 'run-old',
          'avg_wait': '30.71',
          'throughput_veh_per_min': '8.88',
        },
        {
          'run_id': 'run-finished',
          'avg_wait': '4.0',
          'throughput_veh_per_min': '12.0',
        },
      ];

    await tester.pumpWidget(StmsApp(initialStore: store));
    expect(find.text('30.71 s'), findsNothing);
    expect(find.text('8.88'), findsNothing);
    expect(find.text('— s'), findsOneWidget);

    store
      ..selectedRunId = 'run-finished'
      ..status = {
        'run_id': 'run-finished',
        'state': 'finished',
        'family': 'network',
        'controller': 'rule',
        'scenario': 'net_medium',
        'seed': 8000,
        'sim_time': 7200,
        'max_sim_s': 7200,
        'n_tls_controlled': 12,
      }
      ..notifyListeners();
    await tester.pump();
    expect(find.text('4.0 s'), findsOneWidget);
    expect(find.text('12.0'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  test('defaults to the most recently modified raw run', () async {
    final dir = await Directory.systemTemp.createTemp('stms-dashboard-latest-');
    addTearDown(() => dir.delete(recursive: true));
    const header =
        'run_id,controller,scenario,seed,git_commit,config_hash,metrics_version,n_trips,n_trips_junction,n_completed,n_unfinished,completion_rate,completion_rate_junction,avg_travel_time_completed,avg_travel_time_censored,avg_travel_time_junction_completed,avg_travel_time_junction_censored,avg_wait,avg_time_loss,avg_depart_delay,avg_queue,avg_speed,throughput_veh_per_min,frac_time_high_congestion,teleports,sim_end_time,wall_clock_s,family,n_tls_controlled,n_tls_ai,ai_coverage,avg_junction_queue_mean,worst_junction_avg_queue\n';
    Future<void> writeRun(String runId, String avgWait) async {
      final summary = File('${dir.path}/results/raw/$runId/summary.csv');
      await summary.parent.create(recursive: true);
      await summary.writeAsString(
        '$header$runId,rule,net_medium,8000,abc,hash,1,1,1,1,0,1,1,10,10,10,10,$avgWait,0,0,1,5,12,0,0,10,1,network,12,0,none,1,1\n',
      );
    }

    await writeRun('zzz-older', '30');
    await writeRun('aaa-latest', '4');
    final store = DashboardStore();
    await store.loadFolder(dir.path);
    expect(store.selectedRunId, 'aaa-latest');
    expect(store.selectedSummary?['avg_wait'], '4');
    store.dispose();
  });

  test('discovers a run folder created after the initial scan', () async {
    final dir = await Directory.systemTemp.createTemp(
      'stms-dashboard-new-run-',
    );
    addTearDown(() => dir.delete(recursive: true));
    await _writeRun(dir, 'run-old', '30');
    final store = DashboardStore();
    await store.loadFolder(dir.path);
    expect(store.runIds, ['run-old']);

    await _writeRun(dir, 'run-new', '4');
    await store.refreshNow();
    expect(store.runIds, containsAll(['run-old', 'run-new']));
    expect(
      store.summaries.map((row) => row['run_id']),
      containsAll(['run-old', 'run-new']),
    );
    store.dispose();
  });

  test(
    'preserves an existing selected run while discovering a newer run',
    () async {
      final dir = await Directory.systemTemp.createTemp(
        'stms-dashboard-preserve-run-',
      );
      addTearDown(() => dir.delete(recursive: true));
      await _writeRun(dir, 'run-old', '30');
      final store = DashboardStore();
      await store.loadFolder(dir.path);
      await store.selectRun('run-old');

      await _writeRun(dir, 'run-new', '4');
      await store.refreshNow();
      expect(store.selectedRunId, 'run-old');
      expect(store.selectedSummary?['avg_wait'], '30');
      expect(store.runIds, contains('run-new'));
      store.dispose();
    },
  );

  test('completed discovered run is selectable in the UI', () async {
    final dir = await Directory.systemTemp.createTemp(
      'stms-dashboard-select-new-',
    );
    addTearDown(() => dir.delete(recursive: true));
    await _writeRun(dir, 'run-old', '30');
    final store = DashboardStore();
    await store.loadFolder(dir.path);
    await _writeRun(dir, 'run-completed', '4.25');
    await store.refreshNow();
    expect(store.runIds, contains('run-completed'));
    expect(
      store.summaries.any((row) => row['run_id'] == 'run-completed'),
      isTrue,
    );

    await store.selectRun('run-completed');
    expect(store.selectedRunId, 'run-completed');
    expect(store.selectedSummary?['avg_wait'], '4.25');
    store.dispose();
  });

  test(
    'incomplete folders remain discoverable without becoming fake summaries',
    () async {
      final dir = await Directory.systemTemp.createTemp(
        'stms-dashboard-incomplete-',
      );
      addTearDown(() => dir.delete(recursive: true));
      final partial = Directory('${dir.path}/results/raw/run-partial');
      await partial.create(recursive: true);
      await File(
        '${partial.path}/summary.csv',
      ).writeAsString('${_summaryHeader}run-partial,rule,net_medium,8000,abc');
      await File('${partial.path}/status.json').writeAsString('{"run_id":');

      final store = DashboardStore();
      await store.loadFolder(dir.path);
      expect(store.runIds, ['run-partial']);
      expect(store.selectedSummary, isNull);
      expect(store.status, isNull);
      expect(store.invalidStatus, isTrue);
      expect(store.runState, 'no data');
      store.dispose();
    },
  );

  test(
    'selecting a newly discovered incomplete run clears prior run metrics',
    () async {
      final dir = await Directory.systemTemp.createTemp(
        'stms-dashboard-no-leak-',
      );
      addTearDown(() => dir.delete(recursive: true));
      await _writeRun(dir, 'run-old', '30');
      final store = DashboardStore();
      await store.loadFolder(dir.path);
      await store.selectRun('run-old');
      expect(store.selectedSummary?['avg_wait'], '30');

      await Directory(
        '${dir.path}/results/raw/run-new',
      ).create(recursive: true);
      await store.refreshNow();
      await store.selectRun('run-new');
      expect(store.selectedRunId, 'run-new');
      expect(store.selectedSummary, isNull);
      expect(store.steps, isEmpty);
      expect(store.junctions, isEmpty);
      expect(store.status, isNull);
      store.dispose();
    },
  );

  testWidgets('UI remains interactive while folder discovery runs', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final dir = Directory.systemTemp.createTempSync(
      'stms-dashboard-responsive-',
    );
    addTearDown(() => dir.delete(recursive: true));
    final scan = Completer<Map<String, dynamic>>();
    final store = DashboardStore(snapshotLoader: (_, _, _, _) => scan.future);
    final loading = store.loadFolder(dir.path);
    await tester.pumpWidget(StmsApp(initialStore: store));
    expect(find.byType(LinearProgressIndicator), findsAtLeastNWidgets(1));
    expect(
      find.text('CONTROL ROOM  /  TRAFFIC OPERATIONS OVERVIEW'),
      findsOneWidget,
    );
    await tester.tap(find.text('Live Monitoring'));
    await tester.pump();
    expect(
      find.text('CONTROL ROOM  /  LIVE SIGNAL & TRAFFIC MONITORING'),
      findsOneWidget,
    );
    scan.complete({
      'runIds': <String>[],
      'selectedRunId': null,
      'fingerprints': <String, String>{},
      'changedSummaries': <String, dynamic>{},
      'selectedFingerprints': <String, String>{},
      'steps': <Map<String, String>>[],
      'junctions': <Map<String, String>>[],
      'stepsChanged': true,
      'junctionsChanged': true,
      'status': null,
      'invalidStatus': false,
      'comparisons': <Map<String, String>>[],
      'evaluationSummaries': <Map<String, String>>[],
      'modelConfigs': <Map<String, dynamic>>[],
      'error': null,
    });
    await loading;
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('live monitoring refreshes to the newest complete approach sample', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final dir = Directory(
      '${Directory.current.path}/.test-tmp/live-sample-${DateTime.now().microsecondsSinceEpoch}',
    );
    dir.createSync(recursive: true);
    addTearDown(() => dir.delete(recursive: true));
    const stepsHeader =
        'run_id,controller,scenario,seed,sim_time,intersection_id,approach,vehicles,halting,mean_speed,wait_time,phase,phase_elapsed,signal_state,action,action_accepted,congestion\n';
    const initialSample =
        'run-live,fixed,medium,8000,5,tls-a,north,0,0,0.0,0.0,0,5,G,hold,true,Low\n'
        'run-live,fixed,medium,8000,5,tls-a,east,0,0,0.0,0.0,0,5,G,hold,true,Low\n';
    final runDir = Directory('${dir.path}/results/raw/run-live');
    runDir.createSync(recursive: true);
    File('${runDir.path}/summary.csv').writeAsStringSync(
      '$_summaryHeader'
      'run-live,fixed,medium,8000,abc,hash,1,10,10,10,0,1,1,100,100,100,100,3.5,4,0,2,5,12,0,0,10,1,single,1,0,none,,\n',
    );
    final stepsFile = File('${runDir.path}/steps.csv');
    stepsFile.writeAsStringSync('$stepsHeader$initialSample');
    final statusFile = File('${runDir.path}/status.json');
    void writeStatus(int simTime) => statusFile.writeAsStringSync(
      '{"schema_version":1,"run_id":"run-live","state":"running",'
      '"family":"single","controller":"fixed","scenario":"medium",'
      '"seed":8000,"sim_time":$simTime,"max_sim_s":7200,"n_tls_controlled":1,'
      '"started_utc":"2026-11-08T00:00:00Z",'
      '"updated_utc":"${DateTime.now().toUtc().toIso8601String()}","error":null}',
    );
    writeStatus(5);

    final store = DashboardStore();
    await tester.runAsync(() => store.loadFolder(dir.path));
    await tester.pumpWidget(StmsApp(initialStore: store));
    await tester.tap(find.text('Live Monitoring'));
    await tester.pump();
    expect(find.text('Latest sample • sim time 5.0 s'), findsOneWidget);

    stepsFile.writeAsStringSync(
      'run-live,fixed,medium,8000,10,tls-a,north,4,3,2.5,8.0,2,5,rrG,hold,true,Medium\n'
      'run-live,fixed,medium,8000,10,tls-a,east,2,1,3.5,4.0,2,5,rrG,hold,true,Low\n',
      mode: FileMode.append,
      flush: true,
    );
    writeStatus(10);
    await tester.runAsync(store.refreshNow);
    await tester.pump();

    expect(store.runState, 'running');
    expect(find.text('Latest sample • sim time 10.0 s'), findsOneWidget);
    final approachTable = tester.widget<DataTable>(
      find.byType(DataTable).first,
    );
    expect(approachTable.rows, hasLength(2));
    String cellText(DataCell cell) =>
        (((cell.child as SizedBox).child) as Text).data!;
    expect(approachTable.rows.map((row) => cellText(row.cells[1])), ['4', '2']);
    expect(approachTable.rows.map((row) => cellText(row.cells[2])), ['3', '1']);

    await tester.pumpWidget(const SizedBox.shrink());
  });

  test('refreshes a selected run summary created after the directory scan', () async {
    final dir = await Directory.systemTemp.createTemp(
      'stms-dashboard-summary-refresh-',
    );
    addTearDown(() => dir.delete(recursive: true));
    const header =
        'run_id,controller,scenario,seed,git_commit,config_hash,metrics_version,n_trips,n_trips_junction,n_completed,n_unfinished,completion_rate,completion_rate_junction,avg_travel_time_completed,avg_travel_time_censored,avg_travel_time_junction_completed,avg_travel_time_junction_censored,avg_wait,avg_time_loss,avg_depart_delay,avg_queue,avg_speed,throughput_veh_per_min,frac_time_high_congestion,teleports,sim_end_time,wall_clock_s,family,n_tls_controlled,n_tls_ai,ai_coverage,avg_junction_queue_mean,worst_junction_avg_queue\n';
    final oldSummary = File('${dir.path}/results/raw/run-old/summary.csv');
    await oldSummary.parent.create(recursive: true);
    await oldSummary.writeAsString(
      '${header}run-old,rule,net_medium,3000,abc,hash,1,1,1,1,0,1,1,10,10,10,10,30.71,0,0,1,5,8.88,0,0,10,1,network,12,0,none,1,1\n',
    );
    final runDir = Directory('${dir.path}/results/raw/run-current');
    await runDir.create(recursive: true);
    await File('${runDir.path}/status.json').writeAsString(
      '{"schema_version":1,"run_id":"run-current","state":"running","family":"network","controller":"rule","scenario":"net_medium","seed":3000,"sim_time":10,"max_sim_s":7200,"n_tls_controlled":12,"started_utc":"2026-11-02T00:00:00Z","updated_utc":"2026-11-02T00:00:01Z","error":null}',
    );

    final store = DashboardStore();
    await store.loadFolder(dir.path);
    expect(store.selectedRunId, 'run-current');
    expect(store.selectedSummary, isNull);

    await File('${runDir.path}/summary.csv').writeAsString(
      '${header}run-current,rule,net_medium,3000,abc,hash,1,1,1,1,0,1,1,10,10,10,10,4.25,0,0,1,5,12.5,0,0,10,1,network,12,0,none,1,1\n',
    );
    await store.loadFolder(dir.path); // Same directory set and signature.
    expect(store.selectedSummary?['avg_wait'], '4.25');
    expect(store.selectedSummary?['throughput_veh_per_min'], '12.5');
    expect(
      store.summaries.where((row) => row['run_id'] == 'run-current'),
      hasLength(1),
    );
    store.dispose();
  });

  test('loads saved summary, comparison, live rows, status and model config', () async {
    final dir = await Directory.systemTemp.createTemp('stms-dashboard-');
    addTearDown(() => dir.delete(recursive: true));
    Future<void> write(String relative, String contents) async {
      final file = File('${dir.path}/$relative');
      await file.parent.create(recursive: true);
      await file.writeAsString(contents);
    }

    await write(
      'results/raw/run-a/summary.csv',
      'run_id,controller,scenario,seed,git_commit,config_hash,metrics_version,n_trips,n_trips_junction,n_completed,n_unfinished,completion_rate,completion_rate_junction,avg_travel_time_completed,avg_travel_time_censored,avg_travel_time_junction_completed,avg_travel_time_junction_censored,avg_wait,avg_time_loss,avg_depart_delay,avg_queue,avg_speed,throughput_veh_per_min,frac_time_high_congestion,teleports,sim_end_time,wall_clock_s,family,n_tls_controlled,n_tls_ai,ai_coverage,avg_junction_queue_mean,worst_junction_avg_queue\n'
          'run-a,rule,net_medium,8000,abc,hash,1,10,10,10,0,1.0,1.0,100,100,100,100,3.5,4.0,0,2.0,5.0,12.0,0.0,0,3600,100,network,12,0,none,2.0,3.0\n',
    );
    await write(
      'results/raw/run-a/steps.csv',
      'run_id,controller,scenario,seed,sim_time,intersection_id,approach,vehicles,halting,mean_speed,wait_time,phase,phase_elapsed,signal_state,action,action_accepted,congestion\n'
          'run-a,rule,net_medium,8000,5,tls-a,north,2,1,5.0,3.0,0,5,G,hold,true,Low\n'
          'truncated,last',
    );
    await write(
      'results/raw/run-a/status.json',
      '{"schema_version":1,"run_id":"run-a","state":"running","family":"network","controller":"rule","scenario":"net_medium","seed":8000,"sim_time":5,"max_sim_s":3600,"n_tls_controlled":12,"started_utc":"${DateTime.now().toUtc().toIso8601String()}","updated_utc":"${DateTime.now().toUtc().toIso8601String()}","error":null}',
    );
    await write(
      'results/summary/comparison.csv',
      'milestone,scenario,aggregation,controller,metric,scope,trip_basis,mean,std,ci95_low,ci95_high,n_seeds,n_trips_basis,completion_rate_mean,seed_set,improvement_vs_fixed_pct,improvement_vs_rule_pct,target_met\n'
          'M2,headline,headline,rule,travel_time,all,all,310,5,300,320,5,100,0.9,final,0,0,false\n'
          'M2,headline,headline,rule,travel_time,all,common,300,5,290,310,5,80,0.9,final,0,0,false\n'
          'M2,net_low,scenario,rule,travel_time,all,all,999,5,980,1010,5,100,0.5,final,0,0,false\n',
    );
    await write(
      'results/summary/summary.csv',
      'milestone,seed_set,n_rl_cells,n_tls_ai,n_tls_controlled,ai_coverage,model_sha256\n'
          'M2,final,1,0,12,none,hash\n',
    );
    await write(
      'Ai/rl/models/ppo_net/config.json',
      '{"seeds":[1],"git_commit":"abc"}',
    );

    final store = DashboardStore();
    await store.loadFolder(dir.path);
    expect(store.summaries.single['run_id'], 'run-a');
    expect(store.steps, hasLength(1)); // ignores an incomplete trailing row
    expect(store.comparisons, hasLength(3));
    expect(store.evaluationSummary('M2', 'final')?['ai_coverage'], 'none');
    expect(store.status?['state'], 'running');
    expect(store.runState, 'running');
    expect(store.modelConfigs.single['git_commit'], 'abc');
    store.dispose();
  });

  testWidgets('renders saved comparison figures with common-trip context', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final store = DashboardStore()
      ..mode = 'REAL FILES'
      ..summaries = [
        {
          'run_id': 'run-a',
          'avg_wait': '3.5',
          'avg_queue': '2.0',
          'throughput_veh_per_min': '12.0',
        },
      ]
      ..evaluationSummaries = [
        {
          'milestone': 'M2',
          'seed_set': 'final',
          'n_tls_ai': '3',
          'n_tls_controlled': '12',
          'ai_coverage': 'partial',
        },
      ]
      ..comparisons = [
        {
          'milestone': 'M2',
          'seed_set': 'final',
          'aggregation': 'headline',
          'scenario': 'headline',
          'controller': 'rule',
          'metric': 'travel_time',
          'scope': 'all',
          'trip_basis': 'all',
          'mean': '310',
          'ci95_low': '300',
          'ci95_high': '320',
          'completion_rate_mean': '0.9',
          'target_met': 'false',
        },
        {
          'milestone': 'M2',
          'seed_set': 'final',
          'aggregation': 'headline',
          'scenario': 'headline',
          'controller': 'rule',
          'metric': 'travel_time',
          'scope': 'all',
          'trip_basis': 'common',
          'mean': '300',
          'n_trips_basis': '80',
          'completion_rate_mean': '0.9',
          'target_met': 'false',
        },
        {
          'milestone': 'M2',
          'seed_set': 'final',
          'aggregation': 'scenario',
          'scenario': 'net_low',
          'controller': 'rule',
          'metric': 'travel_time',
          'scope': 'all',
          'trip_basis': 'all',
          'mean': '999',
          'target_met': 'false',
        },
      ];
    await tester.pumpWidget(StmsApp(initialStore: store));
    await tester.tap(find.byIcon(Icons.query_stats).first);
    await tester.pump();
    expect(find.text('310'), findsWidgets);
    expect(find.text('300'), findsWidgets);
    expect(find.text('80'), findsOneWidget);
    expect(find.text('0.9'), findsWidgets);
    expect(find.text('Not met'), findsOneWidget);
    expect(find.text('net_low'), findsNothing);
    expect(
      find.text('AI coverage: 3/12 (partial) • provisional until P1'),
      findsOneWidget,
    );
    expect(find.textContaining('Full network-wide AI control'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('shows an explicit prompt when no comparison rows match', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final store = DashboardStore()..mode = 'REAL FILES';
    await tester.pumpWidget(StmsApp(initialStore: store));
    await tester.tap(find.byIcon(Icons.query_stats).first);
    await tester.pump();

    expect(
      find.text(
        'Load results/summary/comparison.csv to see evaluation results',
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  test('reports a stale running status instead of presenting it as live', () {
    final store = DashboardStore();
    store.status = {
      'state': 'running',
      'updated_utc': DateTime.now()
          .toUtc()
          .subtract(const Duration(minutes: 1))
          .toIso8601String(),
    };
    expect(store.runState, 'stale');
    store.status = {'state': 'finished'};
    expect(store.runState, 'finished');
    store.dispose();
  });

  test(
    'loads M2 final comparison values from the saved project artifacts',
    () async {
      final store = realProjectStore!;
      // A legacy run may have a status ID that differs from its folder name;
      // the reader rejects that status while still loading independent results.
      if (store.error != null) expect(store.invalidStatus, isTrue);
      expect(store.comparisons, isNotEmpty);
      final censored = store.comparisons.firstWhere(
        (row) =>
            row['milestone'] == 'M2' &&
            row['seed_set'] == 'final' &&
            row['aggregation'] == 'headline' &&
            row['controller'] == 'hybrid' &&
            row['metric'] == 'travel_time' &&
            row['trip_basis'] == 'all',
      );
      final common = store.comparisons.firstWhere(
        (row) =>
            row['milestone'] == 'M2' &&
            row['seed_set'] == 'final' &&
            row['aggregation'] == 'headline' &&
            row['controller'] == 'hybrid' &&
            row['metric'] == 'travel_time' &&
            row['trip_basis'] == 'common',
      );
      final displayedFields = [
        censored['mean'],
        censored['ci95_low'],
        censored['ci95_high'],
        common['mean'],
        common['n_trips_basis'],
        censored['completion_rate_mean'],
        censored['n_seeds'],
        censored['improvement_vs_fixed_pct'],
        censored['improvement_vs_rule_pct'],
        censored['target_met'],
      ];
      expect(
        displayedFields.whereType<String>().length,
        greaterThanOrEqualTo(10),
      );
      expect(store.evaluationSummary('M2', 'final')?['ai_coverage'], 'none');
      expect(store.evaluationSummary('M2', 'final')?['n_tls_ai'], '0');
      expect(store.evaluationSummary('M2', 'final')?['n_tls_controlled'], '12');
    },
    skip: !hasRealResults,
  );

  testWidgets('renders values from the real saved results', (tester) async {
    final store = realProjectStore!;
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(StmsApp(initialStore: store));
    await tester.tap(find.byIcon(Icons.query_stats).first);
    await tester.pump();

    final censoredRows = store.comparisons.where(
      (row) =>
          row['milestone'] == 'M2' &&
          row['seed_set'] == 'final' &&
          row['aggregation'] == 'headline' &&
          row['metric'] == 'travel_time' &&
          row['scope'] == 'all' &&
          row['trip_basis'] == 'all',
    );
    var shownNumbers = 0;
    for (final row in censoredRows) {
      final common = store.comparisons.firstWhere(
        (candidate) =>
            candidate['milestone'] == row['milestone'] &&
            candidate['seed_set'] == row['seed_set'] &&
            candidate['aggregation'] == row['aggregation'] &&
            candidate['scenario'] == row['scenario'] &&
            candidate['controller'] == row['controller'] &&
            candidate['metric'] == row['metric'] &&
            candidate['scope'] == row['scope'] &&
            candidate['trip_basis'] == 'common',
      );
      final values = [
        row['mean'],
        '${row['ci95_low']} – ${row['ci95_high']}',
        common['mean'],
        common['n_trips_basis'],
        row['completion_rate_mean'],
      ];
      for (final value in values.whereType<String>()) {
        expect(
          find.text(value),
          findsWidgets,
          reason: 'Saved comparison value $value must render.',
        );
        shownNumbers++;
      }
    }
    expect(shownNumbers, greaterThanOrEqualTo(10));
    expect(
      find.text('AI coverage: 0/12 (none) • provisional until P1'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  }, skip: !hasRealResults);
}

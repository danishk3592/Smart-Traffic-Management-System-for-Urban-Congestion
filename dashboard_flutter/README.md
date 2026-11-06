# STMS Flutter dashboard

The dashboard is a local, read-only viewer for saved STMS CSV/JSON artifacts. It does not connect to SUMO or TraCI and cannot control signals. Figures are simulated results from saved files; absent files are shown as no data.

## Supported target

Windows desktop is the supported target. The app uses `dart:io` for directory selection and reading local project files; the generated web target is not supported. Linux/macOS are not declared supported in this delivery.

## Run on Windows

From the repository root, with Flutter for Windows installed and desktop support enabled:

```powershell
cd dashboard_flutter
flutter pub get
flutter run -d windows
```

Choose the repository folder in the app to load `results/raw/`, `results/summary/`, and `Ai/rl/models/`. It refreshes files every three seconds. A running status older than 15 seconds is displayed as stale.

## Verify

```powershell
cd dashboard_flutter
flutter analyze
flutter test
flutter build windows
```

The generated Android, iOS, Linux, macOS and web folders are Flutter scaffold artifacts; only the Windows desktop target is supported by this file-based app.

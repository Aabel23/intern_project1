import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'shared/ui/app_theme.dart';
import 'app/app_navigation.dart';
import 'shared/cloud/cloud_config.dart';
import 'shared/cloud/cloud_crypto.dart';
import 'shared/cloud/cloud_client.dart';
import 'shared/cloud/cloud_error.dart';
import 'shared/cloud/server_endpoint.dart';
import 'feature/user_auth/data/auth_service.dart';
import 'feature/user_auth/data/session_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const _BootstrapApp());
}

class _BootstrapApp extends StatefulWidget {
  const _BootstrapApp();
  @override
  State<_BootstrapApp> createState() => _BootstrapAppState();
}

class _BootstrapAppState extends State<_BootstrapApp> {
  late Future<AuthService> _service;
  @override
  void initState() {
    super.initState();
    _service = _load();
  }

  Future<AuthService> _load() async {
    final trust = Map<String, Object?>.from(
      jsonDecode(await rootBundle.loadString('assets/server-trust.json'))
          as Map,
    );
    final config = CloudConfig(
      // URL do provision_keys.py ghi sẵn; --dart-define vẫn ghi đè được khi cần trỏ server khác.
      baseUrl: Uri.parse(
        const String.fromEnvironment(
          'FLEXMIX_SERVER_BASE_URL',
          defaultValue: defaultServerBaseUrl,
        ),
      ),
      trust: trust,
    );
    final store = SessionStore();
    final client = CloudClient(
      config: config,
      crypto: CloudCrypto(),
      store: store,
    );
    final service = AuthService(client: client, store: store);
    client.refreshSession = (token) => service.refresh(refreshToken: token);
    return service;
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<AuthService>(
    future: _service,
    builder: (context, snapshot) {
      if (snapshot.hasData) return MainApp(authService: snapshot.data!);
      return MaterialApp(
        home: Scaffold(
          body: Center(
            child: snapshot.hasError
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('Không thể tải cấu hình kết nối an toàn.'),
                      TextButton(
                        onPressed: () => setState(() {
                          _service = _load();
                        }),
                        child: const Text('Thử lại'),
                      ),
                    ],
                  )
                : const CircularProgressIndicator(),
          ),
        ),
      );
    },
  );
}

class MainApp extends StatefulWidget {
  const MainApp({super.key, required this.authService});
  final AuthService authService;
  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
  final _navigator = GlobalKey<NavigatorState>();
  late Future<bool> _restoreFuture;
  @override
  void initState() {
    super.initState();
    widget.authService.client.onSessionExpired = () {
      _navigator.currentState?.pushAndRemoveUntil(
        MaterialPageRoute<void>(
          builder: (_) => buildAuthPage(widget.authService),
        ),
        (_) => false,
      );
    };
    _restoreFuture = _restore();
  }

  Future<bool> _restore() async {
    final session = await widget.authService.store.load();
    if (session == null) return false;
    try {
      await widget.authService.refresh(refreshToken: session.refreshToken);
      return true;
    } on CloudError catch (e) {
      if (e.status == 401) {
        await widget.authService.store.clear();
        return false;
      }
      rethrow;
    }
  }

  @override
  void dispose() {
    widget.authService.client.onSessionExpired = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: _navigator,
    title: 'FlexMix',
    debugShowCheckedModeBanner: false,
    theme: buildAppTheme(),
    home: FutureBuilder<bool>(
      future: _restoreFuture,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return snapshot.data!
              ? buildDashboard(widget.authService)
              : buildAuthPage(widget.authService);
        }
        return Scaffold(
          body: Center(
            child: snapshot.hasError
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        'Không thể khôi phục phiên. Vui lòng thử lại.',
                      ),
                      TextButton(
                        onPressed: () => setState(() {
                          _restoreFuture = _restore();
                        }),
                        child: const Text('Thử lại'),
                      ),
                    ],
                  )
                : const CircularProgressIndicator(),
          ),
        );
      },
    ),
  );
}

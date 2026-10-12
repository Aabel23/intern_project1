import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../shared/ui/app_theme.dart';
import '../../../shared/cloud/cloud_error.dart';
import '../data/auth_service.dart';

class OtpPage extends StatefulWidget {
  const OtpPage({
    super.key,
    required this.email,
    required this.retryAfterSeconds,
    required this.authService,
  });
  final String email;
  final int retryAfterSeconds;
  final AuthService authService;
  @override
  State<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends State<OtpPage> {
  final _formKey = GlobalKey<FormState>();
  final _code = TextEditingController();
  final _clock = Stopwatch();
  late final Timer _timer;
  int _resendDeadline = 0, _lockDeadline = 0;
  bool _busy = false, _verified = false;
  String _notice =
      'Thư đã được dịch vụ gửi thư chấp nhận. Nếu chưa thấy, kiểm tra thư rác hoặc gửi lại.';
  int _remaining(int deadline) {
    final seconds = ((deadline - _clock.elapsedMilliseconds) / 1000).ceil();
    return seconds < 0 ? 0 : seconds;
  }

  @override
  void initState() {
    super.initState();
    _clock.start();
    _resendDeadline = widget.retryAfterSeconds * 1000;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  void _error(CloudError e) {
    if (e.code == 'RATE_LIMITED' && e.retryAfterSeconds != null) {
      _resendDeadline =
          _clock.elapsedMilliseconds + e.retryAfterSeconds! * 1000;
    }
    if (e.code == 'OTP_LOCKED' && e.retryAfterSeconds != null) {
      _lockDeadline = _clock.elapsedMilliseconds + e.retryAfterSeconds! * 1000;
    }
    _notice = switch (e.code) {
      'MAIL_UNAVAILABLE' => 'Dịch vụ gửi thư đang lỗi. Vui lòng thử lại.',
      'OTP_INVALID' => 'Mã OTP không đúng.',
      'OTP_EXPIRED' => 'Mã OTP đã hết hạn. Vui lòng gửi lại.',
      'OTP_LOCKED' => 'Đã khóa xác minh tạm thời.',
      _ => 'Không thể hoàn tất (${e.code}). Vui lòng thử lại.',
    };
  }

  Future<void> _resend() async {
    if (_busy || _verified || _remaining(_resendDeadline) > 0) return;
    setState(() => _busy = true);
    try {
      final retry = await widget.authService.sendOtp(email: widget.email);
      if (!mounted) return;
      setState(() {
        _code.clear();
        _resendDeadline = _clock.elapsedMilliseconds + retry * 1000;
        _notice = 'Nếu địa chỉ email có yêu cầu đăng ký, hãy kiểm tra hộp thư và thư rác. Bạn có thể gửi lại khi hết thời gian chờ.';
      });
    } on CloudError catch (e) {
      if (mounted) setState(() => _error(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (_busy ||
        _verified ||
        _remaining(_lockDeadline) > 0 ||
        !_formKey.currentState!.validate()) {
      return;
    }
    setState(() => _busy = true);
    try {
      await widget.authService.verifyOtp(email: widget.email, otp: _code.text);
      if (!mounted) return;
      setState(() => _verified = true);
      _code.clear();
      Navigator.of(context).pop(true);
    } on CloudError catch (e) {
      if (mounted) setState(() => _error(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _timer.cancel();
    _clock.stop();
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    appBar: AppBar(title: const Text('Xác minh email')),
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Nhập mã OTP cho ${widget.email}',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  Text(_notice),
                  TextFormField(
                    key: const ValueKey('otp'),
                    controller: _code,
                    enabled: !_busy && !_verified,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    decoration: const InputDecoration(labelText: 'Mã OTP'),
                    validator: (value) =>
                        value?.length == 6 ? null : 'Nhập mã gồm 6 chữ số.',
                  ),
                  if (_remaining(_lockDeadline) > 0)
                    Text('Xác minh bị khóa còn ${_remaining(_lockDeadline)}s'),
                  FilledButton(
                    onPressed:
                        _busy || _verified || _remaining(_lockDeadline) > 0
                        ? null
                        : _verify,
                    child: const Text('Xác minh'),
                  ),
                  TextButton(
                    onPressed:
                        _busy || _verified || _remaining(_resendDeadline) > 0
                        ? null
                        : _resend,
                    child: Text(
                      _remaining(_resendDeadline) > 0
                          ? 'Gửi lại mã sau ${_remaining(_resendDeadline)}s'
                          : 'Gửi lại mã',
                    ),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Sai email? Quay lại'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

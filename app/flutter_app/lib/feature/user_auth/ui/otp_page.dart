import 'dart:async';

import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';

import 'package:flutter/services.dart';

import 'package:simple_app/feature/user_auth/user_register_request.dart';

class OtpPage extends StatefulWidget {
  const OtpPage({
    super.key,
    required this.email,
    required this.serverUrl,
    required this.registrationId,
    this.initiallyVerified = false,
  });

  final String email;
  final String serverUrl;
  final String registrationId;
  final bool initiallyVerified;

  @override
  State<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends State<OtpPage> {
  final _formKey = GlobalKey<FormState>();
  final _code = TextEditingController();
  bool _busy = false;
  bool _verified = false;
  int _resendSeconds = 60;
  late final Timer _timer;

  @override
  void initState() {
    super.initState();
    _verified = widget.initiallyVerified;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_resendSeconds > 0) setState(() => _resendSeconds--);
    });
  }

  Future<void> _resend() async {
    if (_verified || _busy || _resendSeconds > 0) return;
    setState(() => _busy = true);
    try {
      final result = await requestOtp(widget.serverUrl, {
        'registration_id': widget.registrationId,
      });
      if (!mounted) return;
      if (result['valid'] == true) {
        _code.clear();
        setState(() => _resendSeconds = (result['retry_after'] as int?) ?? 60);
      }
      if (result['retry_after'] is int) {
        setState(() => _resendSeconds = result['retry_after'] as int);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['message'] as String? ?? 'Không gửi được mã OTP.',
          ),
        ),
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Không kết nối được server.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (_verified || _busy || !_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final result = await verifyOtp(widget.serverUrl, {
        'registration_id': widget.registrationId,
        'code': _code.text,
      });
      if (!mounted) return;
      if (result['valid'] == true) {
        setState(() => _verified = true);
        _code.clear();
        _timer.cancel();
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['message'] as String? ?? 'Không xác minh được mã OTP.',
          ),
        ),
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Không kết nối được server.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _timer.cancel();
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(backgroundColor: AppColors.background),
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
                    const Icon(
                      Icons.mark_email_read_outlined,
                      size: 72,
                      color: AppColors.green,
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Xác minh email',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: AppColors.ink,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Nhập mã OTP cho ${widget.email}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.muted),
                    ),
                    const SizedBox(height: 32),
                    TextFormField(
                      key: const ValueKey('otp'),
                      controller: _code,
                      enabled: !_verified && !_busy,
                      autofocus: true,
                      keyboardType: TextInputType.number,
                      textAlign: TextAlign.center,
                      maxLength: 6,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      decoration: const InputDecoration(
                        labelText: 'Mã OTP',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) =>
                          value?.length == 6 ? null : 'Nhập mã gồm 6 chữ số.',
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: _verified || _busy ? null : _verify,
                      child: Text(
                        _verified
                            ? 'Tài khoản đã tạo'
                            : _busy
                            ? 'Đang kiểm tra...'
                            : 'Xác minh',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: _verified || _busy || _resendSeconds > 0
                          ? null
                          : _resend,
                      child: Text(
                        _resendSeconds > 0
                            ? 'Gửi lại mã sau ${_resendSeconds}s'
                            : 'Gửi lại mã',
                      ),
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
}

import 'dart:async';

import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';

import 'package:flutter/services.dart';

class OtpPage extends StatefulWidget {
  const OtpPage({super.key, required this.email});

  final String email;

  @override
  State<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends State<OtpPage> {
  final _formKey = GlobalKey<FormState>();
  final _code = TextEditingController();
  bool _verified = false;
  int _resendSeconds = 60;
  late final Timer _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_resendSeconds > 0) setState(() => _resendSeconds--);
    });
  }

  void _resend() {
    if (_verified || _resendSeconds > 0) return;
    _code.clear();
    setState(() => _resendSeconds = 60);
  }

  void _verify() {
    if (_verified || !_formKey.currentState!.validate()) return;
    setState(() => _verified = true);
    _code.clear();
    _timer.cancel();
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
                      enabled: !_verified,
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
                      onPressed: _verified ? null : _verify,
                      child: Text(_verified ? 'Tài khoản đã tạo' : 'Xác minh'),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: _verified || _resendSeconds > 0
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

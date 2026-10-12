import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';

import 'package:simple_app/feature/user_auth/ui/otp_page.dart';

import '../data/auth_service.dart';
import '../../../shared/cloud/cloud_error.dart';

class AuthPage extends StatefulWidget {
  const AuthPage({
    super.key,
    required this.authService,
    required this.onAuthenticated,
  });
  final AuthService authService;
  final void Function(BuildContext context) onAuthenticated;

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final _formKey = GlobalKey<FormState>();
  final _password = TextEditingController();
  bool _busy = false;
  String? _notice;
  final _email = TextEditingController();
  bool _register = false;
  bool _hidePassword = true;
  bool _hideConfirmation = true;
  static const _green = AppColors.green;
  static const _ink = AppColors.ink;

  @override
  void dispose() {
    _password.dispose();

    _email.dispose();
    super.dispose();
  }

  void _switchMode() {
    if (_busy) return;
    _formKey.currentState?.reset();
    _password.clear();
    setState(() {
      _register = !_register;
      _hidePassword = true;
      _hideConfirmation = true;
    });
  }

  Future<void> _submit() async {
    if (_busy || !_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      final email = _email.text.trim().toLowerCase();
      if (!_register) {
        await widget.authService.login(email: email, password: _password.text);
        if (mounted) widget.onAuthenticated(context);
      } else {
        final retry = await widget.authService.register(
          email: email,
          password: _password.text,
        );
        if (!mounted) return;
        _password.clear();
        final verified = await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => OtpPage(
              email: email,
              retryAfterSeconds: retry,
              authService: widget.authService,
            ),
          ),
        );
        if (!mounted) return;
        _password.clear();
        if (verified == true) {
          setState(() {
            _register = false;
            _notice = 'Email đã xác minh. Vui lòng đăng nhập.';
          });
        }
      }
    } on CloudError catch (e) {
      if (mounted) {
        setState(
          () => _notice = e.code == 'MAIL_UNAVAILABLE'
              ? 'Dịch vụ gửi thư đang lỗi. Vui lòng thử lại.'
              : e.code == 'AUTH_FAILED'
              ? 'Email hoặc mật khẩu không đúng.'
              : 'Không thể hoàn tất (${e.code}). Vui lòng thử lại.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  InputDecoration _decoration(String label, IconData icon, {Widget? suffix}) {
    return InputDecoration(
      labelText: label,
      prefixIcon: Icon(icon, size: 21),
      suffixIcon: suffix,
      filled: true,
      fillColor: AppColors.background,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.border),
      ),
    );
  }

  Widget _visibility(bool hidden, VoidCallback toggle) {
    return IconButton(
      tooltip: hidden ? 'Hiện mật khẩu' : 'Ẩn mật khẩu',
      onPressed: toggle,
      icon: Icon(
        hidden ? Icons.visibility_off_outlined : Icons.visibility_outlined,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: (constraints.maxHeight - 64).clamp(
                  0,
                  double.infinity,
                ),
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.local_cafe_rounded,
                            color: _green,
                            size: 28,
                          ),
                          SizedBox(width: 10),
                          Text(
                            'FlexMix',
                            style: TextStyle(
                              color: _ink,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 2,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 32),
                      Center(
                        child: Container(
                          width: 88,
                          height: 88,
                          decoration: BoxDecoration(
                            color: AppColors.greenTint,
                            borderRadius: BorderRadius.circular(28),
                          ),
                          child: Icon(
                            _register
                                ? Icons.person_add_alt_1_rounded
                                : Icons.waving_hand_rounded,
                            color: _green,
                            size: 40,
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      Text(
                        _register ? 'Khởi đầu cùng nhau' : 'Chào mừng trở lại!',
                        textAlign: TextAlign.center,
                        style: displayNumber(30),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _register
                            ? 'Tạo tài khoản để bắt đầu trải nghiệm của bạn.'
                            : 'Đăng nhập để kết nối và quản lý máy\ncà phê của bạn mỗi ngày.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: AppColors.muted,
                          height: 1.6,
                        ),
                      ),
                      const SizedBox(height: 28),
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(28),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text(
                                _register ? 'Tạo tài khoản' : 'Đăng nhập',
                                style: const TextStyle(
                                  fontSize: 21,
                                  fontWeight: FontWeight.w700,
                                  color: _ink,
                                ),
                              ),
                              const SizedBox(height: 24),
                              TextFormField(
                                key: const ValueKey('email'),
                                controller: _email,
                                enabled: !_busy,
                                keyboardType: TextInputType.emailAddress,
                                autocorrect: false,
                                textInputAction: TextInputAction.next,
                                decoration: _decoration(
                                  'Email',
                                  Icons.mail_outline_rounded,
                                ),
                                validator: (value) =>
                                    !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                        .hasMatch(value?.trim() ?? '')
                                    ? 'Vui lòng nhập email hợp lệ.'
                                    : null,
                              ),
                              const SizedBox(height: 16),
                              TextFormField(
                                key: const ValueKey('password'),
                                controller: _password,
                                obscureText: _hidePassword,
                                enableSuggestions: false,
                                autocorrect: false,
                                textInputAction: _register
                                    ? TextInputAction.next
                                    : TextInputAction.done,
                                onFieldSubmitted: _register
                                    ? null
                                    : (_) => _submit(),
                                decoration: _decoration(
                                  'Mật khẩu',
                                  Icons.lock_outline_rounded,
                                  suffix: _visibility(
                                    _hidePassword,
                                    () => setState(
                                      () => _hidePassword = !_hidePassword,
                                    ),
                                  ),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Vui lòng nhập mật khẩu.';
                                  }
                                  // NIST SP 800-63B-4 (hợp đồng v2 D9), khớp kiểm của server.
                                  if (value.runes.length < 15) {
                                    return 'Mật khẩu cần ít nhất 15 ký tự.';
                                  }
                                  if (value.runes.length > 256) {
                                    return 'Mật khẩu tối đa 256 ký tự.';
                                  }
                                  return null;
                                },
                              ),
                              if (_register) ...[
                                const SizedBox(height: 16),
                                TextFormField(
                                  key: const ValueKey('confirmation'),
                                  obscureText: _hideConfirmation,
                                  enableSuggestions: false,
                                  autocorrect: false,
                                  textInputAction: TextInputAction.done,
                                  onFieldSubmitted: (_) => _submit(),
                                  decoration: _decoration(
                                    'Nhập lại mật khẩu',
                                    Icons.lock_outline_rounded,
                                    suffix: _visibility(
                                      _hideConfirmation,
                                      () => setState(
                                        () => _hideConfirmation =
                                            !_hideConfirmation,
                                      ),
                                    ),
                                  ),
                                  validator: (value) =>
                                      value == null || value.isEmpty
                                      ? 'Vui lòng nhập lại mật khẩu.'
                                      : value != _password.text
                                      ? 'Mật khẩu chưa khớp.'
                                      : null,
                                ),
                              ],
                              if (_notice != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 16),
                                  child: Text(_notice!),
                                ),
                              const SizedBox(height: 24),
                              FilledButton(
                                onPressed: _busy ? null : _submit,
                                style: FilledButton.styleFrom(
                                  backgroundColor: _green,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 17,
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Flexible(
                                      child: Text(
                                        _register
                                            ? 'Tạo tài khoản'
                                            : 'Đăng nhập',
                                        style: const TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    const Icon(
                                      Icons.arrow_forward_rounded,
                                      size: 20,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            _register
                                ? 'Đã có tài khoản?'
                                : 'Bạn chưa có tài khoản?',
                            style: const TextStyle(color: AppColors.muted),
                          ),
                          TextButton(
                            onPressed: _switchMode,
                            child: Text(
                              _register ? 'Đăng nhập' : 'Đăng ký ngay',
                              style: const TextStyle(
                                color: _green,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Một kết nối nhỏ. Một ngày thật trọn vẹn.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: AppColors.muted),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

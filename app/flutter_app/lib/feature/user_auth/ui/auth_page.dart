import 'package:simple_app/config/app_config.dart';

import 'dart:math';

import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';

import 'package:simple_app/feature/user_auth/user_login_request.dart';
import 'package:simple_app/feature/user_auth/ui/otp_page.dart';
import 'package:simple_app/feature/user_auth/user_register_request.dart';

class AuthPage extends StatefulWidget {
  const AuthPage({
    super.key,
    required this.onAuthenticated,
    this.serverUrl = const String.fromEnvironment(
      'SERVER_URL',
      defaultValue: kDefaultServerUrl,
    ),
  });
  final String serverUrl;
  final void Function(BuildContext context, String? token) onAuthenticated;

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final _formKey = GlobalKey<FormState>();
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _email = TextEditingController();
  bool _busy = false;
  String? _requestId;
  List<String>? _requestFields;
  bool _register = false;
  bool _hidePassword = true;
  bool _hideConfirmation = true;
  static const _green = AppColors.green;
  static const _ink = AppColors.ink;

  @override
  void dispose() {
    _password.dispose();
    _name.dispose();
    _username.dispose();
    _email.dispose();
    super.dispose();
  }

  void _switchMode() {
    _formKey.currentState?.reset();
    _password.clear();
    setState(() {
      _register = !_register;
      _hidePassword = true;
      _hideConfirmation = true;
    });
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (!_formKey.currentState!.validate()) return;
    if (widget.serverUrl.trim().isEmpty) {
      _showMessage(
        'App chưa có địa chỉ server. Build lại với '
        '--dart-define=SERVER_URL=http://<IP server>:8000.',
      );
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() => _busy = true);
    try {
      if (!_register) {
        final result = await requestLogin(
          widget.serverUrl,
          username: _username.text.trim(),
          password: _password.text,
        );
        if (!mounted) return;
        if (result['valid'] != true) {
          _showMessage(
            result['message'] as String? ?? 'Sai tên đăng nhập hoặc mật khẩu.',
          );
          return;
        }
        widget.onAuthenticated(context, result['token'] as String?);
        return;
      }
      final email = _email.text.trim();
      final fields = [
        _name.text.trim(),
        _username.text.trim(),
        email,
        _password.text,
      ];
      // Giữ ID khi thử lại cùng dữ liệu; đổi dữ liệu thì tạo yêu cầu mới.
      if (_requestFields == null ||
          List.generate(
            fields.length,
            (i) => fields[i] == _requestFields![i],
          ).contains(false)) {
        final random = Random.secure();
        _requestId = List.generate(
          16,
          (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
        ).join();
        _requestFields = fields;
      }
      final result = await requestRegistration(widget.serverUrl, {
        'request_id': _requestId!,
        'full_name': _name.text.trim(),
        'username': _username.text.trim(),
        'email': email,
        'password': _password.text,
      });
      if (!mounted) return;
      if (result['valid'] != true) {
        _showMessage(result['message'] as String? ?? 'Thông tin không hợp lệ.');
        return;
      }
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => OtpPage(
            email: email,
            serverUrl: widget.serverUrl,
            registrationId: result['registration_id'] as String,
            initiallyVerified: result['verified'] == true,
          ),
        ),
      );
    } catch (_) {
      if (mounted) {
        _showMessage(
          'Không kết nối được server. Kiểm tra Wi-Fi và server trên laptop.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
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
                              if (_register) ...[
                                TextFormField(
                                  key: const ValueKey('name'),
                                  controller: _name,
                                  textCapitalization: TextCapitalization.words,
                                  textInputAction: TextInputAction.next,
                                  decoration: _decoration(
                                    'Họ và tên',
                                    Icons.person_outline_rounded,
                                  ),
                                  validator: (value) =>
                                      value == null || value.trim().isEmpty
                                      ? 'Vui lòng nhập họ và tên.'
                                      : null,
                                ),
                                const SizedBox(height: 16),
                              ],
                              TextFormField(
                                key: const ValueKey('username'),
                                controller: _username,
                                autocorrect: false,
                                textInputAction: TextInputAction.next,
                                decoration: _decoration(
                                  'Tên đăng nhập',
                                  Icons.alternate_email,
                                ),
                                validator: (value) =>
                                    value == null || value.trim().isEmpty
                                    ? 'Vui lòng nhập tên đăng nhập.'
                                    : null,
                              ),
                              const SizedBox(height: 16),
                              if (_register) ...[
                                TextFormField(
                                  key: const ValueKey('email'),
                                  controller: _email,
                                  keyboardType: TextInputType.emailAddress,
                                  textInputAction: TextInputAction.next,
                                  autocorrect: false,
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
                              ],
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
                                  if (_register && value.length < 8) {
                                    return 'Mật khẩu cần ít nhất 8 ký tự.';
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
                                        _busy
                                            ? 'Đang kiểm tra...'
                                            : _register
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
                            onPressed: _busy ? null : _switchMode,
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

class CloudError implements Exception {
  const CloudError(this.code, {this.status, this.retryAfterSeconds});
  final String code;
  final int? status;
  final int? retryAfterSeconds;
  @override
  String toString() => code;
}

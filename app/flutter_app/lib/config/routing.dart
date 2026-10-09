// Names follow objectTargetAction; paths follow /app/<object>/<target>/<action>.
// GET describes the task, not the HTTP method.
// HTTP paths must match server/config/routing.py.
abstract final class Routes {
  // User authentication and registration
  static const userAccountRegister = '/app/user/account/register';
  static const userOtpSend = '/app/user/otp/send';
  static const userOtpVerify = '/app/user/otp/verify';
  static const userSessionLogin = '/app/user/session/login';
  static const userSessionVerify = '/app/user/session/verify';
  static const userSessionLogout = '/app/user/session/logout';

  // Machine registration
  static const userMachineRegister = '/app/user/machine/register';

  // Machine sharing
  static const machineShareCreate = '/app/machine/share/create';
  static const machineShareAccept = '/app/machine/share/accept';
  static const machineStaffList = '/app/machine/staff/list';
  static const machineStaffRevoke = '/app/machine/staff/revoke';

  // Machine list and management
  static const machineNameUpdate = '/app/machine/name/update';
  static const userMachineRemove = '/app/user/machine/remove';
  static const userMachineList = '/app/user/machine/list';
  static const machineStatusGet = '/app/machine/status/get';

  // Machine menu
  static const machineMenuGet = '/app/machine/menu/get';
  static const machineMenuUpdate = '/app/machine/menu/update';

  // Machine ingredients
  static const machineIngredientGet = '/app/machine/ingredient/get';
  static const machineIngredientRefill = '/app/machine/ingredient/refill';
}

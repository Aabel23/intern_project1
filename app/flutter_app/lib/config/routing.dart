// Names follow objectTargetAction; GET describes the task, not the HTTP method.
// HTTP paths must match server/config/routing.py.
abstract final class Routes {
  // User authentication and registration
  static const userAccountRegister = '/app/dang-ky-nguoi-dung';
  static const userOtpSend = '/app/gui-ma-otp';
  static const userOtpVerify = '/app/xac-minh-otp';
  static const userSessionLogin = '/app/dang-nhap';
  static const userLoginVerify = '/app/xac-minh-dang-nhap';
  static const userSessionLogout = '/app/dang-xuat';

  // Machine registration
  static const userMachineRegister = '/app/dang-ky-may';

  // Machine sharing
  static const machineShareCreate = '/app/tao-ma-chia-se';
  static const machineShareAccept = '/app/nhan-chia-se';
  static const machineStaffList = '/app/nhan-vien-may';
  static const machineStaffRevoke = '/app/thu-hoi-quyen';

  // Machine list and management
  static const machineNameUpdate = '/app/doi-ten-may';
  static const userMachineRemove = '/app/go-may';
  static const userMachineList = '/app/may-cua-toi';
  static const machineStatusGet = '/machine/trang-thai';

  // Machine menu
  static const machineMenuGet = '/app/nhan-menu';
  static const machineMenuUpdate = '/app/cap-nhat-menu';

  // Machine ingredients
  static const machineIngredientGet = '/app/nhan-kho';
  static const machineIngredientRefill = '/app/nap-kho';
}

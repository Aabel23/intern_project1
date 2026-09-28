// HTTP paths must match server/config/routing.py.
abstract final class Routes {
  // User authentication and registration
  static const userRegister = '/app/dang-ky-nguoi-dung';
  static const sendOtp = '/app/gui-ma-otp';
  static const verifyOtp = '/app/xac-minh-otp';
  static const userLogin = '/app/dang-nhap';
  static const verifyLogin = '/app/xac-minh-dang-nhap';
  static const logout = '/app/dang-xuat';

  // Machine registration
  static const machineRegister = '/app/dang-ky-may';

  // Machine sharing
  static const createShare = '/app/tao-ma-chia-se';
  static const acceptShare = '/app/nhan-chia-se';
  static const listStaff = '/app/nhan-vien-may';
  static const revokeStaff = '/app/thu-hoi-quyen';

  // Machine list and management
  static const renameMachine = '/app/doi-ten-may';
  static const removeMachine = '/app/go-may';
  static const myMachines = '/app/may-cua-toi';
  static const machineStatus = '/machine/trang-thai';

  // Machine menu
  static const receiveMenu = '/app/nhan-menu';
  static const sendMenu = '/app/gui-menu';

  // Machine ingredients
  static const receiveIngredients = '/app/nhan-kho';
  static const refill = '/app/nap-kho';
}

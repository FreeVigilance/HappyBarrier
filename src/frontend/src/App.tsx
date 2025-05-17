import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import LoginUserPage from "./pages/LoginUserPage";
import VerificationPage from "./pages/VerificationPage";
import UserProfile from "./pages/UserProfile";
import UserRequests from "./pages/UserRequests";
import UserBarriers from "./pages/UserBarriers";
import Barrier from "./pages/Barrier";
import VerifyAdminPage from "./pages/VerifyAdminPage";
import AdminSmsPage from "./pages/AdminSmsPage";
import RestoreCodePage from "./pages/RestoreCodePage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import ChangePhonePage from "./pages/ChangePhonePage";
import AdminPage from "./pages/AdminPage";
import MyBarrierPage from "./pages/MyBarrierPage";
import AddPhonePage from "./pages/AddPhonePage";
import EditPhonePage from "./pages/EditPhonePage";
import DeleteAccount from "./pages/DeleteAccount";
import AdminRequests from "./pages/AdminRequests";
import ChangePhoneAdminPage from "./pages/ChangePhoneAdminPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import AdminBarriersPage from "./pages/AdminBarriersPage";
import AdminBarrierDetails from "./pages/AdminBarrierDetails";
import BarrierUsersPage from "./pages/BarrierUsersPage";
import AdminUserProfile from "./pages/AdminUserProfile";
import AdminAddPhonePage from "./pages/AdminAddPhonePage";
import AdminEditPhonePage from "./pages/AdminEditPhonePage";
import CreateBarrierPage from "./pages/CreateBarrierPage";
import AdminBarrierSettingsPage from "./pages/AdminBarrierSettingsPage";
import UserBarrierActionsPage from "./pages/UserBarrierActionsPage";
import AdminBarrierActionsPage from "./pages/AdminBarrierActionsPage";

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginUserPage />} />
        <Route path="/verifyuser" element={<VerificationPage />} />
        <Route path="/verifyadmin" element={<VerifyAdminPage />} />
        <Route path="/smsadmin" element={<AdminSmsPage />} />
        <Route path="/restoresms" element={<RestoreCodePage />} />
        <Route path="/restorepassword" element={<ResetPasswordPage />} />
        <Route path="/user" element={<UserProfile />} />
        <Route path="/change-phone" element={<ChangePhonePage />} />
        <Route path="/requests" element={<UserRequests />} />
        <Route path="/barriers" element={<UserBarriers />} />
        <Route path="/barrier-details" element={<Barrier />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/mybarrier" element={<MyBarrierPage />} />
        <Route path="/add-phone" element={<AddPhonePage />} />
        <Route path="/edit-phone" element={<EditPhonePage />} />
        <Route path="/delete-account" element={<DeleteAccount />} />
        <Route path="/admin-requests" element={<AdminRequests />} />
        <Route path="/change-phone-admin" element={<ChangePhoneAdminPage />} />
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="/admin-barriers" element={<AdminBarriersPage />} />
        <Route path="/admin-barrier-page" element={<AdminBarrierDetails />} />
        <Route path="/barrier-users" element={<BarrierUsersPage />} />
        <Route path="/user-profile" element={<AdminUserProfile />} />
        <Route path="/add-phone-admin" element={<AdminAddPhonePage />} />
        <Route path="/edit-phone-admin" element={<AdminEditPhonePage />} />
        <Route path="/create-barrier" element={<CreateBarrierPage />} />
        <Route
          path="/barrier-settings"
          element={<AdminBarrierSettingsPage />}
        />
        <Route path="/barrier-history" element={<UserBarrierActionsPage />} />
        <Route
          path="/barrier-history-admin"
          element={<AdminBarrierActionsPage />}
        />
      </Routes>
    </Router>
  );
};

export default App;

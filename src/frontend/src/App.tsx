import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
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

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginUserPage />} />
        <Route path="/verifyuser" element={<VerificationPage />} />
        <Route path="/verifyadmin" element={<VerifyAdminPage />} />
        <Route path="/smsadmin" element={<AdminSmsPage />} />
        <Route path="/restoresms" element={<RestoreCodePage />} />
        <Route path="/restorepassword" element={<ResetPasswordPage />} />
        <Route path="/user" element={<UserProfile />} />
        <Route path="/requests" element={<UserRequests />} />
        <Route path="/barriers" element={<UserBarriers />} />
        <Route path="/barrier-details" element={<Barrier />} />
      </Routes>
    </Router>
  );
};

export default App;

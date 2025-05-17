import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FaArrowLeft } from "react-icons/fa";

const ChangePasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const phone = location.state?.phone || localStorage.getItem("phone");

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const requestCode = async () => {
    setError("");
    try {
      const res = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, mode: "change_password" }),
      });
      const data = await res.json();
      if (res.ok) {
        setVerificationToken(data.verification_token);
        setStep(2);
      } else {
        setError(data.detail || "Ошибка при отправке кода");
      }
    } catch {
      setError("Ошибка сети при отправке кода");
    }
  };

  const verifyCode = async () => {
    setError("");
    try {
      const res = await fetch("/api/auth/codes/verify/", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone,
          code,
          verification_token: verificationToken,
        }),
      });
      const data = await res.json();
      if (res.ok && data.message === "Code verified successfully.") {
        setStep(3);
      } else {
        setError(data.detail || "Неверный код подтверждения");
      }
    } catch {
      setError("Ошибка сети при верификации кода");
    }
  };

  const submitPasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      setError("Новые пароли не совпадают");
      return;
    }
    setError("");

    let token =
      location.state?.access_token || localStorage.getItem("access_token");
    const refresh =
      location.state?.refresh_token || localStorage.getItem("refresh_token");

    const makeRequest = async (access: string) => {
      const res = await fetch("/api/users/me/password/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${access}`,
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
          verification_token: verificationToken,
        }),
      });
      return res;
    };

    try {
      let res = await makeRequest(token);
      if (res.status === 401 && refresh) {
        const refreshRes = await fetch("/api/auth/token/refresh/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
        });
        const refreshData = await refreshRes.json();
        if (refreshRes.ok && refreshData.access) {
          token = refreshData.access;
          localStorage.setItem("access_token", token);
          res = await makeRequest(token);
        } else {
          navigate("/login");
          return;
        }
      }

      const data = await res.json();
      if (res.ok) {
        alert("Пароль успешно изменён");
        navigate("/admin", {
          state: {
            phone,
            access_token: token,
            refresh_token: refresh,
          },
        });
      } else {
        setError(data.detail || "Ошибка при смене пароля");
      }
    } catch {
      setError("Ошибка сети при смене пароля");
    }
  };

  return (
    <div style={styles.container}>
      <button style={styles.backIcon} onClick={() => navigate("/admin")}>
        {" "}
        <FaArrowLeft /> Назад{" "}
      </button>
      <div style={styles.card}>
        <h2 style={styles.title}>Смена пароля</h2>

        {step === 1 && (
          <>
            <p>Мы отправим SMS с кодом на номер {phone}</p>
            <button style={styles.button} onClick={requestCode}>
              Отправить код
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <p>Введите код из SMS</p>
            <input
              style={styles.input}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Код"
            />
            <button style={styles.button} onClick={verifyCode}>
              Подтвердить код
            </button>
            <ResendButton requestCode={requestCode} />
          </>
        )}

        {step === 3 && (
          <>
            <input
              style={styles.input}
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="Старый пароль"
            />
            <input
              style={styles.input}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Новый пароль"
            />
            <input
              style={styles.input}
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Повторите новый пароль"
            />
            <button style={styles.button} onClick={submitPasswordChange}>
              Сменить пароль
            </button>
          </>
        )}

        {error && <p style={styles.error}>{error}</p>}
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    width: "100vw",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "20px",
    color: "#333",
    fontFamily: "sans-serif",
    position: "relative",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "30px",
    borderRadius: "16px",
    boxShadow: "0 4px 20px rgba(90, 68, 120, 0.1)",
    width: "100%",
    maxWidth: "400px",
    textAlign: "center",
    position: "relative",
  },
  title: {
    fontSize: "22px",
    color: "#5a4478",
    marginBottom: "20px",
  },
  input: {
    width: "100%",
    padding: "12px",
    marginBottom: "10px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    fontSize: "16px",
  },
  button: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    cursor: "pointer",
    width: "100%",
    marginTop: "10px",
  },
  error: {
    color: "red",
    marginTop: "10px",
    fontSize: "14px",
  },
  backIcon: {
    alignSelf: "flex-start",
    background: "none",
    border: "none",
    color: "#5a4478",
    fontSize: "20px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    marginBottom: "20px",
  },
};

type ResendButtonProps = {
  requestCode: () => void;
};

const ResendButton: React.FC<ResendButtonProps> = ({ requestCode }) => {
  const [timer, setTimer] = useState(60);
  const [canResend, setCanResend] = useState(false);

  React.useEffect(() => {
    if (!canResend && timer > 0) {
      const interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
      return () => clearInterval(interval);
    } else if (timer <= 0) {
      setCanResend(true);
    }
  }, [timer, canResend]);

  const handleResend = () => {
    if (canResend) {
      requestCode();
      setTimer(60);
      setCanResend(false);
    }
  };

  return (
    <button
      style={{
        ...styles.button,
        backgroundColor: canResend ? "#5a4478" : "#ccc",
        cursor: canResend ? "pointer" : "not-allowed",
      }}
      onClick={handleResend}
      disabled={!canResend}
    >
      {canResend ? "Выслать код повторно" : `Повторно через ${timer} сек`}
    </button>
  );
};

export default ChangePasswordPage;

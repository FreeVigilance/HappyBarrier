import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaTimesCircle } from "react-icons/fa";
import VerifyAdminPage from "./VerifyAdminPage";
import ResetPasswordPage from "./ResetPasswordPage";

const RestoreCodePage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [phone] = useState(() => location.state?.phone || "+79888363930");
  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [timer, setTimer] = useState(60);
  const [isResendDisabled, setIsResendDisabled] = useState(true);

  const didRequest = useRef(false);

  const requestCode = async () => {
    try {
      const response = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ phone, mode: "reset_password" }),
      });

      const data = await response.json();

      if (response.ok && data.verification_token) {
        setVerificationToken(data.verification_token);
        setErrorMessage("");
        setTimer(60);
        setIsResendDisabled(true);
      } else {
        setErrorMessage(data.detail || "Ошибка при отправке кода");
      }
    } catch (error) {
      console.error("Ошибка при отправке кода:", error);
      setErrorMessage("Ошибка сети при отправке кода");
    }
  };

  useEffect(() => {
    if (didRequest.current) return;
    didRequest.current = true;
    requestCode();
  }, [phone]);

  useEffect(() => {
    if (!isResendDisabled) return;
    const interval = setInterval(() => {
      setTimer((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setIsResendDisabled(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [isResendDisabled]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    if (!/^\d{6}$/.test(code)) {
      setErrorMessage("Код должен содержать 6 цифр.");
      return;
    }

    try {
      const response = await fetch("/api/auth/codes/verify/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          phone,
          code,
          verification_token: verificationToken,
        }),
      });

      const result = await response.json();

      if (response.ok && result === "Code verified successfully.") {
        navigate("/restorepassword", {
          state: { phone, verification_token: verificationToken },
        });
      } else {
        setErrorMessage(result.detail || "Неверный код. Повторите попытку.");
      }
    } catch (error) {
      console.error("Ошибка при верификации кода:", error);
      setErrorMessage("Ошибка сети при подтверждении кода");
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Восстановление пароля</h2>
        <p style={styles.subtitle}>Введите код, отправленный на номер:</p>
        <p style={styles.phone}>{phone}</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputBox}>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Код"
              maxLength={6}
              style={styles.input}
              required
            />
            {code && (
              <FaTimesCircle
                onClick={() => setCode("")}
                style={styles.clearIcon}
              />
            )}
          </div>
          {errorMessage && <p style={styles.errorText}>{errorMessage}</p>}
          <p style={styles.helperText}>На телефон выслан код подтверждения</p>
          <button type="submit" style={styles.button}>
            Подтвердить
          </button>
        </form>

        <button
          onClick={requestCode}
          disabled={isResendDisabled}
          style={
            isResendDisabled ? styles.resendButtonDisabled : styles.resendButton
          }
        >
          Отправить код повторно
        </button>

        {isResendDisabled && (
          <p style={styles.timerText}>
            ⏳ Отправить код повторно можно через 0:
            {timer.toString().padStart(2, "0")}
          </p>
        )}
      </div>
    </div>
  );
};
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fff6fa",
    minHeight: "100vh",
    minWidth: "100vw",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: "20px",
    boxSizing: "border-box",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "40px 20px",
    borderRadius: "16px",
    width: "100%",
    maxWidth: "420px",
    boxShadow: "0 8px 40px rgba(90, 68, 120, 0.10)",
    textAlign: "center",
    color: "#000",
    boxSizing: "border-box",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#5a4478",
    marginBottom: "10px",
  },
  subtitle: {
    fontSize: "14px",
    color: "#444",
  },
  phone: {
    fontSize: "16px",
    color: "#222",
    marginBottom: "20px",
    wordBreak: "break-word",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  inputBox: {
    position: "relative",
  },
  input: {
    width: "100%",
    padding: "14px",
    fontSize: "16px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    backgroundColor: "#f8f5fa",
    textAlign: "center",
    color: "#000",
    boxSizing: "border-box",
  },
  clearIcon: {
    position: "absolute",
    right: "10px",
    top: "50%",
    transform: "translateY(-50%)",
    cursor: "pointer",
    color: "#999",
  },
  button: {
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    borderRadius: "25px",
    padding: "14px",
    fontSize: "16px",
    cursor: "pointer",
    transition: "background 0.3s ease",
  },
  resendButton: {
    backgroundColor: "#eee",
    border: "none",
    borderRadius: "25px",
    padding: "10px",
    fontSize: "14px",
    marginTop: "10px",
    cursor: "pointer",
  },
  resendButtonDisabled: {
    backgroundColor: "#ddd",
    border: "none",
    borderRadius: "25px",
    padding: "10px",
    fontSize: "14px",
    marginTop: "10px",
    color: "#888",
    cursor: "not-allowed",
  },
  timerText: {
    marginTop: "10px",
    fontSize: "14px",
    color: "#999",
  },
  errorText: {
    color: "red",
    fontSize: "14px",
  },
  helperText: {
    fontSize: "12px",
    color: "#666",
  },
};

export default RestoreCodePage;

import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FaTimesCircle } from "react-icons/fa";

const AdminSmsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState(
    () => location.state?.phone || "+79888363930",
  );
  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState(
    () => location.state?.verification_token || "",
  );
  const [errorMessage, setErrorMessage] = useState("");
  const [timer, setTimer] = useState(60);
  const [isResendDisabled, setIsResendDisabled] = useState(true);

  const didFetchToken = useRef(false); // 🔹 защита от двойного вызова

  useEffect(() => {
    if (didFetchToken.current) return;
    didFetchToken.current = true;

    let interval: NodeJS.Timeout;

    const fetchTokenAndStartTimer = async () => {
      setErrorMessage("");
      setTimer(60);
      setIsResendDisabled(true);

      try {
        const response = await fetch("/api/auth/codes/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ phone, mode: "login" }),
        });

        const data = await response.json();

        if (response.ok && data.verification_token) {
          setVerificationToken(data.verification_token);
        } else {
          setErrorMessage(
            data.detail || "Не удалось получить токен подтверждения",
          );
        }
      } catch (error) {
        console.error("Ошибка при получении токена:", error);
        setErrorMessage("Ошибка сети при получении токена");
      }

      interval = setInterval(() => {
        setTimer((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            setIsResendDisabled(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    };

    fetchTokenAndStartTimer();

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [phone]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    if (!/^\d{6}$/.test(code)) {
      setErrorMessage("Код должен содержать 6 цифр.");
      return;
    }

    try {
      const verifyResponse = await fetch("/api/auth/codes/verify/", {
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

      const verifyJson = await verifyResponse.json();

      if (verifyJson.message === "Code verified successfully.") {
        const loginResponse = await fetch("/api/auth/login/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            phone,
            verification_token: verificationToken,
          }),
        });

        const loginData = await loginResponse.json();

        if (
          loginResponse.ok &&
          loginData.access_token &&
          loginData.refresh_token
        ) {
          localStorage.setItem("access_token", loginData.access_token);
          localStorage.setItem("refresh_token", loginData.refresh_token);
          localStorage.setItem("phone", phone);

          navigate("/admin", {
            state: {
              phone,
              access_token: loginData.access_token,
              refresh_token: loginData.refresh_token,
            },
          });
        } else {
          setErrorMessage(loginData.detail || "Ошибка входа");
        }
      } else {
        setErrorMessage(verifyJson.detail || "Ошибка верификации");
      }
    } catch (error) {
      console.error("Ошибка сети:", error);
      setErrorMessage("Не удалось связаться с сервером");
    }
  };

  const handleResendCode = async () => {
    setTimer(60);
    setIsResendDisabled(true);
    setErrorMessage("");

    try {
      const response = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ phone, mode: "login" }),
      });

      const data = await response.json();

      if (response.ok && data.verification_token) {
        setVerificationToken(data.verification_token);
      } else {
        setErrorMessage(data.detail || "Ошибка при повторной отправке");
      }
    } catch (error) {
      console.error("Ошибка при повторной отправке:", error);
      setErrorMessage("Не удалось повторно связаться с сервером");
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Мобильный телефон</h2>
        <p style={styles.phone}>{phone}</p>

        <h3 style={styles.subtitle}>Код подтверждения</h3>
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
          <button type="submit" style={styles.confirmButton}>
            Подтвердить
          </button>
        </form>

        <button
          onClick={handleResendCode}
          disabled={isResendDisabled}
          style={
            isResendDisabled ? styles.resendButtonDisabled : styles.resendButton
          }
        >
          Отправить код повторно
        </button>

        {isResendDisabled && (
          <div style={styles.timerBox}>
            <span style={styles.timerText}>
              ⏳ Отправить код повторно можно через 0:
              {timer.toString().padStart(2, "0")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fff6fa",
    minHeight: "100vh",
    width: "100vw",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: "5vw",
    boxSizing: "border-box",
  },
  card: {
    backgroundColor: "#fff",
    padding: "5vw",
    borderRadius: "16px",
    width: "100%",
    maxWidth: "500px",
    minWidth: "min(100%, 300px)",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)",
    textAlign: "center",
    boxSizing: "border-box",
  },
  title: {
    fontSize: "clamp(20px, 5vw, 26px)",
    fontWeight: "bold",
    marginBottom: "10px",
    color: "#000",
  },
  phone: {
    fontSize: "clamp(16px, 4vw, 20px)",
    color: "#000",
    marginBottom: "10px",
    wordBreak: "break-word",
  },
  subtitle: {
    fontSize: "clamp(16px, 5vw, 20px)",
    fontWeight: "bold",
    marginTop: "20px",
    color: "#5a4478",
  },
  form: {
    marginTop: "20px",
  },
  inputBox: {
    position: "relative",
    marginBottom: "10px",
  },
  input: {
    width: "100%",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    backgroundColor: "#f2e9f5",
    fontSize: "16px",
    color: "#000",
    boxSizing: "border-box",
    textAlign: "center",
  },
  clearIcon: {
    position: "absolute",
    right: "10px",
    top: "50%",
    transform: "translateY(-50%)",
    color: "#5a4478",
    cursor: "pointer",
  },
  errorText: {
    color: "red",
    fontSize: "13px",
    marginTop: "4px",
  },
  helperText: {
    fontSize: "12px",
    color: "#666",
    marginBottom: "10px",
  },
  confirmButton: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    padding: "14px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "16px",
    width: "100%",
    boxSizing: "border-box",
  },
  resendButton: {
    backgroundColor: "#d7c4ed",
    color: "#5a4478",
    border: "none",
    padding: "14px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "16px",
    marginTop: "15px",
    width: "100%",
    boxSizing: "border-box",
  },
  resendButtonDisabled: {
    backgroundColor: "#eae0f5",
    color: "#a89bb5",
    border: "none",
    padding: "14px",
    borderRadius: "25px",
    fontSize: "16px",
    marginTop: "15px",
    width: "100%",
    cursor: "not-allowed",
    boxSizing: "border-box",
  },
  timerBox: {
    marginTop: "10px",
    padding: "10px",
    border: "1px solid #ccc",
    borderRadius: "10px",
    backgroundColor: "#fff",
  },
  timerText: {
    fontSize: "14px",
    color: "#666",
  },
};

export default AdminSmsPage;

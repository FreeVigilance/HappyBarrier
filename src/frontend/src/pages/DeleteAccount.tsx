import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const DeleteAccount: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const phone = location.state?.phone || localStorage.getItem("phone");
  const accessToken =
    location.state?.access_token || localStorage.getItem("access_token");

  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [step, setStep] = useState<"request" | "verify" | "done">("request");
  const [timer, setTimer] = useState(60);
  const [resendEnabled, setResendEnabled] = useState(false);

  const didRequestCode = useRef(false);

  const requestCode = async () => {
    setErrorMessage("");
    try {
      const res = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, mode: "delete_account" }),
      });
      const data = await res.json();
      if (res.ok) {
        setVerificationToken(data.verification_token);
        setStep("verify");
        setTimer(60);
        setResendEnabled(false);
      } else {
        setErrorMessage(data.detail || "Ошибка отправки кода");
      }
    } catch {
      setErrorMessage("Ошибка сети при запросе кода");
    }
  };

  useEffect(() => {
    if (!didRequestCode.current) {
      didRequestCode.current = true;
      requestCode();
    }
  }, []);

  useEffect(() => {
    if (step === "verify" && timer > 0) {
      const interval = setInterval(() => {
        setTimer((t) => {
          if (t <= 1) {
            clearInterval(interval);
            setResendEnabled(true);
          }
          return t - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [step, timer]);

  const handleVerifyAndDelete = async () => {
    setErrorMessage("");

    try {
      const verifyRes = await fetch("/api/auth/codes/verify/", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone,
          code,
          verification_token: verificationToken,
        }),
      });

      const verifyData = await verifyRes.json();
      if (
        !verifyRes.ok ||
        verifyData.message !== "Code verified successfully."
      ) {
        setErrorMessage(verifyData.detail || "Ошибка подтверждения кода");
        return;
      }

      const deleteRes = await fetch("/api/users/me/", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ verification_token: verificationToken }),
      });

      if (deleteRes.ok) {
        localStorage.clear();
        setStep("done");
        setTimeout(() => navigate("/login"), 2000);
      } else {
        const data = await deleteRes.json();
        setErrorMessage(data.detail || "Ошибка удаления аккаунта");
      }
    } catch {
      setErrorMessage("Ошибка сети при удалении");
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {step === "request" && (
          <>
            <p>Запрашиваем код подтверждения...</p>
            <button
              style={styles.secondaryButton}
              onClick={() => navigate("/user")}
            >
              Назад в профиль
            </button>
          </>
        )}

        {step === "verify" && (
          <>
            <h2 style={styles.title}>Удаление профиля</h2>
            <p>
              Введите код, отправленный на <strong>{phone}</strong>
            </p>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              placeholder="Код"
              style={styles.input}
            />
            {errorMessage && <p style={styles.errorText}>{errorMessage}</p>}

            <button style={styles.button} onClick={handleVerifyAndDelete}>
              ✅ Подтвердить и удалить
            </button>

            <button
              style={{ ...styles.secondaryButton }}
              onClick={() => navigate("/user")}
            >
              Назад в профиль
            </button>

            <button
              onClick={requestCode}
              disabled={!resendEnabled}
              style={{
                ...styles.linkButton,
                opacity: resendEnabled ? 1 : 0.5,
                cursor: resendEnabled ? "pointer" : "not-allowed",
              }}
            >
              {resendEnabled
                ? "Выслать код повторно"
                : `Повтор через ${timer} сек.`}
            </button>
          </>
        )}

        {step === "done" && (
          <p style={{ textAlign: "center", fontSize: "16px", color: "green" }}>
            ✅ Профиль успешно удалён.
            <br />
            Возврат на вход...
          </p>
        )}
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px",
  },
  card: {
    backgroundColor: "#fff",
    padding: "30px",
    borderRadius: "16px",
    width: "100%",
    maxWidth: "400px",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.1)",
    textAlign: "center",
  },
  title: {
    fontSize: "20px",
    fontWeight: "bold",
    color: "#5a4478",
    marginBottom: "12px",
  },
  input: {
    width: "100%",
    padding: "12px",
    fontSize: "16px",
    marginTop: "10px",
    marginBottom: "10px",
    border: "1px solid #ccc",
    borderRadius: "8px",
    textAlign: "center",
  },
  button: {
    width: "100%",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    backgroundColor: "#d9534f",
    color: "#fff",
    border: "none",
    cursor: "pointer",
    marginTop: "10px",
  },
  secondaryButton: {
    width: "100%",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    backgroundColor: "#e6dbf3",
    color: "#5a4478",
    border: "none",
    cursor: "pointer",
    marginTop: "10px",
  },
  linkButton: {
    marginTop: "14px",
    fontSize: "14px",
    color: "#5a4478",
    background: "none",
    border: "none",
    textDecoration: "underline",
    fontWeight: "bold",
  },
  errorText: {
    color: "red",
    fontSize: "14px",
    marginTop: "10px",
  },
};

export default DeleteAccount;

import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FaArrowLeft, FaTimesCircle } from "react-icons/fa";

const VerifyAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState(
    () => location.state?.phone || "+79888363930",
  );
  const [verification_token, setVerificationToken] = useState(
    () => location.state?.verification_token || "",
  );
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleBack = () => {
    navigate("/login", { state: { phone } });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    if (!password) {
      setErrorMessage("Пароль не должен быть пустым.");
      return;
    }

    try {
      const response = await fetch("/api/auth/admin/password_verification/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone,
          password,
        }),
      });

      const data = await response.json();

      if (response.ok && data.message === "Password verified successfully.") {
        navigate("/smsadmin", {
          state: { phone, verification_token: verification_token },
        });
      } else {
        setErrorMessage(data.detail || "Ошибка верификации пароля.");
      }
    } catch (error) {
      console.error("Ошибка сети:", error);
      setErrorMessage("Не удалось связаться с сервером.");
    }
  };

  const handleRecovery = () => {
    navigate("/restoresms", { state: { phone } });
  };

  return (
    <div style={styles.container}>
      <div style={styles.wrapper}>
        <div style={styles.card}>
          <button onClick={handleBack} style={styles.backButton}>
            <FaArrowLeft style={styles.icon} />{" "}
            <span>Изменить номер телефона</span>
          </button>

          <h2 style={styles.title}>Мобильный телефон</h2>
          <p style={styles.phone}>{phone}</p>

          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.inputWrapper}>
              <label htmlFor="password" style={styles.label}>
                Введите пароль
              </label>
              <div style={styles.inputBox}>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={styles.input}
                  placeholder="Введите пароль"
                />
                {password && (
                  <FaTimesCircle
                    onClick={() => setPassword("")}
                    style={styles.clearIcon}
                  />
                )}
              </div>
              {errorMessage && <p style={styles.errorText}>{errorMessage}</p>}
            </div>

            <div style={styles.buttonRow}>
              <button type="submit" style={styles.button}>
                Далее
              </button>
              <button
                type="button"
                style={styles.button}
                onClick={handleRecovery}
              >
                Восстановить пароль
              </button>
            </div>
          </form>
        </div>
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
    padding: "0",
  },
  wrapper: {
    flex: 1,
    maxWidth: "100%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "100%",
    padding: "20px",
  },
  card: {
    backgroundColor: "#fff",
    padding: "30px",
    borderRadius: "10px",
    width: "100%",
    maxWidth: "400px",
    boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)",
    textAlign: "center",
  },
  backButton: {
    display: "flex",
    alignItems: "center",
    backgroundColor: "transparent",
    border: "none",
    color: "#5a4478",
    cursor: "pointer",
    fontSize: "14px",
    marginBottom: "20px",
  },
  icon: {
    marginRight: "6px",
  },
  title: {
    fontSize: "22px",
    marginBottom: "8px",
    color: "#000",
  },
  phone: {
    fontSize: "18px",
    color: "#000",
    marginBottom: "10px",
  },
  form: {
    marginTop: "20px",
  },
  inputWrapper: {
    marginBottom: "20px",
    textAlign: "left",
  },
  label: {
    display: "block",
    marginBottom: "8px",
    color: "#5a4478",
    fontSize: "14px",
  },
  inputBox: {
    position: "relative",
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
    marginTop: "8px",
  },
  buttonRow: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: "10px",
  },
  button: {
    flex: 1,
    minWidth: "140px",
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    padding: "12px 10px",
    borderRadius: "25px",
    cursor: "pointer",
    fontSize: "14px",
  },
};

export default VerifyAdminPage;

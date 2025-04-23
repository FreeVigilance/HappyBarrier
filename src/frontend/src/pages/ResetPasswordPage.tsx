import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState(
    () => location.state?.phone || "+79888363930",
  );
  const verificationToken = location.state?.verification_token || "";

  const [newPassword, setNewPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage("");

    if (newPassword.length < 6) {
      setErrorMessage("Пароль должен содержать минимум 6 символов.");
      return;
    }

    try {
      const response = await fetch("/api/users/me/password/reset/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          phone,
          new_password: newPassword,
          verification_token: verificationToken,
        }),
      });

      if (response.ok) {
        navigate("/verifyadmin", { state: { phone } });
      } else {
        const data = await response.json();
        setErrorMessage(data.detail || "Ошибка сброса пароля");
      }
    } catch (error) {
      console.error("Ошибка при сбросе пароля:", error);
      setErrorMessage("Ошибка сети");
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Новый пароль</h2>
        <p style={styles.subtitle}>Введите новый пароль для номера:</p>
        <p style={styles.phone}>{phone}</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Новый пароль"
            style={styles.input}
            required
          />
          {errorMessage && <p style={styles.errorText}>{errorMessage}</p>}
          <button type="submit" style={styles.button}>
            Сбросить пароль
          </button>
        </form>
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
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "40px",
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
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
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
  errorText: {
    color: "red",
    fontSize: "14px",
  },
};

export default ResetPasswordPage;

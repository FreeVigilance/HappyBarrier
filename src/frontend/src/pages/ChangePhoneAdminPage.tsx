import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaArrowLeft } from "react-icons/fa";

const ChangePhoneAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [oldCode, setOldCode] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newCode, setNewCode] = useState("");
  const [oldToken, setOldToken] = useState("");
  const [newToken, setNewToken] = useState("");
  const [error, setError] = useState("");

  const isValidPhone = (phone: string) => {
    const cleaned = phone.replace(/[^\d]/g, "");
    return /^7\d{10}$/.test(cleaned);
  };

  const translateError = (error: string): string => {
    const map: { [key: string]: string } = {
      "Verification code was already sent. Try again later.":
        "Код уже был отправлен. Попробуйте позже.",
      "Invalid verification code.": "Неверный код подтверждения.",
      "Phone number is already in use.": "Этот номер уже используется.",
    };
    return map[error] || error;
  };

  const handleSendOldCode = async () => {
    setError("");
    try {
      const res = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone: localStorage.getItem("phone"),
          mode: "change_phone_old",
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setOldToken(data.verification_token);
        setStep(2);
      } else {
        const retryMsg = data.retry_after
          ? ` Повторите через ${data.retry_after} секунд.`
          : "";
        setError(
          translateError(data.detail || "Ошибка отправки кода") + retryMsg,
        );
      }
    } catch (e) {
      setError("Ошибка сети");
    }
  };

  const handleResendOldCode = () => handleSendOldCode();

  const handleVerifyOldCode = async () => {
    try {
      const res = await fetch("/api/auth/codes/verify/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone: localStorage.getItem("phone"),
          code: oldCode,
          verification_token: oldToken,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setStep(3);
      } else {
        setError(translateError(data.detail || "Неверный код"));
      }
    } catch (e) {
      setError("Ошибка сети");
    }
  };

  const handleSendNewCode = async () => {
    if (!isValidPhone(newPhone.replace("+", ""))) {
      setError("Введите корректный номер телефона в формате +7XXXXXXXXXX");
      return;
    }
    try {
      const res = await fetch("/api/auth/codes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone: newPhone,
          mode: "change_phone_new",
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setNewToken(data.verification_token);
        setStep(4);
      } else {
        const retryMsg = data.retry_after
          ? ` Повторите через ${data.retry_after} секунд.`
          : "";
        setError(
          translateError(data.detail || "Ошибка отправки кода на новый номер") +
            retryMsg,
        );
      }
    } catch (e) {
      setError("Ошибка сети");
    }
  };

  const handleResendNewCode = () => handleSendNewCode();

  const handleVerifyNewCodeAndSubmit = async () => {
    try {
      const res = await fetch("/api/auth/codes/verify/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          phone: newPhone,
          code: newCode,
          verification_token: newToken,
        }),
      });
      if (!res.ok) {
        setError("Код для нового номера неверный");
        return;
      }

      const finalRes = await fetch("/api/users/me/phone/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          new_phone: newPhone,
          old_verification_token: oldToken,
          new_verification_token: newToken,
        }),
      });
      const result = await finalRes.json();
      if (finalRes.ok) {
        localStorage.setItem("phone", result.phone);
        alert("Номер телефона успешно обновлён!");
        navigate("/admin");
      } else {
        setError(
          translateError(result.detail || "Не удалось изменить номер телефона"),
        );
      }
    } catch (e) {
      setError("Ошибка сети");
    }
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
    backIcon: {
      position: "absolute",
      top: "20px",
      left: "20px",
      background: "none",
      border: "none",
      color: "#5a4478",
      fontSize: "20px",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: "6px",
    },
    card: {
      backgroundColor: "#ffffff",
      padding: "20px",
      borderRadius: "12px",
      boxShadow: "0 4px 15px rgba(90, 68, 120, 0.2)",
      width: "100%",
      maxWidth: "400px",
      textAlign: "center",
      marginTop: "60px",
    },
    title: {
      fontSize: "22px",
      fontWeight: "bold",
      color: "#5a4478",
      marginBottom: "20px",
    },
    input: {
      width: "100%",
      padding: "12px",
      fontSize: "16px",
      marginBottom: "10px",
      border: "1px solid #ccc",
      borderRadius: "8px",
      outline: "none",
      backgroundColor: "#f2e9f5",
      color: "#333",
    },
    button: {
      backgroundColor: "#5a4478",
      color: "#fff",
      padding: "12px",
      border: "none",
      borderRadius: "25px",
      cursor: "pointer",
      width: "100%",
      marginTop: "10px",
    },
    errorText: {
      color: "red",
      marginTop: "10px",
    },
  };

  return (
    <div style={styles.container}>
      <button style={styles.backIcon} onClick={() => navigate("/admin")}>
        {" "}
        <FaArrowLeft /> Назад{" "}
      </button>
      <div style={styles.card}>
        <h2 style={styles.title}>Смена номера телефона</h2>

        {step === 1 && (
          <>
            <p>Ваш текущий номер: {localStorage.getItem("phone")}</p>
            <button style={styles.button} onClick={handleSendOldCode}>
              Получить код
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <p>Введите код, отправленный на текущий номер</p>
            <input
              style={styles.input}
              value={oldCode}
              onChange={(e) => setOldCode(e.target.value)}
            />
            <button style={styles.button} onClick={handleVerifyOldCode}>
              Подтвердить
            </button>
            <button
              style={{
                ...styles.button,
                backgroundColor: "#d7c4ed",
                color: "#5a4478",
              }}
              onClick={handleResendOldCode}
            >
              Получить код повторно
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <p>Введите новый номер телефона</p>
            <input
              style={styles.input}
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              placeholder="+79990000000"
            />
            <button style={styles.button} onClick={handleSendNewCode}>
              Получить код
            </button>
          </>
        )}

        {step === 4 && (
          <>
            <p>Введите код, отправленный на новый номер</p>
            <input
              style={styles.input}
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
            />
            <button
              style={styles.button}
              onClick={handleVerifyNewCodeAndSubmit}
            >
              Подтвердить и изменить номер
            </button>
            <button
              style={{
                ...styles.button,
                backgroundColor: "#d7c4ed",
                color: "#5a4478",
              }}
              onClick={handleResendNewCode}
            >
              Получить код повторно
            </button>
          </>
        )}

        {error && <p style={styles.errorText}>{error}</p>}
      </div>
    </div>
  );
};

export default ChangePhoneAdminPage;

import React, { useState, useRef, useId } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AddressSuggestions } from "react-dadata";
import "react-dadata/dist/react-dadata.css";

const CreateBarrierPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const accessToken = location.state?.access_token;
  const refreshToken = location.state?.refresh_token;
  const phone = location.state?.phone;

  const suggestionsRef = useRef<any>(null);
  const uid = useId();

  const [address, setAddress] = useState<any>("");
  const [devicePhone, setDevicePhone] = useState("+7");
  const [deviceModel, setDeviceModel] = useState("RTU5025");
  const [devicePassword, setDevicePassword] = useState("");
  const [devicePhonesAmount, setDevicePhonesAmount] = useState("");
  const [additionalInfo, setAdditionalInfo] = useState("");
  const [isPublic, setIsPublic] = useState(true);

  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [successMessage, setSuccessMessage] = useState("");

  const validate = () => {
    const newErrors: { [key: string]: string } = {};

    if (!address || !address.value)
      newErrors.address = "Укажите корректный адрес.";

    if (!/^\+7\d{10}$/.test(devicePhone))
      newErrors.devicePhone = "Неверный формат номера.";

    if (!/^[0-9]{4}$/.test(devicePassword))
      newErrors.devicePassword = "Пароль должен состоять из 4 цифр.";

    const amount = Number(devicePhonesAmount);
    if (!/^[0-9]+$/.test(devicePhonesAmount) || amount < 1 || amount > 10000) {
      newErrors.devicePhonesAmount = "Укажите число от 1 до 10000.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    try {
      const response = await fetch("/api/admin/barriers/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          address: address.value,
          device_phone: devicePhone,
          device_model: deviceModel,
          device_password: devicePassword,
          device_phones_amount: Number(devicePhonesAmount),
          additional_info: additionalInfo,
          is_public: isPublic,
        }),
      });

      const data = await response.json();

      if (response.status === 201) {
        setSuccessMessage("Шлагбаум успешно создан.");
        setTimeout(
          () =>
            navigate("/admin-barriers", {
              state: { access_token: accessToken, refresh_token: refreshToken },
            }),
          1000,
        );
      } else {
        setErrors({ general: data.detail || "Ошибка при создании." });
      }
    } catch {
      setErrors({ general: "Ошибка сети." });
    }
  };

  const handleExampleClick = () => {
    if (suggestionsRef.current) {
      suggestionsRef.current.setInputValue("Манежная площадь, 1, Москва");
    }
  };

  return (
    <div style={styles.container}>
      <button
        onClick={() => navigate("/admin-barriers")}
        style={styles.backButton}
      >
        ← Назад
      </button>

      <h2 style={styles.title}>Создание шлагбаума</h2>

      <div style={styles.formWrapper}>
        <div style={styles.fieldBlock}>
          <label>Адрес</label>
          <AddressSuggestions
            ref={suggestionsRef}
            token="0a416883e15e66e7d5bc38d86325666e4f4809f7"
            value={address}
            onChange={setAddress}
            uid={uid}
            inputProps={{ style: styles.input }}
          />
          <button onClick={handleExampleClick} style={styles.exampleButton}>
            Вставить пример адреса
          </button>
          {errors.address && <p style={styles.error}>{errors.address}</p>}
        </div>

        <div style={styles.fieldBlock}>
          <label>Номер устройства</label>
          <input
            type="tel"
            value={devicePhone}
            onChange={(e) => setDevicePhone(e.target.value)}
            style={styles.input}
            placeholder="+79991234567"
          />
          {errors.devicePhone && (
            <p style={styles.error}>{errors.devicePhone}</p>
          )}
        </div>

        <div style={styles.fieldBlock}>
          <label>Модель устройства</label>
          <select
            value={deviceModel}
            onChange={(e) => setDeviceModel(e.target.value)}
            style={styles.input}
          >
            <option value="RTU5025">RTU5025</option>
          </select>
        </div>

        <div style={styles.fieldBlock}>
          <label>Пароль устройства</label>
          <input
            type="text"
            maxLength={4}
            value={devicePassword}
            onChange={(e) => setDevicePassword(e.target.value)}
            style={styles.input}
            placeholder="1234"
          />
          {errors.devicePassword && (
            <p style={styles.error}>{errors.devicePassword}</p>
          )}
        </div>

        <div style={styles.fieldBlock}>
          <label>Максимум номеров на устройстве</label>
          <input
            type="number"
            value={devicePhonesAmount}
            onChange={(e) => setDevicePhonesAmount(e.target.value)}
            style={styles.input}
            placeholder="Например: 999"
          />
          {errors.devicePhonesAmount && (
            <p style={styles.error}>{errors.devicePhonesAmount}</p>
          )}
        </div>

        <div style={styles.fieldBlock}>
          <label>Доп. информация</label>
          <textarea
            value={additionalInfo}
            onChange={(e) => setAdditionalInfo(e.target.value)}
            style={{ ...styles.input, height: "80px" }}
          />
        </div>

        <div style={styles.fieldBlock}>
          <label>
            <input
              type="checkbox"
              checked={isPublic}
              onChange={() => setIsPublic(!isPublic)}
            />
            &nbsp;Публичный шлагбаум
          </label>
        </div>

        {errors.general && <p style={styles.error}>{errors.general}</p>}
        {successMessage && <p style={styles.success}>{successMessage}</p>}

        <button onClick={handleSubmit} style={styles.button}>
          Создать
        </button>
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
  },
  formWrapper: {
    width: "100%",
    maxWidth: "500px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#5a4478",
    textAlign: "center",
    marginBottom: "20px",
  },
  backButton: {
    alignSelf: "flex-start",
    background: "none",
    border: "none",
    color: "#5a4478",
    fontSize: "18px",
    cursor: "pointer",
    marginBottom: "10px",
  },
  fieldBlock: {
    marginBottom: "16px",
  },
  input: {
    width: "100%",
    padding: "10px",
    fontSize: "16px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    boxSizing: "border-box",
  },
  button: {
    width: "100%",
    padding: "12px",
    backgroundColor: "#5a4478",
    color: "white",
    fontSize: "16px",
    fontWeight: "bold",
    border: "none",
    borderRadius: "20px",
    cursor: "pointer",
  },
  exampleButton: {
    marginTop: "8px",
    backgroundColor: "#eae0f5",
    color: "#5a4478",
    border: "none",
    padding: "8px 12px",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "14px",
  },
  error: {
    color: "red",
    fontSize: "13px",
    marginTop: "4px",
  },
  success: {
    color: "green",
    fontWeight: "bold",
    marginTop: "10px",
    textAlign: "center",
  },
};

export default CreateBarrierPage;

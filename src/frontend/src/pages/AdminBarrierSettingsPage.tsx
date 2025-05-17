import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: "5vw",
    fontFamily: "sans-serif",
    backgroundColor: "#fff6fa",
    minHeight: "100vh",
    color: "#000000",
    boxSizing: "border-box",
    width: "100vw",
  },
  backButton: {
    marginBottom: "20px",
    color: "#5a4478",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "clamp(14px, 3vw, 16px)",
  },
  title: {
    textAlign: "center",
    color: "#5a4478",
    fontSize: "clamp(20px, 5vw, 24px)",
    fontWeight: "bold",
    marginBottom: "20px",
  },
  select: {
    width: "100%",
    maxWidth: "500px",
    padding: "12px",
    fontSize: "clamp(14px, 4vw, 16px)",
    borderRadius: "8px",
    border: "1px solid #ccc",
    margin: "0 auto 20px",
    backgroundColor: "#ffffff",
    color: "#5a4478",
    fontWeight: 600,
    display: "block",
    boxSizing: "border-box",
  },
  settingCard: {
    width: "100%",
    maxWidth: "500px",
    backgroundColor: "#ffffff",
    padding: "20px",
    borderRadius: "10px",
    boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
    margin: "0 auto",
    boxSizing: "border-box",
  },
  settingName: {
    fontSize: "clamp(16px, 4vw, 18px)",
    fontWeight: 600,
    marginBottom: "6px",
  },
  settingDesc: {
    fontSize: "clamp(13px, 3.5vw, 14px)",
    color: "#555",
    marginBottom: "12px",
  },
  inputBlock: {
    marginBottom: "16px",
  },
  label: {
    fontWeight: 600,
    display: "block",
    marginBottom: "6px",
    fontSize: "clamp(14px, 3.5vw, 16px)",
    color: "#000000",
  },
  input: {
    width: "100%",
    padding: "10px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    backgroundColor: "#ffffff",
    color: "#000000",
    fontSize: "clamp(14px, 4vw, 16px)",
    boxSizing: "border-box",
  },
  submitButton: {
    padding: "12px 20px",
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    width: "100%",
    maxWidth: "300px",
    fontSize: "clamp(14px, 4vw, 16px)",
    margin: "0 auto",
    display: "block",
  },
  preview: {
    backgroundColor: "#f0ebfa",
    color: "#000000",
    padding: "10px",
    borderRadius: "8px",
    fontSize: "14px",
    fontFamily: "monospace",
    marginTop: "12px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    boxSizing: "border-box",
  },
  error: {
    color: "#d32f2f",
    textAlign: "center",
    marginTop: "10px",
    fontSize: "clamp(13px, 3vw, 14px)",
  },
  success: {
    color: "#388e3c",
    textAlign: "center",
    marginTop: "10px",
    fontSize: "clamp(13px, 3vw, 14px)",
  },
};

const AdminBarrierSettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const accessToken =
    location.state?.access_token || localStorage.getItem("access_token");
  const refreshToken =
    location.state?.refresh_token || localStorage.getItem("refresh_token");
  const barrierId = location.state?.barrier_id;

  const [settings, setSettings] = useState<any>({});
  const [formValues, setFormValues] = useState<any>({});
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch(`/api/admin/barriers/${barrierId}/settings/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            Accept: "application/json",
          },
        });
        const data = await res.json();
        if (res.ok) {
          setSettings(data.settings || {});
          const firstKey = Object.keys(data.settings)[0];
          setSelectedKey(firstKey);
        } else {
          setError("Ошибка при загрузке настроек");
        }
      } catch {
        setError("Ошибка сети");
      }
    };
    fetchSettings();
  }, [barrierId]);

  const handleChange = (
    settingKey: string,
    paramKey: string,
    value: string,
  ) => {
    setFormValues((prev: any) => ({
      ...prev,
      [settingKey]: {
        ...prev[settingKey],
        [paramKey]: value,
      },
    }));
  };

  const handleSubmit = async (settingKey: string) => {
    setError("");
    setSuccess("");
    try {
      const res = await fetch(`/api/admin/barriers/${barrierId}/settings/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          setting: settingKey,
          params: formValues[settingKey] || {},
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(`Настройка '${settingKey}' успешно отправлена.`);
      } else {
        setError(data.detail || "Ошибка при отправке настройки.");
      }
    } catch {
      setError("Ошибка сети при отправке настройки.");
    }
  };

  const currentSetting = settings[selectedKey];

  const getPreviewCommand = () => {
    if (!currentSetting || !currentSetting.template) return "";
    return currentSetting.template.replace(
      /\{(\w+)\}/g,
      (match: string, key: string) =>
        formValues[selectedKey]?.[key] || `{${key}}`,
    );
  };

  return (
    <div style={styles.container}>
      <button
        onClick={() =>
          navigate("/admin-barriers", {
            state: { access_token: accessToken, refresh_token: refreshToken },
          })
        }
        style={styles.backButton}
      >
        ← Назад
      </button>
      <h2 style={styles.title}>Настройки шлагбаума</h2>

      <select
        value={selectedKey}
        onChange={(e) => setSelectedKey(e.target.value)}
        style={styles.select}
      >
        {Object.entries(settings).map(([key, setting]: any) => (
          <option key={key} value={key}>
            {setting.name}
          </option>
        ))}
      </select>

      {currentSetting && (
        <div style={styles.settingCard}>
          <h3 style={styles.settingName}>{currentSetting.name}</h3>
          <p style={styles.settingDesc}>{currentSetting.description}</p>
          {currentSetting.params.map((param: any) => (
            <div key={param.key} style={styles.inputBlock}>
              <label style={styles.label}>{param.name}</label>
              <input
                type="text"
                placeholder={param.description}
                value={formValues[selectedKey]?.[param.key] || ""}
                onChange={(e) =>
                  handleChange(selectedKey, param.key, e.target.value)
                }
                style={styles.input}
              />
            </div>
          ))}
          <button
            onClick={() => handleSubmit(selectedKey)}
            style={styles.submitButton}
          >
            Отправить
          </button>
          {currentSetting.template && (
            <div style={styles.preview}>
              <strong>Команда:</strong> {getPreviewCommand()}
            </div>
          )}
        </div>
      )}

      {error && <p style={styles.error}>{error}</p>}
      {success && <p style={styles.success}>{success}</p>}
    </div>
  );
};

export default AdminBarrierSettingsPage;

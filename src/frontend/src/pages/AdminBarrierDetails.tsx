import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const AdminBarrierDetails: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { barrier_id, access_token, refresh_token } = location.state || {};

  const [barrier, setBarrier] = useState<any>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [form, setForm] = useState({
    additional_info: "",
    is_public: false,
    device_password: "",
  });

  // ─── НОВОЕ: состояния для лимитов ─────────────────────────────────────
  const [limits, setLimits] = useState<any>(null);
  const [limitsForm, setLimitsForm] = useState<{
    user_phone_limit: number | null;
    user_temp_phone_limit: number | null;
    global_temp_phone_limit: number | null;
    user_schedule_phone_limit: number | null;
    global_schedule_phone_limit: number | null;
    schedule_interval_limit: number | null;
    sms_weekly_limit: number | null;
  }>({
    user_phone_limit: null,
    user_temp_phone_limit: null,
    global_temp_phone_limit: null,
    user_schedule_phone_limit: null,
    global_schedule_phone_limit: null,
    schedule_interval_limit: null,
    sms_weekly_limit: null,
  });
  const [limitsLoading, setLimitsLoading] = useState(false);
  const [limitsSaving, setLimitsSaving] = useState(false);
  const [limitsError, setLimitsError] = useState("");
  const [limitsMessage, setLimitsMessage] = useState("");

  const fetchBarrier = async (token = access_token) => {
    try {
      const res = await fetch(`/api/admin/barriers/${barrier_id}/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (res.status === 401) {
        await refreshAndRetry();
        return;
      }

      const data = await res.json();
      if (res.ok) {
        setBarrier(data);
        setForm({
          additional_info: data.additional_info || "",
          is_public: data.is_public || false,
          device_password: "",
        });
      } else {
        setError("Ошибка загрузки данных");
      }
    } catch {
      setError("Ошибка сети");
    }
  };

  // ─── НОВОЕ: загрузка лимитов ───────────────────────────────────────────
  const fetchLimits = async (token = access_token) => {
    setLimitsLoading(true);
    setLimitsError("");
    try {
      const res = await fetch(`/api/barriers/${barrier_id}/limits/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });
      if (res.status === 401) {
        await refreshAndRetry();
        return;
      }
      const data = await res.json();
      if (res.ok) {
        setLimits(data);
        setLimitsForm({
          user_phone_limit: data.user_phone_limit,
          user_temp_phone_limit: data.user_temp_phone_limit,
          global_temp_phone_limit: data.global_temp_phone_limit,
          user_schedule_phone_limit: data.user_schedule_phone_limit,
          global_schedule_phone_limit: data.global_schedule_phone_limit,
          schedule_interval_limit: data.schedule_interval_limit,
          sms_weekly_limit: data.sms_weekly_limit,
        });
      } else {
        setLimitsError("Ошибка загрузки лимитов");
      }
    } catch {
      setLimitsError("Ошибка сети при загрузке лимитов");
    } finally {
      setLimitsLoading(false);
    }
  };

  const refreshAndRetry = async () => {
    try {
      const res = await fetch("/api/auth/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refresh_token }),
      });
      const data = await res.json();
      if (res.ok && data.access) {
        localStorage.setItem("access_token", data.access);
        fetchBarrier(data.access);
        fetchLimits(data.access);
      } else {
        navigate("/login");
      }
    } catch {
      setError("Ошибка обновления токена");
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const target = e.target as HTMLInputElement;
    const { name, value, type } = target;
    const inputValue = type === "checkbox" ? target.checked : value;
    setForm((prev) => ({
      ...prev,
      [name]: inputValue,
    }));
  };

  const handleSubmit = async () => {
    setError("");
    setMessage("");

    if (form.device_password && !/^\d{4}$/.test(form.device_password)) {
      setError("Пароль устройства должен содержать ровно 4 цифры");
      return;
    }

    setSaving(true);

    try {
      const res = await fetch(`/api/admin/barriers/${barrier_id}/`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          additional_info: form.additional_info,
          is_public: form.is_public,
          ...(form.device_password
            ? { device_password: form.device_password }
            : {}),
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setBarrier(data);
        setMessage("Шлагбаум успешно обновлён.");
      } else {
        setError(data.detail || "Ошибка при обновлении");
      }
    } catch {
      setError("Ошибка сети при обновлении");
    } finally {
      setSaving(false);
    }
  };

  // ─── НОВОЕ: изменение полей лимитов ────────────────────────────────────
  const handleLimitsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const num = value === "" ? null : parseInt(value, 10);
    setLimitsForm((prev) => ({
      ...prev,
      [name]: isNaN(num as number) ? null : num,
    }));
  };

  // ─── НОВОЕ: сохранение лимитов ─────────────────────────────────────────
  const handleLimitsSubmit = async () => {
    setLimitsError("");
    setLimitsMessage("");
    setLimitsSaving(true);
    try {
      const body: any = {};
      Object.entries(limitsForm).forEach(([key, val]) => {
        body[key] = val === null ? null : val;
      });
      const res = await fetch(`/api/admin/barriers/${barrier_id}/limits/`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setLimits(data);
        setLimitsMessage("Лимиты успешно обновлены.");
      } else {
        setLimitsError(data.detail || "Ошибка при обновлении лимитов");
      }
    } catch {
      setLimitsError("Ошибка сети при обновлении лимитов");
    } finally {
      setLimitsSaving(false);
    }
  };

  const handleDelete = async () => {
    setError("");
    setMessage("");
    try {
      const res = await fetch(`/api/admin/barriers/${barrier_id}/`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      });
      if (res.ok) {
        navigate("/admin-barriers", { state: { access_token, refresh_token } });
      } else {
        setError("Не удалось удалить шлагбаум");
      }
    } catch {
      setError("Ошибка сети при удалении");
    }
  };

  useEffect(() => {
    if (barrier_id && access_token) {
      fetchBarrier();
      fetchLimits();
    }
  }, [barrier_id, access_token]);

  if (!barrier) return <p style={styles.loading}>Загрузка...</p>;

  const isTelemetrica = barrier.device_model === "Telemetrica";

  return (
    <div style={styles.container}>
      <button
        style={styles.backButton}
        onClick={() =>
          navigate("/admin-barriers", {
            state: { access_token, refresh_token },
          })
        }
      >
        ← Назад к списку
      </button>

      <div style={styles.card}>
        <h2 style={styles.title}>{barrier.address}</h2>
        <p>
          <strong>Телефон устройства:</strong> {barrier.device_phone}
        </p>
        <p>
          <strong>Модель устройства:</strong> {barrier.device_model}
        </p>
        <p>
          <strong>Количество номеров:</strong> {barrier.device_phones_amount}
        </p>

        <label style={styles.label}>Доп. информация</label>
        <textarea
          name="additional_info"
          value={form.additional_info}
          onChange={handleChange}
          style={styles.input}
        />

        <label style={styles.label}>
          <input
            type="checkbox"
            name="is_public"
            checked={form.is_public}
            onChange={handleChange}
          />{" "}
          Публичный
        </label>

        <label style={styles.label}>Пароль устройства (4 цифры)</label>
        <input
          name="device_password"
          value={form.device_password}
          onChange={handleChange}
          style={styles.input}
          placeholder={isTelemetrica ? "(у вас нет пароля)" : "1234"}
          maxLength={4}
          disabled={isTelemetrica}
        />

        <button
          style={styles.saveButton}
          onClick={handleSubmit}
          disabled={saving || isTelemetrica}
        >
          {saving ? "Сохранение..." : "Сохранить изменения"}
        </button>

        {(error || message) && (
          <p style={error ? styles.error : styles.success}>
            {error || message}
          </p>
        )}

        {/* ─── Блок редактирования лимитов ─────────────────────────────────── */}
        <hr style={{ margin: "20px 0" }} />
        <h3 style={{ marginBottom: 10 }}>Лимиты шлагбаума</h3>
        {limitsLoading ? (
          <p style={styles.loading}>Загрузка лимитов…</p>
        ) : (
          <>
            {[
              {
                label: "Лимит телефонов (пользователь)",
                name: "user_phone_limit",
              },
              {
                label: "Лимит временных телефонов (пользователь)",
                name: "user_temp_phone_limit",
              },
              {
                label: "Глобальный лимит временных телефонов",
                name: "global_temp_phone_limit",
              },
              {
                label: "Лимит расписанных телефонов (пользователь)",
                name: "user_schedule_phone_limit",
              },
              {
                label: "Глобальный лимит расписанных телефонов",
                name: "global_schedule_phone_limit",
              },
              {
                label: "Интервал расписания (мин)",
                name: "schedule_interval_limit",
              },
              { label: "СМС в неделю", name: "sms_weekly_limit" },
            ].map(({ label, name }) => (
              <div key={name}>
                <label style={styles.label}>{label}</label>
                <input
                  type="number"
                  name={name}
                  value={limitsForm[name] ?? ""}
                  onChange={handleLimitsChange}
                  style={styles.input}
                  min={0}
                />
              </div>
            ))}
            <button
              style={styles.saveButton}
              onClick={handleLimitsSubmit}
              disabled={limitsSaving}
            >
              {limitsSaving ? "Сохранение лимитов…" : "Сохранить лимиты"}
            </button>
            {(limitsError || limitsMessage) && (
              <p style={limitsError ? styles.error : styles.success}>
                {limitsError || limitsMessage}
              </p>
            )}
          </>
        )}
        {/* ──────────────────────────────────────────────────────────────── */}

        <div style={styles.footerButtons}>
          <button
            style={styles.navButton}
            onClick={() =>
              navigate("/barrier-users", {
                state: { barrier_id, access_token, refresh_token },
              })
            }
          >
            👥 Редактировать пользователей
          </button>
          <button
            style={styles.navButton}
            onClick={() =>
              navigate("/barrier-settings", {
                state: { barrier_id, access_token, refresh_token },
              })
            }
          >
            ⚙️ Настроить устройство
          </button>
          <button
            style={styles.navButton}
            onClick={() =>
              navigate("/barrier-history-admin", {
                state: { barrier_id, access_token, refresh_token },
              })
            }
          >
            📜 История изменений
          </button>
          <button
            style={styles.deleteButton}
            onClick={() => setShowConfirmModal(true)}
          >
            🗑️ Удалить шлагбаум
          </button>
        </div>
      </div>

      {showConfirmModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <p>Вы точно хотите удалить шлагбаум?</p>
            <div style={styles.modalActions}>
              <button style={styles.confirmYes} onClick={handleDelete}>
                Да
              </button>
              <button
                style={styles.confirmNo}
                onClick={() => setShowConfirmModal(false)}
              >
                Нет
              </button>
            </div>
          </div>
        </div>
      )}
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
    color: "#000000",
    fontFamily: "sans-serif",
    position: "relative",
  },
  backButton: {
    alignSelf: "flex-start",
    marginBottom: "20px",
    backgroundColor: "transparent",
    border: "none",
    color: "#5a4478",
    fontSize: "16px",
    cursor: "pointer",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "30px",
    borderRadius: "16px",
    boxShadow: "0 4px 20px rgba(90, 68, 120, 0.1)",
    width: "100%",
    maxWidth: "500px",
    color: "#000000",
  },
  title: {
    fontSize: "22px",
    color: "#5a4478",
    marginBottom: "20px",
    textAlign: "center",
  },
  input: {
    width: "100%",
    padding: "12px",
    marginBottom: "10px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    fontSize: "14px",
    backgroundColor: "#ffffff",
    color: "#000000",
  },
  label: {
    display: "block",
    margin: "10px 0 5px",
    fontWeight: "bold",
    color: "#000000",
  },
  saveButton: {
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    cursor: "pointer",
    width: "100%",
    marginTop: "20px",
  },
  footerButtons: {
    marginTop: "30px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  navButton: {
    backgroundColor: "#d7c4ed",
    color: "#5a4478",
    border: "none",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    cursor: "pointer",
    width: "100%",
  },
  deleteButton: {
    backgroundColor: "#ffdddd",
    color: "#d32f2f",
    border: "none",
    padding: "12px",
    borderRadius: "25px",
    fontSize: "16px",
    cursor: "pointer",
    width: "100%",
  },
  error: {
    color: "#d32f2f",
    paddingTop: "15px",
    fontSize: "14px",
    textAlign: "center",
  },
  success: {
    color: "#388e3c",
    paddingTop: "15px",
    fontSize: "14px",
    textAlign: "center",
  },
  loading: {
    color: "#000000",
    padding: "20px",
    textAlign: "center",
  },
  modalOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: "#ffffff",
    padding: "20px",
    borderRadius: "12px",
    boxShadow: "0 4px 15px rgba(0,0,0,0.2)",
    textAlign: "center",
    width: "90%",
    maxWidth: "320px",
    color: "#000000",
  },
  modalActions: {
    display: "flex",
    justifyContent: "space-around",
    marginTop: "20px",
  },
  confirmYes: {
    backgroundColor: "#d32f2f",
    color: "#ffffff",
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    cursor: "pointer",
  },
  confirmNo: {
    backgroundColor: "#ccc",
    color: "#000000",
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    cursor: "pointer",
  },
};

export default AdminBarrierDetails;

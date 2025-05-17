import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaArrowLeft, FaTrash, FaPlusCircle } from "react-icons/fa";

const toInputDateTime = (iso: string) => (iso ? iso.slice(0, 16) : "");

const defaultSchedule = {
  monday: [],
  tuesday: [],
  wednesday: [],
  thursday: [],
  friday: [],
  saturday: [],
  sunday: [],
};

const dayNames: Record<string, string> = {
  monday: "Понедельник",
  tuesday: "Вторник",
  wednesday: "Среда",
  thursday: "Четверг",
  friday: "Пятница",
  saturday: "Суббота",
  sunday: "Воскресенье",
};

const AdminEditPhonePage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userId = location.state?.user_id;

  const phoneId = location.state?.phone_id;
  const original = location.state?.phone_data;
  const barrierIdFromState = location.state?.barrier_id;

  const [accessToken] = useState(
    () => location.state?.access_token || localStorage.getItem("access_token"),
  );
  const [refreshToken] = useState(
    () =>
      location.state?.refresh_token || localStorage.getItem("refresh_token"),
  );

  const [name, setName] = useState(original?.name || "");
  const [startTime, setStartTime] = useState(
    toInputDateTime(original?.start_time),
  );
  const [endTime, setEndTime] = useState(toInputDateTime(original?.end_time));

  const buildSafeSchedule = (incoming: any) => {
    const result: any = {};
    for (const day of Object.keys(defaultSchedule)) {
      result[day] = Array.isArray(incoming?.[day]) ? incoming[day] : [];
    }
    return result;
  };

  const [schedule, setSchedule] = useState<any>(
    buildSafeSchedule(original?.schedule),
  );
  const [error, setError] = useState("");

  const handleSave = async () => {
    setError("");

    if (!name) {
      setError("Введите имя.");
      return;
    }

    try {
      let updatedPhone = null;

      if (original.type === "permanent" || original.type === "temporary") {
        const patchBody: any = { user: userId, name };

        if (original.type === "temporary") {
          if (!startTime || !endTime) {
            setError("Укажите время начала и конца.");
            return;
          }
          if (new Date(startTime) >= new Date(endTime)) {
            setError("Время начала должно быть раньше конца.");
            return;
          }

          patchBody.start_time = startTime;
          patchBody.end_time = endTime;
        }

        const res = await fetch(`/api/admin/phones/${phoneId}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(patchBody),
        });

        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          setError(data.detail || "Ошибка обновления номера.");
          return;
        }

        updatedPhone = data;
      }

      if (original.type === "schedule") {
        const patchRes = await fetch(`/api/admin/phones/${phoneId}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ user: userId, name }),
        });

        const patchData = await patchRes.json().catch(() => ({}));

        if (!patchRes.ok) {
          setError(patchData.detail || "Ошибка обновления имени.");
          return;
        }

        const res = await fetch(`/api/admin/phones/${phoneId}/schedule/`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(schedule),
        });

        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          setError(data.detail || "Ошибка обновления расписания.");
          return;
        }

        updatedPhone = { ...data, id: phoneId, barrier: barrierIdFromState };
      }

      const targetBarrierId = updatedPhone?.barrier || barrierIdFromState;

      navigate("/user-profile", {
        state: {
          user_id: userId,
          barrier_id: targetBarrierId,
          access_token: accessToken,
          refresh_token: refreshToken,
        },
      });
    } catch (e) {
      console.error("Ошибка при сохранении:", e);
      setError("Ошибка сети");
    }
  };

  const addSchedulePeriod = (day: string) => {
    const updated = { ...schedule };
    updated[day].push({ start_time: "08:00", end_time: "12:00" });
    setSchedule(updated);
  };

  const renderScheduleEditor = () => (
    <>
      {Object.keys(schedule).map((day) => (
        <div key={day} style={styles.dayBlock}>
          <h4 style={styles.dayTitle}>{dayNames[day]}</h4>
          {schedule[day].map((period: any, i: number) => {
            const isInvalid =
              period.start_time &&
              period.end_time &&
              period.start_time >= period.end_time;
            return (
              <div key={i} style={styles.intervalRow}>
                <input
                  type="time"
                  value={period.start_time}
                  onChange={(e) => {
                    const updated = [...schedule[day]];
                    updated[i].start_time = e.target.value;
                    setSchedule({ ...schedule, [day]: updated });
                  }}
                  style={{
                    ...styles.timeInput,
                    borderColor: isInvalid ? "red" : "#ccc",
                  }}
                />
                <span style={{ fontWeight: "bold" }}>–</span>
                <input
                  type="time"
                  value={period.end_time}
                  onChange={(e) => {
                    const updated = [...schedule[day]];
                    updated[i].end_time = e.target.value;
                    setSchedule({ ...schedule, [day]: updated });
                  }}
                  style={{
                    ...styles.timeInput,
                    borderColor: isInvalid ? "red" : "#ccc",
                  }}
                />
                <button
                  onClick={() => {
                    const updated = [...schedule[day]];
                    updated.splice(i, 1);
                    setSchedule({ ...schedule, [day]: updated });
                  }}
                  style={styles.trashButton}
                >
                  <FaTrash />
                </button>
                {isInvalid && (
                  <span style={styles.invalid}>Неверный интервал</span>
                )}
              </div>
            );
          })}
          <button
            onClick={() => addSchedulePeriod(day)}
            style={styles.addButton}
          >
            <FaPlusCircle /> Добавить интервал
          </button>
        </div>
      ))}
    </>
  );

  return (
    <div style={styles.container}>
      <button style={styles.backButton} onClick={() => navigate(-1)}>
        <FaArrowLeft /> Назад
      </button>

      <h2 style={styles.title}>Редактировать номер</h2>

      <input
        placeholder="Имя (например: Гость Иван)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={styles.input}
      />

      {original.type === "temporary" && (
        <>
          <label>Время начала:</label>
          <input
            type="datetime-local"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            style={styles.input}
          />
          <label>Время окончания:</label>
          <input
            type="datetime-local"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            style={styles.input}
          />
        </>
      )}

      {original.type === "schedule" && renderScheduleEditor()}

      {error && <p style={styles.error}>{error}</p>}

      <button style={styles.saveButton} onClick={handleSave}>
        💾 Сохранить изменения
      </button>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fff6fb",
    minHeight: "100vh",
    width: "100vw",
    padding: "5vw",
    fontFamily: "sans-serif",
  },
  title: {
    fontSize: "24px",
    fontWeight: "bold",
    marginBottom: "20px",
    color: "#5a4478",
    textAlign: "center",
  },
  input: {
    width: "100%",
    maxWidth: "400px",
    margin: "0 auto 12px",
    padding: "12px",
    fontSize: "16px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    display: "block",
    boxSizing: "border-box",
    backgroundColor: "#ffffff", // 👈 всегда белый фон
    color: "#000000", // 👈 всегда чёрный текст
  },
  timeInput: {
    padding: "6px",
    borderRadius: "6px",
    border: "1px solid #ccc",
    backgroundColor: "#ffffff", // 👈 белый фон
    color: "#000000", // 👈 чёрный текст
  },
  saveButton: {
    width: "60%",
    backgroundColor: "#5a4478",
    color: "#fff",
    padding: "14px",
    borderRadius: "24px",
    border: "none",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "16px",
    margin: "20px auto",
    display: "block",
  },
  error: {
    color: "red",
    fontSize: "14px",
    textAlign: "center",
    marginTop: "12px",
  },
  backButton: {
    background: "none",
    border: "none",
    color: "#5a4478",
    fontSize: "16px",
    cursor: "pointer",
    marginBottom: "20px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  dayBlock: {
    border: "1px solid #ddd",
    borderRadius: "10px",
    padding: "16px",
    marginBottom: "20px",
    backgroundColor: "#faf6fd",
    width: "100%",
    maxWidth: "420px",
    marginLeft: "auto",
    marginRight: "auto",
  },
  dayTitle: {
    fontSize: "16px",
    fontWeight: "bold",
    marginBottom: "8px",
    color: "#5a4478",
  },
  intervalRow: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
    marginBottom: "6px",
  },
  trashButton: {
    background: "none",
    border: "none",
    color: "#d9534f",
    cursor: "pointer",
    fontSize: "16px",
  },
  invalid: {
    color: "red",
    fontSize: "12px",
    marginLeft: "8px",
  },
  addButton: {
    backgroundColor: "#e6dbf3",
    color: "#5a4478",
    padding: "6px 12px",
    borderRadius: "8px",
    border: "none",
    cursor: "pointer",
    fontWeight: "bold",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    marginTop: "4px",
    maxWidth: "420px",
  },
};

export default AdminEditPhonePage;

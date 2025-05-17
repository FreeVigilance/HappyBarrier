import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaArrowLeft, FaTrash, FaPlusCircle } from "react-icons/fa";

const AddPhonePage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const barrierId = location.state?.barrier_id;
  const accessToken = location.state?.access_token;

  const logToLoki = (
    message: string,
    level: "info" | "warn" | "error" = "info",
  ) => {
    fetch("http://loki:3100/loki/api/v1/push", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        streams: [
          {
            stream: { level, app: "react-ui", page: "add-phone" },
            values: [[`${Date.now()}000000`, message]],
          },
        ],
      }),
    }).catch(console.error);
  };

  const [phone, setPhone] = useState("+7");
  const [name, setName] = useState("");
  const [type, setType] = useState<"permanent" | "temporary" | "schedule">(
    "permanent",
  );
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  const [schedule, setSchedule] = useState<any>({
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: [],
  });

  const [error, setError] = useState("");

  const isPhoneValid = () => /^(\+7)\d{10}$/.test(phone);

  const isScheduleValid = () => {
    if (type !== "schedule") return true;
    return Object.values(schedule).every(
      (periods) =>
        Array.isArray(periods) &&
        periods.every((p: any) => p.start_time < p.end_time),
    );
  };

  const handleSave = async () => {
    setError("");

    if (!phone || !name) {
      setError("Введите имя и номер телефона.");
      return;
    }

    if (!isPhoneValid()) {
      setError("Номер телефона должен быть в формате +7XXXXXXXXXX.");
      logToLoki(`Введён неверный номер: ${phone}`, "warn");
      return;
    }

    if (!isScheduleValid()) {
      setError("Есть интервалы в расписании с некорректным временем.");
      return;
    }

    const payload: any = { phone, name, type };

    if (type === "temporary") {
      if (!startTime || !endTime) {
        setError("Укажите время начала и конца.");
        return;
      }
      if (new Date(startTime) >= new Date(endTime)) {
        setError("Время начала должно быть раньше времени конца.");
        logToLoki(
          `Некорректный интервал в расписании: ${startTime} >= ${endTime}`,
          "error",
        );
        return;
      }

      payload.start_time = startTime;
      payload.end_time = endTime;
    }

    if (type === "schedule") {
      payload.schedule = schedule;
    }

    try {
      const res = await fetch(`/api/barriers/${barrierId}/phones/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        logToLoki(
          `Номер ${phone} успешно добавлен (${type}) на шлагбаум ${barrierId}`,
          "info",
        );
        navigate("/mybarrier", {
          state: { barrier_id: barrierId, access_token: accessToken },
        });
      } else {
        const data = await res.json();
        console.log(data);
        logToLoki(
          `Ошибка при сохранении номера: ${JSON.stringify(data)}`,
          "error",
        );
        setError(
          data.phone ||
            data.type ||
            data.detail ||
            data.schedule ||
            data.start_time ||
            data.end_time ||
            "Ошибка при сохранении номера.",
        );
      }
    } catch (e) {
      logToLoki(`Сетевая ошибка при добавлении номера: ${phone}`, "error");
      setError("Ошибка сети.");
    }
  };

  const addSchedulePeriod = (day: string) => {
    const updated = { ...schedule };
    updated[day].push({ start_time: "08:00", end_time: "12:00" });
    setSchedule(updated);
  };

  const renderScheduleEditor = () => {
    return (
      <>
        {Object.keys(schedule).map((day) => (
          <div key={day} style={{ marginBottom: "16px" }}>
            <strong style={{ display: "block", marginBottom: "6px" }}>
              {day.charAt(0).toUpperCase() + day.slice(1)}:
            </strong>
            {schedule[day].map((period: any, i: number) => {
              const isInvalid =
                period.start_time &&
                period.end_time &&
                period.start_time >= period.end_time;

              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: "10px",
                    alignItems: "center",
                    marginBottom: "6px",
                  }}
                >
                  <input
                    type="time"
                    value={period.start_time}
                    onChange={(e) => {
                      const updated = [...schedule[day]];
                      updated[i].start_time = e.target.value;
                      setSchedule({ ...schedule, [day]: updated });
                    }}
                    style={{
                      ...styles.input,
                      borderColor: isInvalid ? "red" : "#ccc",
                    }}
                  />
                  <input
                    type="time"
                    value={period.end_time}
                    onChange={(e) => {
                      const updated = [...schedule[day]];
                      updated[i].end_time = e.target.value;
                      setSchedule({ ...schedule, [day]: updated });
                    }}
                    style={{
                      ...styles.input,
                      borderColor: isInvalid ? "red" : "#ccc",
                    }}
                  />
                  <button
                    onClick={() => {
                      const updated = [...schedule[day]];
                      updated.splice(i, 1);
                      setSchedule({ ...schedule, [day]: updated });
                    }}
                  >
                    <FaTrash />
                  </button>
                  {isInvalid && (
                    <span style={{ color: "red", fontSize: "12px" }}>
                      Неверный интервал
                    </span>
                  )}
                </div>
              );
            })}
            <button
              onClick={() => addSchedulePeriod(day)}
              style={{ marginTop: "4px" }}
            >
              <FaPlusCircle /> Добавить интервал
            </button>
          </div>
        ))}
      </>
    );
  };

  return (
    <div style={styles.container}>
      <button style={styles.backButton} onClick={() => navigate(-1)}>
        <FaArrowLeft /> Назад
      </button>

      <h2 style={styles.title}>Добавить номер</h2>

      <input
        placeholder="+79991234567"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        style={{
          ...styles.input,
          borderColor: phone && !isPhoneValid() ? "red" : "#ccc",
        }}
      />
      <input
        placeholder="Имя (например: Гость Иван)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={styles.input}
      />

      <select
        value={type}
        onChange={(e) => setType(e.target.value as any)}
        style={styles.input}
      >
        <option value="permanent">Обычный</option>
        <option value="temporary">Временный</option>
        <option value="schedule">По расписанию</option>
      </select>

      {type === "temporary" && (
        <>
          <label>Время начала:</label>
          <input
            type="datetime-local"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            style={styles.input}
          />
          <label>Время конца:</label>
          <input
            type="datetime-local"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            style={styles.input}
          />
        </>
      )}

      {type === "schedule" && renderScheduleEditor()}

      {error && <p style={styles.error}>{error}</p>}

      <button
        style={{
          ...styles.saveButton,
          backgroundColor:
            !isPhoneValid() || !isScheduleValid() ? "#aaa" : "#5a4478",
          cursor:
            !isPhoneValid() || !isScheduleValid() ? "not-allowed" : "pointer",
        }}
        onClick={handleSave}
        disabled={!isPhoneValid() || !isScheduleValid()}
        title={
          !isPhoneValid()
            ? "Введите правильный номер телефона"
            : !isScheduleValid()
              ? "Исправьте интервалы в расписании"
              : ""
        }
      >
        Сохранить номер
      </button>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    backgroundColor: "#fff6fa",
    minHeight: "100vh",
    width: "100vw",
    padding: "5vw",
    boxSizing: "border-box",
    fontFamily: "sans-serif",
    color: "#000000",
  },
  title: {
    fontSize: "22px",
    fontWeight: "bold",
    marginBottom: "20px",
    color: "#5a4478",
  },
  input: {
    width: "100%",
    maxWidth: "400px",
    margin: "0 auto 12px",
    padding: "12px",
    fontSize: "16px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    boxSizing: "border-box",
    display: "block",
    backgroundColor: "#ffffff",
    color: "#000000",
  },
  saveButton: {
    width: "50%",
    backgroundColor: "#5a4478",
    color: "#ffffff",
    padding: "14px",
    borderRadius: "20px",
    border: "none",
    fontWeight: "bold",
    fontSize: "16px",
    margin: "0 auto 12px",
    display: "block",
    cursor: "pointer",
  },
  error: {
    color: "#d32f2f",
    fontSize: "14px",
    marginTop: "10px",
    textAlign: "center",
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
};

export default AddPhonePage;

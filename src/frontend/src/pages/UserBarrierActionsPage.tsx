import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaArrowLeft } from "react-icons/fa";

const actionTypeLabels: Record<string, string> = {
  add_phone: "Добавление номера",
  delete_phone: "Удаление номера",
  update_phone: "Обновление номера",
  barrier_setting: "Настройка шлагбаума",
};

const reasonLabels: Record<string, string> = {
  manual: "Ручное изменение",
  barrier_exit: "Выход из шлагбаума",
  access_granted: "Выдан доступ",
  primary_phone_change: "Смена основного номера",
  schedule_update: "Обновление расписания",
  end_time: "Окончание доступа",
  barrier_deleted: "Удаление шлагбаума",
  user_deleted: "Удаление пользователя",
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: "5vw",
    fontFamily: "sans-serif",
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    boxSizing: "border-box",
    width: "100vw",
    margin: "0 auto",
    color: "#000000",
  },
  backButton: {
    marginBottom: 20,
    color: "#5a4478",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "16px",
  },
  title: {
    textAlign: "center",
    color: "#5a4478",
    fontSize: "24px",
    fontWeight: "bold",
    marginBottom: 20,
  },
  filters: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "10px",
    marginBottom: 20,
  },
  input: {
    padding: 10,
    borderRadius: 8,
    border: "1px solid #ccc",
    fontSize: "14px",
    width: "100%",
    boxSizing: "border-box",
    backgroundColor: "#ffffff",
    color: "#000000",
  },
  card: {
    backgroundColor: "#ffffff",
    padding: 16,
    borderRadius: 10,
    boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
    marginBottom: 12,
    cursor: "pointer",
    color: "#000000",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 20,
    marginTop: 20,
    color: "#000000",
  },
  error: {
    color: "#d32f2f",
    textAlign: "center",
    fontSize: "14px",
  },
  detailBox: {
    backgroundColor: "#ffffff",
    padding: 16,
    border: "1px solid #eee",
    borderRadius: 8,
    marginTop: 20,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    color: "#000000",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#5a4478",
    fontWeight: "bold",
    cursor: "pointer",
    marginTop: 10,
  },
};

const UserBarrierActionsPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const barrierId = location.state?.barrier_id;
  const accessToken = location.state?.access_token;

  const [actions, setActions] = useState<any[]>([]);
  const [filters, setFilters] = useState<any>({});
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState("");
  const [selectedAction, setSelectedAction] = useState<any>(null);
  const [phoneDetails, setPhoneDetails] = useState<any>(null);

  const fetchActions = async () => {
    setError("");
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: "10",
      ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v)),
    });

    try {
      const res = await fetch(
        `/api/barriers/${barrierId}/actions/?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            Accept: "application/json",
          },
        },
      );
      const data = await res.json();
      if (res.ok) {
        setActions(data.actions || []);
        setTotalPages(Math.ceil(data.total_count / 10));
      } else {
        setError("Ошибка при загрузке истории.");
      }
    } catch (e) {
      console.error("[Actions Fetch Error]", e);
      setError("Ошибка сети.");
    }
  };

  const fetchActionDetail = async (actionId: number) => {
    if (selectedAction?.id === actionId) {
      setSelectedAction(null);
      setPhoneDetails(null);
      return;
    }
    try {
      const res = await fetch(`/api/actions/${actionId}/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await res.json();
      if (res.ok) {
        setSelectedAction(data);
        if (data.phone) {
          const phoneRes = await fetch(`/api/phones/${data.phone}/`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          });
          const phoneData = await phoneRes.json();
          if (phoneRes.ok) {
            setPhoneDetails(phoneData);
          }
        }
      } else {
        setError("Не удалось загрузить детали действия.");
      }
    } catch (e) {
      console.error("[Action Detail Error]", e);
      setError("Ошибка сети при получении деталей.");
    }
  };

  useEffect(() => {
    fetchActions();
  }, [page, filters]);

  return (
    <div style={styles.container}>
      <button onClick={() => navigate(-1)} style={styles.backButton}>
        <FaArrowLeft /> Назад
      </button>
      <h2 style={styles.title}>История изменений</h2>

      <div style={styles.filters}>
        <select
          value={filters.action_type || ""}
          onChange={(e) =>
            setFilters((f: any) => ({ ...f, action_type: e.target.value }))
          }
          style={styles.input}
        >
          <option value="">Все действия</option>
          <option value="add_phone">Добавление номера</option>
          <option value="delete_phone">Удаление номера</option>
          <option value="update_phone">Обновление номера</option>
          <option value="barrier_setting">Настройка шлагбаума</option>
        </select>
        <input
          type="datetime-local"
          value={filters.created_from || ""}
          onChange={(e) =>
            setFilters((f: any) => ({ ...f, created_from: e.target.value }))
          }
          style={styles.input}
        />
        <input
          type="datetime-local"
          value={filters.created_to || ""}
          onChange={(e) =>
            setFilters((f: any) => ({ ...f, created_to: e.target.value }))
          }
          style={styles.input}
        />
      </div>

      {actions.map((a) => (
        <div
          key={a.id}
          style={styles.card}
          onClick={() => fetchActionDetail(a.id)}
        >
          <strong>#{a.id}</strong> —{" "}
          {actionTypeLabels[a.action_type] || a.action_type} <br />
          <small>{a.created_at}</small>
        </div>
      ))}

      <div style={styles.pagination}>
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          ← Назад
        </button>
        <span>
          {page} / {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
        >
          Вперёд →
        </button>
      </div>

      {selectedAction && (
        <div style={styles.detailBox}>
          <h3>Детали действия #{selectedAction.id}</h3>
          <p>
            <strong>Тип:</strong>{" "}
            {actionTypeLabels[selectedAction.action_type] ||
              selectedAction.action_type}
          </p>
          <p>
            <strong>Автор:</strong> {selectedAction.author}
          </p>
          <p>
            <strong>Создано:</strong> {selectedAction.created_at}
          </p>
          <p>
            <strong>Причина:</strong>{" "}
            {reasonLabels[selectedAction.reason] ||
              selectedAction.reason ||
              "-"}
          </p>
          {phoneDetails && (
            <>
              <p>
                <strong>Телефон:</strong> {phoneDetails.phone}
              </p>
              <p>
                <strong>Тип:</strong> {phoneDetails.type}
              </p>
            </>
          )}
          <button
            style={styles.closeBtn}
            onClick={() => {
              setSelectedAction(null);
              setPhoneDetails(null);
            }}
          >
            Скрыть детали
          </button>
        </div>
      )}

      {error && <p style={styles.error}>{error}</p>}
    </div>
  );
};

export default UserBarrierActionsPage;

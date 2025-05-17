import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const UserBarriers: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [search, setSearch] = useState("");
  const [barriers, setBarriers] = useState<any[]>([]);
  const [ordering, setOrdering] = useState("");
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [accessToken, setAccessToken] = useState(
    () => location.state?.access_token || localStorage.getItem("access_token"),
  );
  const [refreshToken] = useState(
    () =>
      location.state?.refresh_token || localStorage.getItem("refresh_token"),
  );
  const phone = location.state?.phone || localStorage.getItem("phone");

  const fetchBarriers = async (token = accessToken) => {
    const isSearch = search.trim() !== "";
    const endpoint = isSearch ? "/api/barriers/" : "/api/barriers/my/";
    const params = new URLSearchParams({
      page: String(page),
      page_size: "5",
    });
    if (ordering) params.append("ordering", ordering);
    if (isSearch) params.append("address", search);

    try {
      const res = await fetch(`${endpoint}?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (res.status === 401) {
        await refreshTokenAndRetry();
        return;
      }

      const data = await res.json();
      if (res.ok) {
        setBarriers(data.barriers || []);
        setTotalPages(Math.ceil(data.total_count / 5));
      } else {
        setError("Ошибка загрузки данных");
      }
    } catch {
      setError("Ошибка сети");
    }
  };

  const refreshTokenAndRetry = async () => {
    try {
      const refreshRes = await fetch("/api/auth/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      const refreshData = await refreshRes.json();
      if (refreshRes.ok && refreshData.access) {
        setAccessToken(refreshData.access);
        localStorage.setItem("access_token", refreshData.access);
        fetchBarriers(refreshData.access);
      } else {
        navigate("/login");
      }
    } catch {
      setError("Ошибка обновления токена");
    }
  };

  const handleBarrierClick = async (barrierId: number, barrier: any) => {
    try {
      const res = await fetch(`/api/barriers/${barrierId}/check_access/`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: "application/json",
        },
      });

      if (res.status === 401) {
        await refreshTokenAndRetry();
        return;
      }

      const data = await res.json();
      if (res.ok) {
        if (data.has_access) {
          navigate("/mybarrier", {
            state: {
              barrier_id: barrierId,
              barrier,
              phone,
              access_token: accessToken,
              refresh_token: refreshToken,
            },
          });
        } else {
          navigate("/barrier-details", {
            state: {
              barrier_id: barrierId,
              barrier,
              phone,
              access_token: accessToken,
              refresh_token: refreshToken,
            },
          });
        }
      } else {
        alert("Ошибка при проверке доступа");
      }
    } catch {
      alert("Ошибка сети при проверке доступа");
    }
  };

  useEffect(() => {
    fetchBarriers();
  }, [search, ordering, page]);

  const handleOrdering = () => {
    if (ordering === "") setOrdering("address");
    else if (ordering === "address") setOrdering("-address");
    else setOrdering("");
  };

  const isSearching = search.trim() !== "";

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h1 style={styles.title}>🔍 Поиск шлагбаумов</h1>

        <div style={styles.searchContainer}>
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            style={styles.searchInput}
            placeholder="Введите адрес..."
          />
          {search && (
            <button style={styles.clearButton} onClick={() => setSearch("")}>
              ✕
            </button>
          )}
        </div>

        <button style={styles.filterButton} onClick={handleOrdering}>
          Сортировка{" "}
          {ordering === "address" ? "↑" : ordering === "-address" ? "↓" : ""}
        </button>

        <h3 style={styles.sectionHeader}>
          {isSearching ? "Результаты поиска" : "Ваши шлагбаумы"}
        </h3>

        {barriers.length > 0 ? (
          <ul style={styles.list}>
            {barriers.map((barrier, index) => (
              <li key={index} style={styles.card}>
                <h3 style={styles.cardTitle}>{barrier.address}</h3>
                <button
                  style={styles.detailButton}
                  onClick={() => handleBarrierClick(barrier.id, barrier)}
                >
                  Подробнее →
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p style={styles.noResults}>Нет результатов</p>
        )}

        <div style={styles.pagination}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={styles.pageButton}
          >
            ← Назад
          </button>
          <span style={{ padding: "0 10px" }}>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={styles.pageButton}
          >
            Вперёд →
          </button>
        </div>

        {error && <p style={styles.errorText}>{error}</p>}
      </div>

      <div style={styles.navbar}>
        <button style={{ ...styles.navButton, ...styles.navButtonActive }}>
          Шлагбаумы
        </button>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/requests", {
              state: {
                phone,
                access_token: accessToken,
                refresh_token: refreshToken,
              },
            })
          }
        >
          Запросы
        </button>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/user", {
              state: {
                phone,
                access_token: accessToken,
                refresh_token: refreshToken,
              },
            })
          }
        >
          Профиль
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  page: {
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    width: "100vw",
    display: "flex",
    justifyContent: "center",
    paddingTop: "40px",
    boxSizing: "border-box",
  },
  container: {
    width: "100%",
    maxWidth: "500px",
    padding: "0 20px 100px",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
  },
  title: {
    fontSize: "26px",
    textAlign: "center",
    marginBottom: "25px",
    color: "#5a4478",
    fontWeight: 700,
  },
  searchContainer: {
    display: "flex",
    alignItems: "center",
    width: "100%",
    marginBottom: "10px",
  },
  searchInput: {
    flex: 1,
    padding: "12px",
    fontSize: "16px",
    border: "1px solid #ccc",
    borderRadius: "8px",
    backgroundColor: "#ffffff",
    color: "#333",
    outline: "none",
  },
  clearButton: {
    marginLeft: "10px",
    padding: "10px 14px",
    backgroundColor: "#eae0f5",
    color: "#5a4478",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "16px",
  },
  filterButton: {
    marginTop: "5px",
    marginBottom: "15px",
    padding: "10px",
    backgroundColor: "#d7c4ed",
    color: "#5a4478",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "bold",
    alignSelf: "flex-start",
  },
  sectionHeader: {
    fontSize: "18px",
    fontWeight: "bold",
    color: "#5a4478",
    marginBottom: "10px",
    marginTop: "15px",
    textAlign: "left",
  },
  list: { listStyleType: "none", padding: 0, margin: 0, width: "100%" },
  card: {
    padding: "15px 20px",
    margin: "8px 0",
    backgroundColor: "#ffffff",
    borderRadius: "10px",
    border: "1px solid #ddd",
    boxShadow: "0 2px 6px rgba(90, 68, 120, 0.1)",
    fontSize: "14px",
    color: "#333",
  },
  cardTitle: {
    color: "#5a4478",
    fontSize: "16px",
    fontWeight: "bold",
    marginBottom: "6px",
  },
  detailButton: {
    marginTop: "10px",
    backgroundColor: "#5a4478",
    color: "#ffffff",
    border: "none",
    borderRadius: "20px",
    padding: "10px 15px",
    fontSize: "14px",
    cursor: "pointer",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    marginTop: "20px",
    fontSize: "14px",
    color: "#5a4478",
  },
  pageButton: {
    padding: "8px 12px",
    backgroundColor: "#eae0f5",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    margin: "0 5px",
    color: "#5a4478",
  },
  noResults: {
    marginTop: "10px",
    color: "#888",
    fontSize: "14px",
    textAlign: "center",
  },
  errorText: { color: "red", marginTop: "10px" },
  navbar: {
    display: "flex",
    justifyContent: "space-around",
    width: "100%",
    position: "fixed",
    bottom: "0",
    backgroundColor: "#f8f3fb",
    padding: "10px 0",
  },
  navButton: {
    background: "none",
    border: "none",
    fontSize: "14px",
    color: "#5a4478",
    cursor: "pointer",
    fontWeight: "bold",
    padding: "6px 12px",
  },
  navButtonActive: { borderBottom: "2px solid #5a4478", paddingBottom: "4px" },
};

export default UserBarriers;

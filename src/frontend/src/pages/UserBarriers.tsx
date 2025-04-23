import { useState } from "react";
import { useNavigate } from "react-router-dom";

const UserBarriers: React.FC = () => {
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  const barriers = ["ул Ленина 5", "ул Ленина 8", "ул Ленина 10"];

  const filteredBarriers = search.toLowerCase().includes("ленина")
    ? barriers
    : [];

  const handleNavigate = (barrier: string) => {
    if (barrier === "ул Ленина 5") {
      navigate("/barrier-details");
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>User Поиск шлагбаумов</h2>
      <div style={styles.searchContainer}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.searchInput}
          placeholder="Введите название улицы..."
        />
        {search && (
          <button style={styles.clearButton} onClick={() => setSearch("")}>
            X
          </button>
        )}
      </div>
      <ul style={styles.list}>
        {filteredBarriers.map((barrier, index) => (
          <li
            key={index}
            style={styles.listItem}
            onClick={() => handleNavigate(barrier)}
          >
            {barrier} →
          </li>
        ))}
      </ul>
      <div style={styles.navbar}>
        <button style={styles.navButton} onClick={() => navigate("/barriers")}>
          Шлагбаумы
        </button>
        <button style={styles.navButton} onClick={() => navigate("/requests")}>
          Запросы
        </button>
        <button
          style={styles.navButton}
          onClick={() => navigate("/profile")}
          disabled
        >
          Профиль
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: "20px",
    backgroundColor: "#fef7fb",
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  title: {
    fontSize: "24px",
    textAlign: "center",
    marginBottom: "20px",
  },
  searchContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
    maxWidth: "400px",
    marginBottom: "15px",
  },
  searchInput: {
    flex: 1,
    padding: "10px",
    fontSize: "16px",
    border: "1px solid #ccc",
    borderRadius: "5px",
  },
  clearButton: {
    marginLeft: "10px",
    padding: "10px",
    backgroundColor: "#ccc",
    border: "none",
    borderRadius: "5px",
    cursor: "pointer",
  },
  list: {
    listStyleType: "none",
    padding: 0,
    width: "100%",
    maxWidth: "400px",
  },
  listItem: {
    padding: "15px",
    margin: "5px 0",
    backgroundColor: "#ffffff",
    borderRadius: "5px",
    cursor: "pointer",
    transition: "background 0.3s",
    border: "1px solid #ccc",
    textAlign: "center",
  },
};

export default UserBarriers;
